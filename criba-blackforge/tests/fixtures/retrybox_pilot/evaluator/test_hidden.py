from __future__ import annotations

import threading
import time

import pytest

from retrybox import JobStore


def test_restart_replay_does_not_reexecute(tmp_path) -> None:
    db = tmp_path / "jobs.sqlite3"
    calls = {"n": 0}

    def handler(payload):
        calls["n"] += 1
        return {"seen": payload["x"]}

    first = JobStore(db).run("restart-1", {"x": 9}, handler)
    second = JobStore(db).run("restart-1", {"x": 9}, handler)

    assert first == second == {"seen": 9}
    assert calls["n"] == 1


def test_distinct_ids_same_payload_are_independent(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    calls = {"n": 0}

    def handler(payload):
        calls["n"] += 1
        return {"call": calls["n"], "x": payload["x"]}

    one = store.run("a", {"x": 1}, handler)
    two = store.run("b", {"x": 1}, handler)

    assert calls["n"] == 2
    assert one["call"] != two["call"]


def test_handler_failure_does_not_create_successful_job(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    calls = {"n": 0}

    def failing(_payload):
        calls["n"] += 1
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        store.run("failure-1", {"x": 1}, failing)

    result = store.run("failure-1", {"x": 1}, lambda p: {"x": p["x"]})
    assert result == {"x": 1}
    assert calls["n"] == 1


def test_concurrent_same_identity_executes_handler_once(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    calls = {"n": 0}
    calls_lock = threading.Lock()
    barrier = threading.Barrier(2)
    results = []
    errors = []

    def handler(payload):
        with calls_lock:
            calls["n"] += 1
            call_no = calls["n"]
        time.sleep(0.08)
        return {"call": call_no, "x": payload["x"]}

    def worker():
        try:
            barrier.wait(timeout=2.0)
            results.append(store.run("race-1", {"x": 7}, handler))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3.0)

    assert not errors
    assert len(results) == 2
    assert results[0] == results[1]
    assert calls["n"] == 1


def test_concurrent_identity_collision_never_misattributes_result(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    barrier = threading.Barrier(2)
    outcomes = []

    def worker(payload):
        try:
            barrier.wait(timeout=2.0)
            result = store.run(
                "collision-1",
                payload,
                lambda p: {"source": p["source"]},
            )
            outcomes.append(("ok", payload["source"], result["source"]))
        except ValueError:
            outcomes.append(("collision", payload["source"], None))

    threads = [
        threading.Thread(target=worker, args=({"source": "A"},)),
        threading.Thread(target=worker, args=({"source": "B"},)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=3.0)

    assert len(outcomes) == 2
    oks = [item for item in outcomes if item[0] == "ok"]
    collisions = [item for item in outcomes if item[0] == "collision"]
    assert len(oks) == 1
    assert len(collisions) == 1
    assert oks[0][1] == oks[0][2]
