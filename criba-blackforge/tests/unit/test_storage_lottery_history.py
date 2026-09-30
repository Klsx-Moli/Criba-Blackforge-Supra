from __future__ import annotations

from datetime import datetime, timezone

from criba.storage import Storage


def _canonical(pair: tuple[str, str]) -> tuple[str, str]:
    first, second = sorted(pair)
    return first, second


def test_save_lottery_combinations_counts_only_new_rows(tmp_path) -> None:
    store = Storage(tmp_path / "history.sqlite3")
    batch = [("a", "b"), ("a", "b"), ("c", "d")]

    assert store.save_lottery_combinations("fp", batch, run_id="r1") == 2
    assert store.save_lottery_combinations("fp", batch, run_id="r2") == 0
    assert store.load_used_lottery_combinations("fp") == {("a", "b"), ("c", "d")}


def test_combo_keys_round_trip_ids_containing_legacy_delimiter(tmp_path) -> None:
    store = Storage(tmp_path / "history.sqlite3")
    pairs = [("alpha::inner", "beta"), ("gamma", "delta::inner")]
    expected = {_canonical(pair) for pair in pairs}

    assert store.save_lottery_combinations("fp", pairs, run_id="r1") == 2
    assert store.load_used_lottery_combinations("fp") == expected
    assert set(store.load_combination_first_seen("fp")) == expected


def test_unambiguous_legacy_combo_key_remains_readable_and_deduplicated(tmp_path) -> None:
    store = Storage(tmp_path / "history.sqlite3")
    now = datetime.now(timezone.utc).isoformat()
    con = store.connect()
    try:
        with con:
            con.execute(
                "INSERT INTO lottery_used_combinations VALUES(?,?,?,?,?,?)",
                ("fp", "legacy-a::legacy-b", now, "old-run", "alternating", 7),
            )
    finally:
        con.close()

    assert store.load_used_lottery_combinations("fp") == {("legacy-a", "legacy-b")}
    assert store.load_combination_first_seen("fp") == {("legacy-a", "legacy-b"): now}
    assert store.save_lottery_combinations(
        "fp", [("legacy-b", "legacy-a")], run_id="new-run"
    ) == 0
