"""B03 contract: replay, retry and restart must never fabricate or lose outcome.

Every test here was written from a reproduced defect or a reproduced absence,
never from reading the implementation. The reproduction notes live in the card
body; the mutation sentinel for each defect is stated next to the test.

Baseline this file pins (0a05119, verified by execution before these tests):
  * an exact retry of a CRIBA project is an idempotent replay
  * the same project_id with different content is a 409, never a silent merge
  * identity_bound is derived by the model and never accepted from the caller
  * one issued attempt cannot receive two execution results
  * corrupt persisted state raises instead of degrading into a false 404

Two defects were reproduced against the HTTP surface and are what this file
protects:
  D1  /api/v1/examples/quick-run and /api/v1/demo/quick-run answer 200 on the
      first call and then die with an unhandled DuplicateProjectError on every
      retry. The failure is a 500 with an EMPTY body, and because the example
      project id is persisted, the endpoint stays dead across restarts.
  D2  GET /api/v1/projects/{id} collapses a BLOCKED, verification-FAIL workflow
      into {"status": "success"}. POST deliberately separates transport,
      workflow, verification and scientific status; the GET used to reconstruct
      state after a restart did not.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi.testclient import TestClient
from supra_agentic.service import app
from supra_agentic.state import state_manager

# raise_server_exceptions=False so an unhandled endpoint crash shows up as the
# status code and body a real client would observe, not as a probe crash.
client = TestClient(app, raise_server_exceptions=False)


# Keep the TemporaryDirectory objects alive for the whole module. Letting them
# be collected deletes the directory out from under the state singleton, and the
# resulting FileNotFoundError is a fixture artifact, not a product defect.
_LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []


def _isolated_storage() -> None:
    """Point the singleton at a fresh, empty directory and drop its cache."""
    tmpdir = tempfile.TemporaryDirectory()
    _LIVE_TEMP_DIRS.append(tmpdir)
    state_manager.storage_dir = Path(tmpdir.name)
    state_manager._projects.clear()


def test_quick_run_replay_is_explicit_instead_of_an_unhandled_crash() -> None:
    """D1: a retry of the deterministic example must be a labelled replay.

    Mutation sentinel: reintroduce the bare ``run_golden_path`` call with no
    DuplicateProjectError handling and this goes red on the second POST.
    """
    _isolated_storage()

    first = client.post("/api/v1/examples/quick-run")
    assert first.status_code == 200, first.text
    assert first.json()["idempotent_replay"] is False

    second = client.post("/api/v1/examples/quick-run")
    assert second.status_code == 200, second.text
    body = second.json()
    assert body["idempotent_replay"] is True
    assert body["project_id"] == "example-quick-run"
    # A replay must report the persisted outcome, not a freshly invented one.
    assert body["stage"] == first.json()["stage"]
    assert body["workflow_status"] == first.json()["workflow_status"]
    assert body["verification_status"] == first.json()["verification_status"]
    assert body["scientific_status"] == "NOT_VALIDATED"


def test_quick_run_replay_body_is_always_machine_readable() -> None:
    """D1: no response from this endpoint may be an empty or non-JSON body.

    Mutation sentinel: let DuplicateProjectError escape without a handler and
    the second POST answers 500 with content-type text/plain and no JSON, which
    fails the content-type assertion and the channel assertions at once.
    """
    _isolated_storage()
    first = client.post("/api/v1/examples/quick-run")
    second = client.post("/api/v1/examples/quick-run")

    for response in (first, second):
        assert response.headers.get("content-type", "").startswith("application/json"), (
            f"HTTP {response.status_code} answered a non-JSON body: {response.text!r}"
        )
        body = response.json()
        for channel in (
            "status",
            "status_scope",
            "workflow_status",
            "verification_status",
            "scientific_status",
            "idempotent_replay",
        ):
            assert channel in body, f"missing status channel {channel!r}"

    assert second.json()["idempotent_replay"] is True


def test_quick_run_replay_survives_a_restart() -> None:
    """D1 across restart: the trap is persisted, so the fix must be too."""
    _isolated_storage()
    client.post("/api/v1/examples/quick-run")

    # Simulate a fresh process: only the durable state remains.
    state_manager._projects.clear()

    replay = client.post("/api/v1/examples/quick-run")
    assert replay.status_code == 200, replay.text
    assert replay.json()["idempotent_replay"] is True


def test_demo_quick_run_alias_shares_the_replay_contract() -> None:
    """D1: the compat alias must not keep the crashing behaviour."""
    _isolated_storage()
    client.post("/api/v1/examples/quick-run")

    alias = client.post("/api/v1/demo/quick-run")
    assert alias.status_code == 200, alias.text
    assert alias.json()["idempotent_replay"] is True


def test_get_project_demarcates_transport_from_workflow_outcome() -> None:
    """D2: GET must not report a blocked, failing workflow as success.

    Mutation sentinel: revert GET to {"status": "success", ...} and the
    ``status``/``status_scope``/``workflow_status`` assertions go red.
    """
    _isolated_storage()
    created = client.post(
        "/api/v1/projects",
        json={
            "objective": "Demarcate transport status from workflow outcome on read",
            "project_id": "b03-get-demarcation",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["workflow_status"] == "BLOCKED"

    state_manager._projects.clear()  # force the post-restart read path
    loaded = client.get("/api/v1/projects/b03-get-demarcation")
    assert loaded.status_code == 200, loaded.text
    body = loaded.json()

    assert body["status_scope"] == "WORKFLOW_EXECUTION_ONLY"
    assert body["status"] == "blocked"
    assert body["completion_status"] == "BLOCKED"
    assert body["workflow_status"] == "BLOCKED"
    assert body["verification_status"] == "FAIL"
    assert body["scientific_status"] == "NOT_VALIDATED"
    assert body["idempotent_replay"] is False
    assert body["posture"]["stage"] == "BLOCKED"


def test_get_project_status_is_derived_from_the_stage_not_independent() -> None:
    """D2 mutation sentinel: ``status`` must not be free to disagree with stage.

    Without this, a later edit could return "success" for a COMPLETED-looking
    body while the stage says FAILED, and the demarcation test above would still
    pass because it only reads one project.
    """
    _isolated_storage()
    state_manager.create_project(
        "Derive transport status from the persisted stage.", "b03-stage-derived"
    )
    state_manager.fail_project("b03-stage-derived", "probe induced failure")

    body = client.get("/api/v1/projects/b03-stage-derived").json()
    assert body["posture"]["stage"] == "FAILED"
    assert body["workflow_status"] == "FAILED"
    assert body["status"] != "success"


def test_get_project_reports_criba_receipt_as_planned_not_executed() -> None:
    """B03 read path must keep PLANNED distinct from EXECUTED after restart."""
    from test_service import _complete_criba_dossier_payload, _criba_request_payload

    _isolated_storage()
    created = client.post(
        "/api/v1/projects",
        json={
            "objective": "Keep planned discriminant protocol distinct from executed",
            "project_id": "b03-criba-read",
            **_criba_request_payload(_complete_criba_dossier_payload()),
        },
    )
    assert created.status_code == 201, created.text

    state_manager._projects.clear()
    body = client.get("/api/v1/projects/b03-criba-read").json()

    assert body["criba_planning_receipt_status"] == "PRESERVED_NOT_EXECUTED"
    assert body["criba_mechanism_execution_status"] == "NOT_EXECUTED"
    assert body["scientific_status"] == "NOT_VALIDATED"
