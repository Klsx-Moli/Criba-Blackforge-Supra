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


def evaluar_banco(
    proponer: Proponer, *, repeticiones: int = 2, referencia: Proponer | None = None
) -> dict[str, Any]:
    if repeticiones < 2:
        raise ValueError("el banco exige al menos dos repeticiones")
    resultados: list[dict[str, Any]] = []
    acuerdos: list[bool] = []
    model_requests = 0
    for caso in CASOS:
        estados: list[str] = []
        mecanismos: list[set[str]] = []
        intentos: list[dict[str, Any]] = []
        for _ in range(repeticiones):
            r = proponer(caso["query"], caso["idea"], None, caso["evidence"])
            model_requests += r.model_requests
            intentos.append(
                {
                    "resultado": r.to_campos(),
                    "raw_output": r.raw_output,
                    "provenance": r.provenance.sin_secretos() if r.provenance else {},
                    "finish_reason": r.finish_reason,
                    "completion_tokens": r.completion_tokens,
                    "reasoning_tokens": r.reasoning_tokens,
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
        consistente = len(set(estados)) == 1
        if mecanismos:
            base = mecanismos[0]
            consistente = consistente and all(
                len(base & m) / max(1, len(base | m)) >= 0.6 for m in mecanismos[1:]
            )
        correcto = all(e == caso["expected"] for e in estados)
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
        if referencia:
            r = referencia(caso["query"], caso["idea"], None, caso["evidence"])
            acuerdos.append(
                (r.es_propuesta and estados[0] == "PROPUESTA")
                or (r.pertinencia == "ABSTENER" and estados[0] == "ABSTENER")
            )
    negativos = [r for r in resultados if r["expected"] == "ABSTENER"]
    return {
        "bank_version": BANK_VERSION,
        "prompt_version": PROMPT_VERSION,
        "schema_version": SCHEMA_VERSION,
        "repeticiones": repeticiones,
        "passed": all(r["correcto"] and r["consistente"] for r in resultados),
        "schema_response_rate": sum(e != "ERROR" for r in resultados for e in r["estados"])
        / (len(CASOS) * repeticiones),
        "correct_abstention_rate": sum(r["correcto"] for r in negativos) / len(negativos),
        "consistency_rate": sum(r["consistente"] for r in resultados) / len(CASOS),
        "reference_agreement": sum(acuerdos) / len(acuerdos) if acuerdos else None,
        "reference_evaluated": bool(acuerdos),
        "model_requests": model_requests,
        "model_requests_scope": "BANK_PROPOSAL_AND_CRITIC_ONLY_EXCLUDES_REFERENCE",
        "cases": resultados,
    }
