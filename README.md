# SUPRA Agentic Taskmaster

**Autonomous Multi-Stage Innovation & Taskmaster Agent powered by Google Gemini 3.7 Flash, Google ADK, and Google Cloud Run.**

[![All Things Agentic 2026](https://img.shields.io/badge/Hackathon-All%20Things%20Agentic%202026-blue)](https://devpost.com)
[![Category](https://img.shields.io/badge/Category-Taskmaster-purple)](#)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Cloud%20Run-green)](https://cloud.google.com/run)
[![Google ADK](https://img.shields.io/badge/Agent%20Framework-Google%20ADK-4285F4)](https://github.com/google/adk)
[![Gemini](https://img.shields.io/badge/Model-Gemini%203.7%20Flash-F4B400)](https://deepmind.google/technologies/gemini/)
[![License](https://img.shields.io/badge/License-Apache%202.0-orange)](LICENSE)

---

## 1. Problem Statement

Modern complex engineering, software architecture, and cybersecurity challenges require more than simple textual advice or one-shot prompt answering. Engineers need an autonomous partner that:
1. Deconstructs ambiguous objectives into formal system invariants versus mutable framing assumptions.
2. Formulates competing orthogonal and disruptive strategy candidates.
3. Rigorously verifies candidates against constraints and executes synthetic code in an isolated sandbox.
4. Issues a verifiable, cryptographically hashed deliverable ledger.

---

## 2. Solution: SUPRA Taskmaster

SUPRA is an autonomous Taskmaster agent built from first principles for the **All Things Agentic Hackathon 2026 (Taskmaster Category)**.

When a user asks **"What do you want to solve?"**, SUPRA does not merely chat:
* It autonomously coordinates a 5-stage lifecycle.
* It invokes 5 typed Google ADK tools.
* It maintains thread-safe, verifiable state persistence.
* It outputs complete technical dossiers with SHA-256 integrity verification.

---

## 3. Architecture & Data Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                       USER INTERACTION ("HAZ TU PREGUNTA")                 │
│                 "What do you want to solve?" (Web UI / REST API)            │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             SUPRA AGENT ORCHESTRATOR (Google ADK + Gemini 3.7 Flash)        │
│          • Autonomous Multi-Turn Coordinator                                │
│          • Vertex AI / Cloud Run Managed Environment                        │
└──────┬───────────────────────┬───────────────────────┬───────────────┬──────┘
       │                       │                       │               │
       ▼                       ▼                       ▼               ▼
┌──────────────┐       ┌──────────────┐       ┌────────────────┐ ┌────────────┐
│ Tool 1       │       │ Tool 2       │       │ Tool 3 & 4     │ │ Tool 5     │
│ decompose_   │       │ synthesize_  │       │ verify_solution│ │ record_    │
│ objective    │       │ strategy     │       │ execute_sandbox│ │ checkpoint │
└──────┬───────┘       └──────┬───────┘       └───────┬────────┘ └─────┬──────┘
       │                       │                       │               │
       └───────────────────────┼───────────────────────┴───────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THREAD-SAFE STATE MACHINE & PERSISTENCE                  │
│   RECEIVED ──► STRUCTURED ──► STRATIFIED ──► SANDBOX_VERIFIED ──► COMPLETED  │
│   • Checkpoint History • Invariant Ledger • SHA-256 Cryptographic Audit Hash │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│             VERIFIABLE DELIVERABLE & EXPORTABLE TECHNICAL DOSSIER           │
│         (1-Click Judge Demo &bull; Markdown Export &bull; Live Telemetry)   │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. The 5 Autonomous Stages

1. **RECEIVED (`01`)**: Captures objective and initializes isolated project session.
2. **STRUCTURED (`02`)**: Decomposes problem into core invariants, mutable assumptions, and subtasks via `decompose_objective`.
3. **STRATIFIED (`03`)**: Formulates Conservative, Orthogonal, and Disruptive pathways and auto-selects the optimal strategy via `synthesize_strategy`.
4. **SANDBOX_VERIFIED (`04`)**: Validates system invariants via `verify_solution` and runs isolated AST simulation in the micro-sandbox via `execute_sandbox_action`.
5. **COMPLETED (`05`)**: Issues the final technical deliverable with checkpoints, telemetry, and SHA-256 cryptographic audit hash via `record_checkpoint`.

---

## 5. Google Technologies Integration

* **Gemini 3.7 Flash:** Serves as the primary reasoning and decision engine.
* **Google ADK (Agent Development Kit):** Orchestrates tool-calling turn sequences and autonomous state resolution.
* **Google Cloud Run:** Hosts the containerized FastAPI backend with auto-scaling, low latency, and global availability.
* **Google Cloud Build:** Manages the automated multi-stage CI/CD container build pipeline.

---

## 6. Installation & Spin-Up

### Prerequisites
* Python 3.11+
* Git
* (Optional) Google Cloud SDK / Vertex AI credentials

### Local Run

```bash
# 1. Clone repository
git clone https://github.com/klssxx/supra-agentic-taskmaster.git
cd supra-agentic-taskmaster

# 2. Install dependencies
pip install -e .

# 3. Start production server
uvicorn supra_agentic.service:app --host 0.0.0.0 --port 8080
```

Open your browser at `http://localhost:8080`.

### Running Tests

```bash
pytest
```

---

## 7. 1-Click Judge Demo Endpoint

For instantaneous evaluation by competition judges:

```bash
# 1-Click Judge Golden Run (<0.5s execution)
curl http://localhost:8080/api/v1/demo/quick-run
```

---

## 8. Originality & Disclosures

* **Clean-Room Build:** Created strictly during the All Things Agentic Hackathon 2026 Submission Period.
* **Zero Legacy Dependencies:** Independent, self-contained architecture with no proprietary imports or symlinks to older local codebases.
* Full audit trail documented in `docs/ORIGINALITY_LEDGER.md` and `docs/BUILD_TIMELINE.md`.

---

## 9. License

Licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.
