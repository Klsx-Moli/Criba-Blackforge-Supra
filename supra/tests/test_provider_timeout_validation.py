"""Timeout regression tests: real provider module, no external network."""

import httpx
import pytest
from supra_agentic.providers.openai_compatible import OpenAICompatibleProvider


@pytest.mark.parametrize(
    "value",
    [float("nan"), float("inf"), -float("inf"), True, False, 0, -1, "5", 10**1000],
    ids=["nan", "inf", "negative-inf", "true", "false", "zero", "negative", "string", "overflow"],
)
def test_invalid_explicit_timeout_is_rejected(value):
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(base_url="http://provider.test/v1", timeout=value)


@pytest.mark.parametrize("value", ["nan", "inf", "-inf", "0", "-1", "bad"])
def test_invalid_environment_timeout_is_rejected(monkeypatch, value):
    monkeypatch.setenv("SUPRA_PROVIDER_TIMEOUT", value)
    with pytest.raises(ValueError):
        OpenAICompatibleProvider(base_url="http://provider.test/v1")


@pytest.mark.parametrize("value", [0.001, 1, 60.0])
def test_positive_finite_timeout_is_preserved(value):
    provider = OpenAICompatibleProvider(base_url="http://provider.test/v1", timeout=value)
    assert provider.timeout == value


def test_missing_timeout_uses_finite_default(monkeypatch):
    monkeypatch.delenv("SUPRA_PROVIDER_TIMEOUT", raising=False)
    provider = OpenAICompatibleProvider(base_url="http://provider.test/v1")
    assert provider.timeout == 60.0


def test_explicit_timeout_overrides_invalid_environment(monkeypatch):
    monkeypatch.setenv("SUPRA_PROVIDER_TIMEOUT", "nan")
    provider = OpenAICompatibleProvider(base_url="http://provider.test/v1", timeout=2.5)
    assert provider.timeout == 2.5


def test_finite_timeout_preserves_real_http_contract():
    requests = []

    def handler(request):
        requests.append(request)
        assert request.extensions["timeout"] == {
            "connect": 2.5, "read": 2.5, "write": 2.5, "pool": 2.5,
        }
        return httpx.Response(
            200,
            json={"model": "test-model", "choices": [{"message": {"content": "ok"}}]},
        )

    provider = OpenAICompatibleProvider(
        base_url="http://provider.test/v1",
        default_model="test-model",
        timeout=2.5,
        transport=httpx.MockTransport(handler),
    )
    result = provider.generate([{"role": "user", "content": "hello"}])
    assert result.text == "ok"
    assert len(requests) == 1
    assert requests[0].url.path == "/v1/chat/completions"
