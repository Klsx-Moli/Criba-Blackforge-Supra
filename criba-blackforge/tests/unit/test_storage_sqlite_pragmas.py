from __future__ import annotations

import sqlite3

import pytest

from criba.storage import SCHEMA_VERSION, Storage


def _pragmas(store: Storage) -> tuple[int, str, int]:
    with store.connect() as con:
        foreign_keys = int(con.execute("PRAGMA foreign_keys").fetchone()[0])
        journal_mode = str(con.execute("PRAGMA journal_mode").fetchone()[0]).lower()
        user_version = int(con.execute("PRAGMA user_version").fetchone()[0])
    return foreign_keys, journal_mode, user_version


def test_sqlite_pragmas_are_active_for_new_db_and_reopen(tmp_path) -> None:
    db = tmp_path / "storage.sqlite3"
    first = Storage(db)
    assert _pragmas(first) == (1, "wal", SCHEMA_VERSION)

    reopened = Storage(db)
    assert _pragmas(reopened) == (1, "wal", SCHEMA_VERSION)


def test_existing_version_zero_db_is_migrated_without_losing_data(tmp_path) -> None:
    db = tmp_path / "legacy.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE legacy_marker(value TEXT NOT NULL)")
        con.execute("INSERT INTO legacy_marker VALUES ('preserve-me')")
        assert con.execute("PRAGMA user_version").fetchone()[0] == 0

    store = Storage(db)
    assert _pragmas(store) == (1, "wal", SCHEMA_VERSION)
    with store.connect() as con:
        assert con.execute("SELECT value FROM legacy_marker").fetchone()[0] == "preserve-me"
        session_columns = {
            row[1] for row in con.execute("PRAGMA table_info(sessions)").fetchall()
        }
    assert "evidence_json" in session_columns


def test_foreign_key_violation_is_enforced_on_real_operation(tmp_path) -> None:
    store = Storage(tmp_path / "foreign-keys.sqlite3")

    with pytest.raises(sqlite3.IntegrityError):
        with store.connect() as con:
            con.execute(
                "INSERT INTO decisions VALUES(?,?,?,?,?,?)",
                ("decision-1", "missing-session", "now", "ADOPTAR", "[]", ""),
            )

    with store.connect() as con:
        assert con.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0


def test_newer_schema_version_fails_closed(tmp_path) -> None:
    db = tmp_path / "future.sqlite3"
    with sqlite3.connect(db) as con:
        con.execute(f"PRAGMA user_version = {SCHEMA_VERSION + 1}")

    with pytest.raises(RuntimeError, match="más nueva"):
        Storage(db)
