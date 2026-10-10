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
import time
from collections.abc import Callable
from dataclasses import replace
from typing import Any

import httpx

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
    ) -> None:
        self.base = (
            base_url or os.getenv("CRIBA_EXTERNAL_BASE_URL") or "http://127.0.0.1:8645/v1"
        ).rstrip("/")
        self.model = model or os.getenv("CRIBA_EXTERNAL_MODEL") or "stealth/space-bunny-alpha"
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
        }

    # -- estado real, no optimista ---------------------------------------
    def operativo(self) -> tuple[bool, str]:
        """Comprueba /models de verdad. Un backend no se declara listo por tener
        configuracion: tiene que responder."""
        if not self.base:
            return False, "sin CRIBA_EXTERNAL_BASE_URL"
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
        model_reported = ""
        raw_output = ""
        finish_reason = ""
        completion_tokens: int | None = None
        reasoning_tokens: int | None = None

        def _numero_opcional(value: Any) -> int | None:
            return value if type(value) is int and value >= 0 else None

        def _fallo(motivo: str, *, raw_para_hash: str | None = None) -> InterpretationResult:
            return InterpretationResult(
                estado=ESTADO_PENDIENTE,
                error=motivo,
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

        try:
            try:
                max_tokens = self.max_tokens
                if not 1 <= max_tokens <= 32768:
                    raise ValueError("max_tokens debe ser positivo")
            except ValueError:
                return replace(_fallo("configuracion_invalida:max_tokens"), model_requests=0)
            payload["max_tokens"] = max_tokens
            if not math.isfinite(self.timeout_s) or not 0 < self.timeout_s <= 1800:
                return replace(_fallo("configuracion_invalida:timeout"), model_requests=0)
            if not math.isfinite(self.temperature) or not 0 <= self.temperature <= 2:
                return replace(_fallo("configuracion_invalida:temperature"), model_requests=0)
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
                        _fallo("configuracion_invalida:reasoning_effort"), model_requests=0
                    )
                from urllib.parse import urlsplit

                if urlsplit(self.base).hostname == "openrouter.ai":
                    payload["reasoning"] = {"effort": self.reasoning_effort}
                else:
                    payload["reasoning_effort"] = self.reasoning_effort
            if self.enable_thinking is not None:
                payload["chat_template_kwargs"] = {"enable_thinking": self.enable_thinking}
            with httpx.Client(timeout=self.timeout_s) as client:
                resp = client.post(
                    f"{self.base}/chat/completions", json=payload, headers=self._headers()
                )
            if resp.status_code == 429:
                # El cuerpo puede contener metadatos de cuenta: se hashea para
                # procedencia, pero no se muestra ni se guarda como salida.
                return _fallo("plan_agotado_429", raw_para_hash=resp.text[:2000])
            if resp.status_code in (401, 403):
                return _fallo(f"credenciales rechazadas: HTTP {resp.status_code}")
            if resp.status_code >= 400:
                return _fallo(f"http_error_{resp.status_code}")

            try:
                cuerpo = resp.json()
            except ValueError as exc:
                return _fallo(f"respuesta_json_invalida:{type(exc).__name__}")
            if not isinstance(cuerpo, dict):
                return _fallo(f"respuesta_tipo_inesperado:{type(cuerpo).__name__}")
            model_reported = str(cuerpo.get("model") or "")
            choices = cuerpo.get("choices")
            if not isinstance(choices, list) or not choices:
                return _fallo("respuesta_sin_choices")
            eleccion = choices[0]
            if not isinstance(eleccion, dict):
                return _fallo(f"choice_tipo_inesperado:{type(eleccion).__name__}")

            finish_reason = str(eleccion.get("finish_reason") or "")
            uso = cuerpo.get("usage")
            if isinstance(uso, dict):
                completion_tokens = _numero_opcional(uso.get("completion_tokens"))
                detalles = uso.get("completion_tokens_details")
                if isinstance(detalles, dict):
                    reasoning_tokens = _numero_opcional(detalles.get("reasoning_tokens"))

            message = eleccion.get("message")
            if not isinstance(message, dict):
                return _fallo(f"message_tipo_inesperado:{type(message).__name__}")
            contenido = message.get("content")
            if contenido is None or (isinstance(contenido, str) and not contenido.strip()):
                if message.get("tool_calls"):
                    return _fallo("tool_calls_sin_contenido")
                return _fallo(
                    f"sin_contenido:finish_reason={finish_reason or 'desconocido'} "
                    f"tokens={completion_tokens} razonamiento={reasoning_tokens}"
                )
            if not isinstance(contenido, str):
                return _fallo(f"contenido_tipo_inesperado:{type(contenido).__name__}")
            raw_output = contenido
            if finish_reason == "length":
                return _fallo(
                    f"salida_truncada:finish_reason=length "
                    f"tokens={completion_tokens} ({len(raw_output)} chars)"
                )
            try:
                _extraer_json(raw_output)
            except (json.JSONDecodeError, ValueError) as exc:
                return _fallo(f"json_invalido:{type(exc).__name__}")
        except httpx.TimeoutException:
            return _fallo("timeout")
        except httpx.HTTPError as exc:
            tipo = type(exc).__name__
            log.warning("interpretacion %s fallo de transporte: %s", request_id, tipo)
            return _fallo(f"transporte_http:{tipo}")
        except Exception as exc:  # noqa: BLE001 - una propuesta nunca rompe el loop
            tipo = type(exc).__name__
            log.warning("interpretacion %s fallo: %s", request_id, tipo)
            return _fallo(f"proposal_failed:{tipo}")

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
