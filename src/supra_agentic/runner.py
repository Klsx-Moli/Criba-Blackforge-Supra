"""SUPRA Taskmaster Autonomous Golden Path Runner."""
from __future__ import annotations

import logging
import time
from typing import Any

from .agent import create_taskmaster_agent
from .models import ProjectPosture, TaskmasterStage
from .state import state_manager
from .tools import (
    decompose_objective,
    execute_sandbox_action,
    record_checkpoint,
    synthesize_strategy,
    verify_solution,
)

logger = logging.getLogger("supra_agentic.runner")


class TaskmasterRunner:
    """Executes the full 5-stage Taskmaster workflow autonomously."""

    def __init__(self, model_name: str = "gemini-3.7-flash") -> None:
        self.model_name = model_name
        self._adk_agent = create_taskmaster_agent(model_name=model_name)

    def run_golden_path(
        self,
        objective: str,
        project_id: str | None = None,
        domain: str = "general",
        allow_disruptive: bool = True,
    ) -> ProjectPosture:
        """Execute the 5-stage autonomous cycle deterministically with full telemetry."""
        start_time = time.monotonic()
        clean_obj = objective.strip()
        if not clean_obj:
            raise ValueError("Objective cannot be empty.")

        # Stage 1: Initialize Project (RECEIVED)
        posture = state_manager.create_project(objective=clean_obj, project_id=project_id)
        pid = posture.project_id
        logger.info(f"[{pid}] Starting Taskmaster Golden Path for: '{clean_obj[:60]}...'")

        try:
            # Stage 2: Decompose (STRUCTURED)
            logger.info(f"[{pid}] Executing Tool 1: decompose_objective")
            decompose_objective(
                project_id=pid,
                objective=clean_obj,
                domain=domain,
            )

            # Stage 3: Synthesize Strategies (STRATIFIED)
            logger.info(f"[{pid}] Executing Tool 2: synthesize_strategy")
            synthesize_strategy(
                project_id=pid,
                pathways_count=3,
                allow_disruptive=allow_disruptive,
            )

            # Stage 4: Verify Invariants
            logger.info(f"[{pid}] Executing Tool 3: verify_solution")
            verify_solution(project_id=pid)

            # Stage 4b: Sandbox Execution (SANDBOX_VERIFIED)
            logger.info(f"[{pid}] Executing Tool 4: execute_sandbox_action")
            execute_sandbox_action(project_id=pid)

            # Stage 5: Final Checkpoint & Deliverable Ledger (COMPLETED)
            logger.info(f"[{pid}] Executing Tool 5: record_checkpoint")
            elapsed = time.monotonic() - start_time
            record_checkpoint(
                project_id=pid,
                deliverable_title=f"Autonomous Solution: {clean_obj[:50]}",
                summary=f"Taskmaster completed all 5 stages in {elapsed:.2f}s with full verification and sandbox execution.",
            )

            final_posture = state_manager.get_project(pid)
            assert final_posture is not None
            logger.info(f"[{pid}] Taskmaster Golden Path COMPLETED successfully in {elapsed:.2f}s.")
            return final_posture

        except Exception as exc:
            logger.error(f"[{pid}] Taskmaster execution encountered an error: {exc}")
            state_manager.fail_project(pid, str(exc))
            failed_posture = state_manager.get_project(pid)
            assert failed_posture is not None
            return failed_posture


# Global Singleton Runner
taskmaster_runner = TaskmasterRunner()
