"""Domain Models and Data Schemas for SUPRA Agentic Taskmaster."""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

RESTRICTED_EXECUTION_SEMANTICS_VERSION = 2
MAX_SAFE_ATTEMPT_GENERATION = (1 << 53) - 1
_ATTEMPT_ID_RE = re.compile(r"^attempt-[0-9a-f]{32}$")


def _is_canonical_attempt_id(value: object) -> bool:
    return isinstance(value, str) and bool(_ATTEMPT_ID_RE.fullmatch(value))


def _is_server_attempt_id(value: str | None) -> bool:
    """Recognize only attempt identifiers emitted by SUPRA itself."""
    if not isinstance(value, str) or not value.startswith("attempt-"):
        return False
    suffix = value.removeprefix("attempt-")
    return len(suffix) == 32 and all(ch in "0123456789abcdef" for ch in suffix)


def is_sha256_version(value: str | None) -> bool:
    """Return whether a version is a canonical lowercase SHA-256 identifier."""
    if not isinstance(value, str) or not value.startswith("sha256:"):
        return False
    digest = value.removeprefix("sha256:")
    return len(digest) == 64 and all(ch in "0123456789abcdef" for ch in digest)


class TaskmasterStage(str, Enum):
    """5 Canonical Stages of the Taskmaster Agent Lifecycle."""

    RECEIVED = "RECEIVED"
    STRUCTURED = "STRUCTURED"
    STRATIFIED = "STRATIFIED"
    RESTRICTED_EXECUTION_VERIFIED = "RESTRICTED_EXECUTION_VERIFIED"
    BLOCKED = "BLOCKED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

    @classmethod
    def _missing_(cls, value: object):
        # Legacy SANDBOX_VERIFIED cannot be promoted into the stronger current
        # execution-accreditation state. Preserve workflow progress only.
        if value == "SANDBOX_VERIFIED":
            return cls.STRATIFIED
        return None


class Subtask(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(default_factory=lambda: f"sub-{uuid.uuid4().hex[:6]}")
    title: str
    description: str
    stage_target: TaskmasterStage
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, SKIPPED


class StructuredDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: str
    core_objective: str
    invariants: list[str] = Field(default_factory=list)
    mutable_assumptions: list[str] = Field(default_factory=list)
    risk_factors: list[str] = Field(default_factory=list)
    subtasks: list[Subtask] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class StrategyCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate_id: str = Field(default_factory=lambda: f"cand-{uuid.uuid4().hex[:6]}")
    pathway_name: str
    paradigm_type: Literal["CONSERVATIVE", "ORTHOGONAL", "LATERAL", "DISRUPTIVE"]
    hypothesis: str
    action_plan: list[str] = Field(default_factory=list)
    divergence_score: float = Field(default=0.5, ge=0.0, le=1.0, allow_inf_nan=False)
    feasibility_score: float = Field(default=0.8, ge=0.0, le=1.0, allow_inf_nan=False)
    is_selected: bool = False

    @field_validator("candidate_id")
    @classmethod
    def _candidate_id_nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("candidate_id must be non-blank")
        return value


def candidate_execution_identity(candidate: StrategyCandidate) -> dict[str, str]:
    """Deterministic identity of the persisted candidate mechanism/claim."""
    mechanism_payload = json.dumps(
        {
            "candidate_id": candidate.candidate_id,
            "pathway_name": candidate.pathway_name,
            "hypothesis": candidate.hypothesis,
            "action_plan": candidate.action_plan,
        },
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return {
        "candidate_id": candidate.candidate_id,
        "mechanism_version": "sha256:"
        + hashlib.sha256(mechanism_payload.encode("utf-8")).hexdigest(),
        "claim_id": "claim-"
        + hashlib.sha256(candidate.hypothesis.encode("utf-8")).hexdigest()[:24],
    }


class VerificationReport(BaseModel):
    """Scoped strategy-coverage report, not deployed-system certification."""

    model_config = ConfigDict(extra="forbid")
    report_id: str = Field(default_factory=lambda: f"rep-{uuid.uuid4().hex[:6]}")
    candidate_id: str
    invariants_preserved: bool = False
    invariants_checked: list[str] = Field(default_factory=list)
    vulnerabilities_detected: list[str] = Field(default_factory=list)
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)
    verdict: Literal["PASS", "CONDITIONAL_PASS", "FAIL", "NOT_EVALUATED"] = "NOT_EVALUATED"
    verification_scope: Literal["TEXTUAL_STRATEGY_COVERAGE"] = "TEXTUAL_STRATEGY_COVERAGE"
    measurement_kind: Literal["HEURISTIC_COVERAGE"] = "HEURISTIC_COVERAGE"
    confidence_semantics: str = "FRACTION_OF_DECLARED_INVARIANTS_WITH_HEURISTIC_PASS"
    rationale: str = ""
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    timestamp: float = Field(default_factory=time.time)


class RestrictedExecutionResult(BaseModel):
    """Telemetry for trusted, in-process restricted execution.

    This model does not assert OS/process isolation and is not evidence that
    arbitrary untrusted code is safe.
    """

    model_config = ConfigDict(extra="forbid")
    execution_id: str = Field(default_factory=lambda: f"exec-{uuid.uuid4().hex[:6]}")
    attempt_id: str | None = None
    attempt_generation: int | None = Field(
        default=None, strict=True, ge=1, le=MAX_SAFE_ATTEMPT_GENERATION
    )
    execution_semantics_version: int | None = None
    candidate_id: str | None = None
    mechanism_version: str | None = None
    claim_id: str | None = None
    protocol_version: str | None = None
    observed_result: str | None = None
    action_type: str
    passed: bool
    output_log: str
    error_type: str | None = None
    duration_ms: float
    side_effects_contained: bool = False
    execution_classification: str = "RESTRICTED_EXECUTION"
    result_scope: str = "RESTRICTED_EXECUTION_ONLY"
    scientific_validation: bool = False
    process_isolated: bool = False
    secure_for_untrusted_code: bool = False
    identity_bound: bool = False
    timestamp: float = Field(default_factory=time.time)

    @field_validator("side_effects_contained", "process_isolated", "secure_for_untrusted_code")
    @classmethod
    def reject_unproven_security_claims(cls, value: bool) -> bool:
        if value:
            raise ValueError("restricted execution cannot claim security isolation")
        return value

    @field_validator("scientific_validation")
    @classmethod
    def reject_scientific_validation_claim(cls, value: bool) -> bool:
        if value:
            raise ValueError("restricted execution cannot claim scientific validation")
        return value

    @model_validator(mode="after")
    def derive_identity_binding(self) -> RestrictedExecutionResult:
        complete = all(
            isinstance(value, str) and bool(value.strip())
            for value in (
                self.candidate_id,
                self.mechanism_version,
                self.claim_id,
                self.protocol_version,
                self.execution_id,
            )
        )
        self.identity_bound = bool(
            complete
            and is_sha256_version(self.protocol_version)
            and self.execution_semantics_version == RESTRICTED_EXECUTION_SEMANTICS_VERSION
        )
        return self


class CheckpointRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")
    checkpoint_id: str = Field(default_factory=lambda: f"chk-{uuid.uuid4().hex[:6]}")
    stage: TaskmasterStage
    title: str
    evidence_summary: str
    actor: str = "agent:supra:provider"
    timestamp: float = Field(default_factory=time.time)


class ProjectPosture(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_execution_telemetry(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        migrated = dict(value)

        if "sandbox_results" in migrated:
            legacy_results = migrated.pop("sandbox_results")
            migrated_results = []
            for result in legacy_results if isinstance(legacy_results, list) else []:
                if isinstance(result, dict):
                    result = dict(result)
                    result["side_effects_contained"] = False
                    result.setdefault("execution_classification", "RESTRICTED_EXECUTION")
                    result.setdefault("process_isolated", False)
                    result.setdefault("secure_for_untrusted_code", False)
                    result.setdefault("scientific_validation", False)
                    result.setdefault("identity_bound", False)
                migrated_results.append(result)
            migrated["restricted_execution_results"] = migrated_results

        raw_results = migrated.get("restricted_execution_results")
        has_bound_pass = False
        for result in raw_results if isinstance(raw_results, list) else []:
            if not isinstance(result, dict) or result.get("passed") is not True:
                continue
            identity_complete = all(
                isinstance(field_value := result.get(field), str) and bool(field_value.strip())
                for field in (
                    "candidate_id",
                    "mechanism_version",
                    "claim_id",
                    "protocol_version",
                    "execution_id",
                )
            )
            semantics_current = (
                result.get("execution_semantics_version") == RESTRICTED_EXECUTION_SEMANTICS_VERSION
            )
            if identity_complete and semantics_current:
                has_bound_pass = True
                break

        stage = migrated.get("stage")
        if stage in {"SANDBOX_VERIFIED", "RESTRICTED_EXECUTION_VERIFIED"} and not has_bound_pass:
            migrated["stage"] = "STRATIFIED"
            checkpoints = list(migrated.get("checkpoints") or [])
            checkpoints.append(
                {
                    "stage": "STRATIFIED",
                    "title": "Legacy execution accreditation invalidated",
                    "evidence_summary": (
                        "Persisted execution-derived stage was downgraded on load "
                        "because no bound passing execution satisfies current semantics."
                    ),
                    "actor": "system:migration_guard",
                }
            )
            migrated["checkpoints"] = checkpoints
        return migrated

    @model_validator(mode="after")
    def revalidate_persisted_execution_accreditation(self) -> ProjectPosture:
        """Revalidate execution-derived state on every load/restart.

        Workflow completion is historical and is not erased. Execution binding,
        however, is derived state: it must still match the persisted selected
        candidate under the current semantics. Cached/final-output execution
        labels are recomputed from that revalidated source state.
        """
        selected_matches = (
            [
                candidate
                for candidate in self.candidates
                if self.selected_candidate is not None
                and candidate.candidate_id == self.selected_candidate.candidate_id
                and candidate.model_dump() == self.selected_candidate.model_dump()
            ]
            if self.selected_candidate is not None
            else []
        )
        expected = (
            candidate_execution_identity(self.selected_candidate)
            if len(selected_matches) == 1 and self.selected_candidate is not None
            else None
        )

        invalid_current_attempt = bool(
            (
                self.restricted_execution_generation == 0
                and self.restricted_execution_attempt_id is not None
            )
            or (
                self.restricted_execution_generation > 0
                and not _is_canonical_attempt_id(self.restricted_execution_attempt_id)
            )
        )
        if invalid_current_attempt:
            # Parseable persisted text is not authority merely because a result
            # repeats it. Only IDs in the server-issued canonical namespace can
            # participate in current execution accreditation.
            self.restricted_execution_attempt_id = None
            self.checkpoints.append(
                CheckpointRecord(
                    stage=self.stage,
                    title="Malformed execution-attempt authority invalidated",
                    evidence_summary=(
                        "Persisted attempt authority did not match the server-issued "
                        "attempt-<32 lowercase hex> format and was cleared on load."
                    ),
                    actor="system:migration_guard",
                )
            )

        for result in self.restricted_execution_results:
            matches_selected_candidate = bool(
                result.identity_bound
                and _is_canonical_attempt_id(result.attempt_id)
                and isinstance(result.attempt_generation, int)
                and result.attempt_generation >= 1
                and expected is not None
                and result.candidate_id == expected["candidate_id"]
                and result.mechanism_version == expected["mechanism_version"]
                and result.claim_id == expected["claim_id"]
                and is_sha256_version(result.protocol_version)
                and _is_server_attempt_id(result.attempt_id)
            )
            result.identity_bound = matches_selected_candidate

        # Persisted state may be parseable yet contain multiple results for one
        # issued attempt/generation. Such a state has no unique causal authority:
        # fail closed by invalidating every colliding result instead of letting
        # list order select a winner after restart.
        attempt_groups: dict[tuple[str, int], list[RestrictedExecutionResult]] = {}
        for result in self.restricted_execution_results:
            if isinstance(result.attempt_id, str) and result.attempt_id and isinstance(
                result.attempt_generation, int
            ):
                attempt_groups.setdefault(
                    (result.attempt_id, result.attempt_generation), []
                ).append(result)
        duplicate_attempt_groups = {
            key: results for key, results in attempt_groups.items() if len(results) > 1
        }
        for results in duplicate_attempt_groups.values():
            for result in results:
                result.identity_bound = False
        if duplicate_attempt_groups:
            self.checkpoints.append(
                CheckpointRecord(
                    stage=self.stage,
                    title="Duplicate execution-attempt authority invalidated",
                    evidence_summary=(
                        "Persisted execution results reused one issued attempt/generation; "
                        "all colliding results were invalidated because list order is not "
                        "causal authority."
                    ),
                    actor="system:migration_guard",
                )
            )

        authoritative_executions = [
            result
            for result in self.restricted_execution_results
            if _is_server_attempt_id(self.restricted_execution_attempt_id)
            and result.attempt_id == self.restricted_execution_attempt_id
            and result.attempt_generation == self.restricted_execution_generation
        ]
        # Persisted duplicate results for one current attempt are ambiguous
        # authority (corruption, replay, or a prior race). Fail closed rather
        # than letting list order choose PASS versus FAIL after restart.
        current_execution_ids = {result.execution_id for result in authoritative_executions}
        semantic_current_results = {
            json.dumps(
                result.model_dump(exclude={"timestamp"}),
                sort_keys=True,
                separators=(",", ":"),
            )
            for result in authoritative_executions
        }
        if len(current_execution_ids) > 1 or len(semantic_current_results) > 1:
            for result in authoritative_executions:
                result.identity_bound = False
        latest_execution = authoritative_executions[-1] if authoritative_executions else None
        latest_authoritative_bound_pass = bool(
            latest_execution and latest_execution.passed and latest_execution.identity_bound
        )
        current_attempt_issued = bool(
            self.restricted_execution_generation >= 1
            and _is_canonical_attempt_id(self.restricted_execution_attempt_id)
        )
        if self.final_output is not None:
            output = dict(self.final_output)
            output["restricted_execution_identity_bound"] = bool(
                latest_execution and latest_execution.identity_bound
            )
            output["restricted_execution_status"] = (
                "BOUND_PASS"
                if latest_execution and latest_execution.passed and latest_execution.identity_bound
                else "BOUND_FAIL"
                if latest_execution and latest_execution.identity_bound
                else "UNBOUND"
                if latest_execution
                else "PENDING"
                if current_attempt_issued
                else "UNBOUND"
                if self.restricted_execution_results
                else "NOT_RUN"
            )
            output["derived_execution_state_revalidated"] = True
            self.final_output = output

        if (
            self.stage is TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
            and not latest_authoritative_bound_pass
        ):
            self.stage = TaskmasterStage.STRATIFIED
            self.checkpoints.append(
                CheckpointRecord(
                    stage=TaskmasterStage.STRATIFIED,
                    title="Persisted execution accreditation invalidated",
                    evidence_summary=(
                        "Execution-derived stage was downgraded on load because "
                        "no current-semantics bound pass matches the persisted "
                        "selected candidate."
                    ),
                    actor="system:migration_guard",
                )
            )

        verification_pass = bool(
            self.verification
            and self.verification.verdict == "PASS"
            and expected is not None
            and self.selected_candidate is not None
            and self.verification.candidate_id == self.selected_candidate.candidate_id
        )
        if self.stage is TaskmasterStage.BLOCKED:
            # BLOCKED is an honest non-completed outcome. Persisted or legacy
            # completion/error payloads must not survive reload and create a
            # contradictory consumer-visible claim.
            self.final_output = None
            self.error_message = None

        if self.stage is TaskmasterStage.COMPLETED and not (
            verification_pass and latest_authoritative_bound_pass
        ):
            self.stage = (
                TaskmasterStage.RESTRICTED_EXECUTION_VERIFIED
                if latest_authoritative_bound_pass
                else TaskmasterStage.STRATIFIED
                if self.selected_candidate is not None
                else TaskmasterStage.STRUCTURED
                if self.decomposition is not None
                else TaskmasterStage.RECEIVED
            )
            if self.final_output is not None:
                output = dict(self.final_output)
                output["workflow_status"] = "EVIDENCE_INVALIDATED"
                output["verification_verdict"] = (
                    self.verification.verdict if self.verification else "NOT_EVALUATED"
                )
                self.final_output = output
            self.checkpoints.append(
                CheckpointRecord(
                    stage=self.stage,
                    title="Persisted completion invalidated",
                    evidence_summary=(
                        "COMPLETED was downgraded on load because current verification "
                        "PASS and latest bound restricted execution PASS are both required."
                    ),
                    actor="system:migration_guard",
                )
            )
        return self

    project_id: str
    objective: str
    stage: TaskmasterStage
    created_at: float
    updated_at: float
    criba_dossier_receipt: dict[str, Any] | None = None
    decomposition: StructuredDecomposition | None = None
    candidates: list[StrategyCandidate] = Field(default_factory=list)
    selected_candidate: StrategyCandidate | None = None
    verification: VerificationReport | None = None
    restricted_execution_results: list[RestrictedExecutionResult] = Field(default_factory=list)
    restricted_execution_generation: int = Field(
        default=0, strict=True, ge=0, le=MAX_SAFE_ATTEMPT_GENERATION
    )
    restricted_execution_attempt_id: str | None = None
    checkpoints: list[CheckpointRecord] = Field(default_factory=list)
    final_output: dict[str, Any] | None = None
    error_message: str | None = None

    def current_authoritative_execution(self) -> RestrictedExecutionResult | None:
        """Return the unique current attempt result, or None when authority is ambiguous."""
        return current_authoritative_execution(self)

    @field_validator("criba_dossier_receipt")
    @classmethod
    def validate_criba_dossier_receipt(
        cls, value: dict[str, Any] | None
    ) -> dict[str, Any] | None:
        """Persist CRIBA planning input without promoting it to execution evidence."""
        if value is None:
            return None
        receipt = dict(value)
        if receipt.get("receipt_scope") != "PLANNED_DISCRIMINANT_PROTOCOL_ONLY":
            raise ValueError("CRIBA dossier receipt has invalid scope")
        if receipt.get("execution_status") != "NOT_EXECUTED":
            raise ValueError("CRIBA dossier receipt cannot claim execution")
        if receipt.get("scientific_status") != "NOT_VALIDATED":
            raise ValueError("CRIBA dossier receipt cannot claim scientific validation")
        required = (
            "criba_dossier_id",
            "criba_candidate_id",
            "claim_id",
            "mechanism_version",
            "protocol_version",
            "alternativa_explicativa",
            "intervencion_prueba",
            "observable",
            "resultado_favorable_mecanismo",
            "resultado_favorable_alternativa",
            "regla_decision",
            "condicion_fracaso",
        )
        if not all(
            isinstance(receipt.get(field), str) and receipt[field].strip()
            for field in required
        ):
            raise ValueError("CRIBA dossier receipt is incomplete")
        return receipt


def current_authoritative_execution(
    posture: ProjectPosture,
) -> RestrictedExecutionResult | None:
    """Return the unique result for the currently issued execution attempt.

    Historical arrival order is never authority. A missing, malformed, or
    duplicate current attempt returns ``None`` so consumers fail closed.
    """
    if (
        posture.restricted_execution_generation < 1
        or not _is_canonical_attempt_id(posture.restricted_execution_attempt_id)
    ):
        return None
    matches = [
        result
        for result in posture.restricted_execution_results
        if result.attempt_id == posture.restricted_execution_attempt_id
        and result.attempt_generation == posture.restricted_execution_generation
    ]
    return matches[0] if len(matches) == 1 else None
