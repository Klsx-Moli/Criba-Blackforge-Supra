"""Tests for provider-neutral SUPRA tools."""
import tempfile
from supra_agentic.models import TaskmasterStage
from supra_agentic.state import ProjectStateManager, state_manager
from supra_agentic.tools import (
    SUPRA_TOOLS,
    decompose_objective,
    execute_sandbox_action,
    record_checkpoint,
    synthesize_strategy,
    verify_solution,
)


def test_toolset_manifest():
    assert len(SUPRA_TOOLS) == 5
    tool_names = [t.__name__ for t in SUPRA_TOOLS]
    assert "decompose_objective" in tool_names
    assert "synthesize_strategy" in tool_names
    assert "verify_solution" in tool_names
    assert "execute_sandbox_action" in tool_names
    assert "record_checkpoint" in tool_names


def test_full_tool_cycle_execution():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Override state manager storage for isolation
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)

        p = state_manager.create_project(objective="Automate multi-region database failover with zero data loss")
        pid = p.project_id

        # 1. Decompose
        r1 = decompose_objective(pid, objective=p.objective, domain="cloud_infrastructure")
        assert r1["status"] == "success"
        assert r1["stage"] == TaskmasterStage.STRUCTURED.value
        assert len(r1["decomposition"]["subtasks"]) == 3

        # 2. Synthesize
        r2 = synthesize_strategy(pid, pathways_count=3, allow_disruptive=True)
        assert r2["status"] == "success"
        assert r2["stage"] == TaskmasterStage.STRATIFIED.value
        assert r2["candidates_count"] == 3
        assert r2["selected_candidate"] is not None

        # 3. Verify (honest contract: verdict derives from evidence executed on invariants,
        # never from preset scores)
        r3 = verify_solution(pid)
        assert r3["status"] == "success"
        report = r3["report"]
        # confidence is fraction of invariants with PASS evidence in [0,1]
        assert 0.0 <= report["confidence_score"] <= 1.0
        # verdict is one of the honest states
        assert report["verdict"] in {"PASS", "CONDITIONAL_PASS", "FAIL", "NOT_EVALUATED"}
        # evidence per invariant is recorded and tied to candidate
        assert isinstance(report["evidence"], list)
        assert len(report["evidence"]) == len(report["invariants_checked"])

        # 4. Sandbox Action
        r4 = execute_sandbox_action(pid)
        assert r4["status"] == "success"
        assert r4["stage"] == TaskmasterStage.SANDBOX_VERIFIED.value
        assert r4["sandbox_result"]["passed"] is True

        # 5. Checkpoint / Final Deliverable
        r5 = record_checkpoint(pid, deliverable_title="Multi-Region Zero-Loss Failover Plan", summary="Autonomous plan synthesized and verified.")
        assert r5["status"] == "success"
        assert r5["stage"] == TaskmasterStage.COMPLETED.value
        assert "audit_sha256" in r5["final_deliverable"]
        assert len(r5["final_deliverable"]["audit_sha256"]) == 64


def test_sandbox_security_rejection():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_manager.storage_dir = type(state_manager.storage_dir)(tmpdir)
        p = state_manager.create_project(objective="Test Sandbox Security")
        pid = p.project_id

        # Attempt to run dangerous code in sandbox
        dangerous_code = "import os\nos.system('echo dangerous')"
        r = execute_sandbox_action(pid, code_snippet=dangerous_code)
        assert r["sandbox_result"]["passed"] is False
        # New sandbox rejects via __import__ not in SAFE_BUILTINS
        assert "import" in r["sandbox_result"]["output_log"].lower() or "prohibited" in r["sandbox_result"]["output_log"].lower() or "__import__" in r["sandbox_result"]["output_log"]