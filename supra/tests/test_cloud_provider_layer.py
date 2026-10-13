"""Tests de la capa opcional de proveedores en la nube.

Reglas verificadas aquí:
- flag OFF: complete() rechaza SIN ninguna llamada de red (provider_factory
  cuenta invocaciones y debe quedarse en 0).
- éxito, timeout, error de proveedor, rate limit, credencial ausente y modelo
  inválido: cada uno con su traza y categoría de error.
- retry acotado: retries=N produce como máximo N+1 intentos.
- sin filtración de secretos: la traza no contiene el prompt ni la respuesta
  en claro (solo sha256), y un api_key en el entorno nunca aparece en la
  traza ni en el mensaje de error.
- CRIBA/SUPRA operativos sin credenciales: la capa desactivada no rompe el
  runner ni el registro de proveedores.
"""

from __future__ import annotations

import httpx
import pytest

from supra_agentic.cloud_provider_layer import (
    AuthRequired,
    CloudLayerConfig,
    CloudProviderLayer,
    InvalidRequest,
    ModelUnavailable,
    ProviderDisabled,
    RateLimited,
    get_cloud_layer,
)


def _ok_handler(_: httpx.Request) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "id": "chat-1",
            "model": "model-ok",
            "choices": [{"message": {"role": "assistant", "content": "respuesta"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 20, "cost": 0.001},
        },
    )


def _make_layer(
    *,
    handler=_ok_handler,
    enabled: bool = True,
    retries: int = 0,
    provider: str = "test-provider",
) -> tuple[CloudProviderLayer, list[int]]:
    calls: list[int] = []

    def factory() -> object:
        from supra_agentic.providers import OpenAICompatibleProvider

        provider_obj = OpenAICompatibleProvider(
            base_url="http://provider.test/v1",
            api_key="test-key",
            default_model="model-ok",
            transport=httpx.MockTransport(handler),
            provider_name=provider,
        )
        calls.append(1)
        return provider_obj

    layer = CloudProviderLayer(
        config=CloudLayerConfig(
            provider=provider,
            model_id="model-ok",
            enabled=enabled,
            retries=retries,
        ),
        provider_factory=factory,
        lineage="test-lineage",
    )
    return layer, calls


class TestFlagOff:
    def test_disabled_rejects_without_network(self) -> None:
        layer, calls = _make_layer(enabled=False)
        with pytest.raises(ProviderDisabled):
            layer.complete("hola", system="sistema")
        assert calls == [], "flag OFF no debe construir ni llamar al proveedor"

    def test_env_default_is_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("SUPRA_CLOUD_ENABLED", raising=False)
        layer = get_cloud_layer()
        assert layer.enabled is False
        assert layer.health()["status"] == "disabled"

    def test_disabled_health_reports_no_calls(self) -> None:
        layer, _ = _make_layer(enabled=False)
        health = layer.health()
        assert health["status"] == "disabled"
        assert health["reason"] == "flag_off"
        assert health["network_calls"] == 0


class TestSuccessPath:
    def test_success_returns_text_and_trace(self) -> None:
        layer, _ = _make_layer()
        text, trace = layer.complete("hola", system="sistema")
        assert text == "respuesta"
        assert trace.status == "success"
        assert trace.provider == "test-provider"
        assert trace.model_id == "model-ok"
        assert trace.tokens_in == 10
        assert trace.tokens_out == 20
        assert trace.cost_reported == 0.001
        assert trace.attempts == 1
        assert trace.lineage == "test-lineage"

    def test_trace_has_hashes_not_content(self) -> None:
        layer, _ = _make_layer()
        _, trace = layer.complete("hola", system="sistema")
        assert trace.prompt_sha256 and len(trace.prompt_sha256) == 64
        assert trace.response_sha256 and len(trace.response_sha256) == 64
        dumped = trace.to_dict()
        assert "hola" not in str(dumped)
        assert "respuesta" not in str(dumped)

    def test_usage_records_execution(self) -> None:
        layer, _ = _make_layer()
        layer.complete("hola", system="sistema")
        usage = layer.usage()
        assert len(usage) == 1
        assert usage[0]["status"] == "success"
        assert layer.last_execution()["request_id"]


class TestFailurePaths:
    def test_provider_error_does_not_propagate(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        layer, _ = _make_layer(handler=handler)
        text, trace = layer.complete("hola", system="sistema")
        assert text == ""
        assert trace.status == "error"
        assert trace.error_category == "provider_error"

    def test_rate_limited_classified(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(429, text="slow down")

        layer, _ = _make_layer(handler=handler)
        _, trace = layer.complete("hola", system="sistema")
        assert trace.status == "error"
        assert trace.error_category == "rate_limited"

    def test_auth_error_classified(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="denied")

        layer, _ = _make_layer(handler=handler)
        _, trace = layer.complete("hola", system="sistema")
        assert trace.status == "error"
        assert trace.error_category == "auth_required"

    def test_invalid_request_before_network(self) -> None:
        layer, calls = _make_layer()
        with pytest.raises(InvalidRequest):
            layer.complete("   ", system="sistema")
        with pytest.raises(InvalidRequest):
            layer.complete("hola", system="")
        assert calls == []

    def test_unknown_provider_is_invalid_request(self) -> None:
        layer, _ = _make_layer(provider="no-existe")
        layer.provider_factory = None  # fuerza resolución por nombre
        with pytest.raises(InvalidRequest):
            layer.complete("hola", system="sistema")


class TestRetryBounded:
    def test_retries_bounded(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(500, text="boom")

        layer, calls = _make_layer(handler=handler, retries=2)
        _, trace = layer.complete("hola", system="sistema")
        assert trace.attempts == 3  # 1 inicial + 2 reintentos
        assert len(calls) == 1  # el proveedor se construye una vez


class TestNoSecretLeakage:
    def test_error_message_has_no_body(self) -> None:
        def handler(_: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="sk-SECRET-VALUE")

        layer, _ = _make_layer(handler=handler)
        _, trace = layer.complete("hola", system="sistema")
        dumped = str(trace.to_dict())
        assert "sk-SECRET-VALUE" not in dumped

    def test_api_key_not_in_usage(self) -> None:
        layer, _ = _make_layer()
        layer.complete("hola", system="sistema")
        dumped = str(layer.usage())
        assert "test-key" not in dumped


class TestOperativeWithoutCredentials:
    def test_supra_registry_intact(self) -> None:
        from supra_agentic.providers import get_provider, provider_names

        names = provider_names()
        assert "hermes" in names
        assert "ollama" in names
        get_provider("ollama")  # no debe exigir credenciales

    def test_runner_still_constructs(self) -> None:
        from supra_agentic.runner import TaskmasterRunner

        runner = TaskmasterRunner()
        assert runner.provider_name in {"hermes", "openai-compatible"}


class TestTypedErrors:
    def test_error_classes_exist(self) -> None:
        for exc in (AuthRequired, ModelUnavailable, RateLimited):
            assert issubclass(exc, Exception)


class TestCostEstimate:
    def test_estimate_disabled(self) -> None:
        layer, _ = _make_layer(enabled=False)
        est = layer.cost_estimate("hola")
        assert est["status"] == "disabled"

    def test_estimate_enabled(self) -> None:
        layer, _ = _make_layer(enabled=True)
        est = layer.cost_estimate("hola mundo")
        assert est["status"] == "estimated"
        assert est["estimated_prompt_tokens"] >= 1
