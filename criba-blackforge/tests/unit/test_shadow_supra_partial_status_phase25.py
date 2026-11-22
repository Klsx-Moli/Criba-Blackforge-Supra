"""F25: no per-dossier report shape may promote the whole Shadow batch."""
from __future__ import annotations

from copy import deepcopy

import pytest

from criba.ui.supra_batch_status import (
    present_batch_recovery, present_partial_diagnostics,
)

IDS = ["dossier-first-1", "dossier-first-2"]


def valid():
    return {
        "batch_id": "batch-original",
        "status": "PARTIAL_DIAGNOSTIC_ONLY",
        "reason": "NO_FULL_BATCH_PROMOTION",
        "scientific_status": "NOT_VALIDATED",
        "mechanism_execution": "NOT_EXECUTED",
        "full_batch_recorded": False,
        "expected": 2,
        "fresh_verified": 1,
        "journal_partials": 1,
        "rows": [
            {"dossier_id": IDS[0],
             "get_status": "FRESH_PLANNING_RECEIPT_VERIFIED",
             "partial_written_now": True},
            {"dossier_id": IDS[1],
             "get_status": "GET_UNAVAILABLE_UNKNOWN"},
        ],
    }


def view(report):
    return present_partial_diagnostics(
        report, batch_id="batch-original", dossier_ids=IDS,
    )


def test_truthful_partial_projection_separates_fresh_and_historical():
    summary = view(valid())
    assert "1/2 recibos actuales" in summary
    assert "1/2 parciales históricos" in summary
    assert "lote completo NO CONFIRMADO" in summary
    assert "sin reenvío POST" in summary


def test_zero_out_of_two_is_unknown_not_false_evidence():
    result = valid()
    result["fresh_verified"] = 0
    result["journal_partials"] = 0
    result["rows"][0]["get_status"] = "GET_UNAVAILABLE_UNKNOWN"
    summary = view(result)
    assert "0/2 recibos actuales" in summary
    assert "lote completo NO CONFIRMADO" in summary


def test_two_of_two_partials_still_do_not_make_batch_confirmed():
    result = valid()
    result["fresh_verified"] = 2
    result["journal_partials"] = 2
    result["rows"][1]["get_status"] = "FRESH_PLANNING_RECEIPT_VERIFIED"
    assert "lote completo NO CONFIRMADO" in view(result)
    assert present_batch_recovery(result)["state"] == "UNKNOWN"


@pytest.mark.parametrize("path, replacement", [
    (("batch_id",), "different"),
    (("status",), "READBACK_OBSERVED"),
    (("status",), None),
    (("reason",), "PERSISTED_PLANNING_RECEIPTS_ONLY"),
    (("scientific_status",), "VALIDATED"),
    (("scientific_status",), None),
    (("mechanism_execution",), "COMPLETED"),
    (("full_batch_recorded",), True),
    (("full_batch_recorded",), None),
    (("expected",), 1),
    (("expected",), True),
    (("fresh_verified",), -1),
    (("fresh_verified",), True),
    (("fresh_verified",), 2),
    (("journal_partials",), 3),
    (("journal_partials",), False),
    (("rows", 0, "dossier_id"), "other-dossier"),
    (("rows", 1, "dossier_id"), IDS[0]),
    (("rows", 1, "get_status"), "POST_NOT_SENT"),
    (("rows", 0, "get_status"), "GET_UNAVAILABLE_UNKNOWN"),
])
def test_report_mutation_cannot_paint_unknown_as_partial_fact(path, replacement):
    report = deepcopy(valid())
    target = report
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = replacement
    assert view(report) is None


def test_partial_report_cannot_be_passed_to_batch_success_presenter():
    assert present_batch_recovery(valid())["state"] == "UNKNOWN"


def test_duplicate_and_missing_dossier_sets_rejected():
    report = valid()
    assert present_partial_diagnostics(
        report, batch_id="batch-original", dossier_ids=["one", "one"],
    ) is None
    assert present_partial_diagnostics(
        report, batch_id="batch-original", dossier_ids=[],
    ) is None
    assert present_partial_diagnostics(
        report, batch_id="batch-original", dossier_ids=IDS + ["third"],
    ) is None


def test_malformed_report_not_rendered():
    for value in (None, False, "recorded", [], {"status": "UNKNOWN"}):
        assert view(value) is None
