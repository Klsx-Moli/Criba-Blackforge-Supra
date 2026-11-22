"""F20: UI language never promotes historical or UNKNOWN to fresh success.

Pure presentation contract; no PySide6, files, network, POST or model calls.
"""
from __future__ import annotations

import pytest

from criba.ui.supra_batch_status import present_batch_recovery


def good(**changes):
    result = {
        "status": "READBACK_OBSERVED",
        "reason": "PERSISTED_PLANNING_RECEIPTS_ONLY",
        "checked": 2,
        "expected": 2,
        "journal_recorded": True,
        "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
    }
    result.update(changes)
    return result


@pytest.mark.parametrize("changes,state", [
    ({}, "FRESH_JOURNALED"),
    ({"journal_recorded": False}, "FRESH_NOT_JOURNALED"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "GET_FAILED"}, "HISTORICAL_ONLY"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "READBACK_NOT_DURABLY_BOUND"}, "HISTORICAL_ONLY"),
    ({"status": "UNKNOWN"}, "UNKNOWN"),
    ({"journal_recorded": None}, "FRESH_NOT_JOURNALED"),
    ({"checked": 1}, "UNKNOWN"),
    ({"expected": 0}, "UNKNOWN"),
    ({"checked": True}, "UNKNOWN"),
    ({"expected": True}, "UNKNOWN"),
    ({"checked": -1}, "UNKNOWN"),
    ({"expected": -1}, "UNKNOWN"),
    ({"status": "READBACK_OBSERVED", "fresh_get_status": None}, "UNKNOWN"),
    ({"fresh_get_status": "GET_FAILED"}, "UNKNOWN"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "GET_FAILED", "journal_recorded": False}, "UNKNOWN"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "VERIFIED_FROM_ARTIFACT", "checked": 1}, "UNKNOWN"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "REMOTE_VALIDATED"}, "UNKNOWN"),
])
def test_status_projection_is_strict(changes, state):
    projected = present_batch_recovery(good(**changes))
    assert projected["state"] == state
    assert "NO VALIDADA" in projected["summary"]
    assert "NO EJECUTADO" in projected["summary"]
    assert "VALIDADO" not in projected["chip"]
    assert "ejecutado" not in projected["chip"].lower()


@pytest.mark.parametrize("value", [
    None, [], {}, "PASS", True, 1, {"status": "COMPLETED"},
])
def test_invalid_result_cannot_promote(value):
    assert present_batch_recovery(value)["state"] == "UNKNOWN"
