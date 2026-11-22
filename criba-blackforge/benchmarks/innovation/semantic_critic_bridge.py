"""Experimental bridge between production critique and semantic lab.

The production critic and lab use DIFFERENT prompts. An old call object
could combine the lab request SHA with the unrelated production message SHA.
preparar_critica now fails closed until the host uses a genuinely bound
request. No production wiring, extra inference, or adjudication is enabled.
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
    """Canonical laboratory request hash, NOT a hash of the production message.

    Only preparar_critica checks whether these prompts actually correspond.
    """
    return _solicitud_laboratorio(trial, reviewer, attempt, stage).sha256


def _solicitud_laboratorio(trial: Any, reviewer: str, attempt: str, stage: str) -> Any:
    """Single canonical source for what the receipt claims was sent."""
    from benchmarks.innovation import semantic_lab

    if stage == "DIRECT":
        return semantic_lab.direct_request(trial, reviewer, attempt)
    if stage == "BLIND":
        return semantic_lab.blind_request(trial, reviewer, attempt)
    raise ValueError(f"stage no soportado: {stage}")


@dataclass(frozen=True)
class CritiqueCall:
    """Todo lo que el host necesita para enviar y luego verificar la critica."""

    request_sha256: str
    _mensajes_json: str
    message_sha256: str
    reviewer: str
    attempt: str
    stage: str

    @property
    def mensajes(self) -> list[dict[str, str]]:
        """Return a fresh copy; do not mutate an already hashed snapshot."""
        return json.loads(self._mensajes_json)


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
    """Reject any source-prompt mismatch before claiming a bound request.

    An identical request digest does not authenticate the production HTTP call.
    This experimental bridge does not authorize production or G0 inference.
    """
    solicitud = _solicitud_laboratorio(trial, reviewer, attempt, stage)
    mensajes = mensaje_de_critica(
        query=query, idea=idea, domain=domain, evidence=evidence, propuesta=propuesta
    )
    # The old bridge hashed the lab DIRECT/BLIND request but prepared the
    # production critique prompt. A receipt could then claim the lab's SHA
    # for different instructions and different source material. Most critically,
    # the production prompt includes query even for BLIND. The two hashes in
    # CritiqueCall are not evidence of equivalence. Fail BEFORE any dispatch.
    if mensajes != mensaje_compuesto(solicitud.prompt):
        raise ValueError(
            "critica_no_vinculada: mensaje enviado distinto de la solicitud del laboratorio"
        )
    return CritiqueCall(
        request_sha256=solicitud.sha256,
        _mensajes_json=json.dumps(
            mensajes, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ),
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
