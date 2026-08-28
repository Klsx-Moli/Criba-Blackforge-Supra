"""Tests for Taskmaster Agent and Golden Path Runner."""
import tempfile
from supra_agentic.models import TaskmasterStage
from supra_agentic.runner import TaskmasterRunner
from supra_agentic.state import state_manager
from supra_agentic.tools import execute_sandbox_action, synthesize_strategy


def test_runner_golden_path_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        runner = TaskmasterRunner()
        posture = runner.run_golden_path(
            objective="Formulate an autonomous self-healing data pipeline for real-time telemetry",
            domain="data_pipeline",
        )

        assert posture.stage == TaskmasterStage.COMPLETED
        assert posture.decomposition is not None
        assert posture.decomposition.domain == "data_pipeline"
        assert len(posture.candidates) == 3
        assert posture.selected_candidate is not None
        assert posture.verification is not None
        assert posture.verification.verdict == "PASS"
        assert len(posture.sandbox_results) >= 1
        assert posture.sandbox_results[-1].passed is True
        assert posture.final_output is not None
        assert "audit_sha256" in posture.final_output
        assert "null_hypothesis_h0" in posture.final_output
        assert len(posture.checkpoints) >= 5


def test_runner_self_correction_feedback():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        # 1. Initialize project
        p = state_manager.create_project(objective="Test Self-Correction Strategy Synthesis")
        pid = p.project_id

        # Decompose first
        from supra_agentic.tools import decompose_objective
        decompose_objective(pid, objective=p.objective)

        # Synthesize with error feedback
        feedback = "AssertionError: Database connection failed during burst mode"
        r = synthesize_strategy(pid, pathways_count=3, allow_disruptive=True, error_feedback=feedback)
        assert r["status"] == "success"
        assert r["self_correction_applied"] is True
        assert r["selected_candidate"]["paradigm_type"] == "DISRUPTIVE"
        assert "Compensatory" in r["selected_candidate"]["pathway_name"]
