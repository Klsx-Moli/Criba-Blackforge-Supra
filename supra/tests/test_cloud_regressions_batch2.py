"""Regression tests for complete real provider modules; network is mocked."""
import json

import httpx
import pytest
from supra_agentic.cloud_provider_layer import (
    CloudLayerConfig,
    CloudProviderLayer,
    InvalidRequest,
    ProviderDisabled,
)
from supra_agentic.providers.base import ProviderResponse
from supra_agentic.providers.openai_compatible import OpenAICompatibleProvider


class RecordingProvider:
    def __init__(self, usage=None):
        self.calls = []
        self.raw_usage = {} if usage is None else usage
    def generate(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        return ProviderResponse(text="answer", model="test-model", raw={"usage": self.raw_usage})


def layer_with(**config):
    provider = RecordingProvider()
    factories = []
    def factory():
        factories.append(True)
        return provider
    layer = CloudProviderLayer(CloudLayerConfig(enabled=True, retries=0, **config), provider_factory=factory)
    return layer, provider, factories


@pytest.mark.parametrize("value", [0, False, True, -1, 0.5, 1.0, "5", float("nan"), float("inf")])
def test_explicit_invalid_max_tokens_never_resolves_provider(value):
    layer, provider, factories = layer_with()
    with pytest.raises(InvalidRequest):
        layer.complete("hello", system="system", max_tokens=value)
    assert not factories and not provider.calls


@pytest.mark.parametrize("value", [0, False, True, -1, 0.5, "5"])
def test_invalid_default_max_tokens_never_resolves_provider(value):
    layer, provider, factories = layer_with(max_tokens=value)
    with pytest.raises(InvalidRequest):
        layer.complete("hello", system="system")
    assert not factories and not provider.calls


@pytest.mark.parametrize("value", [False, True, -1, 0.5, "2", None])
def test_invalid_retries_are_invalid_request_not_assert_or_type_error(value):
    provider = RecordingProvider()
    layer = CloudProviderLayer(CloudLayerConfig(enabled=True, retries=value), provider_factory=lambda: provider)
    with pytest.raises(InvalidRequest):
        layer.complete("hello", system="system")
    assert not provider.calls


@pytest.mark.parametrize("field", ["prompt", "system"])
@pytest.mark.parametrize("value", [None, [], {}, 1, True, b"text"])
def test_non_text_input_is_typed_invalid_request_without_provider(field, value):
    layer, provider, factories = layer_with()
    kwargs = {"prompt": "hello", "system": "system", field: value}
    with pytest.raises(InvalidRequest):
        layer.complete(**kwargs)
    assert not factories and not provider.calls


@pytest.mark.parametrize("value", ["false", "true", 1, [], None])
def test_only_literal_true_activates_layer(value):
    provider = RecordingProvider()
    layer = CloudProviderLayer(CloudLayerConfig(enabled=value), provider_factory=lambda: provider)
    with pytest.raises(ProviderDisabled):
        layer.complete("hello", system="system")
    assert layer.enabled is False
    assert layer.health()["status"] == "disabled"
    assert layer.capabilities()["enabled"] is False
    assert not provider.calls


@pytest.mark.parametrize("value", [None, 0, 1, 10.0])
def test_no_price_information_is_not_a_budget_pass(value):
    layer, _, factories = layer_with(cost_limit=value)
    assert layer.cost_estimate("hello")["within_limit"] is None
    assert not factories


@pytest.mark.parametrize("cost", [float("nan"), float("inf"), -float("inf"), -1, 10**1000])
def test_invalid_reported_cost_is_unknown_and_json_serializable(cost):
    layer, provider, _ = layer_with()
    provider.raw_usage = {"cost": cost}
    _, trace = layer.complete("hello", system="system")
    assert trace.cost_reported is None
    json.dumps(trace.to_dict(), allow_nan=False)


@pytest.mark.parametrize("cost", [0, 0.001, 7])
def test_valid_reported_cost_is_preserved(cost):
    layer, provider, _ = layer_with()
    provider.raw_usage = {"cost": cost}
    _, trace = layer.complete("hello", system="system")
    assert trace.cost_reported == float(cost)


@pytest.mark.parametrize("field", ["prompt_tokens", "completion_tokens"])
@pytest.mark.parametrize("count", [-1, True, "2", 1.5])
def test_invalid_token_usage_is_unknown(field, count):
    layer, provider, _ = layer_with()
    provider.raw_usage = {field: count}
    _, trace = layer.complete("hello", system="system")
    assert (trace.tokens_in if field == "prompt_tokens" else trace.tokens_out) is None


def test_none_uses_default_but_valid_override_is_preserved():
    layer, provider, _ = layer_with(max_tokens=12)
    layer.complete("hello", system="system")
    assert provider.calls[-1][1]["max_tokens"] == 12
    layer.complete("hello", system="system", max_tokens=1)
    assert provider.calls[-1][1]["max_tokens"] == 1


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), True, False, 0, -1, "5", 10**1000])
def test_invalid_explicit_provider_timeout_is_rejected(value):
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(base_url="http://provider.test/v1", timeout=value)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1", "bad"])
def test_invalid_environment_timeout_is_rejected(monkeypatch, value):
    monkeypatch.setenv("SUPRA_PROVIDER_TIMEOUT", value)
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(base_url="http://provider.test/v1")


def test_real_http_provider_success_and_request_contract():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"model": "test", "choices": [{"message": {"content": "answer"}}],
                                       "usage": {"prompt_tokens": 2, "completion_tokens": 3, "cost": 0}})
    provider = OpenAICompatibleProvider(base_url="http://provider.test/v1", api_key="dummy-test-token", default_model="test",
                                        transport=httpx.MockTransport(handler), timeout=1)
    layer = CloudProviderLayer(CloudLayerConfig(enabled=True, retries=0), provider_factory=lambda: provider)
    text, trace = layer.complete("hello", system="system", max_tokens=3)
    assert text == "answer" and trace.status == "success"
    assert trace.tokens_in == 2 and trace.tokens_out == 3 and trace.cost_reported == 0
    assert len(requests) == 1
    assert requests[0].url.path == "/v1/chat/completions"
    assert json.loads(requests[0].content)["max_tokens"] == 3
    assert "dummy-test-token" not in str(layer.usage())
