"""Tests for Taskmaster Agent and Golden Path Runner."""
import tempfile
from supra_agentic.models import TaskmasterStage
from supra_agentic.runner import TaskmasterRunner
from supra_agentic.state import state_manager


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
        assert len(posture.sandbox_results) == 1
        assert posture.sandbox_results[0].passed is True
        assert posture.final_output is not None
        assert "audit_sha256" in posture.final_output
        assert len(posture.checkpoints) >= 5
