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
import os
import time
from typing import Any

import httpx

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
# Medido el 2026-10-03: con 2048 el modelo de razonamiento consumio 1988 tokens
# pensando, devolvio content=null y no emitio propuesta. El adaptador anterior
# pedia 4096 para proponer; bajar eso fue una regresion mia. Configurable porque
# depende del modelo elegido.
MAX_TOKENS = 4096
TEMPERATURA = 0.2

# Un id de modelo inventado devuelve 404 desde el catalogo. Se comprueba al
# arrancar y se dice cual se pidio y cual respondio.
_SYSTEM = "Eres un intérprete de cruces de técnicas. Respondes solo JSON válido."


def _extraer_json(contenido: str) -> dict[str, Any]:
    """Saca el objeto JSON de una respuesta que puede venir envuelta.

    No es permisivo con el contenido: solo quita vallas de markdown y recorta
    hasta el primer objeto completo. Si no hay JSON, se levanta el error y el
    llamador degrada a pendiente con el motivo real.
    """
    raw = (contenido or "").strip()
    if raw.startswith("```json"):
        raw = raw[len("```json") :]
    elif raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()
    try:
        parsed = json.loads(raw)
    except ValueError:
        inicio = raw.find("{")
        fin = raw.rfind("}")
        if inicio == -1 or fin <= inicio:
            raise
        parsed = json.loads(raw[inicio : fin + 1])
    if not isinstance(parsed, dict):
        raise ValueError("la respuesta no es un objeto JSON")
    return parsed


def construir_prompt(
    query: str,
    idea: dict[str, Any],
    domain: dict[str, Any] | None,
    evidence: list[dict[str, Any]] | None,
) -> str:
    """El prompt, sin tocarlo: es el mismo que ya usaba el adaptador.

    Se conserva literal a proposito. Cambiarlo y el parser a la vez haria
    imposible atribuir un fallo a uno u otro.
    """
    dominio = str((domain or {}).get("title") or "general")
    bloque_evidencia = ""
    for i, ev in enumerate((evidence or [])[:3], 1):
        titulo = str(ev.get("title") or "").strip()
        resumen = str(ev.get("abstract") or "").strip()
        if titulo or resumen:
            bloque_evidencia += f"{i}. {titulo}: {resumen[:200]}\n"
    if bloque_evidencia:
        bloque_evidencia = (
            "\nEVIDENCIA LOCAL PERTINENTE (apóyate solo en la que sirva y "
            "cítala por número si la usas):\n" + bloque_evidencia
        )
    bloqueo = idea.get("bloqueo") or {}
    bloqueo_bloque = ""
    if bloqueo.get("bloqueo"):
        bloqueo_bloque = f"""

BLOQUEO IDENTIFICADO (origen declarado: {bloqueo.get("origen_bloqueo", "hipotesis")}):"""
        bloqueo_bloque += f"\n{str(bloqueo.get('bloqueo'))[:400]}"
        bloqueo_bloque += f"\nExplicación: {str(bloqueo.get('explicacion_bloqueo', ''))[:300]}"
        bloqueo_bloque += f"\nResultado buscado: {str(bloqueo.get('resultado_buscado', ''))[:200]}"
        restricciones = str(bloqueo.get("restricciones_obligatorias", []))[:200]
        bloqueo_bloque += f"\nTus restricciones obligatorias: {restricciones}"
        bloqueo_bloque += (
            '\nAñade "ruta_desbloqueo" al JSON con la ruta elegida y su justificación.'
        )
    return f"""Aplica el cruce de técnicas a este problema concreto.

PROBLEMA: {query}
DOMINIO DE ACOPLAMIENTO: {dominio}

CRUCE (dos operadores):
Técnica A: {idea.get("method1", idea.get("title", ""))}
Técnica B: {idea.get("method2", "")}
Título del cruce: {idea.get("title", "")}
{bloqueo_bloque}{bloque_evidencia}
Responde ÚNICAMENTE con JSON válido (nada de markdown) con esta estructura:

{{
  "hipotesis": "propuesta específica para ESTE problema",
  "mecanismo": "cómo funciona causalmente, en términos del dominio",
  "aportacion_por_tecnica": ["qué aporta la técnica A aquí", "qué aporta la técnica B aquí"],
  "supuestos": ["supuesto cuestionable 1"],
  "prueba_concreta": "comparación mínima con métrica y condición de fracaso"
}}

El mecanismo es obligatorio y debe referirse al problema, no a los nombres
de las técnicas. Si el cruce no produce nada pertinente, dilo en hipótesis."""


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
    ) -> None:
        self.base = (
            base_url or os.getenv("CRIBA_EXTERNAL_BASE_URL") or "http://127.0.0.1:8645/v1"
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("CRIBA_EXTERNAL_MODEL")
            or "stealth/space-bunny-alpha"
        )
        # La clave se lee SOLO del entorno y nunca se escribe en logs ni en la
        # procedencia. Un proxy local acepta cualquier bearer.
        self._api_key = api_key if api_key is not None else os.getenv("CRIBA_EXTERNAL_API_KEY", "")
        self.timeout_s = float(
            timeout_s
            if timeout_s is not None
            else os.getenv("CRIBA_EXTERNAL_TIMEOUT_S", TIMEOUT_POR_DEFECTO)
        )
        self.fallback_local = (
            fallback_local
            if fallback_local is not None
            else os.getenv("CRIBA_EXTERNAL_FALLBACK_LOCAL", "false").lower() == "true"
        )
        self.provider = os.getenv(
            "CRIBA_EXTERNAL_PROVIDER", "nous_oauth_subscription_proxy"
        ).strip() or "nous_oauth_subscription_proxy"

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
            if self.model not in ids:
                return False, (
                    f"el modelo {self.model!r} no esta en el catalogo del endpoint "
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
        self, *, request_id: str, inicio: float, model_reported: str, raw: str, fallback_used: bool
    ) -> Provenance:
        return Provenance(
            interpreter_backend=self.backend,
            provider=self.provider,
            model_requested=self.model,
            model_reported=model_reported or "",
            endpoint=sin_secretos(self.base),
            timestamp=marca_temporal(),
            duration_ms=int((time.monotonic() - inicio) * 1000),
            prompt_version=PROMPT_VERSION,
            schema_version=SCHEMA_VERSION,
            request_id=request_id,
            fallback_used=fallback_used,
            raw_output_sha256=hash_salida(raw),
        )

    # -- la operacion del puerto ------------------------------------------
    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> InterpretationResult:
        request_id = nuevo_request_id()
        inicio = time.monotonic()
        prompt = construir_prompt(query, idea, domain, evidence)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": _SYSTEM},
                {"role": "user", "content": prompt},
            ],
            "temperature": TEMPERATURA,
            "max_tokens": int(os.getenv("CRIBA_EXTERNAL_MAX_TOKENS", MAX_TOKENS)),
            # Solicita texto JSON; no se exponen tools, terminal, archivos ni el
            # agente Hermes a la salida del modelo.
            "response_format": {"type": "json_object"},
        }
        model_reported = ""
        raw_output = ""
        finish_reason = ""
        completion_tokens: int | None = None
        reasoning_tokens: int | None = None

        def _numero_opcional(value: Any) -> int | None:
            try:
                return int(value) if value is not None else None
            except (TypeError, ValueError):
                return None

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
                ),
                raw_output=raw_output,
                finish_reason=finish_reason,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
            )

        try:
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
                    f"tokens={completion_tokens or 0} razonamiento={reasoning_tokens or 0}"
                )
            if not isinstance(contenido, str):
                return _fallo(f"contenido_tipo_inesperado:{type(contenido).__name__}")
            raw_output = contenido
            if finish_reason == "length":
                return _fallo(
                    f"salida_truncada:finish_reason=length "
                    f"tokens={completion_tokens or 0} ({len(raw_output)} chars)"
                )
            try:
                parsed = _extraer_json(raw_output)
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

        resultado = InterpretationResult(
            estado=ESTADO_PROPUESTA,
            hipotesis=str(parsed.get("hipotesis", "")),
            mecanismo=str(parsed.get("mecanismo", "")),
            aportacion_por_tecnica=[str(x) for x in (parsed.get("aportacion_por_tecnica") or [])],
            supuestos=[str(x) for x in (parsed.get("supuestos") or [])],
            prueba_concreta=str(parsed.get("prueba_concreta", "")),
            ruta_desbloqueo=str(parsed.get("ruta_desbloqueo", "")),
            provenance=self._provenance(
                request_id=request_id,
                inicio=inicio,
                model_reported=model_reported,
                raw=raw_output,
                fallback_used=False,
            ),
            raw_output=raw_output,
            finish_reason=finish_reason,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
        )
        if not resultado.es_propuesta:
            # PROPUESTA sin mecanismo no es una propuesta. Se degrada con el
            # motivo, sin rellenar el hueco ni perder el diagnóstico bruto.
            return InterpretationResult(
                estado=ESTADO_PENDIENTE,
                error=resultado.motivo_real(),
                provenance=resultado.provenance,
                raw_output=raw_output,
                finish_reason=finish_reason,
                completion_tokens=completion_tokens,
                reasoning_tokens=reasoning_tokens,
            )
        return resultado


class LocalLlamaInterpreter:
    """El GGUF local. Genera ideas; la interpretación NO está operativa.

    Se mantiene en el selector para diagnóstico y reparación futura, y se
    declara como lo que es. No devuelve propuestas: devolver una plantilla
    sería presentar relleno como si fuera una interpretación, que es
    exactamente lo que el resto del sistema prohíbe.

    Para considerarlo operativo tiene que pasar el mismo E2E que el externo:
    esquema válido, dossier, SupraClient, persistencia en SUPRA, GET y
    presencia en Shadow.
    """

    backend = "local_llama"
    provider = "local_gguf"

    ETIQUETA = "EXPERIMENTAL / NO VERIFICADO"
    MOTIVO = (
        "el modelo local genera ideas pero no tiene interpretación operativa: "
        "no existe todavia un contrato validado que convierta su salida en "
        "propuesta. Se mantiene en el selector para diagnostico."
    )

    def operativo(self) -> tuple[bool, str]:
        return False, self.MOTIVO

    def proponer(
        self,
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None = None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> InterpretationResult:
        return pendiente(
            self.MOTIVO,
            Provenance(
                interpreter_backend=self.backend,
                provider=self.provider,
                model_requested=str(os.getenv("CRIBA_LOCAL_MODEL", "local-gguf")),
                model_reported="",
                endpoint=sin_secretos(os.getenv("CRIBA_LOCAL_BASE", "local")),
                timestamp=marca_temporal(),
                duration_ms=0,
                prompt_version=PROMPT_VERSION,
                schema_version=SCHEMA_VERSION,
                request_id=nuevo_request_id(),
                fallback_used=False,
                raw_output_sha256="",
            ),
        )
