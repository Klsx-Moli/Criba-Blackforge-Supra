"""SUPRA Google ADK Agent Integration.

Configures and instantiates the Google ADK Agent with Gemini 3.7 Flash and Vertex AI.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from .tools import SUPRA_ADK_TOOLS

logger = logging.getLogger("supra_agentic.agent")

# Configure Google Cloud / Vertex AI environment defaults
os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", "REMOVED_CREDENTIAL_PATH")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "REMOVED_PROJECT_ID")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "global")
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")

TASKMASTER_SYSTEM_INSTRUCTION = """You are SUPRA: the principal autonomous Taskmaster Agent for the All Things Agentic Hackathon 2026.

YOUR MISSION:
Execute multi-stage autonomous problem decomposition, causal strategy synthesis, sandbox verification, and verifiable deliverable generation.

CORE WORKFLOW:
1. DECOMPOSE: Call `decompose_objective` to separate core invariants from mutable assumptions and establish clear subtasks.
2. SYNTHESIZE: Call `synthesize_strategy` to formulate competing conservative, orthogonal, and disruptive candidate pathways.
3. VERIFY: Call `verify_solution` to validate the chosen candidate against all system invariants.
4. SANDBOX EXECUTION: Call `execute_sandbox_action` to run an isolated simulation / AST verification in the micro-sandbox.
5. CHECKPOINT & RECORD: Call `record_checkpoint` to compile the final deliverable ledger with a cryptographic SHA-256 integrity hash.

GUIDING PRINCIPLES:
- Autonomous Action: Execute the required steps directly rather than just offering textual advice.
- Verifiable Evidence: Ground every conclusion in structured checkpoints and telemetry.
- Safe Containment: Ensure zero uncontained side-effects.
"""


def create_taskmaster_agent(
    model_name: str = "gemini-3.7-flash",
    agent_name: str = "supra_taskmaster_agent",
) -> Any:
    """Instantiate and return a configured Google ADK Agent."""
    try:
        from google.adk.agents import Agent
        return Agent(
            name=agent_name,
            model=model_name,
            description="SUPRA Autonomous Multi-Stage Taskmaster Agent for All Things Agentic 2026.",
            instruction=TASKMASTER_SYSTEM_INSTRUCTION,
            tools=list(SUPRA_ADK_TOOLS),
        )
    except Exception as exc:
        logger.warning(f"Google ADK Agent instantiation notice: {exc}. Local deterministic runner will be used.")
        return None
