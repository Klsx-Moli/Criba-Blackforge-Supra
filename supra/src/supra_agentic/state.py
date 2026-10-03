"""Thread-safe file-backed project state manager.

Filesystem storage is classified honestly as local, configured, or instance
ephemeral. A configured path may be durable only when the deployment mounts
a durable external backend there.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from .models import (
    MAX_SAFE_ATTEMPT_GENERATION,
    CheckpointRecord,
    ProjectPosture,
    RestrictedExecutionResult,
    StrategyCandidate,
    StructuredDecomposition,
    TaskmasterStage,
    VerificationReport,
    candidate_execution_identity,
    current_authoritative_execution,
    is_sha256_version,
)

logger = logging.getLogger("supra_agentic.state")

_PROJECT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")


class DuplicateProjectError(ValueError):
    """Raised when project creation would overwrite existing persisted state."""


class ProjectStateLoadError(RuntimeError):
    """Raised when a persisted project exists but cannot be trusted or decoded."""

    def __init__(self, project_id: str, error_type: str) -> None:
        self.project_id = project_id
        self.error_type = error_type
        super().__init__(
            f"persisted project {project_id!r} is corrupt or incompatible ({error_type})"
        )


# Where a served posture came from. Declared, never inferred by the consumer.
PROVENANCE_ARTIFACT = "PERSISTED_STATE"
PROVENANCE_MEMORY_CACHE = "IN_PROCESS_MEMORY_CACHE"

# Verification verdict for the durable copy that backs the served posture.
# These are four distinct facts; collapsing them is what made a cached read
# indistinguishable from a persisted one.
ARTIFACT_VERIFIED = "VERIFIED_FROM_ARTIFACT"
ARTIFACT_MATCHES_CACHE = "MATCHES_CACHE"
ARTIFACT_DIVERGES = "DIVERGES_FROM_CACHE"
ARTIFACT_UNVERIFIABLE = "UNVERIFIABLE"
ARTIFACT_MISSING = "MISSING"


def _validate_project_id(project_id: str) -> str:
    """Return a storage-safe project identifier or reject it."""
    if not _PROJECT_ID_RE.fullmatch(project_id) or project_id in {".", ".."}:
        raise ValueError("project_id must be 1-64 storage-safe ASCII characters")
    return project_id


def _get_storage_configuration(
    explicit: Path | str | None = None,
) -> tuple[Path, str]:
    """Resolve filesystem location without claiming unverified durability."""
    if explicit is not None:
        return Path(explicit), "CONFIGURED_FILESYSTEM"
    for env_var in ("SUPRA_STORAGE_DIR", "CLOUD_RUN_PERSISTENT_DIR"):
        if path := os.getenv(env_var):
            return Path(path), "CONFIGURED_FILESYSTEM"
    if os.getenv("K_SERVICE"):
        return Path(tempfile.gettempdir()) / "supra-agentic", "INSTANCE_EPHEMERAL"
    if os.name == "nt":
        root = Path(os.getenv("LOCALAPPDATA", tempfile.gettempdir()))
        return root / "SUPRA-Agentic", "LOCAL_FILESYSTEM"
    return Path.home() / ".supra" / "projects", "LOCAL_FILESYSTEM"


class ProjectStateManager:
    """Manage project lifecycles with locked filesystem persistence."""

    def __init__(self, storage_dir: Path | str | None = None) -> None:
        self._lock = threading.RLock()
        self._projects: dict[str, ProjectPosture] = {}
        self._last_list_load_errors: list[dict[str, str]] = []
        self.storage_dir, self.storage_mode = _get_storage_configuration(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        objective: str,
        project_id: str | None = None,
        *,
        criba_dossier_receipt: dict[str, Any] | None = None,
    ) -> ProjectPosture:
        """Create a new project session in RECEIVED stage."""
        with self._lock:
            pid = _validate_project_id(project_id) if project_id is not None else f"proj-{uuid.uuid4().hex[:8]}"
            if pid in self._projects or (self.storage_dir / f"{pid}.json").exists():
                raise DuplicateProjectError(f"project_id {pid!r} already exists")
            now = time.time()
            posture = ProjectPosture(
                project_id=pid,
                objective=objective.strip(),
                stage=TaskmasterStage.RECEIVED,
                created_at=now,
                updated_at=now,
                criba_dossier_receipt=criba_dossier_receipt,
                checkpoints=[
                    CheckpointRecord(
                        stage=TaskmasterStage.RECEIVED,
                        title="Project Initialized",
                        evidence_summary=f"Objective registered: '{objective[:100]}...'",
                        actor="system:session_manager",
                    )
                ],
            )
            self._projects[pid] = posture
            self._persist_transition_or_rollback(pid, None)
            return posture

    def get_project(self, project_id: str) -> ProjectPosture | None:
        """Retrieve a project state by ID.

        Compatibility wrapper: callers that do not care about provenance keep
        this signature. ``get_project_with_provenance`` is the same read plus
        the two facts the wrapper used to assert on its behalf.
        """
        posture, _source, _artifact = self.get_project_with_provenance(project_id)
        return posture

    def get_project_with_provenance(
        self, project_id: str
    ) -> tuple[ProjectPosture | None, str, str]:
        """Retrieve a project state and declare where it actually came from.

        M3 decision on the limitation K1 declared: the in-process cache is
        sound, the label was not. A cache hit is a real, correct answer, but it
        is not read from the durable copy, so it must not be published as
        ``PERSISTED_STATE``. The artifact verdict travels with the answer
        instead of replacing it, because refusing to serve a correct posture
        because its duplicate is unverifiable would throw away true state.

        Reproduced by execution against the real server before this change:
        a live read of a project whose artifact had been corrupted returned
        200 with ``status_source=PERSISTED_STATE`` and an empty
        ``storage_errors``, and only the process restart turned it into 500.
        """
        with self._lock:
            _validate_project_id(project_id)
            p_file = self.storage_dir / f"{project_id}.json"
            cached = self._projects.get(project_id)

            if cached is not None:
                return (
                    cached,
                    PROVENANCE_MEMORY_CACHE,
                    self._classify_artifact(p_file, cached),
                )

            if p_file.exists():
                try:
                    data = json.loads(p_file.read_text(encoding="utf-8"))
                    posture = ProjectPosture.model_validate(data)
                except Exception as exc:
                    error_type = type(exc).__name__
                    logger.error(
                        "Failed to load project %s from disk (%s)",
                        project_id,
                        error_type,
                    )
                    raise ProjectStateLoadError(project_id, error_type) from exc
                self._projects[project_id] = posture
                return posture, PROVENANCE_ARTIFACT, ARTIFACT_VERIFIED
            return None, PROVENANCE_ARTIFACT, ARTIFACT_MISSING

    def _classify_artifact(self, p_file: Path, cached: ProjectPosture) -> str:
        """Report what the durable copy says about a memory-served posture.

        Never raises: this describes the duplicate of an answer already being
        served, and failing here would turn a healthy read into an error.
        """
        if not p_file.exists():
            return ARTIFACT_MISSING
        try:
            raw = p_file.read_text(encoding="utf-8")
            on_disk = ProjectPosture.model_validate(json.loads(raw))
        except Exception as exc:  # noqa: BLE001 — any decode failure is UNVERIFIABLE
            logger.error(
                "Cached project %s has an unreadable artifact (%s)",
                cached.project_id,
                type(exc).__name__,
            )
            return ARTIFACT_UNVERIFIABLE
        return ARTIFACT_MATCHES_CACHE if on_disk == cached else ARTIFACT_DIVERGES

    def update_decomposition(
        self, project_id: str, decomp: StructuredDecomposition
    ) -> ProjectPosture:
        """Store decomposition and advance stage to STRUCTURED."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            p.decomposition = decomp
            p.stage = TaskmasterStage.STRUCTURED
            p.updated_at = time.time()
            p.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.STRUCTURED,
                    title="Objective Structured",
                    evidence_summary=f"Decomposed into {len(decomp.invariants)} invariants, {len(decomp.mutable_assumptions)} mutable assumptions, and {len(decomp.subtasks)} subtasks.",
                    actor="agent:supra:decompose",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def add_candidates(
        self, project_id: str, candidates: list[StrategyCandidate], select_best: bool = True
    ) -> ProjectPosture:
        """Store strategy candidates and advance stage to STRATIFIED."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            candidate_ids = [candidate.candidate_id for candidate in candidates]
            if len(set(candidate_ids)) != len(candidate_ids):
                raise ValueError("duplicate candidate_id values are not allowed")
            p.candidates = candidates
            if select_best and candidates:
                # Select candidate with highest combined feasibility + divergence score
                best = max(
                    candidates, key=lambda c: c.feasibility_score * 0.6 + c.divergence_score * 0.4
                )
                best.is_selected = True
                p.selected_candidate = best
            p.stage = TaskmasterStage.STRATIFIED
            p.updated_at = time.time()
            sel_name = p.selected_candidate.pathway_name if p.selected_candidate else "None"
            p.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.STRATIFIED,
                    title="Strategies Synthesized",
                    evidence_summary=f"Generated {len(candidates)} strategic candidates. Selected primary pathway: '{sel_name}'.",
                    actor="agent:supra:strategy",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def record_verification(self, project_id: str, report: VerificationReport) -> ProjectPosture:
        """Store verification report."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            if (
                report.verdict == "PASS"
                and p.selected_candidate is not None
                and report.candidate_id != p.selected_candidate.candidate_id
            ):
                raise ValueError("verification PASS must bind the persisted selected candidate")
            p.verification = report
            if report.verdict != "PASS" and p.stage is TaskmasterStage.COMPLETED:
                current_execution = current_authoritative_execution(p)
                p.stage = (
                    TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
                    if current_execution
                    and current_execution.passed
                    and current_execution.identity_bound
                    else TaskmasterStage.STRATIFIED
                    if p.selected_candidate is not None
                    else TaskmasterStage.STRUCTURED
                    if p.decomposition is not None
                    else TaskmasterStage.RECEIVED
                )
                if p.final_output is not None:
                    output = dict(p.final_output)
                    output["workflow_status"] = "EVIDENCE_INVALIDATED"
                    output["verification_verdict"] = report.verdict
                    p.final_output = output
            p.updated_at = time.time()
            p.checkpoints.append(
                CheckpointRecord(
                    stage=p.stage,
                    title="Strategy Coverage Evaluated",
                    evidence_summary=(
                        f"Coverage verdict: {report.verdict}; "
                        f"coverage fraction: {report.confidence_score:.2f}; "
                        f"scope: {report.verification_scope}; "
                        "not deployed-system or scientific validation."
                    ),
                    actor="agent:supra:verifier",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def issue_restricted_execution_attempt(self, project_id: str) -> tuple[str, int]:
        """Persist causal authority before restricted execution starts."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            if p.restricted_execution_generation >= MAX_SAFE_ATTEMPT_GENERATION:
                raise ValueError(
                    "restricted execution generation exhausted JavaScript-safe integer range"
                )
            p.restricted_execution_generation += 1
            p.restricted_execution_attempt_id = f"attempt-{uuid.uuid4().hex}"
            if p.stage in {
                TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED,
                TaskmasterStage.COMPLETED,
            }:
                p.stage = (
                    TaskmasterStage.STRATIFIED
                    if p.selected_candidate is not None
                    else TaskmasterStage.STRUCTURED
                    if p.decomposition is not None
                    else TaskmasterStage.RECEIVED
                )
            if p.final_output is not None:
                output = dict(p.final_output)
                output["restricted_execution_status"] = "PENDING"
                output["restricted_execution_identity_bound"] = False
                output["workflow_status"] = "EVIDENCE_INVALIDATED"
                p.final_output = output
            p.updated_at = time.time()
            self._persist_transition_or_rollback(project_id, before)
            return p.restricted_execution_attempt_id, p.restricted_execution_generation

    def record_restricted_execution(
        self, project_id: str, result: RestrictedExecutionResult
    ) -> ProjectPosture:
        """Record trusted restricted execution without claiming process isolation."""
        with self._lock:
            p = self._get_required_project(project_id)
            authoritative_attempt = bool(
                result.attempt_id
                and result.attempt_id == p.restricted_execution_attempt_id
                and result.attempt_generation == p.restricted_execution_generation
            )
            expected = (
                candidate_execution_identity(p.selected_candidate)
                if p.selected_candidate is not None
                else None
            )
            identity_matches = bool(
                result.identity_bound
                and expected is not None
                and result.candidate_id == expected["candidate_id"]
                and result.mechanism_version == expected["mechanism_version"]
                and result.claim_id == expected["claim_id"]
                and is_sha256_version(result.protocol_version)
            )
            result.identity_bound = bool(identity_matches and authoritative_attempt)

            # One issued attempt names exactly one semantic execution event.
            # A second execution_id for the same attempt/generation is a
            # conflicting replay, not a newer authority-bearing result.
            if authoritative_attempt:
                for existing in p.restricted_execution_results:
                    same_attempt = (
                        existing.attempt_id == result.attempt_id
                        and existing.attempt_generation == result.attempt_generation
                    )
                    if same_attempt and existing.execution_id != result.execution_id:
                        raise ValueError(
                            "attempt result conflict: same attempt has multiple execution ids"
                        )

            # execution_id names one semantic execution event. Retries of the
            # same event are idempotent; reusing the id for different content
            # is a conflict and must never change which event is authoritative.
            semantic_result = result.model_dump(exclude={"timestamp", "identity_bound"})
            for existing in p.restricted_execution_results:
                if existing.execution_id != result.execution_id:
                    continue
                semantic_existing = existing.model_dump(exclude={"timestamp", "identity_bound"})
                if semantic_existing == semantic_result:
                    return p
                raise ValueError("execution_id conflict: same id has different semantic payload")

            # A server-issued attempt is a single causal execution slot. It may
            # produce at most one semantic result. Allowing a second execution_id
            # for the same attempt/generation would make arrival order decide the
            # authoritative outcome (FAIL->PASS or PASS->FAIL), defeating the
            # generation contract. Exact replay is already handled above.
            if result.attempt_id is not None and result.attempt_generation is not None:
                for existing in p.restricted_execution_results:
                    if (
                        existing.attempt_id == result.attempt_id
                        and existing.attempt_generation == result.attempt_generation
                    ):
                        raise ValueError(
                            "attempt result conflict: one issued attempt cannot have multiple execution results"
                        )

            before = p.model_copy(deep=True)
            p.restricted_execution_results.append(result)
            if not authoritative_attempt:
                p.updated_at = time.time()
                self._persist_transition_or_rollback(project_id, before)
                return p
            if p.stage is not TaskmasterStage.FAILED:
                if result.passed and identity_matches:
                    if p.stage is not TaskmasterStage.COMPLETED:
                        p.stage = TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
                elif p.selected_candidate is not None:
                    # The latest bound or unbound review replaces derived
                    # execution state; a failed review cannot preserve PASS or COMPLETED.
                    p.stage = TaskmasterStage.STRATIFIED
                elif p.stage is TaskmasterStage.COMPLETED:
                    p.stage = TaskmasterStage.RECEIVED
            if p.final_output is not None:
                output = dict(p.final_output)
                output["restricted_execution_identity_bound"] = result.identity_bound
                output["restricted_execution_status"] = (
                    "BOUND_PASS"
                    if result.passed and result.identity_bound
                    else "BOUND_FAIL"
                    if result.identity_bound
                    else "UNBOUND"
                )
                output["derived_execution_state_revalidated"] = True
                if not (result.passed and result.identity_bound):
                    output["workflow_status"] = "EVIDENCE_INVALIDATED"
                p.final_output = output
            p.updated_at = time.time()
            p.checkpoints.append(
                CheckpointRecord(
                    stage=p.stage,
                    title="Trusted Restricted Execution",
                    evidence_summary=(
                        f"Executed {result.action_type} in {result.duration_ms:.1f}ms. "
                        f"Passed: {result.passed}. Identity bound: {result.identity_bound}. "
                        "Process isolated: False. Scientific validation: False."
                    ),
                    actor="agent:supra:restricted-executor",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def complete_project(self, project_id: str, final_output: dict[str, Any]) -> ProjectPosture:
        """Mark workflow completion without implying verification or scientific proof."""
        with self._lock:
            p = self._get_required_project(project_id)
            verification_pass = bool(
                p.verification
                and p.verification.verdict == "PASS"
                and p.selected_candidate is not None
                and p.verification.candidate_id == p.selected_candidate.candidate_id
            )
            latest_execution = current_authoritative_execution(p)
            execution_pass = bool(
                latest_execution and latest_execution.passed and latest_execution.identity_bound
            )
            if not verification_pass or not execution_pass:
                raise ValueError(
                    "completion gate requires verification PASS and latest bound restricted execution PASS"
                )
            before = p.model_copy(deep=True)
            p.final_output = final_output
            p.stage = TaskmasterStage.COMPLETED
            p.updated_at = time.time()
            verification_status = str(p.verification.verdict) if p.verification else "NOT_EVALUATED"
            execution_status = (
                "BOUND_PASS"
                if latest_execution and latest_execution.passed and latest_execution.identity_bound
                else "BOUND_FAIL"
                if latest_execution and latest_execution.identity_bound
                else "UNBOUND"
                if latest_execution
                else "NOT_RUN"
            )
            p.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.COMPLETED,
                    title="Taskmaster Workflow Complete",
                    evidence_summary=(
                        f"Workflow completed. Verification status: {verification_status}. "
                        f"Restricted execution status: {execution_status}. "
                        "Scientific validation: NOT_CLAIMED."
                    ),
                    actor="agent:supra:coordinator",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def block_project(self, project_id: str, reason: str) -> ProjectPosture:
        """Persist an honest non-terminal outcome when completion gates are unmet."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            p.stage = TaskmasterStage.BLOCKED
            p.error_message = None
            p.updated_at = time.time()
            p.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.BLOCKED,
                    title="Completion Gate Blocked",
                    evidence_summary=reason,
                    actor="system:completion_gate",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def fail_project(self, project_id: str, error_message: str) -> ProjectPosture:
        """Mark project as FAILED."""
        with self._lock:
            p = self._get_required_project(project_id)
            before = p.model_copy(deep=True)
            p.error_message = error_message
            p.stage = TaskmasterStage.FAILED
            p.updated_at = time.time()
            p.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.FAILED,
                    title="Mission Aborted",
                    evidence_summary=f"Error encountered: {error_message}",
                    actor="system:safety_guard",
                )
            )
            self._persist_transition_or_rollback(project_id, before)
            return p

    def list_projects_with_errors(
        self, limit: int = 50
    ) -> tuple[list[ProjectPosture], list[dict[str, str]]]:
        """Return projects and storage errors from one locked filesystem snapshot.

        Every artifact on disk is classified, INCLUDING the ones already in
        the in-process cache. Skipping the cached ones (the previous behaviour)
        let a corrupt or deleted artifact disappear from ``storage_errors``
        while the process lived: reproduced by execution, the listing returned
        an empty error list for a project whose file was no longer valid JSON.
        The enumeration that reports storage health must not be the one thing
        that cannot see a storage fault.
        """
        with self._lock:
            load_errors: list[dict[str, str]] = []
            for p_file in self.storage_dir.glob("*.json"):
                pid = p_file.stem
                try:
                    _validate_project_id(pid)
                except ValueError:
                    logger.error("Ignoring project file with invalid storage id: %s", p_file.name)
                    load_errors.append(
                        {"project_id": pid, "error": "INVALID_PROJECT_FILENAME"}
                    )
                    continue
                cached = self._projects.get(pid)
                if cached is not None:
                    verdict = self._classify_artifact(p_file, cached)
                    if verdict == ARTIFACT_UNVERIFIABLE:
                        load_errors.append(
                            {
                                "project_id": pid,
                                "error": "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE",
                            }
                        )
                    elif verdict == ARTIFACT_MISSING:
                        load_errors.append(
                            {"project_id": pid, "error": "PERSISTED_ARTIFACT_MISSING"}
                        )
                    continue
                try:
                    self.get_project(pid)
                except ProjectStateLoadError:
                    load_errors.append(
                        {
                            "project_id": pid,
                            "error": "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE",
                        }
                    )
            # A cached project whose artifact was deleted leaves no file to
            # glob, so it is checked explicitly instead of silently reported
            # as healthy.
            for pid in self._projects:
                if (self.storage_dir / f"{pid}.json").exists():
                    continue
                load_errors.append(
                    {"project_id": pid, "error": "PERSISTED_ARTIFACT_MISSING"}
                )
            self._last_list_load_errors = [dict(item) for item in load_errors]
            items = list(self._projects.values())
            items.sort(key=lambda x: x.updated_at, reverse=True)
            project_snapshot = [item.model_copy(deep=True) for item in items[:limit]]
            return project_snapshot, [dict(item) for item in load_errors]

    def list_projects(self, limit: int = 50) -> list[ProjectPosture]:
        """Compatibility wrapper returning only the project snapshot."""
        projects, _load_errors = self.list_projects_with_errors(limit=limit)
        return projects

    @property
    def last_list_load_errors(self) -> list[dict[str, str]]:
        """Return sanitized errors from the most recent project listing."""
        with self._lock:
            return [dict(item) for item in self._last_list_load_errors]

    def _get_required_project(self, project_id: str) -> ProjectPosture:
        p = self.get_project(project_id)
        if not p:
            raise KeyError(f"Project '{project_id}' not found.")
        return p

    def _persist_project(self, project_id: str) -> None:
        """Persist project to disk with proper error handling (B-6 fix)."""
        p = self._projects.get(project_id)
        if not p:
            logger.error(f"Cannot persist non-existent project {project_id}")
            return
        tmp_path: Path | None = None
        try:
            p_file = self.storage_dir / f"{project_id}.json"
            # The reader (`get_project`) decodes strictly as UTF-8, so the writer
            # must not defer to the host locale: text mode without an explicit
            # encoding emits the ANSI code page on Windows and any project with
            # a non-ASCII field becomes unreadable after restart. newline="\n"
            # additionally keeps the artifact byte-identical across hosts.
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=self.storage_dir,
                suffix=".tmp",
                delete=False,
            ) as tmp:
                tmp.write(p.model_dump_json(indent=2))
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = Path(tmp.name)
            tmp_path.replace(p_file)
        except Exception as exc:
            error_type = type(exc).__name__
            logger.error(
                "Project persistence failed (%s); data-loss risk for project %s",
                error_type,
                project_id,
            )
            raise RuntimeError(
                f"Persistence failed for project {project_id} ({error_type})"
            ) from exc
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    def _persist_transition_or_rollback(
        self, project_id: str, before: ProjectPosture | None
    ) -> None:
        """Persist one authority transition or restore its prior in-memory state."""
        try:
            self._persist_project(project_id)
        except Exception:
            if before is None:
                self._projects.pop(project_id, None)
            else:
                self._projects[project_id] = before
            raise


# Global Singleton Instance
state_manager = ProjectStateManager()
