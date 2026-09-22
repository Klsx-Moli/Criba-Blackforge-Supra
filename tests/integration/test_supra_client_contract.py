"""Contract tests for the single CRIBA -> SUPRA HTTP client."""

from __future__ import annotations

import json

import httpx
import pytest

from criba.integrations.supra_client import (
    SupraClient,
    SupraClientConfig,
    SupraClientError,
)


def _client(handler, *, api_key: str = "") -> SupraClient:
    return SupraClient(
        SupraClientConfig(endpoint="https://supra.test", api_key=api_key, timeout=2.0),
        transport=httpx.MockTransport(handler),
    )


def test_health_uses_real_root_health_route_and_auth_header() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/health"
        assert request.headers["authorization"] == "Bearer secret"
        return httpx.Response(
            200,
            json={"status": "healthy", "service": "supra-agentic-taskmaster", "version": "1.0.0"},
        )

    with _client(handler, api_key="secret") as client:
        assert client.health().status == "healthy"


def test_run_project_uses_real_payload_and_preserves_blocked_status() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/projects"
        payload = json.loads(request.content)
        assert set(payload) == {
            "objective", "domain", "allow_disruptive", "use_model", "project_id"
        }
        assert payload["project_id"] == "criba-run-1"
        return httpx.Response(
            201,
            json={
                "status": "blocked",
                "status_scope": "WORKFLOW_EXECUTION_ONLY",
                "completion_status": "BLOCKED",
                "workflow_status": "RESTRICTED_EXECUTION_VERIFIED",
                "verification_status": "FAIL",
                "scientific_status": "NOT_VALIDATED",
                "project_id": "criba-run-1",
                "stage": "RESTRICTED_EXECUTION_VERIFIED",
                "posture": {"project_id": "criba-run-1"},
            },
        )

    with _client(handler) as client:
        result = client.run_project(
            objective="Evaluate this bounded CRIBA candidate",
            project_id="criba-run-1",
        )
    assert result.status == "blocked"
    assert result.verification_status == "FAIL"
    assert result.stage != "COMPLETED"


def test_project_id_is_validated_before_transport() -> None:
    def forbidden(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("transport must not be called for unsafe ids")

    with _client(forbidden) as client:
        with pytest.raises(ValueError):
            client.get_project("../escape")
        with pytest.raises(ValueError):
            client.export_dossier("nested/path")


def test_list_projects_uses_only_real_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/projects"
        assert request.url.params["limit"] == "5"
        return httpx.Response(200, json={"status": "success", "count": 0, "projects": []})

    with _client(handler) as client:
        result = client.list_projects(limit=5)
    assert result.projects == []


def test_mcp_uses_real_jsonrpc_endpoint() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/api/v1/mcp"
        payload = json.loads(request.content)
        assert payload == {"jsonrpc": "2.0", "id": 7, "method": "tools/list"}
        return httpx.Response(200, json={"jsonrpc": "2.0", "id": 7, "result": {"tools": []}})

    with _client(handler) as client:
        result = client.mcp("tools/list", request_id=7)
    assert result["result"]["tools"] == []


def test_client_has_no_historical_fabricated_routes() -> None:
    source = __import__("inspect").getsource(SupraClient)
    for forbidden in (
        "/api/v1/health",
        "/api/v1/dossiers",
        "/api/v1/dossiers/run",
        "/logs",
    ):
        assert forbidden not in source


def test_http_failure_does_not_become_success() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "Invalid or missing API credentials."})

    with _client(handler) as client:
        with pytest.raises(SupraClientError, match="HTTP 401"):
            client.list_projects()



def test_client_rejects_legacy_fail_plus_completed_overclaim() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            201,
            json={
                "status": "success",
                "status_scope": "WORKFLOW_EXECUTION_ONLY",
                "completion_status": "COMPLETED",
                "workflow_status": "COMPLETED",
                "verification_status": "FAIL",
                "scientific_status": "NOT_VALIDATED",
                "project_id": "legacy-overclaim",
                "stage": "COMPLETED",
                "posture": {"project_id": "legacy-overclaim"},
            },
        )

    with _client(handler) as client:
        with pytest.raises(ValueError, match="failed/unevaluated"):
            client.run_project(objective="Reject contradictory SUPRA completion")


def test_gui_uses_canonical_supra_client_without_direct_http_routes() -> None:
    from pathlib import Path

    source = Path("src/criba/ui/actions.py").read_text(encoding="utf-8")
    assert "from ..integrations import SupraClient" in source
    assert "_execute_supra_dossiers" in source
    assert "httpx" not in source
    assert "/api/v1/" not in source


def test_dossier_mapping_preserves_epistemic_language() -> None:
    from criba.integrations import objective_from_dossier

    objective = objective_from_dossier(
        {
            "problema": "Reduce thermal drift",
            "hipotesis": "A bounded calibration loop reduces drift",
            "mecanismo": "Closed-loop correction",
            "prueba_discriminante": {
                "intervencion_prueba": "Compare calibrated and baseline runs",
                "observable": "temperature-adjusted error",
                "regla_decision": "prefer lower held-out error",
                "condicion_fracaso": "no measurable separation",
            },
        }
    )
    assert "sin convertir evidencia ausente en PASS" in objective
    assert "Closed-loop correction" in objective
    assert "no measurable separation" in objective
    assert len(objective) <= 2000
