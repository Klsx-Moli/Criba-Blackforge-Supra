"""Minimal, conservative guards for archival and SUPRA-bound interpreted entries.

This verifies *declared structure and state*, not scientific merit, provenance
of model calls, novelty, or experimental success. Historical records remain
readable, but an unverified record is never silently completed for SUPRA.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

_PROTOCOL_FIELDS = (
    "metrica", "baseline", "umbral", "condicion_fracaso",
    "alternativa_explicativa", "resultado_favorable_mecanismo",
    "resultado_favorable_alternativa",
)


def errores_entrada_interpretada(entry: Any, *, para_supra: bool = False) -> list[str]:
    """Fail closed on contradictory state; stricter factual fields for SUPRA.

    A valid record is still only a *proposed* mechanism, not evidence or PASS.
    """
    if not isinstance(entry, Mapping):
        return ["entrada_no_es_objeto"]
    errors: list[str] = []
    if entry.get("estado_interpretacion") != "PROPUESTA":
        errors.append("estado_interpretacion_no_es_PROPUESTA")
    for name in ("hipotesis", "mecanismo"):
        v = entry.get(name)
        if not isinstance(v, str) or not v.strip():
            errors.append(f"campo_no_declarado:{name}")
    err = entry.get("interpretacion_error", "")
    if not isinstance(err, str) or err.strip():
        errors.append("interpretacion_con_error")
    result = entry.get("interprete_result")
    if result is not None:
        if (not isinstance(result, Mapping) or result.get("estado") != "PROPUESTA"
                or result.get("error") != ""):
            errors.append("resultado_interno_inconsistente")
    if not para_supra:
        return errors
    for name in ("candidate_id", "prueba_concreta"):
        v = entry.get(name)
        if not isinstance(v, str) or not v.strip() or v != v.strip():
            errors.append(f"campo_no_declarado:{name}")
    protocol = entry.get("prueba")
    if not isinstance(protocol, Mapping):
        errors.append("prueba_no_declarada")
    else:
        for name in _PROTOCOL_FIELDS:
            v = protocol.get(name)
            if not isinstance(v, str) or not v.strip():
                errors.append(f"prueba_sin:{name}")
    criticism = entry.get("critica")
    if isinstance(criticism, Mapping) and criticism.get("evaluation_status") not in (
        None, "", "CRITIQUED"
    ):
        errors.append("critica_no_acreditada")
    return errors


def exigir_entrada_interpretada(entry: Any, *, para_supra: bool = False) -> None:
    errors = errores_entrada_interpretada(entry, para_supra=para_supra)
    if errors:
        raise ValueError("entrada interpretada no aceptable: " + ", ".join(errors))


def propuestas_para_supra(entries: Any) -> list[dict[str, Any]]:
    """Preflight the *whole* batch before any dossier write or worker start.

    Pending entries may coexist and are skipped; a mislabeled PROPUESTA aborts
    the batch rather than silently disappearing or partially exporting it.
    """
    if not isinstance(entries, list):
        raise ValueError("lote de propuestas no es una lista")
    proposals: list[dict[str, Any]] = []
    seen_candidates: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"entrada {index} no es un objeto")
        state = entry.get("estado_interpretacion")
        if state == "PENDIENTE_INTERPRETACION":
            continue
        if state != "PROPUESTA":
            raise ValueError(f"entrada {index}: estado no admitido ({state!r})")
        try:
            exigir_entrada_interpretada(entry, para_supra=True)
        except ValueError as exc:
            raise ValueError(f"entrada {index}: {exc}") from exc
        candidate = entry["candidate_id"]
        if candidate in seen_candidates:
            raise ValueError(f"entrada {index}: candidate_id repetido")
        seen_candidates.add(candidate)
        proposals.append(entry)
    return proposals
