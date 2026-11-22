"""F20: active Shadow dossier-batch recovery uses GET only, never second POST.

Qt is required to import production actions. Workers are queued doubles:
the tests do not open a GUI event loop, perform HTTP, or call a model.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from criba.ui import actions
from test_shadow_supra_stale_callback_phase09 import harness, sheet, window


def _queued_recovery(harness):
    workers, errors = harness
    win = window(sheet("f20", "one"))
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1
    workers[0].signals.fail.emit("synthetic timeout")
    assert win._supra_submission_token is None
    assert len(errors) == 1
    actions.on_desarrollar_supra(win)
    assert len(workers) == 2
    return win, workers, errors


def _result(win, *, status="READBACK_OBSERVED",
            reason="PERSISTED_PLANNING_RECEIPTS_ONLY",
            fresh="VERIFIED_FROM_ARTIFACT", recorded=True):
    return {
        "batch_id": win.invent_sheet["dossier_batch_id"],
        "status": status, "reason": reason, "fresh_get_status": fresh,
        "checked": 1 if fresh == "VERIFIED_FROM_ARTIFACT" else 0,
        "expected": 1, "journal_recorded": recorded,
        "scientific_status": "NOT_VALIDATED",
        "mechanism_execution": "NOT_EXECUTED",
    }


def test_second_click_after_failed_submission_is_get_only(harness, monkeypatch):
    win, workers, _ = _queued_recovery(harness)
    calls = []
    monkeypatch.setattr(
        actions, "_reconciliar_lote_supra_get",
        lambda batch_id: calls.append(("GET_ONLY", batch_id))
        or _result(win, status="UNKNOWN", reason="GET_FAILED", fresh=None,
                   recorded=False),
    )
    monkeypatch.setattr(
        actions, "_execute_supra_dossiers",
        lambda *args, **kwargs: pytest.fail("second POST forbidden"),
    )
    result = workers[1].fn()
    assert calls == [("GET_ONLY", win.invent_sheet["dossier_batch_id"])]
    workers[1].signals.done.emit(result)
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"
    assert "NO VALIDADA" in win.refs["ideaSummary"].text
    assert "NO EJECUTADO" in win.refs["ideaSummary"].text


def test_historical_only_result_does_not_claim_fresh_get(harness):
    win, workers, _ = _queued_recovery(harness)
    result = _result(
        win, reason="PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED",
        fresh="GET_FAILED",
    )
    workers[1].signals.done.emit(result)
    assert win.invent_sheet["dossier_recovery_view_state"] == "HISTORICAL_ONLY"
    assert win.invent_sheet["dossier_remote_state"] == "READBACK_OBSERVED"
    assert "HISTÓRICO" in win.refs["ideaSummary"].text
    assert "GET actual NO CONFIRMADO" in win.refs["ideaSummary"].text
    assert "recibo histórico" in win.refs["ideaEstadoChip"].text


def test_exact_batch_get_accepted_but_no_scientific_promotion(harness):
    win, workers, _ = _queued_recovery(harness)
    workers[1].signals.done.emit(_result(win))
    assert win.invent_sheet["dossier_recovery_view_state"] == "FRESH_JOURNALED"
    assert win.invent_sheet["dossier_fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert "GET actual verificado" in win.refs["ideaSummary"].text
    assert "NO VALIDADA" in win.refs["ideaSummary"].text
    assert "NO EJECUTADO" in win.refs["ideaSummary"].text


def test_response_for_other_batch_is_unknown(harness):
    win, workers, _ = _queued_recovery(harness)
    reply = _result(win)
    reply["batch_id"] = "batch-other"
    workers[1].signals.done.emit(reply)
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    assert "remoto no confirmado" in win.refs["ideaEstadoChip"].text


def test_second_click_while_get_running_does_not_duplicate_worker(harness):
    win, workers, _ = _queued_recovery(harness)
    actions.on_desarrollar_supra(win)
    assert len(workers) == 2
    workers[1].signals.done.emit(_result(win))


def test_get_response_after_replacing_sheet_is_silent(harness):
    win, workers, errors = _queued_recovery(harness)
    old = win.invent_sheet
    new = sheet("another", "another")
    win.invent_sheet = new
    before = win.refs["ideaSummary"].text
    workers[1].signals.done.emit(_result_for_batch(old))
    assert win.refs["ideaSummary"].text == before
    assert "dossier_recovery_view_state" not in old
    assert "dossier_recovery_view_state" not in new
    assert win._supra_batch_recovery_token is None
    assert len(errors) == 1


def _result_for_batch(old):
    return {
        "batch_id": old["dossier_batch_id"],
        "status": "READBACK_OBSERVED",
        "reason": "PERSISTED_PLANNING_RECEIPTS_ONLY",
        "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
        "checked": 1, "expected": 1, "journal_recorded": True,
    }


def test_stale_get_failure_cannot_show_error_on_new_sheet(harness):
    win, workers, errors = _queued_recovery(harness)
    win.invent_sheet = sheet("other", "other")
    workers[1].signals.fail.emit("old GET timeout")
    assert len(errors) == 1
    assert win._supra_batch_recovery_token is None


def test_new_latest_restore_invalidates_old_batch_get(harness):
    win, workers, _ = _queued_recovery(harness)
    actions.on_restore_latest_supra(win)
    assert len(workers) == 3
    before = win.refs["ideaSummary"].text
    workers[1].signals.done.emit(_result(win))
    assert win.refs["ideaSummary"].text == before
    assert "dossier_recovery_view_state" not in win.invent_sheet


def test_unjournaled_post_worker_callback_never_promotes(harness):
    workers, _ = harness
    win = window(sheet("no-ack", "one"))
    actions.on_desarrollar_supra(win)
    workers[0].signals.done.emit({
        "runs": [{"dossier_id": "dossier-one",
                  "read": {"status_source": "PERSISTED_STATE"},
                  "completion_status": "COMPLETED",
                  "criba_mechanism_execution_status": "NOT_EXECUTED"}]
    })
    assert "supra_runs" not in win.invent_sheet
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    assert "SIN RECIBO" in win.refs["ideaSummary"].text
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"


def test_current_failure_is_pending_not_completed(harness):
    win, workers, errors = _queued_recovery(harness)
    workers[1].signals.fail.emit("synthetic GET crash")
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"
    assert win.invent_sheet["dossier_fresh_get_status"] == "GET_FAILED"
    assert "remoto no confirmado" in win.refs["ideaEstadoChip"].text
    assert len(errors) == 2


def test_get_only_entrypoint_imports_reconciliation_not_post(monkeypatch):
    from criba import dossier_batch_recovery as recovery
    from criba import integrations
    calls = []

    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def run_project(self, **kwargs):
            pytest.fail("POST forbidden")

        def list_projects(self, **kwargs):
            pytest.fail("LIST-latest cannot replace exact batch GET")

    monkeypatch.setattr(integrations, "SupraClient", Client)
    monkeypatch.setattr(
        recovery, "reconciliar_lote_por_get",
        lambda batch_id, client: calls.append((batch_id, client)) or
        {"batch_id": batch_id, "status": "UNKNOWN"},
    )
    assert actions._reconciliar_lote_supra_get("batch-known")["batch_id"] == "batch-known"
    assert len(calls) == 1 and calls[0][0] == "batch-known"
    assert isinstance(calls[0][1], Client)
