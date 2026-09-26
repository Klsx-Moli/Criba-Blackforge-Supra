"""Focused SUPRA sentinels for ASTRA epistemic boundaries."""

import tempfile

import pytest
from supra_agentic.dossier import generate_svg_architecture
from supra_agentic.models import RestrictedExecutionResult, TaskmasterStage
from supra_agentic.state import state_manager
from supra_agentic.tools import (
    decompose_objective,
    record_checkpoint,
    restricted_python_executor,
    synthesize_strategy,
)


def test_astra_017_restricted_execution_model_cannot_claim_scientific_validation():
    with pytest.raises(ValueError, match="scientific validation"):
        RestrictedExecutionResult(
            action_type="x",
            passed=True,
            output_log="",
            duration_ms=1,
            scientific_validation=True,
        )


def test_astra_017_execution_identity_is_derived_from_selected_candidate():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        p = state_manager.create_project("claim")
        decompose_objective(p.project_id, "claim")
        synthesize_strategy(p.project_id, pathways_count=2, allow_disruptive=False)
        selected = state_manager.get_project(p.project_id).selected_candidate
        assert selected is not None

        result = restricted_python_executor(p.project_id)["restricted_execution_result"]
        assert result["candidate_id"] == selected.candidate_id
        assert result["mechanism_version"].startswith("sha256:")
        assert result["claim_id"].startswith("claim-")
        assert result["protocol_version"].startswith("sha256:")
        assert result["execution_id"]
        assert result["identity_bound"] is True
        assert result["result_scope"] == "RESTRICTED_EXECUTION_ONLY"
        assert result["scientific_validation"] is False


def test_astra_001_checkpoint_without_verification_cannot_complete():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        p = state_manager.create_project("claim")
        with pytest.raises(ValueError, match="completion gate"):
            record_checkpoint(p.project_id, "title", "summary")
        current = state_manager.get_project(p.project_id)
        assert current is not None
        assert current.stage is not TaskmasterStage.COMPLETED

def test_astra_017_svg_without_verification_never_defaults_to_pass():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        p = state_manager.create_project("claim")
        svg = generate_svg_architecture(p)
        assert "NOT_EVALUATED" in svg
        assert "PASS" not in svg


def test_astra_completion_gate_rejects_not_evaluated_and_missing_execution(tmp_path):
    state_manager.storage_dir = type(state_manager.storage_dir)(tmp_path)
    p = state_manager.create_project("completion gate")
    with pytest.raises(ValueError, match="completion gate"):
        record_checkpoint(p.project_id, "title", "summary")
    current = state_manager.get_project(p.project_id)
    assert current is not None
    assert current.stage is not TaskmasterStage.COMPLETED


def test_astra_project_id_rejects_path_traversal(tmp_path):
    from supra_agentic.state import ProjectStateManager

    sm = ProjectStateManager(tmp_path / "projects")
    outside = tmp_path / "escape.json"
    with pytest.raises(ValueError, match="project_id"):
        sm.create_project("safe objective", project_id="../escape")
    assert not outside.exists()


def test_astra_project_id_collision_cannot_overwrite_existing_project(tmp_path):
    from supra_agentic.state import ProjectStateManager

    sm = ProjectStateManager(tmp_path / "projects")
    first = sm.create_project("first objective", project_id="stable-id")
    with pytest.raises(ValueError, match="already exists"):
        sm.create_project("second objective", project_id="stable-id")
    assert sm.get_project(first.project_id).objective == "first objective"


def test_astra_completed_project_is_revoked_by_later_verification_fail(tmp_path):
    from supra_agentic.models import VerificationReport
    from supra_agentic.state import ProjectStateManager

    sm = ProjectStateManager(tmp_path / "projects")
    p = sm.create_project("revocation")
    # A completed state is legacy/corrupt input for this sentinel; a later FAIL must revoke it.
    p.stage = TaskmasterStage.COMPLETED
    p.final_output = {"workflow_status": "COMPLETED"}
    sm.record_verification(
        p.project_id,
        VerificationReport(candidate_id="candidate", verdict="FAIL"),
    )
    current = sm.get_project(p.project_id)
    assert current.stage is not TaskmasterStage.COMPLETED
    assert current.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"


def test_astra_restart_downgrades_stale_completed_without_current_gates():
    from supra_agentic.models import ProjectPosture

    raw = {
        "project_id": "stale-completed",
        "objective": "stale",
        "stage": "COMPLETED",
        "created_at": 1.0,
        "updated_at": 2.0,
        "checkpoints": [],
        "final_output": {"workflow_status": "COMPLETED"},
    }
    posture = ProjectPosture.model_validate(raw)
    assert posture.stage is TaskmasterStage.RECEIVED
    assert posture.final_output["workflow_status"] == "EVIDENCE_INVALIDATED"


def test_astra_html_dossier_escapes_user_controlled_content(tmp_path):
    from supra_agentic.dossier import export_full_html_dossier
    from supra_agentic.state import ProjectStateManager

    sm = ProjectStateManager(tmp_path / "projects")
    p = sm.create_project('<script>alert("x")</script>')
    html = export_full_html_dossier(p)
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html


def test_astra_verification_pass_must_bind_selected_candidate(tmp_path):
    from supra_agentic.models import StrategyCandidate, VerificationReport
    from supra_agentic.state import ProjectStateManager

    sm = ProjectStateManager(tmp_path / "projects")
    p = sm.create_project("candidate binding")
    selected = StrategyCandidate(
        pathway_name="selected",
        paradigm_type="ORTHOGONAL",
        hypothesis="selected hypothesis",
        action_plan=["step"],
        divergence_score=0.5,
        feasibility_score=0.5,
    )
    posture = sm.add_candidates(p.project_id, [selected], select_best=True)
    assert posture.selected_candidate is not None
    with pytest.raises(ValueError, match="selected candidate"):
        sm.record_verification(
            p.project_id,
            VerificationReport(candidate_id="other-candidate", verdict="PASS"),
        )
