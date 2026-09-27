"""Tests for the SUPRA FastAPI service and provider-neutral endpoints."""

import tempfile

from fastapi.testclient import TestClient
from supra_agentic.service import app
from supra_agentic.state import state_manager

client = TestClient(app)


def test_healthcheck():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["provider"]["name"] == "hermes"
    assert data["provider"]["protocol"] == "openai-compatible"
    assert data["webmcp_enabled"] is True
    assert "provider" in data


def test_serve_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "SUPRA" in response.text
    assert "What do you want to solve?" in response.text


def test_quick_run_example():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        response = client.post("/api/v1/examples/quick-run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["example"] is True
        assert data["stage"] == "BLOCKED"
        assert data["workflow_status"] == "BLOCKED"
        assert data["deliverable"] is None


def test_webmcp_jsonrpc_protocol():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        # 1. initialize
        init_res = client.post(
            "/api/v1/mcp", json={"jsonrpc": "2.0", "id": 1, "method": "initialize"}
        )
        assert init_res.status_code == 200
        assert init_res.json()["result"]["serverInfo"]["name"] == "supra-agentic-taskmaster"

        # 2. tools/list
        tools_res = client.post(
            "/api/v1/mcp", json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
        )
        assert tools_res.status_code == 200
        assert len(tools_res.json()["result"]["tools"]) >= 5

        # 3. tools/call supra_quick_run
        call_res = client.post(
            "/api/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {
                    "name": "supra_quick_run",
                    "arguments": {
                        "objective": "Test WebMCP autonomous task run",
                        "domain": "general",
                    },
                },
            },
        )
        assert call_res.status_code == 200
        assert "COMPLETED" in call_res.json()["result"]["content"][0]["text"]


def test_create_and_run_project_and_html_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        payload = {
            "objective": "Formulate an autonomous Zero-Trust secretless mesh with continuous invariant verification",
            "domain": "cloud_security",
            "allow_disruptive": True,
        }
        response = client.post("/api/v1/projects", json=payload)
        # A strategy-coverage FAIL is not a workflow/server failure.
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["status_scope"] == "WORKFLOW_EXECUTION_ONLY"
        assert "project_id" in data
        assert data["stage"] == "BLOCKED"
        assert data["workflow_status"] == "BLOCKED"
        assert data["verification_status"] == "FAIL"
        assert data["scientific_status"] == "NOT_VALIDATED"


def test_create_project_records_provider_without_calling_it():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        response = client.post(
            "/api/v1/projects",
            json={
                "objective": "Design a bounded local automation controller",
                "provider": "ollama",
                "model": "llama3.2",
                "use_model": False,
            },
        )

        # A strategy-coverage FAIL is not a workflow/server failure.
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["status_scope"] == "WORKFLOW_EXECUTION_ONLY"
        assert "project_id" in data
        assert data["stage"] == "BLOCKED"
        assert data["workflow_status"] == "BLOCKED"
        assert data["verification_status"] == "FAIL"
        assert data["scientific_status"] == "NOT_VALIDATED"


def test_blocked_project_survives_cache_clear_and_get_without_final_output():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        response = client.post(
            "/api/v1/projects",
            json={"objective": "Design a bounded local automation controller"},
        )
        assert response.status_code == 201
        created = response.json()
        assert created["stage"] == "BLOCKED"
        project_id = created["project_id"]

        # Simulate a fresh process cache: authoritative state must reload from disk.
        state_manager._projects.clear()
        loaded = client.get(f"/api/v1/projects/{project_id}")
        assert loaded.status_code == 200
        posture = loaded.json()["posture"]
        assert posture["stage"] == "BLOCKED"
        assert posture["final_output"] is None
        assert posture["error_message"] is None
