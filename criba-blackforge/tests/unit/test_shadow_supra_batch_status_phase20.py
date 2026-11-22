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
        "scientific_status": "NOT_VALIDATED",
        "mechanism_execution": "NOT_EXECUTED",
    }
    result.update(changes)
    return result


@pytest.mark.parametrize("changes,state", [
    ({}, "FRESH_JOURNALED"),
    ({"journal_recorded": False}, "FRESH_NOT_JOURNALED"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "GET_FAILED", "checked": 0}, "HISTORICAL_ONLY"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "READBACK_NOT_DURABLY_BOUND", "checked": 1}, "HISTORICAL_ONLY"),
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
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED"}, "UNKNOWN"),
    ({"reason": "SYNTHETIC_FRESH_SUCCESS"}, "UNKNOWN"),
    ({"reason": "JOURNAL_CONFIRMED_CONCURRENTLY",
      "journal_recorded": False}, "UNKNOWN"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "GET_FAILED", "checked": 2}, "UNKNOWN"),
    ({"reason": "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
      "fresh_get_status": "READBACK_NOT_DURABLY_BOUND",
      "checked": 2}, "UNKNOWN"),
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


@pytest.mark.parametrize("mutation", [
    {"scientific_status": "VALIDATED"},
    {"scientific_status": "PASS"},
    {"scientific_status": "UNKNOWN"},
    {"scientific_status": None},
    {"scientific_status": ""},
    {"scientific_status": 0},
    {"scientific_status": True},
    {"mechanism_execution": "COMPLETED"},
    {"mechanism_execution": "EXECUTED"},
    {"mechanism_execution": "UNKNOWN"},
    {"mechanism_execution": None},
    {"mechanism_execution": ""},
    {"mechanism_execution": False},
    {"mechanism_execution": 0},
    {"scientific_status": "VALIDATED", "mechanism_execution": "EXECUTED"},
])
def test_conflicting_epistemic_channels_never_confirm_receipt(mutation):
    forged = good(**mutation)
    state = present_batch_recovery(forged)
    assert state["state"] == "UNKNOWN"
    assert "remoto no confirmado" in state["chip"]


@pytest.mark.parametrize("missing", ["scientific_status", "mechanism_execution"])
def test_missing_epistemic_channel_is_unknown(missing):
    forged = good()
    del forged[missing]
    assert present_batch_recovery(forged)["state"] == "UNKNOWN"


@pytest.mark.parametrize("fresh, reason, checked, expected", [
    ("VERIFIED_FROM_ARTIFACT", "PERSISTED_PLANNING_RECEIPTS_ONLY", 2, 2),
    ("GET_FAILED", "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED", 0, 2),
])
def test_valid_epistemic_channels_preserve_fresh_and_historical_receipts(
    fresh, reason, checked, expected,
):
    report = good(fresh_get_status=fresh, reason=reason,
                  checked=checked, expected=expected)
    output = present_batch_recovery(report)
    assert output["state"] == (
        "FRESH_JOURNALED" if fresh == "VERIFIED_FROM_ARTIFACT"
        else "HISTORICAL_ONLY"
    )
