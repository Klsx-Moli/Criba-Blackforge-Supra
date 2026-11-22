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
            and fresh == "VERIFIED_FROM_ARTIFACT" and checked == expected):
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
            and fresh in ("GET_FAILED", "READBACK_NOT_DURABLY_BOUND")):
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
