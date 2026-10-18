"""First vertical slice: explain a permission from an exported configuration.

This is the slice the v1 contract names, executed end to end with real
computation and no LLM call:

  exported snapshot  ->  rival hypotheses  ->  discriminating rule
                    ->  deterministic evaluation of a declarative model
                    ->  bounded conclusion, or INDETERMINATE

What this slice deliberately does NOT do:

* It never queries or modifies a real system. The only thing it computes is
  the declarative model contained in the snapshot.
* It never runs code supplied inside the snapshot. The model is interpreted
  from a fixed, closed vocabulary; unknown verbs are refused.
* It never claims correspondence with production. The conclusion always says
  so, because a snapshot is a claim about a snapshot.

Reproducibility means: same snapshot, same rule, same versions -> same
conclusion. It does not mean identical answers from fresh model calls, and no
model is consulted anywhere in this module.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

from .blackforge_case import (
    AuthorizationAxis,
    CaseError,
    Conclusion,
    DefensiveCase,
    EvaluationAxis,
    Evidence,
    EvidenceOrigin,
    ExecutionAxis,
    Hypothesis,
    Plan,
    PlanStep,
    WorkflowState,
    digest_of,
)

SNAPSHOT_SCHEMA = "bf-authz-snapshot/1"

# Closed vocabulary. A verb outside this set is refused rather than guessed.
SUPPORTED_VERBS = frozenset(
    {"grants", "denies", "inherits", "revokes", "requires_role"}
)


class SnapshotError(ValueError):
    """The snapshot cannot be interpreted. Refused, not guessed."""


@dataclass(frozen=True)
class GrantEdge:
    subject: str
    object_key: str
    verb: str
    via: str = ""


@dataclass(frozen=True)
class AuthzSnapshot:
    """A self-contained export of subjects, roles and rules."""

    users: tuple[str, ...]
    roles: tuple[str, ...]
    edges: tuple[GrantEdge, ...]
    declared_authority: str
    completeness: str
    source: str
    snapshot_id: str

    def __post_init__(self) -> None:
        if not self.users:
            raise SnapshotError("El snapshot exige al menos un usuario.")
        if not self.roles:
            raise SnapshotError("El snapshot exige al menos un rol.")
        for edge in self.edges:
            if edge.verb not in SUPPORTED_VERBS:
                raise SnapshotError(
                    f"Verbo {edge.verb!r} fuera del vocabulario soportado "
                    f"{sorted(SUPPORTED_VERBS)}; no se ejecuta codigo del snapshot."
                )
        if self.completeness not in {"COMPLETE", "PARTIAL", "DECLARED_INCOMPLETE"}:
            raise SnapshotError(f"Completitud desconocida: {self.completeness!r}")
        if not self.declared_authority.strip():
            raise SnapshotError("El snapshot exige autoridad declarada.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": SNAPSHOT_SCHEMA,
            "snapshot_id": self.snapshot_id,
            "declared_authority": self.declared_authority,
            "completeness": self.completeness,
            "source": self.source,
            "users": list(self.users),
            "roles": list(self.roles),
            "edges": [
                {
                    "subject": e.subject,
                    "object": e.object_key,
                    "verb": e.verb,
                    **({"via": e.via} if e.via else {}),
                }
                for e in self.edges
            ],
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "AuthzSnapshot":
        if raw.get("schema") != SNAPSHOT_SCHEMA:
            raise SnapshotError(
                f"Esquema {raw.get('schema')!r} distinto de {SNAPSHOT_SCHEMA!r}."
            )
        return cls(
            users=tuple(str(u) for u in raw.get("users", ())),
            roles=tuple(str(r) for r in raw.get("roles", ())),
            edges=tuple(
                GrantEdge(
                    subject=str(e["subject"]),
                    object_key=str(e["object"]),
                    verb=str(e["verb"]),
                    via=str(e.get("via", "")),
                )
                for e in raw.get("edges", ())
            ),
            declared_authority=str(raw.get("declared_authority", "")),
            completeness=str(raw.get("completeness", "")),
            source=str(raw.get("source", "")),
            snapshot_id=str(raw.get("snapshot_id", "")),
        )

    def digest(self) -> str:
        return digest_of(self.to_dict())


# ---------------------------------------------------------------------------
# Declarative model evaluation. No target is touched.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelEvaluation:
    """What the declarative model says, plus what it cannot say."""

    user: str
    permission: str
    effective_grants: tuple[tuple[str, str], ...]  # (source_kind, detail)
    resolution_path: tuple[str, ...]
    blockers: tuple[str, ...]
    computed: bool
    verdict_class: str  # DIRECT | INHERITED | ABSENT | INDETERMINATE

    def to_dict(self) -> dict[str, Any]:
        return {
            "user": self.user,
            "permission": self.permission,
            "effective_grants": [
                {"source_kind": kind, "detail": detail} for kind, detail in self.effective_grants
            ],
            "resolution_path": list(self.resolution_path),
            "blockers": list(self.blockers),
            "computed": self.computed,
            "verdict_class": self.verdict_class,
            "model_is_declarative": True,
            "real_system_queried": False,
        }


def _inherited_role(snapshot: AuthzSnapshot, user: str) -> tuple[str, ...]:
    out: list[str] = []
    for edge in snapshot.edges:
        if edge.subject == user and edge.verb in {"inherits", "grants"} and edge.object_key in snapshot.roles:
            if edge.object_key not in out:
                out.append(edge.object_key)
    return tuple(out)


def evaluate_declarative_model(
    snapshot: AuthzSnapshot, user: str, permission: str
) -> ModelEvaluation:
    """Resolve one permission against the declarative model only.

    Returns INDETERMINATE whenever the snapshot cannot support a decision,
    rather than inferring a grant from missing data.
    """
    if user not in snapshot.users:
        return ModelEvaluation(
            user, permission, (), (), (f"usuario {user} ausente del snapshot",),
            computed=False, verdict_class="INDETERMINATE",
        )
    direct = [
        e for e in snapshot.edges
        if e.subject == user and e.object_key == permission and e.verb == "grants"
    ]
    denying = [
        e for e in snapshot.edges
        if e.subject == user and e.object_key == permission and e.verb == "denies"
    ]
    if denying:
        return ModelEvaluation(
            user, permission,
            (("DENY_DIRECT", "regla de denegacion explicita"),),
            (f"{user} -{denying[0].verb}-> {permission}",),
            (), computed=True, verdict_class="ABSENT",
        )
    if direct:
        return ModelEvaluation(
            user, permission,
            (("GRANT_DIRECT", f"sujeto={direct[0].subject}"),),
            (f"{user} -{direct[0].verb}-> {permission}",),
            (), computed=True, verdict_class="DIRECT",
        )

    # No direct rule: look for inheritance to a role that carries it.
    path: list[str] = []
    for role in _inherited_role(snapshot, user):
        via_role = [
            e for e in snapshot.edges
            if e.subject == role and e.object_key == permission
        ]
        path.append(f"{user} -{ 'inherits' }-> {role}")
        if via_role:
            return ModelEvaluation(
                user, permission,
                (("GRANT_INHERITED", f"rol={role} regla={via_role[0].verb}"),),
                (*path, f"{role} -{via_role[0].verb}-> {permission}"),
                (), computed=True, verdict_class="INHERITED",
            )

    if snapshot.completeness != "COMPLETE":
        return ModelEvaluation(
            user, permission, (), tuple(path),
            (
                f"el snapshot declara completitud {snapshot.completeness}; "
                f"una ausencia no equivale a denegacion",
            ),
            computed=False, verdict_class="INDETERMINATE",
        )
    return ModelEvaluation(
        user, permission, (), tuple(path), (),
        computed=True, verdict_class="ABSENT",
    )


# ---------------------------------------------------------------------------
# The slice
# ---------------------------------------------------------------------------


@dataclass
class SliceOutcome:
    case: DefensiveCase
    evaluation: ModelEvaluation
    simulated_evidence_id: str = ""


def build_permission_case(
    snapshot: AuthzSnapshot,
    *,
    user: str,
    permission: str,
    author: str,
    case_id: str,
) -> DefensiveCase:
    """Declare intent, scope, provenance and the two rival explanations."""
    if not user.strip() or not permission.strip():
        raise CaseError("La comprobacion exige usuario y permiso concretos.")
    case = DefensiveCase(
        case_id=case_id,
        author=author,
        question=(
            f"¿El usuario {user} obtiene {permission} de forma directa o por herencia?"
        ),
        defensive_objective=(
            "Explicar el origen del permiso a partir del modelo declarativo exportado."
        ),
        closure_criterion=(
            "Determinar si la concesion es DIRECTA o HEREDADA, o declarar "
            "INDETERMINATE con su causa."
        ),
        declared_authority=snapshot.declared_authority,
        assets=(f"snapshot:{snapshot.snapshot_id}",),
        lab_instance="modelo-declarativo-sin-sistema-real",
        exclusions=("ninguna consulta al sistema real", "ninguna modificacion del sistema"),
    )
    case.add_evidence(
        Evidence(
            evidence_id=f"EV-{snapshot.snapshot_id}-SNAPSHOT",
            origin=EvidenceOrigin.DECLARED_EXTERNALLY,
            producer=snapshot.source,
            method="exportacion-de-configuracion",
            observed_at=snapshot.snapshot_id and "2026-10-05T00:00:00+00:00",
            recorded_at="2026-10-05T00:00:00+00:00",
            content=json.dumps(snapshot.to_dict(), ensure_ascii=False, sort_keys=True),
            reference=f"snapshot://{snapshot.snapshot_id}",
            integrity=snapshot.digest(),
            validated=True,
        )
    )
    case.add_hypothesis(
        Hypothesis(
            hypothesis_id="H-DIRECT",
            explanation=f"{permission} se concede directamente a {user}",
            mechanism="existe una regla cuyo sujeto es el usuario y cuyo objeto es el permiso",
            preconditions=("regla directa presente en el snapshot",),
            prediction="el modelo resuelve con veredicto DIRECT sin traversing de roles",
        )
    )
    case.add_hypothesis(
        Hypothesis(
            hypothesis_id="H-INHERITED",
            explanation=f"{permission} llega a {user} por herencia de un rol",
            mechanism="el usuario hereda un rol y ese rol lleva la regla del permiso",
            preconditions=("relacion de herencia presente", "regla en el rol"),
            prediction="el modelo resuelve con veredicto INHERITED y una ruta de herencia",
        )
    )
    # Seal the declarative plan. The state machine refuses to skip this: the
    # prior decision rule and the absence of an active-probe branch must be
    # part of the plan before anything is computed, so the rule applied to the
    # result is always the rule that was sealed first.
    case.seal_plan(
        Plan(
            steps=(
                PlanStep(
                    order=0,
                    kind="evaluate_declarative_authz_model",
                    resolved_target=f"snapshot://{snapshot.snapshot_id}",
                    params=(("user", user), ("permission", permission)),
                ),
            ),
            environment="modelo-declarativo-sin-sistema-real",
            limits=(
                "no consultar el sistema real",
                "no ejecutar codigo del snapshot",
                "no ejecutar contra objetivos: v1 no tiene rama de sonda activa",
            ),
            prior_rule=(
                "DIRECT -> H-DIRECT; INHERITED -> H-INHERITED; "
                "ABSENT o snapshot incompleto -> INDETERMINATE con su causa"
            ),
            inconclusive_result="INDETERMINATE",
            lab_instance="modelo-declarativo-sin-sistema-real",
        )
    )
    return case


def run_permission_slice(
    snapshot: AuthzSnapshot,
    *,
    user: str,
    permission: str,
    author: str,
    case_id: str,
    lab_authorized: bool = False,
) -> SliceOutcome:
    """Execute the slice: real computation on the declarative model only.

    `lab_authorized` is deliberately NOT a switch that unlocks anything here.
    This slice has no active-probe branch at all: it computes the model and
    records a SIMULATED evidence item. Adding an active branch later must go
    through the broker, never through a flag in this signature.
    """
    case = build_permission_case(
        snapshot, user=user, permission=permission, author=author, case_id=case_id
    )
    evaluation = evaluate_declarative_model(snapshot, user, permission)
    simulated_id = f"EV-{case.case_id}-MODEL"
    case.add_evidence(
        Evidence(
            evidence_id=simulated_id,
            origin=EvidenceOrigin.SIMULATED,
            producer="blackforge_case.evaluate_declarative_model",
            method="interpretacion-del-modelo-declarativo",
            observed_at="2026-10-05T00:00:00+00:00",
            recorded_at="2026-10-05T00:00:00+00:00",
            content=json.dumps(evaluation.to_dict(), ensure_ascii=False, sort_keys=True),
            reference="model://declarative/eval",
            validated=True,
        )
    )

    # No authorised lab branch exists in v1, so the active check is blocked
    # while the declarative simulation stands on its own.
    case.mark_auth_blocked(
        "v1 no ejecuta contra objetivos; solo simulacion declarativa"
    )

    pair = case.competing_hypotheses()
    assert pair is not None  # built above
    if case.non_discriminating():
        verdict = "INDETERMINATE"
        evaluation_axis = EvaluationAxis.INDETERMINATE
        justification = [simulated_id]
        unknowns = ["las hipotesis predicen lo mismo; no hay regla discriminante"]
    else:
        verdict = _verdict_text(evaluation, user, permission)
        evaluation_axis = _verdict_axis(evaluation)
        justification = [simulated_id, f"EV-{snapshot.snapshot_id}-SNAPSHOT"]
        unknowns = list(evaluation.blockers)

    conclusion = Conclusion(
        verdict=verdict,
        evaluation=evaluation_axis,
        justifications=tuple(justification),
        scope=(
            f"segun el snapshot {snapshot.snapshot_id} "
            f"(completitud declarada: {snapshot.completeness}); "
            f"correspondencia con produccion NO verificada"
        ),
        limitations=(
            "el modelo es declarativo: no se ejecuto codigo ni se consulto el sistema real",
            "una conclusion sobre el snapshot no es una certificacion de seguridad",
        ),
        unknowns=tuple(unknowns),
        rule_applied=(
            "si el modelo resuelve DIRECT -> H-DIRECT; si resuelve INHERITED -> "
            "H-INHERITED; si el snapshot es incompleto o bloquea -> INDETERMINATE"
        ),
        decided_at="2026-10-05T00:00:00+00:00",
    )
    case.record_declarative_result()
    case.assess(conclusion)
    case.close()
    return SliceOutcome(case=case, evaluation=evaluation, simulated_evidence_id=simulated_id)


def _verdict_text(evaluation: ModelEvaluation, user: str, permission: str) -> str:
    if evaluation.verdict_class == "DIRECT":
        return f"Segun este snapshot, {permission} se concede directamente a {user}."
    if evaluation.verdict_class == "INHERITED":
        return (
            f"Segun este snapshot, {permission} depende de la herencia "
            f"(ruta: {' -> '.join(evaluation.resolution_path)})."
        )
    if evaluation.verdict_class == "ABSENT":
        return f"Segun este snapshot, {user} no obtiene {permission}."
    return (
        f"INDETERMINATE: {evaluation.blockers[0] if evaluation.blockers else 'sin causa declarada'}"
    )


def _verdict_axis(evaluation: ModelEvaluation) -> EvaluationAxis:
    if evaluation.verdict_class == "DIRECT":
        return EvaluationAxis.SUPPORTS_H1
    if evaluation.verdict_class == "INHERITED":
        return EvaluationAxis.SUPPORTS_H2
    if evaluation.verdict_class == "ABSENT":
        return EvaluationAxis.INDETERMINATE
    return EvaluationAxis.INDETERMINATE


__all__ = [
    "AuthzSnapshot",
    "GrantEdge",
    "ModelEvaluation",
    "SNAPSHOT_SCHEMA",
    "SUPPORTED_VERBS",
    "SliceOutcome",
    "SnapshotError",
    "build_permission_case",
    "evaluate_declarative_model",
    "run_permission_slice",
]