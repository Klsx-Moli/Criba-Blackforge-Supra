"""Tests for SUPRA FastAPI Service and Endpoints."""
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
    assert data["google_stack"]["model"] == "gemini-3.7-flash"
    assert data["google_stack"]["framework"] == "google-adk"


def test_serve_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "SUPRA" in response.text
    assert "What do you want to solve?" in response.text


def test_quick_run_judge_demo():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        response = client.get("/api/v1/demo/quick-run")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["google_stack_verified"] is True
        assert data["stage"] == "COMPLETED"
        assert "audit_sha256" in data["deliverable"]


def test_create_and_run_project():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        payload = {
            "objective": "Formulate an autonomous Zero-Trust secretless mesh with continuous invariant verification",
            "domain": "cloud_security",
            "allow_disruptive": True,
        }
        response = client.post("/api/v1/projects", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "success"
        assert data["stage"] == "COMPLETED"
        pid = data["project_id"]

        # Get project
        get_res = client.get(f"/api/v1/projects/{pid}")
        assert get_res.status_code == 200
        assert get_res.json()["posture"]["stage"] == "COMPLETED"

        # Export dossier
        exp_res = client.get(f"/api/v1/export/dossier/{pid}")
        assert exp_res.status_code == 200
        assert "TECHNICAL DOSSIER" in exp_res.json()["markdown_dossier"]
