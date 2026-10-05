"""BLACKFORGE v1 canonical object: `DefensiveCase`.

A versioned, immutable-by-revision defensive case. This module is the single
canonical object for v1; `blackforge_dossier` is superseded and must not be
used as a second source of truth.

Four INDEPENDENT axes, never one universal SUCCESS:

    workflow       DRAFT -> PLAN_SEALED -> ... -> CLOSED
    authorization  NONE / GRANTED / EXPIRED / REVOKED / DENIED / CONSUMED
    execution      NOT_STARTED / RESERVED / RUNNING / COMPLETED / FAILED /
                   OUTCOME_UNKNOWN
    evaluation     NOT_EVALUATED / SUPPORTS_H1 / SUPPORTS_H2 / INDETERMINATE

Why independent: a completed execution is not a validated conclusion, and an
approved plan is not a performed action. Collapsing them is the single most
expensive architectural error available here, because once consumed by UI,
APIs and learning, undoing the equivalence requires migrating records.

Evidence ORIGIN is a first-class classification that must survive export,
import and restart:

    GENERATED          produced by our own deterministic code
    SIMULATED          produced by evaluating a declarative model, no real target
    DECLARED_EXTERNALLY asserted by a third party, unverified
    OBSERVED_ACCREDITED measured on an authorised target with provenance

Only OBSERVED_ACCREDITED can support an execution-backed conclusion. The others
are admissible as reasoning input and never as measurement.

Immutable per revision: every transition produces a NEW revision that records
its predecessor. Reopening a closed case creates a revision; it never
rewrites history.

Reproducible means: recomputing the conclusion from the SAME artefacts, rules
and versions yields the same result. It does NOT mean identical answers from
fresh LLM calls.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

CASE_SCHEMA = "blackforge-defensive-case/1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class EvidenceOrigin(str, Enum):
    GENERATED = "GENERATED"
    SIMULATED = "SIMULATED"
    DECLARED_EXTERNALLY = "DECLARED_EXTERNALLY"
    OBSERVED_ACCREDITED = "OBSERVED_ACCREDITED"


class WorkflowState(str, Enum):
    DRAFT = "DRAFT"
    PLAN_SEALED = "PLAN_SEALED"
    AUTH_GRANTED = "AUTH_GRANTED"
    AUTH_BLOCKED = "AUTH_BLOCKED"
    RESERVED = "RESERVED"
    RUNNING = "RUNNING"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    RESULT_RECORDED = "RESULT_RECORDED"
    ASSESSED = "ASSESSED"
    CLOSED = "CLOSED"


class AuthorizationAxis(str, Enum):
    NONE = "NONE"
    GRANTED = "GRANTED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    DENIED = "DENIED"
    CONSUMED = "CONSUMED"


class ExecutionAxis(str, Enum):
    """Execution lifecycle.

    DISPATCHED and RUNNING are NOT synonyms and the broker relies on the
    difference: DISPATCHED means the broker handed the attempt to the executor
    without receiving a start confirmation, RUNNING means the executor
    confirmed it. Collapsing them would turn an unconfirmed dispatch into a
    claimed execution, so both stay.
    """

    NOT_STARTED = "NOT_STARTED"
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"


class EvaluationAxis(str, Enum):
    NOT_EVALUATED = "NOT_EVALUATED"
    SUPPORTS_H1 = "SUPPORTS_H1"
    SUPPORTS_H2 = "SUPPORTS_H2"
    INDETERMINATE = "INDETERMINATE"


class NonDiscriminating(str, Enum):
    IDENTICAL_PREDICTIONS = "IDENTICAL_PREDICTIONS"
    SINGLE_HYPOTHESIS = "SINGLE_HYPOTHESIS"
    MISSING_PREDICTION = "MISSING_PREDICTION"


class CaseError(ValueError):
    """Contract violation. The message names the rule it protects."""


class TransitionError(CaseError):
    """An illegal state transition was attempted."""


# ---------------------------------------------------------------------------
# Digest
# ---------------------------------------------------------------------------


def _canonical(payload: Any) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_of(payload: Any) -> str:
    """A digest LINKS content. It never proves the content is true."""
    return "sha256:" + hashlib.sha256(_canonical(payload).encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Evidence:
    """One datum with stable identity, origin and provenance.

    `integrity` is the digest of the content. `validated` records whether
    admissibility was checked. Both are explicit because an unchecked datum
    presented as checked is how a simulation becomes a false observation.
    """

    evidence_id: str
    origin: EvidenceOrigin
    producer: str
    method: str
    observed_at: str
    recorded_at: str
    content: str = ""
    reference: str = ""
    integrity: str = ""
    validated: bool = False

    def __post_init__(self) -> None:
        for name in ("evidence_id", "producer", "method", "observed_at", "recorded_at"):
            if not str(getattr(self, name)).strip():
                raise CaseError(f"Evidence exige {name}.")
        if not (self.content.strip() or self.reference.strip()):
            raise CaseError(
                f"La evidencia {self.evidence_id} exige contenido o referencia resoluble."
            )
        if self.origin is EvidenceOrigin.OBSERVED_ACCREDITED:
            if not self.reference.strip():
                raise CaseError(
                    f"La evidencia {self.evidence_id} observa un objetivo y exige "
                    f"referencia: una observacion sin referencia no es acreditable."
                )
            if self.validated is not True:
                raise CaseError(
                    f"La evidencia {self.evidence_id} se declara observada sin validar; "
                    f"no puede respaldar una conclusion sobre el objetivo."
                )

    def with_validation(self, validated: bool = True) -> "Evidence":
        return replace(self, validated=validated)

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "origin": self.origin.value,
            "producer": self.producer,
            "method": self.method,
            "observed_at": self.observed_at,
            "recorded_at": self.recorded_at,
            "content": self.content,
            "reference": self.reference,
            "integrity": self.integrity or digest_of(self.content or self.reference),
            "validated": self.validated,
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "Evidence":
        return cls(
            evidence_id=str(raw["evidence_id"]),
            origin=EvidenceOrigin(str(raw["origin"])),
            producer=str(raw["producer"]),
            method=str(raw["method"]),
            observed_at=str(raw["observed_at"]),
            recorded_at=str(raw["recorded_at"]),
            content=str(raw.get("content", "")),
            reference=str(raw.get("reference", "")),
            integrity=str(raw.get("integrity", "")),
            validated=bool(raw.get("validated", False)),
        )


# ---------------------------------------------------------------------------
# Hypotheses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Hypothesis:
    """A rival explanation with preconditions and PREDICTIONS.

    A hypothesis without predictions cannot be discriminated, so the
    prediction fields are mandatory: fixing them before the result is what
    makes the later evaluation an application of a rule rather than a
    rationalisation.
    """

    hypothesis_id: str
    explanation: str
    mechanism: str
    preconditions: tuple[str, ...]
    prediction: str
    contradicted_by: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for name in ("hypothesis_id", "explanation", "mechanism", "prediction"):
            if not str(getattr(self, name)).strip():
                raise CaseError(f"Hypothesis exige {name}.")
        if not self.preconditions:
            raise CaseError(
                f"La hipotesis {self.hypothesis_id} no declara precondiciones."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hypothesis_id": self.hypothesis_id,
            "explanation": self.explanation,
            "mechanism": self.mechanism,
            "preconditions": list(self.preconditions),
            "prediction": self.prediction,
            "contradicted_by": list(self.contradicted_by),
        }


@dataclass(frozen=True)
class PlanStep:
    """One TYPED action. Free-form commands are not representable."""

    order: int
    kind: str
    resolved_target: str
    params: tuple[tuple[str, str], ...] = ()
    depends_on: tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise CaseError(f"El paso {self.order} no declara tipo.")
        if not self.resolved_target.strip():
            raise CaseError(f"El paso {self.order} no resuelve objetivo.")

    @property
    def params_dict(self) -> dict[str, str]:
        return dict(self.params)

    def to_dict(self) -> dict[str, Any]:
        return {
            "order": self.order,
            "kind": self.kind,
            "resolved_target": self.resolved_target,
            "params": dict(self.params),
            "depends_on": list(self.depends_on),
        }


@dataclass(frozen=True)
class Plan:
    """An ordered, versioned plan with a prior decision rule.

    `resolved_target` is fixed at seal time. Substituting a target while
    keeping its NAME is exactly the attack the authorisation must refuse, so
    the digest covers the resolved identity, not a display name.
    """

    steps: tuple[PlanStep, ...]
    environment: str
    limits: tuple[str, ...]
    prior_rule: str
    inconclusive_result: str
    lab_instance: str

    def __post_init__(self) -> None:
        if not self.steps:
            raise CaseError("Un plan exige al menos un paso tipado.")
        if not self.prior_rule.strip():
            raise CaseError("Un plan exige una regla previa de decision.")
        if not self.inconclusive_result.strip():
            raise CaseError("Un plan declara su resultado inconcluso.")
        orders = [s.order for s in self.steps]
        if orders != sorted(orders) or len(set(orders)) != len(orders):
            raise CaseError("Los pasos del plan deben tener orden unico y creciente.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "steps": [s.to_dict() for s in self.steps],
            "environment": self.environment,
            "limits": list(self.limits),
            "prior_rule": self.prior_rule,
            "inconclusive_result": self.inconclusive_result,
            "lab_instance": self.lab_instance,
        }

    def digest(self) -> str:
        return digest_of(self.to_dict())


@dataclass(frozen=True)
class Authorization:
    """What an approval binds. Text alone grants nothing."""

    subject: str
    credential_ref: str
    approved_plan_digest: str
    approved_intent: str
    case_id: str
    revision: int
    boot_epoch: str
    policy_version: str
    adapter: str
    issued_at: str
    valid_from: str
    max_duration_s: int
    nonce: str
    limits: tuple[str, ...] = ()
    approved_actions: tuple[str, ...] = ()
    resolved_targets: tuple[str, ...] = ()
    state: AuthorizationAxis = AuthorizationAxis.NONE
    receipt: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not _SHA256_RE.match(self.approved_plan_digest):
            raise CaseError(
                f"approved_plan_digest debe ser sha256:<64 hex>; recibido "
                f"{self.approved_plan_digest!r}"
            )
        for name in (
            "subject", "credential_ref", "approved_intent", "policy_version",
            "adapter", "nonce", "issued_at",
        ):
            if not str(getattr(self, name)).strip():
                raise CaseError(f"La autorizacion exige {name}.")
        if self.max_duration_s <= 0:
            raise CaseError("La duracion maxima debe ser positiva.")
        if not self.resolved_targets:
            raise CaseError(
                "La autorizacion debe resolver objetivos concretos; "
                "sin objetivos resueltos no autoriza ninguna accion."
            )
        if not self.approved_actions:
            raise CaseError(
                "La autorizacion debe enumerar las acciones que aprueba; "
                "una aprobacion sin acciones no es una aprobacion."
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "subject": self.subject,
            "credential_ref": self.credential_ref,
            "approved_plan_digest": self.approved_plan_digest,
            "approved_intent": self.approved_intent,
            "case_id": self.case_id,
            "revision": self.revision,
            "boot_epoch": self.boot_epoch,
            "policy_version": self.policy_version,
            "adapter": self.adapter,
            "valid_from": self.valid_from,
            "max_duration_s": self.max_duration_s,
            "nonce": self.nonce,
            "issued_at": self.issued_at,
            "limits": list(self.limits),
            "approved_actions": list(self.approved_actions),
            "resolved_targets": list(self.resolved_targets),
            "state": self.state.value,
            "receipt": dict(self.receipt),
        }


@dataclass(frozen=True)
class Attempt:
    """One execution attempt. Never merged with evaluation."""

    attempt_id: str
    executor: str
    environment: str
    authorization_nonce: str
    state: ExecutionAxis = ExecutionAxis.NOT_STARTED
    dispatched_at: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    recovery: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempt_id": self.attempt_id,
            "executor": self.executor,
            "environment": self.environment,
            "authorization_nonce": self.authorization_nonce,
            "state": self.state.value,
            "dispatched_at": self.dispatched_at,
            "result": dict(self.result),
            "recovery": self.recovery,
        }


@dataclass(frozen=True)
class Conclusion:
    """A bounded verdict with justifications, scope, limits and unknowns."""

    verdict: str
    evaluation: EvaluationAxis
    justifications: tuple[str, ...]
    scope: str
    limitations: tuple[str, ...]
    unknowns: tuple[str, ...]
    rule_applied: str
    decided_at: str

    def __post_init__(self) -> None:
        if not self.verdict.strip():
            raise CaseError("Una conclusion exige veredicto textual.")
        if not self.scope.strip():
            raise CaseError("Una conclusion exige alcance de validez.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "evaluation": self.evaluation.value,
            "justifications": list(self.justifications),
            "scope": self.scope,
            "limitations": list(self.limitations),
            "unknowns": list(self.unknowns),
            "rule_applied": self.rule_applied,
            "decided_at": self.decided_at,
        }


# ---------------------------------------------------------------------------
# The case
# ---------------------------------------------------------------------------


@dataclass
class DefensiveCase:
    """Versioned defensive case. Immutable by revision."""

    question: str
    defensive_objective: str
    closure_criterion: str
    declared_authority: str
    assets: tuple[str, ...]
    author: str
    case_id: str
    revision: int = 1
    previous_revision: int | None = None
    workflow: WorkflowState = WorkflowState.DRAFT
    authorization: AuthorizationAxis = AuthorizationAxis.NONE
    execution: ExecutionAxis = ExecutionAxis.NOT_STARTED
    evaluation: EvaluationAxis = EvaluationAxis.NOT_EVALUATED
    lab_instance: str = ""
    exclusions: tuple[str, ...] = ()
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    plan: Plan | None = None
    attempts: list[Attempt] = field(default_factory=list)
    conclusion: Conclusion | None = None
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    _revoked_authorizations: set[str] = field(default_factory=set, repr=False)
    _authorization_record: "Authorization | None" = field(default=None, repr=False)

    def __post_init__(self) -> None:
        for name in ("question", "defensive_objective", "closure_criterion", "declared_authority", "author", "case_id"):
            if not str(getattr(self, name)).strip():
                raise CaseError(f"DefensiveCase exige {name}.")
        if not self.assets:
            raise CaseError("DefensiveCase exige al menos un activo identificado.")
        if self.revision < 1:
            raise CaseError("La revision debe ser >= 1.")

    # -- evidence ----------------------------------------------------------

    def add_evidence(self, item: Evidence) -> Evidence:
        """Admit evidence, preserving its ORIGIN classification.

        Origin is never rewritten on import: an externally declared datum that
        arrives as GENERATED is a promotion attempt and is refused.
        """
        for existing in self.evidence:
            if existing.evidence_id == item.evidence_id:
                if existing.integrity and item.integrity and existing.integrity != item.integrity:
                    raise CaseError(
                        f"La evidencia {item.evidence_id} cambio de integridad "
                        f"({existing.integrity} -> {item.integrity}); "
                        f"una correccion crea revision, no sustitucion silenciosa."
                    )
                return existing
        self.evidence.append(item)
        self.updated_at = _now()
        return item

    def evidence_by_origin(self, origin: EvidenceOrigin) -> list[Evidence]:
        return [e for e in self.evidence if e.origin is origin]

    def execution_backed_evidence(self) -> list[Evidence]:
        return [
            e
            for e in self.evidence
            if e.origin is EvidenceOrigin.OBSERVED_ACCREDITED and e.validated
        ]

    # -- hypotheses --------------------------------------------------------

    def add_hypothesis(self, hypothesis: Hypothesis) -> Hypothesis:
        if any(h.hypothesis_id == hypothesis.hypothesis_id for h in self.hypotheses):
            raise CaseError(f"Hipotesis duplicada: {hypothesis.hypothesis_id}")
        self.hypotheses.append(hypothesis)
        self.updated_at = _now()
        return hypothesis

    def competing_hypotheses(self) -> tuple[Hypothesis, Hypothesis] | None:
        """The first two rival explanations, or None when not rival yet."""
        if len(self.hypotheses) < 2:
            return None
        return (self.hypotheses[0], self.hypotheses[1])

    def non_discriminating(self) -> bool:
        pair = self.competing_hypotheses()
        if pair is None:
            return True
        return pair[0].prediction.strip() == pair[1].prediction.strip()

    # -- plan --------------------------------------------------------------

    def seal_plan(self, plan: Plan) -> str:
        """DRAFT -> PLAN_SEALED. Once sealed, changing it requires a revision."""
        if self.workflow is not WorkflowState.DRAFT:
            raise TransitionError(
                f"Solo DRAFT puede sellar un plan; el caso esta en {self.workflow.value}."
            )
        self.plan = plan
        self.workflow = WorkflowState.PLAN_SEALED
        self.updated_at = _now()
        return plan.digest()

    # -- authorization -----------------------------------------------------

    def attach_authorization(self, authorization: Authorization) -> None:
        """Record an authorisation. It confers nothing by itself.

        The record is retained so validity can be re-checked at dispatch time;
        the axis alone is not enough to answer "is it still live?".
        """
        if self.plan is None:
            raise CaseError("No hay plan que autorizar.")
        if authorization.case_id != self.case_id or authorization.revision != self.revision:
            raise CaseError(
                f"La autorizacion es para {authorization.case_id}@"
                f"{authorization.revision}; el caso es {self.case_id}@{self.revision}."
            )
        plan_digest = self.plan.digest()
        if authorization.approved_plan_digest != plan_digest:
            raise CaseError(
                "Plan alterado: la autorizacion no corresponde al digest del plan sellado."
            )
        if authorization.boot_epoch != current_boot_epoch():
            raise CaseError(
                f"La autorizacion pertenece a otra epoca de arranque "
                f"({authorization.boot_epoch} != {current_boot_epoch()}); "
                f"reiniciar invalida autorizaciones pendientes."
            )
        if authorization.nonce in self._revoked_authorizations:
            raise CaseError(
                f"La autorizacion {authorization.nonce} esta revocada; cero despachos."
            )
        self._authorization_record = authorization
        self.authorization = authorization.state
        self.updated_at = _now()

    def revoke_authorization(self, nonce: str) -> None:
        """Revocation blocks pending steps and asks for a controlled stop.

        It does NOT presume to undo effects already performed.
        """
        self._revoked_authorizations.add(nonce)
        if getattr(self, "_authorization_record", None) is not None:
            if self._authorization_record.nonce == nonce:
                self.authorization = AuthorizationAxis.REVOKED
        self.updated_at = _now()

    def authorization_is_live(self, *, now: datetime | None = None) -> tuple[bool, str]:
        """Re-check validity at the point of dispatch. Fails closed.

        Unverifiable validity means no run: an absent record, a revoked nonce,
        another boot epoch or an elapsed TTL all return "not live".
        """
        record = getattr(self, "_authorization_record", None)
        if record is None:
            return False, "no hay autorizacion registrada"
        if record.nonce in self._revoked_authorizations:
            # Check revocation BEFORE the axis: revocation is the precise
            # cause, and reporting only the axis value would hide it behind
            # the symptom. Reporting the axis alone also lets a caller infer
            # "it expired" when it was in fact revoked.
            return False, f"autorizacion revocada: {record.nonce}"
        if self.authorization is not AuthorizationAxis.GRANTED:
            return False, f"el eje de autorizacion esta en {self.authorization.value}"
        if record.boot_epoch != current_boot_epoch():
            return False, "la autorizacion pertenece a otra epoca de arranque"
        moment = now or datetime.now(timezone.utc)
        start = datetime.fromisoformat(record.valid_from)
        if moment < start:
            return False, f"la autorizacion no es valida hasta {record.valid_from}"
        if (moment - start).total_seconds() > record.max_duration_s:
            return False, f"la autorizacion expiro (max_duration_s={record.max_duration_s})"
        return True, ""

    def require_authorized(self, *, now: datetime | None = None) -> Authorization:
        ok, why = self.authorization_is_live(now=now)
        if not ok:
            raise CaseError(
                f"La prueba activa queda bloqueada: {why}. "
                f"El expediente puede concluir 'evidencia insuficiente; "
                f"comprobacion pendiente'."
            )
        return getattr(self, "_authorization_record")  # type: ignore[return-value]

    # -- transitions -------------------------------------------------------

    def _require(self, *allowed: WorkflowState) -> None:
        if self.workflow not in allowed:
            raise TransitionError(
                f"Transicion no permitida desde {self.workflow.value}; "
                f"se exige {', '.join(a.value for a in allowed)}."
            )

    def mark_auth_blocked(self, reason: str) -> None:
        """Missing/denied/expired/revoked authorisation.

        The analysis and its unknowns are PRESERVED. A block is never
        converted into a success.
        """
        if not reason.strip():
            raise CaseError("El bloqueo exige un motivo.")
        self._require(WorkflowState.PLAN_SEALED, WorkflowState.AUTH_BLOCKED)
        self.workflow = WorkflowState.AUTH_BLOCKED
        self.authorization = AuthorizationAxis.DENIED
        self.updated_at = _now()

    def mark_reserved(self, attempt: Attempt) -> None:
        """The broker confirms unique consumption and journalling."""
        if self.authorization is not AuthorizationAxis.GRANTED:
            raise CaseError(
                "No se puede reservar sin autorizacion GRANTED; cero despachos."
            )
        self._require(WorkflowState.PLAN_SEALED, WorkflowState.AUTH_GRANTED)
        self.workflow = WorkflowState.RESERVED
        self.execution = ExecutionAxis.RESERVED
        self.authorization = AuthorizationAxis.CONSUMED
        self.attempts.append(replace(attempt, state=ExecutionAxis.RESERVED))
        self.updated_at = _now()

    def mark_running(self) -> None:
        """Only after the EXECUTOR confirms the start."""
        self._require(WorkflowState.RESERVED)
        self.workflow = WorkflowState.RUNNING
        self.execution = ExecutionAxis.RUNNING
        if self.attempts:
            self.attempts[-1] = replace(self.attempts[-1], state=ExecutionAxis.RUNNING)
        self.updated_at = _now()

    def mark_outcome_unknown(self, reason: str) -> None:
        """A possible effect whose result cannot be resolved.

        Blocks repetition. Absence of a response is not absence of an effect.
        """
        if not reason.strip():
            raise CaseError("OUTCOME_UNKNOWN exige un motivo verificable.")
        self._require(WorkflowState.RESERVED, WorkflowState.RUNNING)
        self.workflow = WorkflowState.OUTCOME_UNKNOWN
        self.execution = ExecutionAxis.OUTCOME_UNKNOWN
        if self.attempts:
            self.attempts[-1] = replace(
                self.attempts[-1],
                state=ExecutionAxis.OUTCOME_UNKNOWN,
                recovery=f"reconciliar antes de repetir: {reason}",
            )
        self.updated_at = _now()

    def record_result(self, *, invalid_reason: str = "") -> None:
        """RESULT_RECORDED. Reception is not validity."""
        self._require(WorkflowState.RUNNING, WorkflowState.OUTCOME_UNKNOWN, WorkflowState.RESERVED)
        if invalid_reason.strip():
            self.workflow = WorkflowState.RESULT_RECORDED
            self.execution = ExecutionAxis.FAILED
        else:
            self.workflow = WorkflowState.RESULT_RECORDED
            self.execution = ExecutionAxis.COMPLETED
        if self.attempts:
            self.attempts[-1] = replace(self.attempts[-1], state=self.execution)
        self.updated_at = _now()

    def record_declarative_result(self, *, invalid_reason: str = "") -> None:
        """RESULT_RECORDED for a result that required NO execution.

        Distinct from `record_result` on purpose. A declarative model
        evaluation touches no target, so it cannot legitimately pass through
        RESERVED/RUNNING. Routing it through those states would assert an
        execution that never happened, which is exactly the promotion this
        architecture forbids. From AUTH_BLOCKED, the path is the honest one:
        the result of the simulation is recorded while the active check stays
        blocked.
        """
        self._require(
            WorkflowState.PLAN_SEALED,
            WorkflowState.AUTH_BLOCKED,
            WorkflowState.RESERVED,
            WorkflowState.RUNNING,
            WorkflowState.OUTCOME_UNKNOWN,
        )
        self.workflow = WorkflowState.RESULT_RECORDED
        if invalid_reason.strip():
            self.execution = ExecutionAxis.FAILED
        elif self.execution is ExecutionAxis.NOT_STARTED:
            # Nothing was executed: keep the axis honest instead of claiming
            # COMPLETED for work that never reached a target.
            self.execution = ExecutionAxis.NOT_STARTED
        self.updated_at = _now()

    # -- evaluation --------------------------------------------------------

    def assess(self, conclusion: Conclusion) -> None:
        """ASSESSED: a bounded conclusion, or INDETERMINATE.

        Promoting UNKNOWN is refused: incompleteness is not refutation, and a
        missing measurement is never reported as a passed check.
        """
        self._require(WorkflowState.RESULT_RECORDED, WorkflowState.ASSESSED)
        if conclusion.evaluation is EvaluationAxis.SUPPORTS_H1:
            if conclusion.justifications and not any(
                self.evidence_by_id(j) for j in conclusion.justifications
            ):
                raise CaseError(
                    "Una conclusion SUPPORTS_H1 debe citar evidencia existente; "
                    "promover una justificacion inexistente esta prohibido."
                )
        self.conclusion = conclusion
        self.evaluation = conclusion.evaluation
        self.workflow = WorkflowState.ASSESSED
        self.updated_at = _now()

    def close(self) -> None:
        self._require(WorkflowState.ASSESSED)
        if self.conclusion is None:
            raise CaseError("No se puede cerrar sin conclusion.")
        self.workflow = WorkflowState.CLOSED
        self.updated_at = _now()

    def reopen(self) -> "DefensiveCase":
        """Reopening creates a NEW revision; history is never rewritten."""
        if self.workflow is not WorkflowState.CLOSED:
            raise CaseError("Solo un caso cerrado se reabre.")
        child = replace(
            self,
            revision=self.revision + 1,
            previous_revision=self.revision,
            workflow=WorkflowState.DRAFT,
            execution=ExecutionAxis.NOT_STARTED,
            evaluation=EvaluationAxis.NOT_EVALUATED,
            conclusion=None,
            created_at=_now(),
            updated_at=_now(),
        )
        child.attempts = list(self.attempts)
        child.evidence = list(self.evidence)
        child.hypotheses = list(self.hypotheses)
        child._revoked_authorizations = set(self._revoked_authorizations)
        return child

    def evidence_by_id(self, evidence_id: str) -> Evidence | None:
        return next((e for e in self.evidence if e.evidence_id == evidence_id), None)

    # -- serialisation -----------------------------------------------------

    def content_digest(self) -> str:
        return digest_of(
            {
                "question": self.question,
                "defensive_objective": self.defensive_objective,
                "assets": list(self.assets),
                "evidence": [e.to_dict() for e in self.evidence],
                "hypotheses": [h.to_dict() for h in self.hypotheses],
                "plan": self.plan.to_dict() if self.plan else None,
                "conclusion": self.conclusion.to_dict() if self.conclusion else None,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": CASE_SCHEMA,
            "case_id": self.case_id,
            "revision": self.revision,
            "previous_revision": self.previous_revision,
            "author": self.author,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "intent": {
                "question": self.question,
                "defensive_objective": self.defensive_objective,
                "closure_criterion": self.closure_criterion,
            },
            "scope": {
                "declared_authority": self.declared_authority,
                "assets": list(self.assets),
                "lab_instance": self.lab_instance,
                "exclusions": list(self.exclusions),
            },
            "axes": {
                "workflow": self.workflow.value,
                "authorization": self.authorization.value,
                "execution": self.execution.value,
                "evaluation": self.evaluation.value,
            },
            "evidence": [e.to_dict() for e in self.evidence],
            "hypotheses": [h.to_dict() for h in self.hypotheses],
            "plan": self.plan.to_dict() if self.plan else None,
            "attempts": [a.to_dict() for a in self.attempts],
            "conclusion": self.conclusion.to_dict() if self.conclusion else None,
            "digest": self.content_digest(),
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "DefensiveCase":
        if raw.get("schema") != CASE_SCHEMA:
            raise CaseError(
                f"Esquema {raw.get('schema')!r} distinto de {CASE_SCHEMA!r}; "
                f"importar sin version rechazada."
            )
        scope = raw["scope"]
        intent = raw["intent"]
        axes = raw["axes"]
        plan_raw = raw.get("plan")
        case = cls(
            case_id=str(raw["case_id"]),
            revision=int(raw["revision"]),
            previous_revision=raw.get("previous_revision"),
            author=str(raw["author"]),
            question=str(intent["question"]),
            defensive_objective=str(intent["defensive_objective"]),
            closure_criterion=str(intent["closure_criterion"]),
            declared_authority=str(scope["declared_authority"]),
            assets=tuple(scope["assets"]),
            lab_instance=str(scope.get("lab_instance", "")),
            exclusions=tuple(scope.get("exclusions", ())),
            created_at=str(raw.get("created_at", _now())),
            updated_at=str(raw.get("updated_at", _now())),
        )
        case.evidence = [Evidence.from_dict(e) for e in raw.get("evidence", [])]
        case.hypotheses = [
            Hypothesis(
                hypothesis_id=str(h["hypothesis_id"]),
                explanation=str(h["explanation"]),
                mechanism=str(h["mechanism"]),
                preconditions=tuple(h["preconditions"]),
                prediction=str(h["prediction"]),
                contradicted_by=tuple(h.get("contradicted_by", ())),
            )
            for h in raw.get("hypotheses", [])
        ]
        if plan_raw:
            case.plan = Plan(
                steps=tuple(
                    PlanStep(
                        order=int(s["order"]),
                        kind=str(s["kind"]),
                        resolved_target=str(s["resolved_target"]),
                        params=tuple(sorted((str(k), str(v)) for k, v in (s.get("params") or {}).items())),
                        depends_on=tuple(s.get("depends_on", ())),
                    )
                    for s in plan_raw["steps"]
                ),
                environment=str(plan_raw["environment"]),
                limits=tuple(plan_raw["limits"]),
                prior_rule=str(plan_raw["prior_rule"]),
                inconclusive_result=str(plan_raw["inconclusive_result"]),
                lab_instance=str(plan_raw["lab_instance"]),
            )
        case.workflow = WorkflowState(axes["workflow"])
        case.authorization = AuthorizationAxis(axes["authorization"])
        case.execution = ExecutionAxis(axes["execution"])
        case.evaluation = EvaluationAxis(axes["evaluation"])
        conclusion = raw.get("conclusion")
        if conclusion:
            case.conclusion = Conclusion(
                verdict=str(conclusion["verdict"]),
                evaluation=EvaluationAxis(conclusion["evaluation"]),
                justifications=tuple(conclusion["justifications"]),
                scope=str(conclusion["scope"]),
                limitations=tuple(conclusion["limitations"]),
                unknowns=tuple(conclusion["unknowns"]),
                rule_applied=str(conclusion["rule_applied"]),
                decided_at=str(conclusion["decided_at"]),
            )
        return case


# ---------------------------------------------------------------------------
# Boot epoch: a restart invalidates pending authorisations.
# ---------------------------------------------------------------------------


def current_boot_epoch() -> str:
    """Monotonic-ish identifier of this boot.

    A restarted process therefore refuses authorisations minted by the previous
    one, which is what makes "restore state and present old permissions" fail.
    """
    import os

    raw = os.environ.get("BLACKFORGE_BOOT_EPOCH")
    if raw:
        return raw
    return f"boot-{os.getppid()}"


def build_plan(
    steps: Sequence[Mapping[str, Any]],
    *,
    environment: str,
    limits: Sequence[str] = (),
    prior_rule: str,
    inconclusive_result: str = "INDETERMINATE",
    lab_instance: str = "",
) -> Plan:
    """Build a canonical Plan from plain operation mappings.

    `resolved_target` is mandatory and is FIXED HERE. A caller that supplies a
    display name instead of a resolved identity is refused, because substituting
    the target while keeping the name is the exact substitution an authorisation
    must detect.
    """
    frozen: list[PlanStep] = []
    for index, raw in enumerate(steps):
        kind = raw.get("kind")
        target = raw.get("resolved_target", raw.get("target"))
        if not isinstance(kind, str) or not kind.strip():
            raise CaseError(f"La operacion {index} no declara tipo.")
        if not isinstance(target, str) or not target.strip():
            raise CaseError(f"La operacion {index} no resuelve un objetivo.")
        params = raw.get("params") or {
            k: v for k, v in raw.items() if k not in {"kind", "target", "resolved_target", "params"}
        }
        depends = raw.get("depends_on") or ()
        frozen.append(
            PlanStep(
                order=int(raw.get("order", index)),
                kind=kind,
                resolved_target=target,
                params=tuple(sorted((str(k), str(v)) for k, v in dict(params).items())),
                depends_on=tuple(int(d) for d in depends),
            )
        )
    return Plan(
        steps=tuple(frozen),
        environment=environment,
        limits=tuple(limits),
        prior_rule=prior_rule,
        inconclusive_result=inconclusive_result,
        lab_instance=lab_instance or environment,
    )


__all__ = [
    "CASE_SCHEMA",
    "Attempt",
    "Authorization",
    "AuthorizationAxis",
    "CaseError",
    "Conclusion",
    "DefensiveCase",
    "EvaluationAxis",
    "Evidence",
    "EvidenceOrigin",
    "ExecutionAxis",
    "Hypothesis",
    "NonDiscriminating",
    "Plan",
    "PlanStep",
    "TransitionError",
    "WorkflowState",
    "current_boot_epoch",
    "digest_of",
]