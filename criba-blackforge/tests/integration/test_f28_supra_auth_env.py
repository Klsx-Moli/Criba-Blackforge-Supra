"""F28: service bearer credentials are separate from inference-provider credentials.

All requests use httpx.MockTransport; no network, model or paid inference.
"""
from __future__ import annotations

import httpx
import pytest

from criba.integrations.supra_client import SupraClient, SupraClientConfig


@pytest.mark.parametrize(
    ("service_token", "provider_key", "expected"),
    [
        ("service-auth-only", "provider-secret", "Bearer service-auth-only"),
        ("service-auth-only", "", "Bearer service-auth-only"),
        ("", "provider-secret", None),
        ("", "", None),
    ],
)
def test_service_auth_env_never_uses_provider_key(
    monkeypatch, service_token, provider_key, expected,
):
    monkeypatch.setenv("SUPRA_ENDPOINT", "http://127.0.0.1:8080")
    if service_token:
        monkeypatch.setenv("SUPRA_API_TOKEN", service_token)
    else:
        monkeypatch.delenv("SUPRA_API_TOKEN", raising=False)
    if provider_key:
        monkeypatch.setenv("SUPRA_API_KEY", provider_key)
    else:
        monkeypatch.delenv("SUPRA_API_KEY", raising=False)

    configured = SupraClientConfig.from_env()
    assert configured.api_key == service_token

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/health"
        assert request.headers.get("authorization") == expected
        assert "provider-secret" not in str(request.headers)
        return httpx.Response(
            200,
            json={"status": "healthy", "service": "supra-agentic-taskmaster",
                  "version": "1.0.0"},
        )

    with SupraClient(configured, transport=httpx.MockTransport(handler)) as client:
        assert client.health().status == "healthy"


def test_explicit_client_token_is_still_supported(monkeypatch):
    monkeypatch.setenv("SUPRA_API_KEY", "provider-secret")
    monkeypatch.setenv("SUPRA_API_TOKEN", "service-token")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") == "Bearer explicitly-provided"
        return httpx.Response(
            200,
            json={"status": "healthy", "service": "supra-agentic-taskmaster",
                  "version": "1.0.0"},
        )

    config = SupraClientConfig(endpoint="http://127.0.0.1:8080",
                               api_key="explicitly-provided", timeout=2.0)
    with SupraClient(config, transport=httpx.MockTransport(handler)) as client:
        assert client.health().status == "healthy"


def test_provider_key_does_not_become_server_token_after_restart(monkeypatch):
    monkeypatch.delenv("SUPRA_API_TOKEN", raising=False)
    monkeypatch.setenv("SUPRA_API_KEY", "provider-key")
    one = SupraClientConfig.from_env()
    two = SupraClientConfig.from_env()
    assert one.api_key == two.api_key == ""
    assert one.endpoint == two.endpoint
