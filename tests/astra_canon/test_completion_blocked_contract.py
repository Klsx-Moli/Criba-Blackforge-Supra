import tempfile
from pathlib import Path

from supra_agentic.models import TaskmasterStage
from supra_agentic.runner import TaskmasterRunner
from supra_agentic.state import state_manager


def test_not_evaluated_golden_path_is_blocked_not_failed_or_completed():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = Path(tmpdir)
        posture = TaskmasterRunner().run_golden_path(
            objective="Design a bounded local automation controller",
            project_id="blocked-contract",
            domain="general",
        )
        assert posture.verification is not None
        assert posture.verification.verdict != "PASS"
        assert posture.stage is TaskmasterStage.BLOCKED
        assert posture.final_output is None
        assert posture.error_message is None

        loaded = state_manager.get_project(posture.project_id)
        assert loaded is not None
        assert loaded.stage is TaskmasterStage.BLOCKED
        assert loaded.verification is not None
        assert loaded.verification.verdict == posture.verification.verdict


def test_blocked_is_distinct_from_execution_failure():
    assert TaskmasterStage.BLOCKED is not TaskmasterStage.FAILED
    assert TaskmasterStage.BLOCKED is not TaskmasterStage.COMPLETED



def test_persisted_blocked_state_scrubs_corrupt_parseable_completion_claims():
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = Path(tmpdir)
        state_manager._projects.clear()
        posture = state_manager.create_project(
            "Design a bounded local automation controller", project_id="blocked-corrupt"
        )
        state_manager.block_project(posture.project_id, "verification did not pass")
        state_manager._projects.clear()

        path = Path(tmpdir) / "blocked-corrupt.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["final_output"] = {
            "workflow_status": "COMPLETED",
            "scientific_status": "VALIDATED",
            "audit_sha256": "forged",
        }
        payload["error_message"] = "forged failure channel"
        path.write_text(json.dumps(payload), encoding="utf-8")

        loaded = state_manager.get_project("blocked-corrupt")
        assert loaded is not None
        assert loaded.stage is TaskmasterStage.BLOCKED
        assert loaded.final_output is None
        assert loaded.error_message is None
