"""Diagnóstico estructurado del intérprete para Shadow.

Un fallo sin causa no es diagnosticable. Este módulo convierte cualquier
fallo del puerto en un objeto con:

- ``error_code``: código canónico del megaprompt (TRANSPORT_UNAVAILABLE,
  HTTP_ERROR, ...). Identifica la clase de fallo sin interpretar texto.
- ``phase``: dónde falló (configuracion, transporte, parseo, validacion,
  critica, cancelacion, banco).
- ``reason``: motivo legible en español, ya presente en el resultado.
- ``retryable``: si reintentar la misma petición tiene sentido.
- ``http_status``: código HTTP si lo hubo, si no ``None``.
- ``model_requested`` / ``model_reported``: identidad del modelo.
- ``request_id``: correlación con la procedencia.
- ``constrained_decoding``: modo de decodificación usado.
- ``finish_reason`` / ``completion_tokens`` / ``reasoning_tokens``: fin real
  de la respuesta, para distinguir truncamiento de abstención.
- ``next_action``: qué hacer a continuación (texto para la UI).
- ``raw_output_sha256``: hash de la salida cruda (sin guardarla).
- ``provenance``: procedencia saneada de la petición que falló.

Invariantes que respeta:

- ``ABSTENER`` correcto NO es ``ERROR``: si el resultado es una abstención
  válida (``error_kind`` vacío y ``estado == PROPUESTA`` o abstención de
  dominio), el código es ``CORRECT_ABSTENTION`` con ``retryable=False``.
- ``REJECTED`` no implica avería del proveedor: un fallo de contrato del
  modelo (schema/dominio) es ``SCHEMA_VALIDATION_FAILED`` o
  ``DOMAIN_CONTRACT_FAILED``, no un fallo de transporte.
- Un 503 no es "modelo suspendido": es ``HTTP_ERROR`` con ``http_status=503``
  y ``retryable`` según el código.
- Banco aprobado no implica servicio disponible; modelo cargado no implica
  interpretación validada: ``phase`` distingue cada etapa.
- No hay fallback silencioso: cada código mapea a una acción explícita.

No forma parte de ``CAMPOS_PROPUESTA`` ni de ``to_campos()``: es una vista
de diagnóstico para la UI, no altera el contrato científico.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

# Códigos canónicos del megaprompt CB-02.
TRANSPORT_UNAVAILABLE = "TRANSPORT_UNAVAILABLE"
HTTP_ERROR = "HTTP_ERROR"
AUTH_REJECTED = "AUTH_REJECTED"
RATE_LIMITED = "RATE_LIMITED"
TIMEOUT = "TIMEOUT"
INVALID_CONFIGURATION = "INVALID_CONFIGURATION"
INVALID_JSON = "INVALID_JSON"
SCHEMA_VALIDATION_FAILED = "SCHEMA_VALIDATION_FAILED"
DOMAIN_CONTRACT_FAILED = "DOMAIN_CONTRACT_FAILED"
TRUNCATED_RESPONSE = "TRUNCATED_RESPONSE"
CRITIQUE_UNAVAILABLE = "CRITIQUE_UNAVAILABLE"
CRITIQUE_INVALID = "CRITIQUE_INVALID"
CORRECT_ABSTENTION = "CORRECT_ABSTENTION"
DOMAIN_REJECTION = "DOMAIN_REJECTION"
CANCELLED = "CANCELLED"
BANK_NOT_PASSED = "BANK_NOT_PASSED"
BANK_CANCELLED = "BANK_CANCELLED"
BANK_MODE_MISMATCH = "BANK_MODE_MISMATCH"


@dataclass(frozen=True)
class Diagnostic:
    """Causa real de un fallo (o de una abstención correcta), sin secretos."""

    error_code: str
    phase: str
    reason: str
    retryable: bool
    http_status: int | None = None
    model_requested: str = ""
    model_reported: str = ""
    request_id: str = ""
    constrained_decoding: str = ""
    finish_reason: str = ""
    completion_tokens: int | None = None
    reasoning_tokens: int | None = None
    next_action: str = ""
    raw_output_sha256: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


# Acciones sugeridas por código, para la UI.
_NEXT_ACTION = {
    TRANSPORT_UNAVAILABLE: "Comprueba que el endpoint esté activo y sea accesible; no reintentes hasta confirmarlo.",
    HTTP_ERROR: "Consulta el código HTTP; si es 5xx el servicio del proveedor falló, si es 4xx revisa la petición.",
    AUTH_REJECTED: "Las credenciales fueron rechazadas; revisa CRIBA_EXTERNAL_API_KEY sin exponerla.",
    RATE_LIMITED: "Plan o cuota agotados; espera o cambia de plan/proveedor.",
    TIMEOUT: "El proveedor no respondió a tiempo; sube CRIBA_EXTERNAL_TIMEOUT_S si el modelo es lento.",
    INVALID_CONFIGURATION: "Revisa max_tokens, temperature y reasoning_effort en la configuración.",
    INVALID_JSON: "El modelo no devolvió JSON válido; puede requerir constrained decoding o un modelo distinto.",
    SCHEMA_VALIDATION_FAILED: "La respuesta no cumple el esquema del contrato; no es un fallo del proveedor.",
    DOMAIN_CONTRACT_FAILED: "La respuesta incumple una regla científica del contrato; revisa el prompt o el modelo.",
    TRUNCATED_RESPONSE: "La respuesta se cortó por límite de tokens; sube max_tokens o acorta el prompt.",
    CRITIQUE_UNAVAILABLE: "La crítica automática falló; sin ella la propuesta no se admite.",
    CRITIQUE_INVALID: "La crítica no cumple su contrato; la propuesta queda pendiente.",
    CORRECT_ABSTENTION: "Abstención correcta: no es un error. No reintentes.",
    DOMAIN_REJECTION: "Abstención por regla de dominio (fuera de alcance).",
    CANCELLED: "Cancelado por el usuario; no reintenta automáticamente.",
    BANK_NOT_PASSED: "El intérprete local no ha superado el banco; ejecuta el banco antes de usarlo.",
    BANK_CANCELLED: "El banco fue cancelado; el intérprete local no está admitido.",
    BANK_MODE_MISMATCH: "El banco se evaluó en otro modo de decodificación; reevalúalo.",
}

# Códigos cuya reintentada tiene sentido.
_RETRYABLE = {
    TRANSPORT_UNAVAILABLE: True,
    HTTP_ERROR: True,
    AUTH_REJECTED: False,
    RATE_LIMITED: True,
    TIMEOUT: True,
    INVALID_CONFIGURATION: False,
    INVALID_JSON: False,
    SCHEMA_VALIDATION_FAILED: False,
    DOMAIN_CONTRACT_FAILED: False,
    TRUNCATED_RESPONSE: True,
    CRITIQUE_UNAVAILABLE: True,
    CRITIQUE_INVALID: False,
    CORRECT_ABSTENTION: False,
    DOMAIN_REJECTION: False,
    CANCELLED: False,
    BANK_NOT_PASSED: False,
    BANK_CANCELLED: False,
    BANK_MODE_MISMATCH: False,
}

# Fase donde se produce cada código.
_PHASE = {
    TRANSPORT_UNAVAILABLE: "transporte",
    HTTP_ERROR: "transporte",
    AUTH_REJECTED: "transporte",
    RATE_LIMITED: "transporte",
    TIMEOUT: "transporte",
    INVALID_CONFIGURATION: "configuracion",
    INVALID_JSON: "parseo",
    SCHEMA_VALIDATION_FAILED: "validacion",
    DOMAIN_CONTRACT_FAILED: "validacion",
    TRUNCATED_RESPONSE: "transporte",
    CRITIQUE_UNAVAILABLE: "critica",
    CRITIQUE_INVALID: "critica",
    CORRECT_ABSTENTION: "dominio",
    DOMAIN_REJECTION: "dominio",
    CANCELLED: "cancelacion",
    BANK_NOT_PASSED: "banco",
    BANK_CANCELLED: "banco",
    BANK_MODE_MISMATCH: "banco",
}


def _http_status_of(reason: str) -> int | None:
    """Extrae el código HTTP de un motivo del tipo 'http_error_503'."""
    import re

    m = re.search(r"http_error_(\d{3})", reason or "")
    return int(m.group(1)) if m else None


def classify(result: Any) -> Diagnostic:
    """Construye el diagnóstico de un ``InterpretationResult``.

    Acepta cualquier objeto con los atributos que usa el puerto
    (``estado``, ``error``, ``error_kind``, ``provenance``, ``finish_reason``,
    etc.). No importa el módulo del puerto para evitar ciclos: solo lee
    atributos con ``getattr`` y valores por defecto.
    """
    estado = getattr(result, "estado", "") or ""
    error = getattr(result, "error", "") or ""
    error_kind = getattr(result, "error_kind", "") or ""
    prov = getattr(result, "provenance", None)
    if prov is None:
        prov_d: dict[str, Any] = {}
    else:
        saneado = prov.sin_secretos()
        prov_d = saneado.as_dict() if hasattr(saneado, "as_dict") else dict(saneado)

    # Sin error y no pendiente: propuesta válida o abstención de dominio.
    if not error and estado:
        return Diagnostic(
            error_code=CORRECT_ABSTENTION,
            phase="dominio",
            reason="Abstención correcta (no es un error).",
            retryable=False,
            model_requested=prov_d.get("model_requested", ""),
            model_reported=prov_d.get("model_reported", ""),
            request_id=prov_d.get("request_id", ""),
            constrained_decoding=(
                prov_d.get("generation_parameters", {}) or {}
            ).get("constrained_decoding", ""),
            finish_reason=getattr(result, "finish_reason", "") or "",
            completion_tokens=getattr(result, "completion_tokens", None),
            reasoning_tokens=getattr(result, "reasoning_tokens", None),
            next_action=_NEXT_ACTION[CORRECT_ABSTENTION],
            raw_output_sha256=prov_d.get("raw_output_sha256", ""),
            provenance=prov_d,
        )

    # Abstención por regla de dominio: 'validacion:abstencion:...'
    if error.startswith("validacion:abstencion:"):
        return Diagnostic(
            error_code=DOMAIN_REJECTION,
            phase="dominio",
            reason=error.split("abstencion:", 1)[-1],
            retryable=False,
            model_requested=prov_d.get("model_requested", ""),
            model_reported=prov_d.get("model_reported", ""),
            request_id=prov_d.get("request_id", ""),
            next_action=_NEXT_ACTION[DOMAIN_REJECTION],
            raw_output_sha256=prov_d.get("raw_output_sha256", ""),
            provenance=prov_d,
        )

    # Fallo de contrato del modelo (schema/dominio): no es fallo del proveedor.
    if error.startswith("validacion:"):
        code = (
            SCHEMA_VALIDATION_FAILED
            if error_kind == "schema"
            else DOMAIN_CONTRACT_FAILED
        )
        return Diagnostic(
            error_code=code,
            phase="validacion",
            reason=error.split("validacion:", 1)[-1],
            retryable=_RETRYABLE[code],
            model_requested=prov_d.get("model_requested", ""),
            model_reported=prov_d.get("model_reported", ""),
            request_id=prov_d.get("request_id", ""),
            next_action=_NEXT_ACTION[code],
            raw_output_sha256=prov_d.get("raw_output_sha256", ""),
            provenance=prov_d,
        )

    # Crítica: fallo de disponibilidad o contrato.
    if error.startswith("critica_no_disponible:"):
        inner = error.split("critica_no_disponible:", 1)[-1]
        code = CRITIQUE_UNAVAILABLE if "json_invalido" not in inner else CRITIQUE_INVALID
        return Diagnostic(
            error_code=code,
            phase="critica",
            reason=inner,
            retryable=_RETRYABLE[code],
            model_requested=prov_d.get("model_requested", ""),
            model_reported=prov_d.get("model_reported", ""),
            request_id=prov_d.get("request_id", ""),
            next_action=_NEXT_ACTION[code],
            raw_output_sha256=prov_d.get("raw_output_sha256", ""),
            provenance=prov_d,
        )

    # Banco local.
    if "banco local cancelado" in error:
        return Diagnostic(
            error_code=BANK_CANCELLED,
            phase="banco",
            reason=error,
            retryable=False,
            next_action=_NEXT_ACTION[BANK_CANCELLED],
            provenance=prov_d,
        )
    if "otro modo de decodificación" in error:
        return Diagnostic(
            error_code=BANK_MODE_MISMATCH,
            phase="banco",
            reason=error,
            retryable=False,
            next_action=_NEXT_ACTION[BANK_MODE_MISMATCH],
            provenance=prov_d,
        )
    if "banco local" in error:
        return Diagnostic(
            error_code=BANK_NOT_PASSED,
            phase="banco",
            reason=error,
            retryable=False,
            next_action=_NEXT_ACTION[BANK_NOT_PASSED],
            provenance=prov_d,
        )

    # Cancelación explícita del usuario.
    if error.startswith("cancelado"):
        return Diagnostic(
            error_code=CANCELLED,
            phase="cancelacion",
            reason=error,
            retryable=False,
            next_action=_NEXT_ACTION[CANCELLED],
            provenance=prov_d,
        )

    # Transporte: timeout, credenciales, 429, http_error_N, JSON inválido.
    if error == "timeout":
        code = TIMEOUT
    elif error.startswith("credenciales rechazadas"):
        code = AUTH_REJECTED
    elif error.startswith("plan_agotado_429"):
        code = RATE_LIMITED
    elif error.startswith("http_error_"):
        code = HTTP_ERROR
    elif error.startswith("respuesta_json_invalida") or error.startswith("json_invalido"):
        code = INVALID_JSON
    elif error.startswith("salida_truncada"):
        code = TRUNCATED_RESPONSE
    elif error.startswith("transporte_http"):
        code = TRANSPORT_UNAVAILABLE
    elif error.startswith("configuracion_invalida"):
        code = INVALID_CONFIGURATION
    elif error.startswith("sin_contenido") or error.startswith("respuesta_sin_choices"):
        code = HTTP_ERROR
    else:
        code = TRANSPORT_UNAVAILABLE

    return Diagnostic(
        error_code=code,
        phase=_PHASE.get(code, "transporte"),
        reason=error,
        retryable=_RETRYABLE[code],
        http_status=_http_status_of(error),
        model_requested=prov_d.get("model_requested", ""),
        model_reported=prov_d.get("model_reported", ""),
        request_id=prov_d.get("request_id", ""),
        constrained_decoding=(
            prov_d.get("generation_parameters", {}) or {}
        ).get("constrained_decoding", ""),
        finish_reason=getattr(result, "finish_reason", "") or "",
        completion_tokens=getattr(result, "completion_tokens", None),
        reasoning_tokens=getattr(result, "reasoning_tokens", None),
        next_action=_NEXT_ACTION.get(code, ""),
        raw_output_sha256=prov_d.get("raw_output_sha256", ""),
        provenance=prov_d,
    )
