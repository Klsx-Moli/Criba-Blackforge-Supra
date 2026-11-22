"""F33: SQLite writer lock spans only atomic chain-memory persistence, not JSON work."""
from __future__ import annotations

import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from criba.storage import Storage


def _prepare_store(tmp_path):
    store = Storage(tmp_path / "chain-memory.sqlite3")
    store.save_chain_session("chain-f33", "question", 1, "RUNNING")
    return store


def _rows(store):
    with store.connect() as con:
        return [
            (row["field_name"], row["field_value"])
            for row in con.execute(
                "SELECT field_name, field_value FROM chain_memory "
                "WHERE chain_id=? AND stage=? ORDER BY field_name, field_value",
                ("chain-f33", 1),
            ).fetchall()
        ]


def test_serialization_happens_before_sqlite_begin_immediate(tmp_path, monkeypatch):
    """Must fail on the prior implementation: JSON probe cannot take writer lock."""
    import criba.storage as storage_module

    store = _prepare_store(tmp_path)
    original_dumps = json.dumps
    observed = []

    def probe_dumps(value, *args, **kwargs):
        # During JSON serialization another connection must be able to
        # reserve a writer, proving no SQLite write lock has been acquired.
        with sqlite3.connect(
            store.path, timeout=0.05, isolation_level=None,
        ) as observer:
            observer.execute("PRAGMA busy_timeout=50")
            observer.execute("BEGIN IMMEDIATE")
            observer.execute("ROLLBACK")
        observed.append(True)
        return original_dumps(value, *args, **kwargs)

    monkeypatch.setattr(storage_module.json, "dumps", probe_dumps)
    payload = {"items": ["α", "β", {"deep": "ñ"}]}
    store.save_chain_memory("chain-f33", 1, {"memory": payload})

    assert observed == [True]
    assert _rows(store) == [
        ("memory", original_dumps(payload, ensure_ascii=False)),
    ]


def test_concurrent_identical_writes_still_deduplicate_atomically(tmp_path):
    store = _prepare_store(tmp_path)
    value = {"payload": ["α", "β", 2]}

    def write(_index):
        store.save_chain_memory("chain-f33", 1, {"memory": value})

    with ThreadPoolExecutor(max_workers=4) as workers:
        list(workers.map(write, range(12)))

    assert _rows(store) == [
        ("memory", json.dumps(value, ensure_ascii=False)),
    ]


def test_bad_later_json_value_never_causes_partial_chain_memory_write(tmp_path):
    store = _prepare_store(tmp_path)
    store.save_chain_memory("chain-f33", 1, {"existing": "kept"})

    with pytest.raises(TypeError):
        store.save_chain_memory(
            "chain-f33",
            1,
            {"first": {"serializable": True}, "later": {"bad": object()}},
        )

    assert _rows(store) == [("existing", "kept")]


def test_distinct_field_values_preserve_original_dedup_semantics(tmp_path):
    store = _prepare_store(tmp_path)
    store.save_chain_memory(
        "chain-f33", 1,
        {"nested": {"n": 1}, "plain": None, "repeated": [1, 2]},
    )
    store.save_chain_memory(
        "chain-f33", 1,
        {"nested": {"n": 2}, "plain": None, "repeated": [1, 2]},
    )

    assert _rows(store) == [
        ("nested", '{"n": 1}'),
        ("nested", '{"n": 2}'),
        ("plain", "None"),
        ("repeated", "[1, 2]"),
    ]
