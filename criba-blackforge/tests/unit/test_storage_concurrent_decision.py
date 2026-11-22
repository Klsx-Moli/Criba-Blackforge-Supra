"""Deterministic real SQLite interleavings: session mirror must not lose evidence."""
from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event, local

import pytest

from criba.storage import Storage


def _seed(store):
    con = store.connect()
    try:
        with con:
            con.execute(
                "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    "s", "2026-09-21T00:00:00+00:00", "h", "query", "c", "ACTIVATED",
                    "{}", "{}", "[]",
                ),
            )
    finally:
        con.close()


def _interleave(store, monkeypatch, operations):
    """Let the first read old state; schedule the second at its lock/read boundary.

    SQLite itself executes all SQL and transactions on separate connections.
    Event gates control scheduling only, not SQL values or commit outcomes.
    """
    first_read, second_ready, first_done = Event(), Event(), Event()
    role = local()
    connect = store.connect

    class Cursor:
        def __init__(self, inner, worker, immediate):
            self.inner = inner
            self.worker = worker
            self.immediate = immediate

        def fetchone(self):
            row = self.inner.fetchone()
            if self.worker == 0:
                first_read.set()
                assert second_ready.wait(10), "second writer failed to reach boundary"
            elif not self.immediate:
                second_ready.set()
                assert first_done.wait(10), "first writer failed to finish"
            return row

    class Connection:
        def __init__(self, inner, worker):
            self.inner = inner
            self.worker = worker
            self.immediate = False

        def __enter__(self):
            self.inner.__enter__()
            return self

        def __exit__(self, *args):
            return self.inner.__exit__(*args)

        def __getattr__(self, key):
            return getattr(self.inner, key)

        def execute(self, sql, *args):
            normalized = " ".join(sql.upper().split())
            if normalized == "BEGIN IMMEDIATE":
                self.immediate = True
                if self.worker == 1:
                    # Signal before the real SQLite call blocks waiting for writer 0.
                    second_ready.set()
            cursor = self.inner.execute(sql, *args)
            if normalized.startswith("SELECT EVIDENCE_JSON FROM SESSIONS WHERE ID="):
                return Cursor(cursor, self.worker, self.immediate)
            return cursor

    def wrapped_connect():
        return Connection(connect(), role.worker)

    def run(worker):
        role.worker = worker
        if worker == 1:
            assert first_read.wait(10), "first writer failed to read"
        try:
            if operations[worker] == "event":
                return store.record_event("s", "mitigation_proposed", {"writer": worker})
            status = "ADOPTAR" if worker == 0 else "AMPLIAR PRUEBA"
            return store.record_decision("s", status, {"writer": worker})
        finally:
            if worker == 0:
                first_done.set()

    with monkeypatch.context() as mp:
        mp.setattr(store, "connect", wrapped_connect)
        with ThreadPoolExecutor(max_workers=2) as pool:
            left, right = pool.submit(run, 0), pool.submit(run, 1)
            return left.result(timeout=20), right.result(timeout=20)


@pytest.mark.parametrize(
    "operations",
    [("decision", "decision"), ("decision", "event"),
     ("event", "decision"), ("event", "event")],
)
def test_concurrent_evidence_append_preserves_both_returned_ids(
    tmp_path, monkeypatch, operations
):
    db = tmp_path / "race.sqlite3"
    store = Storage(db)
    _seed(store)
    left, right = _interleave(store, monkeypatch, operations)
    con = Storage(db).connect()
    try:
        session = con.execute("SELECT status,evidence_json FROM sessions WHERE id='s'").fetchone()
        evidence = json.loads(session["evidence_json"])
        rows = con.execute("SELECT id FROM decisions WHERE session_id='s'").fetchall()
    finally:
        con.close()
    # The API returned two successful IDs. Both must survive in the session projection.
    assert [entry["id"] for entry in evidence] == [left["id"], right["id"]]
    assert {row["id"] for row in rows} == {
        entry["id"]
        for operation, entry in zip(operations, (left, right), strict=True)
        if operation == "decision"
    }
    assert [entry["evidence"] for entry in evidence] == [{"writer": 0}, {"writer": 1}]
    expected_status = (
        "AMPLIAR PRUEBA" if operations[1] == "decision"
        else "ADOPTAR" if operations[0] == "decision" else "ACTIVATED"
    )
    assert session["status"] == expected_status


def test_rollback_and_reopen_after_forced_update_failure(tmp_path):
    db = tmp_path / "rollback.sqlite3"
    store = Storage(db)
    _seed(store)
    first = store.record_decision("s", "ADOPTAR", {"old": 1})
    con = store.connect()
    try:
        with con:
            con.execute(
                "CREATE TRIGGER fail_update BEFORE UPDATE OF evidence_json ON sessions "
                "BEGIN SELECT RAISE(ABORT, 'fault'); END"
            )
    finally:
        con.close()
    with pytest.raises(sqlite3.IntegrityError, match="fault"):
        store.record_decision("s", "ABANDONAR", {"new": 1})
    store = Storage(db)
    assert store.get("s")["evidence"] == [first]
    con = store.connect()
    try:
        assert con.execute("SELECT id FROM decisions").fetchone()[0] == first["id"]
        assert con.execute("SELECT count(*) FROM decisions").fetchone()[0] == 1
        with con:
            con.execute("DROP TRIGGER fail_update")
    finally:
        con.close()
    second = store.record_decision("s", "ABANDONAR", {"new": 1})
    assert Storage(db).get("s")["evidence"] == [first, second]


def test_real_concurrent_append(tmp_path):
    db = tmp_path / "stress.sqlite3"
    store = Storage(db)
    _seed(store)
    with ThreadPoolExecutor(max_workers=4) as ex:
        result = list(
            ex.map(lambda i: store.record_decision("s", "ADOPTAR", {"i": i}), range(64))
        )
    reopened = Storage(db).get("s")
    assert {e["id"] for e in reopened["evidence"]} == {r["id"] for r in result}
    assert len(reopened["evidence"]) == 64


def test_bad_evidence_rolls_back_and_releases(tmp_path):
    db = tmp_path / "bad.sqlite3"
    store = Storage(db)
    _seed(store)
    with pytest.raises(TypeError):
        store.record_decision("s", "ADOPTAR", {"bad": object()})
    assert store.get("s")["evidence"] == []
    with pytest.raises(ValueError):
        store.record_decision("missing", "ADOPTAR", {})
    store.record_decision("s", "ADOPTAR", {})
    assert len(Storage(db).get("s")["evidence"]) == 1
