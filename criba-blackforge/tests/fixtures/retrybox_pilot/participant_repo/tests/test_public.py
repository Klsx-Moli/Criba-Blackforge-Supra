from __future__ import annotations

import pytest

from retrybox import JobStore


def test_same_identity_same_payload_replays_without_reexecution(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    calls = {"n": 0}

    def handler(payload):
        calls["n"] += 1
        return {"value": payload["value"] * 2}

    first = store.run("job-1", {"value": 3}, handler)
    second = store.run("job-1", {"value": 3}, handler)

    assert first == {"value": 6}
    assert second == first
    assert calls["n"] == 1


def test_same_identity_different_payload_is_rejected(tmp_path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    store.run("job-1", {"value": 3}, lambda p: {"value": p["value"]})

    with pytest.raises(ValueError):
        store.run("job-1", {"value": 4}, lambda p: {"value": p["value"]})
