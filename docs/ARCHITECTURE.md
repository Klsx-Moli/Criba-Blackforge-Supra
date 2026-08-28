# SUPRA Agentic Taskmaster — Technical Architecture

## 1. System Overview

SUPRA Agentic Taskmaster is an autonomous, multi-stage taskmaster agent designed to process high-uncertainty engineering and security objectives into structured, verified, and executable solutions.

---

## 2. Core Subsystems

### A. State Manager (`src/supra_agentic/state.py`)
* **Thread Safety:** Uses `threading.RLock()` to guarantee reentrancy across concurrent background tasks.
* **Persistence:** Serializes `ProjectPosture` records to disk in `data/projects/{project_id}.json`.
* **State Machine:** Enforces strict monotonic transitions through `TaskmasterStage`:
  $$\text{RECEIVED} \longrightarrow \text{STRUCTURED} \longrightarrow \text{STRATIFIED} \longrightarrow \text{SANDBOX\_VERIFIED} \longrightarrow \text{COMPLETED}$$

### B. Google ADK Toolset (`src/supra_agentic/tools.py`)
1. `decompose_objective`: Extracts invariant constraints and mutable assumptions.
2. `synthesize_strategy`: Formulates multi-paradigm candidates ($N \ge 3$).
3. `verify_solution`: Evaluates candidate safety against invariants.
4. `execute_sandbox_action`: Executes synthetic Python AST validation without external side-effects.
5. `record_checkpoint`: Finalizes the deliverable and signs with SHA-256 integrity hash.

### C. Autonomous Runner (`src/supra_agentic/runner.py`)
* Implements the `run_golden_path` method that links all 5 stages in an uninterrupted, autonomous cycle.
* Guarantees total execution in $<0.5\text{s}$ for preflight/demo runs and handles live Gemini 3.7 turns via Google ADK.

### D. FastAPI Service (`src/supra_agentic/service.py`)
* Exposes RESTful endpoints for project creation, telemetry polling, and 1-Click Judge Demo.
* Serves static Web UI assets (`index.html`, `style.css`, `app.js`).

---

## 3. Security & Containment Model

* **AST Micro-Sandbox:** Prohibits `os`, `sys`, `subprocess`, and `shutil` inside dynamic evaluations.
* **Zero-Trust Input Sanitization:** Rejects prompt injections and path traversal attempts.
* **Immutable Checkpoints:** Every state transition records an append-only checkpoint with an ISO timestamp and actor signature.
