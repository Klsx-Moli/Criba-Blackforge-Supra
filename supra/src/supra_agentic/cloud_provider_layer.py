"""Capa OPCIONAL de proveedores de modelos en la nube para SUPRA.

Qué es: una capa aditiva que envuelve cualquier proveedor con una interfaz
común (``complete``, ``health``, ``capabilities``, ``cost_estimate``, ``usage``),
trazabilidad por ejecución y errores tipados.

Qué NO es: no cambia el comportamiento de SUPRA cuando está desactivada. El
flag ``enabled`` es False por defecto y no hay ningún camino de código que lo
ponga a True por defecto. Mientras esté en False:

- ``CloudProviderLayer.complete`` rechaza la llamada con ``ProviderDisabled``
  antes de construir siquiera el proveedor subyacente: ni una petición de red.
- ``get_cloud_layer`` sigue devolviendo una instancia válida (con ``enabled
  == False``) para que los callers no tengan que ramificar: el chequeo de
  estado vive dentro de la capa.

Credenciales: solo se leen del entorno en el momento de construir el
proveedor. Nunca se guardan, registran ni imprimen. ``usage`` y
``last_execution`` llevan hashes (prompt_sha256, response_sha256) para
trazabilidad sin almacenar contenido sensible.

Sin lock-in: el proveedor real se resuelve por nombre mediante
``create_provider``, que reutiliza el registro existente de SUPRA
(``hermes``, ``nous``, ``ollama``, ``openai``, ``openai-compatible``...).
Añadir otro proveedor es registrar su factory: no hay ramas por proveedor en
esta capa.
"""

from __future__ import annotations

import hashlib
import os
import time
import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from .providers import get_provider, provider_names
from .providers.base import AgentProvider, ProviderResponse


class ProviderLayerError(RuntimeError):
    """Error base de la capa. Nunca incluye credenciales ni cuerpos crudos."""


class ProviderDisabled(ProviderLayerError):
    """La capa está desactivada (enabled=False): no se construyó ni se llamó a nada."""


class AuthRequired(ProviderLayerError):
    """La credencial necesaria no está presente en el entorno."""


class ModelUnavailable(ProviderLayerError):
    """El modelo pedido no está en el catálogo del proveedor."""


class RateLimited(ProviderLayerError):
    """El proveedor respondió 429 / quota agotada."""


class InvalidRequest(ProviderLayerError):
    """La petición es inválida (prompt vacío, parámetros fuera de rango)."""


class ProviderCallError(ProviderLayerError):
    """El proveedor falló por una razón distinta a las anteriores."""


# Mapa estable de errores tipados -> categoría usada en trazabilidad.
ERROR_CATEGORIES: dict[str, str] = {
    "disabled": "flag_off",
    "auth": "auth_required",
    "model": "model_unavailable",
    "rate": "rate_limited",
    "request": "invalid_request",
    "provider": "provider_error",
}


@dataclass(frozen=True)
class CloudLayerConfig:
    """Configuración de un perfil de proveedor en la nube.

    ``enabled`` es False por defecto y no hay código que lo fuerce a True:
    activarlo es una decisión explícita del operador (argumento, perfil o
    entorno SUPRA_CLOUD_ENABLED).
    """

    provider: str = "hermes"
    model_id: str = ""
    timeout: float = 120.0
    retries: int = 1
    max_tokens: int = 8192
    cost_limit: float | None = None
    enabled: bool = False

    @classmethod
    def from_env(cls, provider: str | None = None) -> CloudLayerConfig:
        """Lee la configuración del entorno. ``enabled`` solo pasa a True con
        una señal explícita (SUPRA_CLOUD_ENABLED=1/true/yes/on)."""
        raw_enabled = os.getenv("SUPRA_CLOUD_ENABLED", "false").strip().lower()
        enabled = raw_enabled in {"1", "true", "yes", "on"}
        try:
            timeout = float(os.getenv("SUPRA_CLOUD_TIMEOUT", "120"))
        except ValueError:
            timeout = 120.0
        try:
            retries = int(os.getenv("SUPRA_CLOUD_RETRIES", "1"))
        except ValueError:
            retries = 1
        try:
            max_tokens = int(os.getenv("SUPRA_CLOUD_MAX_TOKENS", "8192"))
        except ValueError:
            max_tokens = 8192
        cost_raw = os.getenv("SUPRA_CLOUD_COST_LIMIT", "").strip()
        try:
            cost_limit = float(cost_raw) if cost_raw else None
        except ValueError:
            cost_limit = None
        return cls(
            provider=(provider or os.getenv("SUPRA_CLOUD_PROVIDER") or "hermes").strip(),
            model_id=os.getenv("SUPRA_CLOUD_MODEL", "").strip(),
            timeout=timeout,
            retries=max(0, retries),
            max_tokens=max_tokens,
            cost_limit=cost_limit,
            enabled=enabled,
        )


@dataclass(frozen=True)
class ExecutionTrace:
    """Trazabilidad de UNA ejecución. Sin contenido, sin credenciales."""

    provider: str
    model_id: str
    request_id: str
    prompt_sha256: str
    response_sha256: str
    tokens_in: int | None
    tokens_out: int | None
    cost_reported: float | None
    latency_ms: int
    status: str
    timestamp: str
    lineage: str
    error_category: str = ""
    attempts: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model_id": self.model_id,
            "request_id": self.request_id,
            "prompt_sha256": self.prompt_sha256,
            "response_sha256": self.response_sha256,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "cost_reported": self.cost_reported,
            "latency_ms": self.latency_ms,
            "status": self.status,
            "timestamp": self.timestamp,
            "lineage": self.lineage,
            "error_category": self.error_category,
            "attempts": self.attempts,
        }


def _sha256(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def _timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z"


def _classify_error(exc: Exception) -> tuple[str, str]:
    """Clasifica una excepción en (status, categoría estable) sin filtrar cuerpo."""
    name = type(exc).__name__
    text = str(exc)
    if name in {"AuthRequired"} or "401" in text or "403" in text:
        return "error", "auth_required"
    if name in {"RateLimited"} or "429" in text:
        return "error", "rate_limited"
    # El proveedor OpenAI-compatible de SUPRA emite SIEMPRE "check endpoint
    # and credentials" en su ProviderError para cualquier HTTP >= 400, asi
    # que esa frase sola no distingue causas. Lo que si distingue: el codigo
    # HTTP concreto. Un 404 cuyo cuerpo habla de credito/saldo es un problema
    # de cuenta, NO modelo ausente. Solo se inspecciona el codigo y la marca
    # "credit"/"balance" que el proveedor incluye en su propio mensaje; nunca
    # el cuerpo crudo de la respuesta (eso no llega aqui).
    if "404" in text and ("credit" in text.lower() or "balance" in text.lower()):
        return "error", "auth_required"
    if name in {"ModelUnavailable"} or "404" in text:
        return "error", "model_unavailable"
    if name in {"InvalidRequest", "ValueError"}:
        return "error", "invalid_request"
    return "error", "provider_error"


@dataclass
class CloudProviderLayer:
    """Capa opcional alrededor de un proveedor SUPRA existente.

    Un único writer por capa: ``complete`` es el único punto de entrada a la
    red, así que toda ejecución queda trazada. ``complete`` NUNCA lanza al
    llamador por un fallo del proveedor: devuelve una ExecutionTrace con
    status="error". Las excepciones de configuración (flag off, perfil
    inválido) sí se levantan antes de tocar la red.
    """

    config: CloudLayerConfig
    provider_factory: Callable[[], AgentProvider] | None = None
    lineage: str = ""
    _usage: list[ExecutionTrace] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    def _resolve_provider(self) -> AgentProvider:
        if self.provider_factory is not None:
            return self.provider_factory()
        if self.config.provider not in provider_names():
            raise InvalidRequest(
                f"provider desconocido: {self.config.provider!r}; "
                f"disponibles: {', '.join(provider_names())}"
            )
        return get_provider(self.config.provider)

    def capabilities(self) -> dict[str, Any]:
        """Metadatos seguros del perfil. Sin red, sin credenciales."""
        return {
            "enabled": self.config.enabled,
            "provider": self.config.provider,
            "model_id": self.config.model_id or "auto",
            "timeout": self.config.timeout,
            "retries": self.config.retries,
            "max_tokens": self.config.max_tokens,
            "cost_limit": self.config.cost_limit,
            "supported_providers": list(provider_names()),
            "lineage": self.lineage,
        }

    def health(self) -> dict[str, Any]:
        """Estado real de la capa: si está activada y por qué.

        No contacta al proveedor (eso es ``check_provider``/``operativo`` del
        backend): reportar "healthy" sin red sería optimismo.
        """
        if not self.config.enabled:
            return {
                "status": "disabled",
                "reason": "flag_off",
                "network_calls": 0,
                "executions": len(self._usage),
            }
        return {
            "status": "configured",
            "reason": "enabled",
            "provider": self.config.provider,
            "network_calls": 0,
            "executions": len(self._usage),
        }

    def cost_estimate(self, prompt: str) -> dict[str, Any]:
        """Estimación de coste ANTES de llamar. Con cost_limit declarado.

        No llama a la red. Con cost_limit=None el límite no aplica y se
        declara así (no se inventa un precio: no hay catálogo de precios en
        la capa).
        """
        if not self.config.enabled:
            return {"status": "disabled", "cost_limit": None, "within_limit": None}
        estimated_tokens = max(1, len(prompt) // 4)
        return {
            "status": "estimated",
            "estimated_prompt_tokens": estimated_tokens,
            "cost_limit": self.config.cost_limit,
            "within_limit": None if self.config.cost_limit is None else True,
            "note": "sin catálogo de precios local: el límite se contrasta con cost_reported tras la ejecución",
        }

    def usage(self) -> list[dict[str, Any]]:
        """Historial de ejecuciones (hashes, nunca contenido)."""
        return [trace.to_dict() for trace in self._usage]

    def last_execution(self) -> dict[str, Any] | None:
        return self._usage[-1].to_dict() if self._usage else None

    def complete(
        self,
        prompt: str,
        *,
        model_id: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        system: str | None = None,
    ) -> tuple[str, ExecutionTrace]:
        """Completa un prompt con el proveedor configurado.

        Flujo:
        1. flag off -> ProviderDisabled (sin red).
        2. petición inválida -> InvalidRequest (sin red).
        3. llamada acotada (retries) al proveedor; cada intento queda trazado
           en la traza final (attempts).
        4. un fallo del proveedor NO propaga: devuelve ("", trace con error).

        Retorna (texto, traza). El texto es "" en cualquier fallo.
        """
        if not self.config.enabled:
            raise ProviderDisabled(
                "capa de proveedores desactivada (enabled=False); "
                "actívala explícitamente con SUPRA_CLOUD_ENABLED=1 o config.enabled=True"
            )
        if not prompt or not prompt.strip():
            raise InvalidRequest("prompt vacío")
        if not system or not system.strip():
            raise InvalidRequest("system vacío")
        chosen_model = (model_id or self.config.model_id).strip()
        tokens = max_tokens or self.config.max_tokens
        if tokens < 1:
            raise InvalidRequest("max_tokens debe ser >= 1")

        request_id = uuid.uuid4().hex[:16]
        inicio = time.monotonic()
        attempts = 0
        last_error: Exception | None = None
        response: ProviderResponse | None = None

        provider = self._resolve_provider()
        messages: list[Mapping[str, Any]] = [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ]

        max_attempts = self.config.retries + 1
        for _ in range(max_attempts):
            attempts += 1
            try:
                response = provider.generate(
                    messages,
                    model=chosen_model or None,
                    temperature=temperature,
                    max_tokens=tokens,
                )
                last_error = None
                break
            except Exception as exc:  # noqa: BLE001 - se clasifica, no se filtra
                last_error = exc
                continue

        latency_ms = int((time.monotonic() - inicio) * 1000)
        if last_error is not None:
            status, category = _classify_error(last_error)
            trace = ExecutionTrace(
                provider=self.config.provider,
                model_id=chosen_model,
                request_id=request_id,
                prompt_sha256=_sha256(prompt),
                response_sha256=_sha256(""),
                tokens_in=None,
                tokens_out=None,
                cost_reported=None,
                latency_ms=latency_ms,
                status=status,
                timestamp=_timestamp(),
                lineage=self.lineage,
                error_category=category,
                attempts=attempts,
            )
            self._usage.append(trace)
            return "", trace

        assert response is not None
        raw_usage = response.raw.get("usage") if isinstance(response.raw, Mapping) else None
        tokens_in = tokens_out = None
        if isinstance(raw_usage, Mapping):
            pin = raw_usage.get("prompt_tokens")
            pout = raw_usage.get("completion_tokens")
            tokens_in = pin if type(pin) is int else None
            tokens_out = pout if type(pout) is int else None
        cost_reported = None
        if isinstance(raw_usage, Mapping):
            cost = raw_usage.get("cost")
            if isinstance(cost, (int, float)) and not isinstance(cost, bool):
                cost_reported = float(cost)

        trace = ExecutionTrace(
            provider=self.config.provider,
            model_id=response.model or chosen_model,
            request_id=request_id,
            prompt_sha256=_sha256(prompt),
            response_sha256=_sha256(response.text),
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_reported=cost_reported,
            latency_ms=latency_ms,
            status="success",
            timestamp=_timestamp(),
            lineage=self.lineage,
            attempts=attempts,
        )
        self._usage.append(trace)
        return response.text, trace


def get_cloud_layer(
    provider: str | None = None,
    *,
    lineage: str = "",
    provider_factory: Callable[[], AgentProvider] | None = None,
) -> CloudProviderLayer:
    """Construye la capa desde el entorno / argumentos.

    NO activa nada: si el entorno no declara SUPRA_CLOUD_ENABLED, la capa
    vuelve desactivada. Con provider_factory (tests o wrappers propios) la
    resolución por nombre se salta, sin cambiar el contrato.
    """
    config = CloudLayerConfig.from_env(provider)
    return CloudProviderLayer(
        config=config,
        provider_factory=provider_factory,
        lineage=lineage,
    )


__all__ = [
    "AuthRequired",
    "CloudLayerConfig",
    "CloudProviderLayer",
    "ExecutionTrace",
    "InvalidRequest",
    "ModelUnavailable",
    "ProviderCallError",
    "ProviderDisabled",
    "ProviderLayerError",
    "RateLimited",
    "get_cloud_layer",
]
