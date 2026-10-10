"""Banco fijo de admisión local; errores de transporte no cuentan como abstención."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable
from typing import Any

from .contrato import PROMPT_VERSION, SCHEMA_VERSION
from .puerto import InterpretationResult

CASOS: tuple[dict[str, Any], ...] = (
    {
        "id": "pertinente",
        "expected": "PROPUESTA",
        "query": (
            "Reducir la cola de atención causada por segundas visitas por errores de registro."
        ),
        "idea": {
            "method1": "Poka-Yoke",
            "method2": "Retroalimentación",
            "title": "Prevenir errores de registro antes de confirmar la cita",
        },
        "evidence": [
            {
                "title": "Registro de visitas",
                "abstract": (
                    "30 de 100 visitas se repiten por registros incompletos; aún no hay ensayo."
                ),
            }
        ],
    },
    {
        "id": "irrelevante",
        "expected": "ABSTENER",
        "query": "Demostrar un teorema de números primos usando exclusivamente una prueba formal.",
        "idea": {
            "method1": "Perfumería",
            "method2": "Marketing olfativo",
            "title": "Cambiar el aroma de la sala; sin transformación matemática permitida",
        },
        "evidence": [],
    },
    {
        "id": "contradiccion",
        "expected": "ABSTENER",
        "query": "Eliminar segundas visitas SOLO con confirmación automática de registros.",
        "idea": {
            "method1": "Confirmación automática",
            "method2": "Recordatorios",
            "title": "Confirmar sin revisar; no se permite proponer otra intervención",
        },
        "evidence": [
            {
                "title": "Ensayo controlado de la única intervención permitida",
                "abstract": "La confirmación automática aumenta retornos del 10% al 30%,"
                " incluso con recordatorios; no reduce errores.",
            }
        ],
    },
    {
        "id": "imposible",
        "expected": "ABSTENER",
        "query": "Transferir registros completos entre dos sedes.",
        "idea": {
            "method1": "Replicación",
            "method2": "Mensajería",
            "bloqueo": {
                "restricciones_obligatorias": [
                    "No transmitir ningún dato por ningún medio.",
                    "La sede receptora carece de cualquier copia y debe recibir los registros.",
                ]
            },
        },
        "evidence": [],
    },
)
BANK_VERSION = hashlib.sha256(
    json.dumps([CASOS, PROMPT_VERSION, SCHEMA_VERSION], sort_keys=True, ensure_ascii=False).encode()
).hexdigest()

Proponer = Callable[
    [str, dict[str, Any], dict[str, Any] | None, list[dict[str, Any]] | None], InterpretationResult
]


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _clasificar_error(r: InterpretationResult) -> tuple[str | None, str | None, str]:
    """Separa error TÉCNICO de error DERIVADO. El técnico nunca se sobrescribe.

    Patrones ANCLADOS al inicio del error (nunca ``in``), un error por patrón.
    El ``kind`` estructurado (``error_kind``) lo fija el validador de contrato.

    Jerarquía (BANCO-TRACE-01/04A):
      - json_invalido:               → ERROR, técnico conservado
      - salida_truncada:/truncated   → ERROR
      - timeout                      → ERROR
      - critica_no_disponible:/proposal_failed:/entrada_invalida:/transporte_http:/
        http_error_/plan_agotado/credenciales/... → ERROR, técnico conservado
      - raw_output vacía             → empty_response, ERROR
      - es propuesta                 → PASS
      - error_kind == "schema"       → schema_invalido, ERROR
      - validacion:abstencion:...    → ABSTENER (técnico None, REJECTED)
      - resto de validacion:...      → REJECTED
    """
    err = r.error or ""
    if err.startswith("json_invalido:"):
        return err, "invalid_json", "ERROR"
    if err.startswith(("salida_truncada:", "truncated_response")):
        return "truncated_response", "truncated_response", "ERROR"
    if err.startswith("timeout"):
        return "timeout", "timeout", "ERROR"
    if err.startswith(
        (
            "critica_no_disponible:",
            "proposal_failed:",
            "entrada_invalida:",
            "transporte_http:",
            "http_error_",
            "plan_agotado",
            "credenciales",
            "sin_contenido:",
            "contenido_tipo",
            "message_tipo",
            "tool_calls_sin_contenido",
            "choice_tipo",
            "configuracion_invalida",
        )
    ):
        return err, "transport_failure", "ERROR"
    raw = r.raw_output
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "empty_response", "no_interpretable_output", "ERROR"
    # JSON parseado con éxito: la forma está bien; clasifica el validador.
    if r.es_propuesta:
        return None, None, "PASS"
    if r.error_kind == "schema":
        detalle = err[len("validacion:") :] if err.startswith("validacion:") else err
        return f"schema_invalido:{detalle}", "schema_validation_failed", "ERROR"
    if err.startswith("validacion:abstencion:"):
        return None, err, "REJECTED"
    if err:
        return None, err, "REJECTED"
    return None, None, "REJECTED"


def evaluar_banco(
    proponer: Proponer,
    *,
    repeticiones: int = 2,
    referencia: Proponer | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    constrained_decoding: str = "",
) -> dict[str, Any]:
    if repeticiones < 2:
        raise ValueError("el banco exige al menos dos repeticiones")
    resultados: list[dict[str, Any]] = []
    acuerdos: list[bool] = []
    model_requests = 0
    completed = 0
    total = len(CASOS) * repeticiones
    cancelled = False
    for caso in CASOS:
        estados: list[str] = []
        mecanismos: list[set[str]] = []
        intentos: list[dict[str, Any]] = []
        for intento in range(repeticiones):
            if cancel_requested is not None and cancel_requested():
                cancelled = True
                break
            r = proponer(caso["query"], caso["idea"], None, caso["evidence"])
            completed += 1
            model_requests += r.model_requests
            technical_error, derived_error, result = _clasificar_error(r)
            provenance = r.provenance.sin_secretos() if r.provenance else {}
            latency_s = (
                round(provenance["duration_ms"] / 1000, 3)
                if isinstance(provenance.get("duration_ms"), int)
                else None
            )
            intentos.append(
                {
                    "case_id": caso["id"],
                    "resultado": r.to_campos(),
                    "raw_output": r.raw_output,
                    "technical_error": technical_error,
                    "derived_error": derived_error,
                    "result": result,
                    "provenance": provenance,
                    "finish_reason": r.finish_reason,
                    "completion_tokens": r.completion_tokens,
                    "reasoning_tokens": r.reasoning_tokens,
                    "latency_s": latency_s,
                    "cap_hit": r.finish_reason == "length",
                    "model_requests": r.model_requests,
                }
            )
            estado = (
                "PROPUESTA"
                if r.es_propuesta
                else (
                    "ABSTENER"
                    if r.pertinencia == "ABSTENER" and r.error.startswith("validacion:abstencion:")
                    else "ERROR"
                )
            )
            estados.append(estado)
            if r.es_propuesta:
                mecanismos.append(_tokens(r.mecanismo))
            if progress is not None:
                progress(
                    {
                        "phase": "bank",
                        "completed": completed,
                        "total": total,
                        "case": caso["id"],
                        "attempt": intento + 1,
                        "status": estado,
                    }
                )
        consistente = bool(estados) and len(set(estados)) == 1
        if mecanismos:
            base = mecanismos[0]
            consistente = consistente and all(
                len(base & m) / max(1, len(base | m)) >= 0.6 for m in mecanismos[1:]
            )
        correcto = bool(estados) and all(e == caso["expected"] for e in estados)
        resultados.append(
            {
                "id": caso["id"],
                "expected": caso["expected"],
                "estados": estados,
                "correcto": correcto,
                "consistente": consistente,
                "attempts": intentos,
            }
        )
        if cancel_requested is not None and cancel_requested():
            cancelled = True
        if cancelled:
            break
        if referencia:
            r = referencia(caso["query"], caso["idea"], None, caso["evidence"])
            acuerdos.append(
                (r.es_propuesta and estados[0] == "PROPUESTA")
                or (r.pertinencia == "ABSTENER" and estados[0] == "ABSTENER")
            )
    if not cancelled and cancel_requested is not None and cancel_requested():
        cancelled = True
    negativos = [r for r in resultados if r["expected"] == "ABSTENER"]
    total_negativos = sum(1 for caso in CASOS if caso["expected"] == "ABSTENER")
    return {
        "bank_version": BANK_VERSION,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "repeticiones": repeticiones,
        "constrained_decoding": constrained_decoding,
        "cancelled": cancelled,
        "completed_attempts": completed,
        "total_attempts": total,
        "passed": not cancelled and len(resultados) == len(CASOS)
        and all(r["correcto"] and r["consistente"] for r in resultados),
        "schema_response_rate": sum(e != "ERROR" for r in resultados for e in r["estados"])
        / total,
        "correct_abstention_rate": sum(r["correcto"] for r in negativos) / total_negativos,
        "consistency_rate": sum(r["consistente"] for r in resultados) / len(CASOS),
        "reference_agreement": sum(acuerdos) / len(acuerdos) if acuerdos else None,
        "reference_evaluated": bool(acuerdos),
        "model_requests": model_requests,
        "model_requests_scope": "BANK_PROPOSAL_AND_CRITIC_ONLY_EXCLUDES_REFERENCE",
        "cases": resultados,
    }
