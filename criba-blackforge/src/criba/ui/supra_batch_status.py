"""Truthful, headless Shadow UI projection of a batch GET reconciliation report.

This is presentation only, never an execution or persistence authority.
UNKNOWN and missing fields must not silently become a success.
"""
from __future__ import annotations

from typing import Any


def present_batch_recovery(report: Any) -> dict[str, str]:
    """Bound UI language to persisted planning receipts, not mechanism success."""
    baseline = {
        "state": "UNKNOWN",
        "chip": "SUPRA · remoto no confirmado",
        "summary": (
            "Lote SUPRA: resultado remoto UNKNOWN; no hay GET actual y journal "
            "comprobados conjuntamente · evidencia científica NO VALIDADA · "
            "mecanismo CRIBA NO EJECUTADO"
        ),
        "fresh_get_status": "UNKNOWN",
    }
    if not isinstance(report, dict):
        return baseline
    # The reconciler explicitly preserves these epistemic channels.
    # A contradictory or partial transport object has no authority to label
    # a receipt verified, even if it copies the expected counters/reason.
    if (report.get("scientific_status") != "NOT_VALIDATED"
            or report.get("mechanism_execution") != "NOT_EXECUTED"):
        return baseline
    status = report.get("status")
    fresh = report.get("fresh_get_status")
    reason = report.get("reason")
    recorded = report.get("journal_recorded") is True
    checked = report.get("checked")
    expected = report.get("expected")
    valid_counts = (
        type(checked) is int and type(expected) is int
        and expected > 0 and 0 <= checked <= expected
    )
    if (status == "READBACK_OBSERVED" and valid_counts
            and fresh == "VERIFIED_FROM_ARTIFACT" and checked == expected
            and reason in ("PERSISTED_PLANNING_RECEIPTS_ONLY",
                           "JOURNAL_CONFIRMED_CONCURRENTLY")
            and (recorded or reason != "JOURNAL_CONFIRMED_CONCURRENTLY")):
        if recorded:
            return {
                "state": "FRESH_JOURNALED",
                "chip": "SUPRA · recibo GET confirmado",
                "summary": (
                    f"Lote SUPRA: GET actual verificado {checked}/{expected} · "
                    "recibos de planificación registrados en journal · "
                    "evidencia científica NO VALIDADA · mecanismo CRIBA NO EJECUTADO"
                ),
                "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
            }
        return {
            "state": "FRESH_NOT_JOURNALED",
            "chip": "SUPRA · GET sin registro local",
            "summary": (
                f"Lote SUPRA: GET actual verificado {checked}/{expected}, pero "
                "registro local NO CONFIRMADO · evidencia científica NO VALIDADA · "
                "mecanismo CRIBA NO EJECUTADO"
            ),
            "fresh_get_status": "VERIFIED_FROM_ARTIFACT",
        }
    if (status == "READBACK_OBSERVED" and recorded and valid_counts
            and reason == "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED"
            and fresh in ("GET_FAILED", "READBACK_NOT_DURABLY_BOUND")
            and checked < expected):
        return {
            "state": "HISTORICAL_ONLY",
            "chip": "SUPRA · recibo histórico",
            "summary": (
                "Lote SUPRA: recibo de planificación HISTÓRICO preservado; "
                "GET actual NO CONFIRMADO · evidencia científica NO VALIDADA · "
                "mecanismo CRIBA NO EJECUTADO"
            ),
            "fresh_get_status": fresh,
        }
    return baseline



def submitted_batch_receipt_valid(
    report: Any, dossier_ids: Any, batch_id: Any,
) -> bool:
    """Verify the worker-to-Shadow *presentation* contract.

    This is defense-in-depth, not a substitute for the underlying fsynced
    journal. The actual producer must only return journal_recorded=True after
    successful v2 receipt persistence. This function refuses conflicting
    execution/scientific/status-source fields even with that flag set.
    """
    if (not isinstance(report, dict) or not isinstance(batch_id, str)
            or not batch_id or report.get("batch_id") != batch_id
            or report.get("journal_recorded") is not True):
        return False
    if (not isinstance(dossier_ids, list) or not dossier_ids
            or any(not isinstance(x, str) or not x or x.strip() != x
                   for x in dossier_ids)
            or len(set(dossier_ids)) != len(dossier_ids)):
        return False
    runs = report.get("runs")
    if not isinstance(runs, list) or len(runs) != len(dossier_ids):
        return False
    seen: set[str] = set()
    for run in runs:
        if not isinstance(run, dict):
            return False
        identity = run.get("dossier_id")
        if not isinstance(identity, str) or identity not in dossier_ids or identity in seen:
            return False
        seen.add(identity)
        read = run.get("read")
        if not isinstance(read, dict):
            return False
        receipt = read.get("receipt")
        if (not isinstance(receipt, dict)
                or receipt.get("criba_dossier_id") != identity
                or receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
                or receipt.get("integration_version") != "criba-supra/1"
                or receipt.get("execution_status") != "NOT_EXECUTED"
                or receipt.get("scientific_status") != "NOT_VALIDATED"
                or read.get("status_source") != "PERSISTED_STATE"
                or read.get("persisted_artifact_status") != "VERIFIED_FROM_ARTIFACT"
                or read.get("scientific_status") != "NOT_VALIDATED"
                or read.get("criba_mechanism_execution_status") != "NOT_EXECUTED"
                or read.get("criba_planning_receipt_status")
                   != "PRESERVED_NOT_EXECUTED"
                or run.get("scientific_status") != "NOT_VALIDATED"
                or run.get("criba_mechanism_execution_status") != "NOT_EXECUTED"):
            return False
    return seen == set(dossier_ids)
