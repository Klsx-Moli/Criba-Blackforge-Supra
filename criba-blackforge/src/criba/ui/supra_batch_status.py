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
        if not isinstance(receipt, dict):
            return False
        # Schema shape only: the journal validates these hashes against the
        # original payload. A syntactically valid hash is not independent proof.
        for name in ("criba_candidate_id", "claim_id"):
            value = receipt.get(name)
            if not isinstance(value, str) or not value or value != value.strip():
                return False
        for name in ("mechanism_version", "protocol_version", "payload_fingerprint"):
            value = receipt.get(name)
            if (not isinstance(value, str) or len(value) != 71
                    or not value.startswith("sha256:")
                    or any(c not in "0123456789abcdef" for c in value[7:])):
                return False
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



def present_partial_diagnostics(
    report: Any, *, batch_id: Any, dossier_ids: Any,
) -> str | None:
    """Show row-level GET facts without turning UNKNOWN into a batch success.

    Even 100% positive partial receipts lack the whole-batch v2 marker.
    A historical count is never a fresh GET, or proof a POST did not run.
    """
    if (not isinstance(report, dict) or not isinstance(batch_id, str)
            or report.get("batch_id") != batch_id
            or report.get("status") != "PARTIAL_DIAGNOSTIC_ONLY"
            or report.get("reason") != "NO_FULL_BATCH_PROMOTION"
            or report.get("scientific_status") != "NOT_VALIDATED"
            or report.get("mechanism_execution") != "NOT_EXECUTED"
            or report.get("full_batch_recorded") is not False):
        return None
    if (not isinstance(dossier_ids, list) or not dossier_ids
            or any(not isinstance(x, str) or not x or x != x.strip()
                   for x in dossier_ids)
            or len(set(dossier_ids)) != len(dossier_ids)):
        return None
    n = len(dossier_ids)
    fresh = report.get("fresh_verified")
    historical = report.get("journal_partials")
    if (type(report.get("expected")) is not int
            or report["expected"] != n
            or type(fresh) is not int or not 0 <= fresh <= n
            or type(historical) is not int or not 0 <= historical <= n):
        return None
    rows = report.get("rows")
    if not isinstance(rows, list) or len(rows) != n:
        return None
    allowed = {
        "GET_UNAVAILABLE_UNKNOWN", "UNBOUND_READBACK_UNKNOWN",
        "JOURNAL_WRITE_UNCONFIRMED", "FRESH_PLANNING_RECEIPT_VERIFIED",
    }
    if (any(
            not isinstance(r, dict)
            or not isinstance(r.get("get_status"), str)
            or r["get_status"] not in allowed
            or not isinstance(r.get("dossier_id"), str)
            or r["dossier_id"] not in dossier_ids
            for r in rows
    )
            or {r["dossier_id"] for r in rows} != set(dossier_ids)
            or len({r["dossier_id"] for r in rows}) != n
            or any(type(r.get("historical_partial_recorded")) is not bool
                   for r in rows)
            or sum(r["historical_partial_recorded"] is True
                   for r in rows) != historical
            or sum(r["get_status"] == "FRESH_PLANNING_RECEIPT_VERIFIED"
                   for r in rows) != fresh):
        return None
    return (
        f"diagnóstico GET: {fresh}/{n} recibos actuales de planificación; "
        f"{historical}/{n} parciales históricos en journal; "
        "resto UNKNOWN · lote completo NO CONFIRMADO · sin reenvío POST"
    )
