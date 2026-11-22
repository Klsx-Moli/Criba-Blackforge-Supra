"""Puente entre la MISMA llamada de critica de produccion y el laboratorio.

No es un tercer viaje al modelo ni un evaluador nuevo: reutiliza
``prompt_critica`` y ``validar_critica`` del contrato real.

El laboratorio (``semantic_lab``) identifica una peticion con el hash de su
propio request canonico. Este adaptador NO inventa un segundo formato de
identidad: delega en ``direct_request``/``blind_request`` del laboratorio,
de modo que no puede divergir de el. Aparte, liga el MENSAJE COMPUESTO
realmente enviado (system + user) para dejar constancia de lo que viajo.

El laboratorio exige un recibo con ``request_sha256``, ``observed_model``,
``transport_id``, ``finish_reason`` y ``body``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any

from criba.interprete.contrato import prompt_critica, validar_critica


def _system_de_produccion() -> str:
    """System prompt real de la critica, tomado del modulo de produccion."""
    from criba.interprete.openai_compatible import _SYSTEM

    return _SYSTEM


def mensaje_compuesto(prompt_critica_real: str) -> list[dict[str, str]]:
    """Reconstruye el mensaje que produccion envia de verdad.

    Debe coincidir EXACTAMENTE con lo que ``_pedir`` monta en
    ``openai_compatible``: system fijo + user con el prompt de critica.
    """
    return [
        {"role": "system", "content": _system_de_produccion()},
        {"role": "user", "content": prompt_critica_real},
    ]


def sha_mensaje_compuesto(mensajes: list[dict[str, str]]) -> str:
    """Hash canonico del mensaje compuesto enviado al modelo."""
    canonico = json.dumps(
        mensajes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(canonico.encode("utf-8")).hexdigest()


def mensaje_de_critica(
    *,
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    evidence: list[dict[str, Any]] | None,
    propuesta: dict[str, Any],
) -> list[dict[str, str]]:
    """Mensaje que produccion enviaria para esta critica concreta."""
    return mensaje_compuesto(prompt_critica(query, idea, domain, evidence, propuesta))


def request_sha_de_critica(
    trial: Any,
    *,
    reviewer: str,
    attempt: str,
    stage: str = "DIRECT",
) -> str:
    """Hash del request TAL COMO LO ENTIENDE ``semantic_lab``.

    Delega en la funcion canonica del laboratorio: si el laboratorio cambia
    su contrato, este puente lo sigue sin duplicar logica.
    """
    from benchmarks.innovation import semantic_lab

    if stage == "DIRECT":
        return semantic_lab.direct_request(trial, reviewer, attempt).sha256
    if stage == "BLIND":
        return semantic_lab.blind_request(trial, reviewer, attempt).sha256
    raise ValueError(f"stage no soportado: {stage}")


@dataclass(frozen=True)
class CritiqueCall:
    """Todo lo que el host necesita para enviar y luego verificar la critica."""

    request_sha256: str
    mensajes: list[dict[str, str]]
    message_sha256: str
    reviewer: str
    attempt: str
    stage: str


def preparar_critica(
    trial: Any,
    *,
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    evidence: list[dict[str, Any]] | None,
    propuesta: dict[str, Any],
    reviewer: str,
    attempt: str,
    stage: str = "DIRECT",
) -> CritiqueCall:
    """Prepara la llamada ligando identidad del laboratorio y mensaje real."""
    mensajes = mensaje_de_critica(
        query=query, idea=idea, domain=domain, evidence=evidence, propuesta=propuesta
    )
    return CritiqueCall(
        request_sha256=request_sha_de_critica(
            trial, reviewer=reviewer, attempt=attempt, stage=stage
        ),
        mensajes=mensajes,
        message_sha256=sha_mensaje_compuesto(mensajes),
        reviewer=reviewer,
        attempt=attempt,
        stage=stage,
    )


def build_receipt(
    *,
    request_sha256: str,
    observed_model: str,
    transport_id: str,
    finish_reason: str,
    body: dict[str, Any],
) -> str:
    """Serializa el recibo que ``semantic_lab._receipt`` espera.

    ``observed_model`` debe ser el modelo EFECTIVAMENTE observado por el
    transporte, no el solicitado. Si no coinciden, el laboratorio lo
    rechaza: un alias no acredita identidad.
    """
    if finish_reason != "stop":
        raise ValueError("el recibo exige finish_reason=stop")
    return json.dumps(
        {
            "request_sha256": request_sha256,
            "observed_model": observed_model,
            "transport_id": transport_id,
            "finish_reason": finish_reason,
            "body": body,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def validar_critica_produccion(body: dict[str, Any]) -> list[str]:
    """Aplica ``validar_critica`` real sobre el cuerpo devuelto.

    Devuelve la lista de errores del contrato. No puntua ni decide: solo
    reutiliza la fuente de verdad existente.
    """
    if not isinstance(body, dict):
        return ["body no es objeto"]
    return validar_critica(body)


def contiene_instrucciones_prompt_inyectadas(prompt: str) -> bool:
    """Senala si el prompt trae marcadores de rol que delaten inyeccion."""
    marcas = ("\nSYSTEM:", "\nUSER:", "\nASSISTANT:")
    return any(marca in prompt for marca in marcas)