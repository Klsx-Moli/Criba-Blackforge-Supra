from __future__ import annotations

import asyncio
import json
import tempfile

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request
from supra_agentic import service

client = TestClient(service.app)


def _jsonrpc_body_of_size(size: int) -> bytes:
    prefix = b'{"jsonrpc":"2.0","id":1,"method":"initialize","padding":"'
    suffix = b'"}'
    if size < len(prefix) + len(suffix):
        raise ValueError("requested body is too small")
    return prefix + (b"x" * (size - len(prefix) - len(suffix))) + suffix


def _request_without_content_length(body: bytes) -> Request:
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/mcp",
            "headers": [],
        },
        receive,
    )


def test_cors_absent_is_closed() -> None:
    assert service._parse_cors_origins(None) == []
    assert service._parse_cors_origins("") == []


def test_cors_accepts_one_and_multiple_explicit_origins() -> None:
    assert service._parse_cors_origins("https://one.example") == ["https://one.example"]
    assert service._parse_cors_origins("https://one.example, http://localhost:3000") == [
        "https://one.example",
        "http://localhost:3000",
    ]


@pytest.mark.parametrize("raw", ["one.example", "ftp://one.example", "https://ok.example,"])
def test_cors_rejects_invalid_values(raw: str) -> None:
    with pytest.raises(RuntimeError):
        service._parse_cors_origins(raw)


def test_mcp_accepts_body_exactly_at_limit() -> None:
    body = _jsonrpc_body_of_size(service.MAX_MCP_BODY_SIZE)
    response = client.post(
        "/api/v1/mcp",
        content=body,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["result"]["serverInfo"]["name"] == "supra-agentic-taskmaster"


def test_mcp_rejects_actual_body_above_limit_even_with_false_small_header() -> None:
    body = _jsonrpc_body_of_size(service.MAX_MCP_BODY_SIZE + 1)
    response = client.post(
        "/api/v1/mcp",
        content=body,
        headers={"content-type": "application/json", "content-length": "1"},
    )
    assert response.status_code == 413


def test_mcp_accepts_missing_content_length_when_actual_body_is_small() -> None:
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize"}).encode()
    result = asyncio.run(service.mcp_jsonrpc_endpoint(_request_without_content_length(body)))
    assert result["result"]["serverInfo"]["name"] == "supra-agentic-taskmaster"


def test_mcp_rejects_missing_content_length_when_actual_body_is_large() -> None:
    request = _request_without_content_length(_jsonrpc_body_of_size(service.MAX_MCP_BODY_SIZE + 1))
    with pytest.raises(HTTPException) as raised:
        asyncio.run(service.mcp_jsonrpc_endpoint(request))
    assert raised.value.status_code == 413


def test_mcp_rejects_invalid_content_length_json_and_jsonrpc() -> None:
    invalid_length = client.post(
        "/api/v1/mcp",
        content=b"{}",
        headers={"content-type": "application/json", "content-length": "not-a-number"},
    )
    assert invalid_length.status_code == 400

    invalid_json = client.post(
        "/api/v1/mcp", content=b"not-json", headers={"content-type": "application/json"}
    )
    assert invalid_json.status_code == 400

    invalid_rpc = client.post("/api/v1/mcp", json={"id": 1, "method": "initialize"})
    assert invalid_rpc.status_code == 400


def test_internal_project_error_is_generic_and_secret_not_logged(monkeypatch, caplog) -> None:
    secret = "SENTINEL_DO_NOT_LEAK_6f0f"

    def explode(*args, **kwargs):
        raise RuntimeError(secret)

    monkeypatch.setattr(service.TaskmasterRunner, "run_golden_path", explode)
    response = client.post(
        "/api/v1/projects",
        json={"objective": "bounded objective for error contract"},
    )

    assert response.status_code == 500
    assert response.json() == {"detail": "Project execution failed."}
    assert secret not in response.text
    assert secret not in caplog.text
    assert "RuntimeError" in caplog.text


def test_create_project_rejects_path_traversal_project_id_before_runtime():
    local_client = TestClient(service.app)
    response = local_client.post(
        "/api/v1/projects",
        json={"objective": "valid objective", "project_id": "../escape"},
    )
    assert response.status_code == 422


def test_remote_mutations_require_bearer_authority(monkeypatch) -> None:
    monkeypatch.setenv("SUPRA_API_TOKEN", "correct-token")
    unauthenticated = client.post(
        "/api/v1/projects", json={"objective": "bounded remote mutation attempt"}
    )
    assert unauthenticated.status_code == 401

    wrong = client.post(
        "/api/v1/projects",
        json={"objective": "bounded remote mutation attempt"},
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert wrong.status_code == 401


def test_mcp_discovery_is_public_but_tool_calls_share_mutation_authority(monkeypatch) -> None:
    monkeypatch.setenv("SUPRA_API_TOKEN", "mcp-secret")
    discovery = client.post(
        "/api/v1/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
    )
    assert discovery.status_code == 200

    denied = client.post(
        "/api/v1/mcp",
        json={
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "supra_quick_run",
                "arguments": {"objective": "bounded MCP mutation attempt"},
            },
        },
    )
    assert denied.status_code == 401
    assert denied.json() == {"detail": "Mutation authorization required."}


def test_mutation_token_uses_bearer_scheme_and_accepts_exact_secret(monkeypatch) -> None:
    monkeypatch.setenv("SUPRA_API_TOKEN", "exact-secret")
    with tempfile.TemporaryDirectory() as tmpdir:
        service.state_manager.storage_dir = type(service.state_manager.storage_dir)(tmpdir)
        allowed = client.post(
            "/api/v1/projects",
            json={"objective": "bounded authorized mutation path"},
            headers={"Authorization": "Bearer exact-secret"},
        )
    assert allowed.status_code == 201


def test_cors_rejects_wildcard_origin() -> None:
    with pytest.raises(RuntimeError):
        service._parse_cors_origins("*")


def test_unconfigured_auth_is_loopback_only(monkeypatch) -> None:
    monkeypatch.delenv("SUPRA_API_TOKEN", raising=False)
    remote = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/projects",
            "headers": [],
            "client": ("203.0.113.10", 4242),
        }
    )
    with pytest.raises(HTTPException) as raised:
        service._require_mutation_authority(remote)
    assert raised.value.status_code == 403

    loopback = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/projects",
            "headers": [],
            "client": ("127.0.0.1", 4242),
        }
    )
    service._require_mutation_authority(loopback)


def test_quick_run_mutation_is_not_exposed_as_simple_get() -> None:
    # A cross-origin browser can send a simple GET even when CORS blocks reading
    # the response. A mutating demo endpoint therefore must not be GET.
    assert client.get("/api/v1/examples/quick-run").status_code == 405
    assert client.get("/api/v1/demo/quick-run").status_code == 405


def test_duplicate_project_id_is_conflict_not_internal_error() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        service.state_manager.storage_dir = type(service.state_manager.storage_dir)(tmpdir)
        service.state_manager._projects.clear()
        payload = {
            "objective": "bounded duplicate project contract",
            "project_id": "duplicate-contract",
        }
        first = client.post("/api/v1/projects", json=payload)
        second = client.post("/api/v1/projects", json=payload)
    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {"detail": "project_id already exists."}
