from __future__ import annotations

import json
import sqlite3

import pytest

from criba.storage import Storage


def _insert_session(store: Storage, session_id: str = "session-1") -> None:
    with store.connect() as con:
        con.execute(
            "INSERT INTO sessions VALUES(?,?,?,?,?,?,?,?,?)",
            (
                session_id,
                "2026-09-21T00:00:00+00:00",
                "query-hash",
                "query",
                "current-1",
                "ACTIVATED",
                "{}",
                "{}",
                "[]",
            ),
        )


def test_record_decision_preserves_and_appends_evidence_across_reopen(tmp_path) -> None:
    db = tmp_path / "decisions.sqlite3"
    store = Storage(db)
    _insert_session(store)

    first = store.record_decision("session-1", "ADOPTAR", {"same": "first"})
    second = store.record_decision("session-1", "ADOPTAR", {"same": "second"})

    reopened = Storage(db).get("session-1")
    assert reopened["status"] == "ADOPTAR"
    assert [item["id"] for item in reopened["evidence"]] == [first["id"], second["id"]]
    assert [item["evidence"] for item in reopened["evidence"]] == [
        {"same": "first"},
        {"same": "second"},
    ]


def test_record_decision_accepts_empty_object_and_rejects_none(tmp_path) -> None:
    store = Storage(tmp_path / "decisions.sqlite3")
    _insert_session(store)

    entry = store.record_decision("session-1", "ADOPTAR", {})
    assert entry["evidence"] == {}

    with pytest.raises(ValueError, match="evidence"):
        store.record_decision("session-1", "ADOPTAR", None)  # type: ignore[arg-type]


def test_record_decision_rolls_back_insert_when_session_update_fails(tmp_path) -> None:
    store = Storage(tmp_path / "decisions.sqlite3")
    _insert_session(store)
    first = store.record_decision("session-1", "ADOPTAR", [{"kind": "baseline"}])

    with store.connect() as con:
        con.execute(
            """
            CREATE TRIGGER abort_session_update
            BEFORE UPDATE OF evidence_json ON sessions
            BEGIN
                SELECT RAISE(ABORT, 'forced update failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced update failure"):
        store.record_decision("session-1", "ABANDONAR", [{"kind": "new"}])

    with store.connect() as con:
        decisions = con.execute(
            "SELECT id, evidence_json FROM decisions WHERE session_id=? ORDER BY created_at",
            ("session-1",),
        ).fetchall()
        stored_evidence = json.loads(
            con.execute(
                "SELECT evidence_json FROM sessions WHERE id=?", ("session-1",)
            ).fetchone()[0]
        )

    assert [(row["id"], json.loads(row["evidence_json"])) for row in decisions] == [
        (first["id"], [{"kind": "baseline"}])
    ]
    assert [item["id"] for item in stored_evidence] == [first["id"]]

def test_record_event_preserves_session_status_and_rolls_back_atomically(tmp_path) -> None:
    store = Storage(tmp_path / "events.sqlite3")
    packet = {
        "activation_id": "activation-1",
        "timestamp": "2026-10-01T00:00:00+00:00",
        "status": "OK",
        "schema": "blackforge_headless_packet",
        "selection": {"selected_ids": ["BF-1"]},
    }
    store.save_blackforge_session(
        "bf-session",
        "query",
        packet,
        {"seed": 1},
    )

    first = store.record_event(
        "bf-session",
        "mitigation_proposed",
        {"proposal_id": "prop-1"},
    )
    reopened = store.get("bf-session")
    assert reopened["status"] == "OK"
    assert reopened["evidence"] == [first]

    with store.connect() as con:
        con.execute(
            """
            CREATE TRIGGER abort_event_evidence_update
            BEFORE UPDATE OF evidence_json ON sessions
            BEGIN
                SELECT RAISE(ABORT, 'forced event update failure');
            END
            """
        )

    with pytest.raises(sqlite3.IntegrityError, match="forced event update failure"):
        store.record_event(
            "bf-session",
            "mitigation_applied",
            {"proposal_id": "prop-1"},
        )

    with store.connect() as con:
        events = con.execute(
            "SELECT status FROM decisions WHERE session_id=? ORDER BY created_at",
            ("bf-session",),
        ).fetchall()
    assert [row["status"] for row in events] == ["mitigation_proposed"]
    assert store.get("bf-session")["evidence"] == [first]

