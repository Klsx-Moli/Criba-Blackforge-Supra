"""Tests for the SUPRA FastAPI service and provider-neutral endpoints."""

import tempfile

from fastapi.testclient import TestClient
from supra_agentic.models import TaskmasterStage
from supra_agentic.service import (
    CribaDossierRequest,
    CreateProjectRequest,
    _criba_dossier_receipt,
    _criba_payload_fingerprint,
    _criba_request_fingerprint,
    app,
)
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
        assert data["status"] == "blocked"
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
        assert data["status"] == "blocked"
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


def _complete_criba_dossier_payload() -> dict:
    return {
        "dossier_id": "dossier-0123456789abcdef0123456789abcdef",
        "candidate_id": "cand-thermal-1",
        "run_id": "",
        "claim_id": "claim-thermal-1",
        "protocol_version": "sha256:" + "a" * 64,
        "mechanism_version": "sha256:" + "b" * 64,
        "problema": "Reduce thermal drift in sensor",
        "bloqueo": "",
        "origen_bloqueo": "",
        "hipotesis": "Bounded calibration loop reduces thermal drift",
        "mecanismo": "Closed-loop correction with 5ms window",
        "evidence_delivered": [],
        "evidence_documented_as_used": [],
        "evidencia_utilizada": [],
        "prueba_discriminante": {
            "afirmacion_decisiva": "Compare calibrated vs baseline runs under load",
            "alternativa_explicativa": "Ambient temperature stabilization alone",
            "intervencion_prueba": "Compare calibrated vs baseline runs under load",
            "observable": "temperature-adjusted error over 1h",
            "comparacion": "Compare the two preregistered rival predictions",
            "metrica": "temperature-adjusted error over 1h",
            "resultado_favorable_mecanismo": "drift < 0.1C sustained",
            "resultado_favorable_alternativa": "drift reduction from ambient alone",
            "regla_decision": "prefer mechanism when drift separation > 0.05C",
            "condicion_fracaso": "no measurable separation between arms",
            "coste_permisos": "review before execution",
            "estado_prueba": "NO_EJECUTADA",
        },
        "supuestos": [],
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": "2026-09-25T00:00:00+00:00",
    }


def _criba_request_payload(dossier: dict) -> dict:
    parsed = CribaDossierRequest.model_validate(dossier)
    return {
        "criba_dossier": dossier,
        "criba_integration_version": "criba-supra/1",
        "criba_payload_fingerprint": _criba_payload_fingerprint(parsed),
    }


def test_create_project_persists_criba_dossier_as_planning_receipt() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        response = client.post(
            "/api/v1/projects",
            json={
                "objective": "Evaluate a bounded thermal calibration mechanism",
                "domain": "thermal_engineering",
                "allow_disruptive": False,
                **_criba_request_payload(_complete_criba_dossier_payload()),
            },
        )

        assert response.status_code == 201
        receipt = response.json()["posture"]["criba_dossier_receipt"]
        assert receipt["receipt_scope"] == "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
        assert receipt["execution_status"] == "NOT_EXECUTED"
        assert receipt["scientific_status"] == "NOT_VALIDATED"
        assert receipt["criba_candidate_id"] == "cand-thermal-1"
        assert (
            receipt["alternativa_explicativa"]
            == "Ambient temperature stabilization alone"
        )
        assert receipt["intervencion_prueba"] == (
            "Compare calibrated vs baseline runs under load"
        )
        assert receipt["observable"] == "temperature-adjusted error over 1h"
        assert receipt["resultado_favorable_mecanismo"] == "drift < 0.1C sustained"
        assert receipt["resultado_favorable_alternativa"] == (
            "drift reduction from ambient alone"
        )


def test_criba_receipt_survives_cache_clear_get_with_version_and_fingerprint() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        envelope = _criba_request_payload(dossier)
        created = client.post(
            "/api/v1/projects",
            json={
                "objective": "Persist exact CRIBA planning lineage across restart",
                "project_id": "criba-restart-lineage",
                **envelope,
            },
        )
        assert created.status_code == 201

        state_manager._projects.clear()
        loaded = client.get("/api/v1/projects/criba-restart-lineage")
        assert loaded.status_code == 200
        receipt = loaded.json()["posture"]["criba_dossier_receipt"]
        assert receipt["integration_version"] == "criba-supra/1"
        assert receipt["payload_fingerprint"] == envelope["criba_payload_fingerprint"]
        assert receipt["criba_dossier_id"] == dossier["dossier_id"]
        assert receipt["criba_candidate_id"] == dossier["candidate_id"]
        assert receipt["claim_id"] == dossier["claim_id"]
        assert receipt["mechanism_version"] == dossier["mechanism_version"]
        assert receipt["protocol_version"] == dossier["protocol_version"]
        assert receipt["execution_status"] == "NOT_EXECUTED"
        assert receipt["scientific_status"] == "NOT_VALIDATED"


def test_same_criba_request_is_idempotent_after_lost_response_and_restart() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        request_payload = {
            "objective": "Recognize exact CRIBA retry without rerunning workflow",
            "project_id": "criba-idempotent-retry",
            "domain": "thermal_engineering",
            "allow_disruptive": False,
            **_criba_request_payload(dossier),
        }
        first = client.post("/api/v1/projects", json=request_payload)
        assert first.status_code == 201
        first_body = first.json()

        # Simulate caller losing the response and the server process restarting.
        state_manager._projects.clear()
        second = client.post("/api/v1/projects", json=request_payload)

        assert second.status_code == 200
        second_body = second.json()
        assert second_body["idempotent_replay"] is True
        assert second_body["project_id"] == first_body["project_id"]
        assert second_body["stage"] == first_body["stage"]
        first_receipt = first_body["posture"]["criba_dossier_receipt"]
        second_receipt = second_body["posture"]["criba_dossier_receipt"]
        assert second_receipt["payload_fingerprint"] == first_receipt["payload_fingerprint"]
        assert second_receipt["execution_status"] == "NOT_EXECUTED"
        assert second_receipt["scientific_status"] == "NOT_VALIDATED"


def test_same_project_and_dossier_fingerprint_with_changed_objective_is_conflict() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        base = {
            "project_id": "criba-retry-conflict",
            "domain": "thermal_engineering",
            "allow_disruptive": False,
            **_criba_request_payload(dossier),
        }
        first = client.post(
            "/api/v1/projects",
            json={"objective": "Original bounded CRIBA request", **base},
        )
        assert first.status_code == 201
        state_manager._projects.clear()
        second = client.post(
            "/api/v1/projects",
            json={"objective": "Changed objective under same dossier fingerprint", **base},
        )
        assert second.status_code == 409


def test_exact_criba_retry_is_resolved_before_runner_side_effects(monkeypatch) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        request_payload = {
            "objective": "Preflight idempotent replay before any runner work",
            "project_id": "criba-preflight-retry",
            **_criba_request_payload(dossier),
        }
        first = client.post("/api/v1/projects", json=request_payload)
        assert first.status_code == 201
        state_manager._projects.clear()

        def forbidden_runner(*_args, **_kwargs):
            raise AssertionError("exact replay must not construct TaskmasterRunner")

        monkeypatch.setattr("supra_agentic.service.TaskmasterRunner", forbidden_runner)
        replay = client.post("/api/v1/projects", json=request_payload)
        assert replay.status_code == 200
        assert replay.json()["idempotent_replay"] is True


def test_same_project_with_different_criba_payload_remains_conflict_after_restart() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        original = _complete_criba_dossier_payload()
        first_payload = {
            "objective": "Reject semantic overwrite of persisted CRIBA request",
            "project_id": "criba-semantic-conflict",
            **_criba_request_payload(original),
        }
        first = client.post("/api/v1/projects", json=first_payload)
        assert first.status_code == 201

        state_manager._projects.clear()
        changed = _complete_criba_dossier_payload()
        changed["mecanismo"] = "Different closed-loop mechanism under same project ID"
        changed_payload = {
            "objective": first_payload["objective"],
            "project_id": first_payload["project_id"],
            **_criba_request_payload(changed),
        }
        second = client.post("/api/v1/projects", json=changed_payload)
        assert second.status_code == 409


def test_exact_retry_does_not_promote_partial_crash_state_to_completion() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        payload = {
            "objective": "Crash window must stay nonterminal",
            "project_id": "criba-partial-retry",
            **_criba_request_payload(dossier),
        }
        req = CreateProjectRequest.model_validate(payload)
        receipt = _criba_dossier_receipt(
            req.criba_dossier,
            integration_version=req.criba_integration_version or "",
            payload_fingerprint=req.criba_payload_fingerprint or "",
            request_fingerprint=_criba_request_fingerprint(req),
        )
        state_manager.create_project(
            objective=req.objective,
            project_id=req.project_id,
            criba_dossier_receipt=receipt,
        )
        state_manager._projects.clear()

        replay = client.post("/api/v1/projects", json=payload)
        assert replay.status_code == 409
        assert replay.json()["detail"] == "existing project is nonterminal; automatic replay unsafe."


def test_exact_retry_preserves_failed_state_instead_of_claiming_completion() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        state_manager._projects.clear()
        dossier = _complete_criba_dossier_payload()
        payload = {
            "objective": "Failed workflow must remain failed on exact retry",
            "project_id": "criba-failed-retry",
            **_criba_request_payload(dossier),
        }
        req = CreateProjectRequest.model_validate(payload)
        receipt = _criba_dossier_receipt(
            req.criba_dossier,
            integration_version=req.criba_integration_version or "",
            payload_fingerprint=req.criba_payload_fingerprint or "",
            request_fingerprint=_criba_request_fingerprint(req),
        )
        posture = state_manager.create_project(
            objective=req.objective,
            project_id=req.project_id,
            criba_dossier_receipt=receipt,
        )
        posture.stage = TaskmasterStage.FAILED
        posture.error_message = "simulated internal failure"
        state_manager._persist_project(posture.project_id)
        state_manager._projects.clear()

        replay = client.post("/api/v1/projects", json=payload)
        assert replay.status_code == 500
        body = replay.json()
        assert body["status"] == "error"
        assert body["stage"] == "FAILED"
        assert body["idempotent_replay"] is True
        assert body["error"] == "Pipeline execution failed"


def test_create_project_rejects_incomplete_criba_discriminant_protocol() -> None:
    payload = _complete_criba_dossier_payload()
    payload["prueba_discriminante"]["alternativa_explicativa"] = ""

    response = client.post(
        "/api/v1/projects",
        json={
            "objective": "Reject incomplete CRIBA discriminant protocol",
            "criba_dossier": payload,
        },
    )

    assert response.status_code == 422


def test_criba_envelope_rejects_same_identity_with_mutated_payload_fingerprint() -> None:
    dossier = _complete_criba_dossier_payload()
    envelope = _criba_request_payload(dossier)
    dossier["mecanismo"] = "MUTATED mechanism under the same dossier_id"
    response = client.post(
        "/api/v1/projects",
        json={"objective": "Reject changed content under stable dossier identity", **envelope},
    )
    assert response.status_code == 422


def test_criba_envelope_rejects_version_skew() -> None:
    dossier = _complete_criba_dossier_payload()
    envelope = _criba_request_payload(dossier)
    envelope["criba_integration_version"] = "criba-supra/999"
    response = client.post(
        "/api/v1/projects",
        json={"objective": "Reject unsupported CRIBA integration version", **envelope},
    )
    assert response.status_code == 422
