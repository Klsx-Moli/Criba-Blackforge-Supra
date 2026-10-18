"""Intérprete OpenAI-compatible, apuntable a Hermes u a otro endpoint.

Por qué este backend y no el anterior: la interpretación necesita un modelo
alcanzable y la credencial no puede ir dentro del paquete. Hermes expone un
proxy OpenAI-compatible local que adjunta las credenciales reales, así que este
cliente habla HTTP estándar y la llave, si la hay, se queda en el entorno.

Contrato: hereda la forma de petición que ya usaba el adaptador anterior, pero
todo lo que devuelve pasa por el mismo ``InterpretationResult`` y la misma
validación que el resto de backends. No hay atajos.
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import httpx
from tenacity import (
    RetryCallState,
    retry,
    retry_if_exception,
    stop_after_attempt,
    stop_after_delay,
    wait_exponential_jitter,
)
from tenacity.wait import wait_base

from .contrato import (
    CRITICA_INSTRUCCIONES,
    KIND_DOMAIN,
    KIND_SCHEMA,
    PREGUNTAS_TEXTO,
    SYSTEM,
    prompt_propuesta,
    schema_critica,
    schema_propuesta,
    validar_critica,
    validar_propuesta,
    validar_propuesta_estructurada,
)
from .puerto import (
    ESTADO_PENDIENTE,
    ESTADO_PROPUESTA,
    PROMPT_VERSION,
    SCHEMA_VERSION,
    InterpretationResult,
    Provenance,
    hash_salida,
    marca_temporal,
    nuevo_request_id,
    pendiente,
    sin_secretos,
)

log = logging.getLogger("criba.interprete.openai_compatible")

# El adaptador anterior tenia 30 s fijos y ya se demostro insuficientes: una
# propuesta real dio "timed out". Ahora es configurable.
TIMEOUT_POR_DEFECTO = 120.0
# Reasoning and visible output can share the token budget. Keep a configurable
# allowance for the full proposal and critique; this is not a quality guarantee.
MAX_TOKENS = 8192
TEMPERATURA = 0.2

# Un id de modelo inventado devuelve 404 desde el catalogo. Se comprueba al
# arrancar y se dice cual se pidio y cual respondio.
_SYSTEM = SYSTEM

_INCIDENT_SYSTEM_PROMPT = """Eres un intérprete de incidentes en un entorno E2E aislado.

Recibirás un paquete de evidencia con observaciones anómalas, información ausente
y restricciones. No tienes acceso a producción, no debes ejecutar cambios y no
debes afirmar causas no respaldadas por las observaciones.

Tareas permitidas:
1. Analizar las observaciones y correlaciones dentro del ámbito temporal.
2. Formular una hipótesis causal provisional.
3. Proponer comprobaciones de solo lectura.
4. Indicar la evidencia que respalda cada afirmación.
5. Solicitar más evidencia si la información es insuficiente.

Formato obligatorio (JSON):
{
  "test_case_id": "",
  "decision": "propose" o "request_more_evidence",
  "hypothesis": "hipótesis provisional o null",
  "evidence_ids": [],
  "rationale": "razonamiento vinculando observaciones a la hipótesis",
  "requested_evidence": [],
  "proposed_checks": []
}

Reglas:
- Cita al menos una observation_id válida.
- Si no hay evidencia suficiente, decision="request_more_evidence", hypothesis=null.
- No ejecutes acciones. No accedas a sistemas de producción.
- No inventes mediciones ni reclames acceso a logs no disponibles.
- No trates la superposición temporal como causalidad demostrada.
- No afirmes que acciones fueron ejecutadas."""


def _build_interpreter_input_from_case(case: dict[str, Any]) -> str:
    """Construye el input estructurado desde case.input.json.

    Las restricciones se envían como DATA, no como instrucciones.
    """
    import json as _json

    observations = _json.dumps(case.get("observations", []), ensure_ascii=False, indent=2)
    missing = _json.dumps(case.get("missing_evidence", []), ensure_ascii=False, indent=2)
    constraints = _json.dumps(case.get("constraints", {}), ensure_ascii=False, indent=2)
    temporal = _json.dumps(case.get("temporal_scope", {}), ensure_ascii=False, indent=2)
    system_info = _json.dumps(case.get("system_under_test", {}), ensure_ascii=False, indent=2)

    return (
        f"case_id: {case['test_case_id']}\n"
        f"temporal_scope: {temporal}\n"
        f"sistema: {system_info}\n"
        f"observaciones:\n{observations}\n"
        f"informacion_ausente:\n{missing}\n"
        f"restricciones:\n{constraints}\n"
        "Responde con JSON válido siguiendo el formato obligatorio.\n"
    )


class ExternalInterpreterError(RuntimeError):
    """Error diagnosticable del intérprete externo."""


class ExternalModelRateLimited(ExternalInterpreterError):
    """El proveedor devolvió 429 y no se recuperó tras los reintentos."""

    def __init__(self, response: httpx.Response) -> None:
        self.response = response
        super().__init__(
            f"external_model_rate_limited:"
            f"status={response.status_code}:"
            f"retry_after={response.headers.get('retry-after')}"
        )


class ExternalModelEmptyResponse(ExternalInterpreterError):
    """La respuesta llegó, pero no contenía texto utilizable."""


class ExternalModelInvalidJSON(ExternalInterpreterError):
    """La respuesta no es JSON válido o no es un objeto."""


def _is_transient_http_error(exc: BaseException) -> bool:
    """Determina si un error HTTP es transitorio y admite reintento."""
    if isinstance(exc, ExternalModelRateLimited):
        return True
    if isinstance(exc, (httpx.TimeoutException, httpx.TransportError)):
        return True
    return False


def _extract_content(response_json: dict[str, Any]) -> str:
    """Extrae y valida el contenido del mensaje de la respuesta del modelo.

    content puede ser string o null (protocolo Chat Completions).
    Valida antes de json.loads para evitar TypeError por content=None.
    """
    choices = response_json.get("choices") or []

    if not choices:
        raise ExternalModelEmptyResponse("external_model_empty_choices")

    choice = choices[0]
    message = choice.get("message") or {}
    content = message.get("content")
    finish_reason = choice.get("finish_reason")

    if content is None:
        raise ExternalModelEmptyResponse(
            f"external_model_null_content:finish_reason={finish_reason!r}"
        )

    if not isinstance(content, str):
        raise ExternalModelEmptyResponse(
            f"external_model_invalid_content_type:{type(content).__name__}"
        )

    content = content.strip()

    if not content:
        raise ExternalModelEmptyResponse(
            f"external_model_empty_content:finish_reason={finish_reason!r}"
        )

    return content


def _parse_model_json(raw: str) -> dict[str, Any]:
    """Parsea el contenido como JSON, validando que sea un objeto dict."""
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ExternalModelInvalidJSON("external_model_invalid_json") from exc

    if not isinstance(parsed, dict):
        raise ExternalModelInvalidJSON(
            f"external_model_invalid_json_type:{type(parsed).__name__}"
        )

    return parsed


def _is_truncated_response(exc: BaseException) -> bool:
    """Detecta respuestas truncadas por finish_reason='length'."""
    return (
        isinstance(exc, ExternalModelEmptyResponse)
        and "finish_reason='length'" in str(exc)
    )


class wait_retry_after(wait_base):
    """Estrategia de espera que respeta Retry-After (segundos o fecha HTTP)."""

    def __init__(self, fallback: Any) -> None:
        self.fallback = fallback

    def __call__(self, retry_state: RetryCallState) -> float:
        outcome = retry_state.outcome
        exc = outcome.exception() if outcome else None

        if isinstance(exc, ExternalModelRateLimited):
            raw = exc.response.headers.get("retry-after")
            if raw:
                try:
                    return min(max(float(raw), 1.0), 30.0)
                except ValueError:
                    try:
                        from email.utils import parsedate_to_datetime

                        target = parsedate_to_datetime(raw)
                        delay = target.timestamp() - time.time()
                        return min(max(delay, 1.0), 30.0)
                    except (TypeError, ValueError):
                        pass

        return float(self.fallback(retry_state))


@retry(
    retry=retry_if_exception(_is_transient_http_error),
    stop=(stop_after_attempt(4) | stop_after_delay(45)),
    wait=wait_retry_after(
        fallback=wait_exponential_jitter(initial=1, max=15, jitter=2)
    ),
    reraise=True,
)
def _post_chat_completion(
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> httpx.Response:
    """POST a /chat/completions con reintentos para 429 y errores transitorios."""
    response = client.post(url, json=payload, headers=headers)

    if response.status_code == 429:
        raise ExternalModelRateLimited(response)

    response.raise_for_status()
    return response


@retry(
    retry=retry_if_exception(_is_truncated_response),
    stop=stop_after_attempt(2),
    wait=wait_exponential_jitter(initial=1, max=5),
    reraise=True,
)
def _request_structured_json(
    client: httpx.Client,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
) -> dict[str, Any]:
    """Obtiene JSON estructurado con reintento único si se trunca por max_tokens.

    No reintenta content=None con tool_calls o content_filter; esos son errores
    diagnósticos permanentes.
    """
    response = _post_chat_completion(client, url, payload, headers)
    raw = _extract_content(response.json())

    try:
        return _parse_model_json(raw)
    except ExternalModelInvalidJSON:
        raise ExternalModelEmptyResponse(
            "external_model_invalid_json:possible_truncation"
        )


def _extraer_json(contenido: str) -> dict[str, Any]:
    """Saca el objeto JSON de una respuesta que puede venir envuelta.

    No es permisivo con el contenido: solo quita vallas de markdown y recorta
    hasta el primer objeto completo. Si no hay JSON, se levanta el error y el
    llamador degrada a pendiente con el motivo real.
    """

    def pares_unicos(pares: list[tuple[str, Any]]) -> dict[str, Any]:
        objeto: dict[str, Any] = {}
        for clave, valor in pares:
            if clave in objeto:
                raise ValueError("clave JSON duplicada")
            objeto[clave] = valor
        return objeto

    def constante_invalida(value: str) -> Any:
        raise ValueError("constante no válida en JSON")

    raw = (contenido or "").strip()
    if raw.startswith("```json"):
        raw = raw[len("```json") :]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        parsed = json.loads(raw, object_pairs_hook=pares_unicos, parse_constant=constante_invalida)
    except ValueError:
        inicio = raw.find("{")
        fin = raw.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise
        parsed = json.loads(
            raw[inicio : fin + 1], object_pairs_hook=pares_unicos, parse_constant=constante_invalida
        )
    if not isinstance(parsed, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    return parsed


def construir_prompt(
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    evidence: list[dict[str, Any]] | None,
) -> str:
    """Contrato versionado con evidencia y preguntas epistemológicas."""
    return prompt_propuesta(query, idea, domain, evidence)



def endpoint_problem(base: str) -> str | None:
    """Motivo por el que un endpoint NO debe contactarse, o ``None`` si es aceptable.

    Se evalúa ANTES de abrir ninguna conexión, para que ni la URL ni el
    ``Authorization: Bearer`` lleguen a un destino no confiable:

    - esquema distinto de http/https o sin host -> rechazado;
    - usuario/contraseña embebidos en la URL -> rechazado (credenciales en claro);
    - http sin TLS hacia un host que no es loopback -> rechazado (el Bearer
      viajaría sin cifrar). https remoto sigue permitido.
    """
    import ipaddress
    from urllib.parse import urlsplit

    try:
        url = urlsplit(base)
        host = url.hostname
        _ = url.port  # fuerza la validación del puerto
    except ValueError:
        return "URL malformada"
    if url.scheme not in ("http", "https"):
        return "esquema no permitido (solo http/https)"
    if not host:
        return "URL sin host"
    if url.username or url.password:
        return "credenciales embebidas en la URL"
    if url.scheme == "http":
        loopback = host == "localhost"
        if not loopback:
            try:
                loopback = ipaddress.ip_address(host).is_loopback
            except ValueError:
                loopback = False
        if not loopback:
            return "http sin TLS hacia un host que no es loopback"
    return None


class OpenAICompatibleInterpreter:
    """Un interprete, un endpoint. Sin llave embebida y sin estado global."""

    backend = "openai_compatible"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        timeout_s: float | None = None,
        fallback_local: bool | None = None,
        critic_model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        enable_thinking: bool | None = None,
        seed: int | None = None,
    ) -> None:
        self.base = (
            base_url or os.getenv("CRIBA_EXTERNAL_BASE_URL") or "http://127.0.0.1:8645/v1"
        ).rstrip("/")
        self.model = model or os.getenv("CRIBA_EXTERNAL_MODEL") or "poolside/laguna-s-2.1:free"
        self.critic_model = critic_model or os.getenv("CRIBA_CRITIC_MODEL") or self.model
        # La clave se lee SOLO del entorno y nunca se escribe en logs ni en la
        # procedencia. Un proxy local acepta cualquier bearer.
        self._api_key = api_key if api_key is not None else os.getenv("CRIBA_EXTERNAL_API_KEY", "")
        self.timeout_s = float(
            timeout_s
            if timeout_s is not None
            else os.getenv("CRIBA_EXTERNAL_TIMEOUT_S", TIMEOUT_POR_DEFECTO)
        )
        try:
            self.max_tokens = int(
                max_tokens
                if max_tokens is not None
                else os.getenv("CRIBA_EXTERNAL_MAX_TOKENS", MAX_TOKENS)
            )
        except (TypeError, ValueError, OverflowError):
            self.max_tokens = 0
        self.temperature = TEMPERATURA if temperature is None else temperature
        self.reasoning_effort = (
            reasoning_effort
            if reasoning_effort is not None
            else os.getenv("CRIBA_EXTERNAL_REASONING_EFFORT", "").strip()
        )
        self.enable_thinking = enable_thinking
        semilla = seed if seed is not None else os.getenv("CRIBA_EXTERNAL_SEED", "").strip()
        try:
            self.seed: int | None = int(semilla) if semilla != "" else None
        except (TypeError, ValueError):
            self.seed = None
        self.fallback_local = (
            fallback_local
            if fallback_local is not None
            else os.getenv("CRIBA_EXTERNAL_FALLBACK_LOCAL", "false").lower() == "true"
        )
        self.provider = (
            os.getenv("CRIBA_EXTERNAL_PROVIDER", "nous_oauth_subscription_proxy").strip()
            or "nous_oauth_subscription_proxy"
        )

    @property
    def generation_parameters(self) -> dict[str, Any]:
        """Snapshot used in request provenance and the cache identity."""
        return {
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "timeout_s": self.timeout_s,
            "reasoning_effort": self.reasoning_effort,
            "enable_thinking": self.enable_thinking,
            "seed": self.seed,
        }

    # -- estado real, no optimista ---------------------------------------
    def operativo(self) -> tuple[bool, str]:
        """Comprueba /models de verdad. Un backend no se declara listo por tener
        configuracion: tiene que responder."""
        if not self.base:
            return False, "sin CRIBA_EXTERNAL_BASE_URL"
        problema = endpoint_problem(self.base)
        if problema:
            return False, f"endpoint rechazado antes de conectar: {problema}"
        try:
            with httpx.Client(timeout=min(self.timeout_s, 15.0)) as client:
                resp = client.get(f"{self.base}/models", headers=self._headers())
            if resp.status_code != 200:
                return False, f"el endpoint no responde /models: HTTP {resp.status_code}"
            data = resp.json()
            ids = [m.get("id") for m in (data.get("data") or []) if isinstance(m, dict)]
            ausentes = [m for m in {self.model, self.critic_model} if m not in ids]
            if ausentes:
                return False, (
                    f"el modelo {ausentes[0]!r} no esta en el catalogo del endpoint "
                    f"(hay {len(ids)} disponibles)"
                )
            return True, f"endpoint responde y {self.model!r} esta en el catalogo"
        except Exception as exc:  # noqa: BLE001 - el estado tambien debe ser honesto
            return False, f"no se pudo contactar el interprete: {type(exc).__name__}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    def _provenance(
        self,
        *,
        request_id: str,
        inicio: float,
        model_reported: str,
        raw: str,
        fallback_used: bool,
        prompt: str = "",
        model_requested: str = "",
        constrained_decoding: str = "",
    ) -> Provenance:
        parametros = dict(self.generation_parameters)
        if constrained_decoding:
            parametros["constrained_decoding"] = constrained_decoding
        return Provenance(
            interpreter_backend=self.backend,
            provider=self.provider,
            model_requested=model_requested or self.model,
            model_reported=model_reported or "",
            endpoint=sin_secretos(self.base),
            timestamp=marca_temporal(),
            duration_ms=int((time.monotonic() - inicio) * 1000),
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            request_id=request_id,
            fallback_used=fallback_used,
            raw_output_sha256=hash_salida(raw),
            prompt_sha256=hash_salida(_SYSTEM + prompt),
            generation_parameters=parametros,
        )

    def _pedir(
        self, prompt: str, model: str, schema: dict[str, Any] | None = None
    ) -> InterpretationResult:
        """Una petición, con diagnóstico y procedencia propios incluso si falla.

        ``schema`` activa decodificación restringida (json_schema -> grammar en
        llama-server). Fija la forma del JSON, nunca el veredicto. La procedencia
        registra que se usó para no comparar peras con manzanas.
        """
        request_id = nuevo_request_id()
        inicio = time.monotonic()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": self.temperature,
            "response_format": (
                {
                    "type": "json_schema",
                    "json_schema": {"name": "propuesta", "schema": schema},
                }
                if schema
                else {"type": "json_object"}
            ),
        }
        if self.seed is not None:
            payload["seed"] = self.seed
        model_reported = ""
        raw_output = ""
        finish_reason = ""
        completion_tokens: int | None = None
        reasoning_tokens: int | None = None

        def _numero_opcional(value: Any) -> int | None:
            return value if type(value) is int and value >= 0 else None

        def _fallo(
            motivo: str,
            *,
            raw_para_hash: str | None = None,
            error_kind: str = "",  # NEW: clasificación estructurada del fallo
        ) -> InterpretationResult:
            return InterpretationResult(
                estado=ESTADO_PENDIENTE,
                error=motivo,
                error_kind=error_kind,
                provenance=self._provenance(
                    request_id=request_id,
                    inicio=inicio,
                    model_reported=model_reported,
                    raw=raw_output if raw_para_hash is None else raw_para_hash,
                    fallback_used=False,
                    prompt=prompt,
                    model_requested=model,
                    constrained_decoding="json_schema" if schema is not None else "",
                ),
                raw_output=raw_output,
                finish_reason=finish_reason,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
                model_requests=1,
            )

        problema_endpoint = endpoint_problem(self.base)
        if problema_endpoint:
            return replace(
                _fallo(f"configuracion_invalida:endpoint:{problema_endpoint}", error_kind="config"),
                model_requests=0,
            )

        try:
            try:
                max_tokens = self.max_tokens
                if not 1 <= max_tokens <= 32768:
                    raise ValueError("max_tokens debe ser positivo")
            except ValueError:
                return replace(_fallo("configuracion_invalida:max_tokens", error_kind="config"), model_requests=0)
            payload["max_tokens"] = max_tokens
            if not math.isfinite(self.timeout_s) or not 0 < self.timeout_s <= 1800:
                return replace(_fallo("configuracion_invalida:timeout", error_kind="config"), model_requests=0)
            if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
                return replace(_fallo("configuracion_invalida:temperature", error_kind="config"), model_requests=0)
            if self.reasoning_effort:
                if self.reasoning_effort not in {
                    "none",
                    "minimal",
                    "low",
                    "medium",
                    "high",
                    "xhigh",
                    "max",
                }:
                    return replace(
                        _fallo("configuracion_invalida:reasoning_effort", error_kind="config"), model_requests=0
                    )
                from urllib.parse import urlsplit

                if urlsplit(self.base).hostname == "openrouter.ai":
                    payload["reasoning"] = {"effort": self.reasoning_effort}
                else:
                    payload["reasoning_effort"] = self.reasoning_effort
            if self.enable_thinking is not None:
                payload["chat_template_kwargs"] = {"enable_thinking": self.enable_thinking}
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = _post_chat_completion(
                    client,
                    f"{self.base}/chat/completions",
                    payload=payload,
                    headers=self._headers(),
                )
            try:
                cuerpo = resp.json()
            except ValueError as exc:
                return _fallo(f"respuesta_json_invalida:{type(exc).__name__}", error_kind="schema")
            if not isinstance(cuerpo, dict):
                return _fallo(f"respuesta_tipo_inesperado:{type(cuerpo).__name__}", error_kind="schema")
            model_reported = str(cuerpo.get("model") or "")
            choices = cuerpo.get("choices")
            if not isinstance(choices, list) or not choices:
                return _fallo("respuesta_sin_choices", error_kind="schema")
            eleccion = choices[0]
            if not isinstance(eleccion, dict):
                return _fallo(f"choice_tipo_inesperado:{type(eleccion).__name__}", error_kind="schema")

            finish_reason = str(eleccion.get("finish_reason") or "")
            uso = cuerpo.get("usage")
            if isinstance(uso, dict):
                completion_tokens = _numero_opcional(uso.get("completion_tokens"))
                detalles = uso.get("completion_tokens_details")
                if isinstance(detalles, dict):
                    reasoning_tokens = _numero_opcional(detalles.get("reasoning_tokens"))
            message = eleccion.get("message")
            if not isinstance(message, dict):
                return _fallo(f"message_tipo_inesperado:{type(message).__name__}", error_kind="schema")

            # Usa _extract_content para validar content (None, tipo, vacío)
            try:
                raw_output = _extract_content(cuerpo)
            except ExternalModelEmptyResponse as exc:
                # finish_reason='length' -> ExternalModelEmptyResponse con finish_reason='length'
                if "finish_reason='length'" in str(exc):
                    return _fallo(
                        f"sin_contenido:finish_reason=length "
                        f"tokens={completion_tokens} razonamiento={reasoning_tokens}",
                        error_kind="truncated",
                    )
                # Un content de tipo inesperado no se convierte a texto: se
                # nombra el tipo real para que el diagnóstico sea accionable.
                if "invalid_content_type" in str(exc):
                    tipo = str(exc).rsplit(":", 1)[-1]
                    return _fallo(f"contenido_tipo_inesperado:{tipo}", error_kind="schema")
                if message.get("tool_calls"):
                    return _fallo("tool_calls_sin_contenido", error_kind="schema")
                return _fallo(
                    f"sin_contenido:finish_reason={finish_reason or 'desconocido'} "
                    f"tokens={completion_tokens} razonamiento={reasoning_tokens}",
                    error_kind="schema",
                )

            # Validación JSON (usa _extraer_json que ya existe para consistencia)
            try:
                _extraer_json(raw_output)
            except (json.JSONDecodeError, ValueError) as exc:
                # Una respuesta cortada por límite de tokens NO es JSON inválido:
                # decir "JSONDecodeError" oculta la causa real. Se atribuye al
                # truncamiento cuando el modelo lo declaró con finish_reason.
                if finish_reason == "length":
                    return _fallo(
                        f"salida_truncada:finish_reason=length "
                        f"tokens={completion_tokens} razonamiento={reasoning_tokens}",
                        error_kind="truncated",
                    )
                return _fallo(f"json_invalido:{type(exc).__name__}", error_kind="parse_error")
        except httpx.TimeoutException:
            return _fallo("timeout", error_kind="timeout")
        except ExternalModelRateLimited as exc:
            # El 429 se reintenta en _post_chat_completion (4 intentos / 45s) y
            # agota el plan: se conserva el código y NO se vuelca el cuerpo de la
            # respuesta. Sin este manejador el error caía en el `except Exception`
            # genérico y el motivo real se perdía como proposal_failed:AttributeError.
            return _fallo(
                "plan_agotado_429",
                error_kind="rate_limit",
                raw_para_hash=exc.response.text[:2000],
            )
        except httpx.HTTPStatusError as exc:
            # Contrato restaurado del flujo previo al refactor de tenacity:
            # 401/403 -> credenciales rechazadas; cualquier otro -> http_error_N.
            # En ninguno de los dos se vuelca el cuerpo de la respuesta.
            codigo = exc.response.status_code if exc.response is not None else 0
            if codigo in (401, 403):
                return _fallo(f"credenciales rechazadas: HTTP {codigo}", error_kind="auth")
            return _fallo(f"http_error_{codigo}", error_kind="http")
        except httpx.HTTPError as exc:
            tipo = type(exc).__name__
            log.warning("interpretacion %s fallo de transporte: %s", request_id, tipo)
            return _fallo(f"transporte_http:{tipo}", error_kind="transport")
        except Exception as exc:  # noqa: BLE001 - una propuesta nunca rompe el loop
            tipo = type(exc).__name__
            log.warning("interpretacion %s fallo: %s", request_id, tipo)
            return _fallo(f"proposal_failed:{tipo}", error_kind="internal_error")

        return InterpretationResult(
            estado=ESTADO_PROPUESTA,
            provenance=self._provenance(
                request_id=request_id,
                inicio=inicio,
                model_reported=model_reported,
                raw=raw_output,
                fallback_used=False,
                prompt=prompt,
                model_requested=model,
                constrained_decoding="json_schema" if schema is not None else "",
            ),
            raw_output=raw_output,
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
            model_requests=1,
        )

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> InterpretationResult:
        try:
            prompt = construir_prompt(query, idea, domain, evidence)
        except (ValueError, TypeError) as exc:
            return pendiente(
                f"entrada_invalida:{type(exc).__name__}",
                self._provenance(
                    request_id=nuevo_request_id(),
                    inicio=time.monotonic(),
                    model_reported="",
                    raw="",
                    fallback_used=False,
                ),
            )
        restringido = os.getenv("CRIBA_CONSTRAINED_DECODING", "").strip().lower() in (
            "json_schema",
            "1",
            "true",
        )
        transporte = self._pedir(
            prompt,
            self.model,
            schema=schema_propuesta(idea, evidence) if restringido else None,
        )
        if transporte.estado == ESTADO_PENDIENTE:
            return transporte
        parsed = _extraer_json(transporte.raw_output)
        errores_estructurados = validar_propuesta_estructurada(parsed, idea, evidence)
        if errores_estructurados:
            kinds = {kind for kind, _ in errores_estructurados}
            error_kind = KIND_SCHEMA if KIND_SCHEMA in kinds else KIND_DOMAIN
            return replace(
                transporte,
                estado=ESTADO_PENDIENTE,
                pertinencia=str(parsed.get("pertinencia") or ""),
                error="validacion:" + "; ".join(m for _, m in errores_estructurados),
                error_kind=error_kind,
            )
        critica_prompt = (
            CRITICA_INSTRUCCIONES
            + "\n"
            + PREGUNTAS_TEXTO
            + "\nENTRADA:\n"
            + prompt
            + "\nPROPUESTA A CRITICAR:\n"
            + json.dumps(parsed, ensure_ascii=False)
        )
        critica = self._pedir(
            critica_prompt, self.critic_model, schema=schema_critica() if restringido else None
        )
        diagnostico: dict[str, Any] = {
            "evaluation_status": "NOT_EVALUATED",
            "independent_validation": False,
            "same_model": self.critic_model == self.model,
            "provenance": critica.provenance.sin_secretos() if critica.provenance else {},
            "raw_output": critica.raw_output,
            "finish_reason": critica.finish_reason,
            "completion_tokens": critica.completion_tokens,
            "reasoning_tokens": critica.reasoning_tokens,
        }
        if critica.estado == ESTADO_PENDIENTE:
            return replace(
                transporte,
                estado=ESTADO_PENDIENTE,
                error="critica_no_disponible:" + critica.error,
                critica=diagnostico,
                model_requests=transporte.model_requests + critica.model_requests,
            )
        contenido_critica = _extraer_json(critica.raw_output)
        diagnostico["respuesta"] = contenido_critica
        errores = validar_critica(contenido_critica)
        diagnostico["evaluation_status"] = "CRITIQUED" if not errores else "REJECTED"
        if errores:
            return replace(
                transporte,
                estado=ESTADO_PENDIENTE,
                error="validacion:" + "; ".join(errores),
                critica=diagnostico,
                model_requests=transporte.model_requests + critica.model_requests,
            )
        campos = {
            k: parsed[k]
            for k in (
                "hipotesis",
                "mecanismo",
                "aportacion_por_tecnica",
                "supuestos",
                "prueba_concreta",
                "pertinencia",
                "cadena_causal",
                "evidencia_citada",
                "conocimiento_previo",
                "incertidumbre",
                "novedad",
                "prueba",
                "comprobacion_restricciones",
            )
        }
        return replace(
            transporte,
            **campos,
            ruta_desbloqueo=parsed.get("ruta_desbloqueo", ""),
            critica=diagnostico,
            model_requests=transporte.model_requests + critica.model_requests,
        )

    def analizar_caso(self, case: dict[str, Any]) -> dict[str, Any]:
        """Analiza un caso estructurado de evidencia eincidente.

        Envía observaciones, información ausente y restricciones como DATA
        al modelo y devuelve JSON validado. Aplica reintentos de Tenacity
        para errores transitorios (429, timeouts, transport errors).

        Lanza:
          - ExternalModelRateLimited: tras 4 intentos o 45s (no reintentable)
          - ExternalModelEmptyResponse: content=None/vacío (no reintentable)
          - ExternalModelInvalidJSON: respuesta no es JSON válido
        """
        input_text = _build_interpreter_input_from_case(case)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _INCIDENT_SYSTEM_PROMPT},
                {"role": "user", "content": input_text},
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "response_format": {"type": "json_object"},
        }
        if self.seed is not None:
            payload["seed"] = self.seed

        with httpx.Client(timeout=self.timeout_s) as client:
            return _request_structured_json(
                client,
                f"{self.base}/chat/completions",
                payload=payload,
                headers=self._headers(),
            )


class LocalLlamaInterpreter(OpenAICompatibleInterpreter):
    """Runtime local OpenAI-compatible, operativo solo tras superar el banco."""

    backend = "local_llama"
    ETIQUETA = "EXPERIMENTAL / NO VERIFICADO"
    MOTIVO = "interpretación operativa pendiente: falta superar el banco local"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        *,
        cancel_requested: Callable[[], bool] | None = None,
        progress: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        from criba.model_config import load_model_settings

        self._bank_cancel_requested = cancel_requested
        self._bank_progress = progress
        settings = load_model_settings()
        profile = settings.active_profile() if settings.enabled else None
        base = (
            base_url
            or os.getenv("CRIBA_LOCAL_BASE")
            or (profile.endpoint if profile else "http://127.0.0.1:8080")
        )
        base = base.rstrip("/")
        if not base.endswith("/v1"):
            base += "/v1"
        local_model = (
            model or os.getenv("CRIBA_LOCAL_MODEL") or (profile.model if profile else "criba-local")
        )
        super().__init__(
            base_url=base,
            model=local_model,
            api_key="",
            critic_model=local_model,
            timeout_s=profile.timeout if profile else TIMEOUT_POR_DEFECTO,
            max_tokens=profile.max_output_tokens if profile else MAX_TOKENS,
            temperature=profile.temperature if profile else TEMPERATURA,
            reasoning_effort="none" if profile and profile.reasoning == "fast" else "",
            enable_thinking=profile.reasoning != "fast" if profile else None,
        )
        self.provider = "local_gguf"
        self.gate_report: dict[str, Any] | None = None

    def _local(self) -> bool:
        import ipaddress
        from urllib.parse import urlsplit

        url = urlsplit(self.base)
        if url.scheme not in ("http", "https") or url.username or url.password:
            return False
        if url.hostname == "localhost":
            return True
        try:
            return ipaddress.ip_address(url.hostname or "").is_loopback
        except ValueError:
            return False

    def _modo_actual(self) -> str:
        """Modo de decodificación con el que se evaluaría el banco ahora mismo."""
        restringido = os.getenv("CRIBA_CONSTRAINED_DECODING", "").strip().lower() in (
            "json_schema",
            "1",
            "true",
        )
        return "json_schema" if restringido else ""

    def operativo(self) -> tuple[bool, str]:
        if not self._local():
            return False, "interpretación operativa rechazada: el endpoint local no es loopback"
        modo = self._modo_actual()
        if self.gate_report is not None:
            if self.gate_report.get("constrained_decoding", "") != modo:
                return False, (
                    "banco local evaluado en otro modo de decodificación "
                    f"({self.gate_report.get('constrained_decoding', '')!r} != {modo!r}); "
                    "reevaluar"
                )
            ok = bool(self.gate_report["passed"])
            return ok, "banco local superado" if ok else self.MOTIVO
        listo, motivo = super().operativo()
        if not listo:
            return False, self.MOTIVO + "; " + motivo
        from .banco import evaluar_banco

        self.gate_report = evaluar_banco(
            lambda q, i, d, e: super(LocalLlamaInterpreter, self).proponer(q, i, d, e),
            cancel_requested=self._bank_cancel_requested,
            progress=self._bank_progress,
            constrained_decoding=modo,
        )
        ok = bool(self.gate_report["passed"])
        self.ETIQUETA = "" if ok else "EXPERIMENTAL / NO VERIFICADO"
        if self.gate_report["cancelled"]:
            return False, "banco local cancelado; intérprete no admitido"
        return ok, "banco local superado" if ok else self.MOTIVO

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> InterpretationResult:
        listo, motivo = self.operativo()
        if not listo:
            return pendiente(
                motivo,
                self._provenance(
                    request_id=nuevo_request_id(),
                    inicio=time.monotonic(),
                    model_reported="",
                    raw="",
                    fallback_used=False,
                ),
            )
        return super().proponer(query, idea, domain, evidence)
