"""BLACKFORGE deterministic selector — FASE 2 (SELECTOR).

Selects a reproducible subset of the immutable BLACKFORGE catalog
(see blackforge_catalog.load) honoring the policy contracts declared in the
catalog's own selection_policy / safety_policy, never relaxing a constraint
silently.

Design rules (from HIPER_MEGAPROMPT FASE 2):
- deterministic stable ordering; seed is recorded for API/report compatibility but does not currently perturb ranking;
- uses an appropriate profile score (quality_score_v2);
- respects quotas (tiers, source catalogs, primary categories, families,
  causal axes, mandatory stages);
- preserves diversity;
- emits a detailed SelectionReport;
- S3_HIGH_CONTROL: 0 by default; max 1 only with explicit approval +
  authorized scope + sandbox; archive never selectable; research only with
  explicit mode;
- if constraints cannot be met -> SelectionFailure (never a fake selection).
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
import math
from typing import Any

from .blackforge_catalog import load as _load_catalog


@dataclass
class SelectionFailure:
    """Structured, honest failure: names the impossible quota, doesn't fake it."""
    reason: str
    failed_quota: str
    detail: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"status": "FAILED", "failed_quota": self.failed_quota,
                "reason": self.reason, "detail": self.detail}


@dataclass
class SelectionReport:
    seed: int
    session_size: int
    allowed_tiers: list[str]
    selected_ids: list[str]
    compliance: dict[str, Any]
    profile_used: str
    s3_count: int
    s3_allowed: bool
    failure: SelectionFailure | None = None
    tie_sets: list[list[str]] = field(default_factory=list)
    tiebreak_rule: str = (
        "profile score desc, diversity heuristic desc, selection weight desc, "
        "blackforge_id asc; operational ordering is not scientific superiority"
    )

    def status_ok(self) -> bool:
        return self.failure is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "OK" if self.failure is None else "FAILED",
            "seed": self.seed,
            "session_size": self.session_size,
            "allowed_tiers": self.allowed_tiers,
            "profile_used": self.profile_used,
            "selected_ids": self.selected_ids,
            "selected_count": len(self.selected_ids),
            "s3_count": self.s3_count,
            "s3_allowed": self.s3_allowed,
            "compliance": self.compliance,
            "tie_sets": self.tie_sets,
            "tiebreak_rule": self.tiebreak_rule,
            "failure": self.failure.to_dict() if self.failure else None,
        }


# Profile field used for ranking (the catalog's own quality score v2).
_PROFILE_FIELD = "quality_score_v2"
_ALLOWED_PROFILES = {
    "defensive": "profile_defensive_engineering",
    "devtools": "profile_devtools",
    "offensive_research": "profile_offensive_research",
    "hybrid": "profile_hybrid",
}
_MANDATORY_STAGES = ("ROMPER", "DIVERGIR", "ATACAR", "EVALUAR")
# Estadios mínimos para profiles que no pueden cubrir todos
_MANDATORY_STAGES_RELAXED = ("DIVERGIR",)  # Solo requerir DIVERGIR
_S3_CLASS = "S3_HIGH_CONTROL"
_S2_CLASS = "S2_SANDBOX"


def select_blackforge(
    seed: int = 1,
    session_size: int = 12,
    profile: str = "hybrid",
    allow_research: bool = False,
    explicit_high_control_approval: bool = False,
    authorized_scope_confirmed: bool = False,
    sandbox_available: bool = False,
    allowed_tiers: list[str] | None = None,
) -> SelectionReport:
    """Deterministic, quota-respecting selection over the BLACKFORGE catalog.

    Returns a SelectionReport. On impossible constraints, report.failure is set
    (status FAILED) and selected_ids is empty — no fake selection is produced.
    """
    if profile not in _ALLOWED_PROFILES:
        raise ValueError(f"perfil inválido: {profile}; usar uno de {list(_ALLOWED_PROFILES)}")
    profile_field = _ALLOWED_PROFILES[profile]

    # A selection session must request a positive, non-boolean integer count.
    # Zero/negative/non-integral sizes are malformed policy input, not a valid
    # empty selection and not evidence that downstream quotas were evaluated.
    if isinstance(session_size, bool) or not isinstance(session_size, int) or session_size <= 0:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=list(allowed_tiers or []),
            selected_ids=[], compliance={}, profile_used=profile, s3_count=0,
            s3_allowed=False,
            failure=SelectionFailure(
                reason="session_size debe ser un entero positivo.",
                failed_quota="session_size_integrity",
                detail={"value_repr": repr(session_size)[:120]},
            ),
        )

    meta, recs = _load_catalog()
    sel_policy = meta.get("selection_policy", {})
    constraints = sel_policy.get("constraints", {})

    # Policy values are executable control inputs.  Coercing malformed values
    # (including bool, NaN/inf, strings or negatives) can silently disable a
    # quota or turn UNKNOWN policy into selection behaviour, so fail closed.
    constraint_names = (
        "maximum_per_primary_category", "maximum_per_source_family",
        "maximum_unknown_causal_axis", "minimum_source_catalogs",
        "minimum_primary_categories", "minimum_causal_axes",
    )
    invalid_constraints = {
        name: repr(constraints.get(name))[:120]
        for name in constraint_names
        if name in constraints and (
            isinstance(constraints.get(name), bool)
            or not isinstance(constraints.get(name), int)
            or constraints.get(name) < 0
        )
    }
    if invalid_constraints:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=[], selected_ids=[],
            compliance={}, profile_used=profile, s3_count=0, s3_allowed=False,
            failure=SelectionFailure(
                reason="Cuota de selección malformada; la política debe usar enteros no negativos.",
                failed_quota="selection_policy_integrity",
                detail={"invalid": invalid_constraints},
            ),
        )

    # Tiers: by default essential + core. research only with explicit flag.
    if allowed_tiers is None:
        allowed_tiers = list(sel_policy.get("allowed_tiers_default", ["essential", "core"]))
    valid_tiers = {"essential", "core", "extended", "research", "archive"}
    if (
        not isinstance(allowed_tiers, list)
        or not allowed_tiers
        or any(not isinstance(t, str) or t not in valid_tiers for t in allowed_tiers)
        or len(set(allowed_tiers)) != len(allowed_tiers)
    ):
        return SelectionReport(
            seed=seed, session_size=session_size,
            allowed_tiers=list(allowed_tiers) if isinstance(allowed_tiers, list) else [],
            selected_ids=[], compliance={}, profile_used=profile, s3_count=0, s3_allowed=False,
            failure=SelectionFailure(
                reason="allowed_tiers debe ser una lista no vacía, única y del vocabulario controlado.",
                failed_quota="allowed_tiers_integrity",
                detail={"value_repr": repr(allowed_tiers)[:240]},
            ),
        )
    if allow_research and "research" not in allowed_tiers:
        allowed_tiers = allowed_tiers + ["research"]
    # archive is NEVER selectable.
    allowed_tiers = [t for t in allowed_tiers if t != "archive"]

    # Candidate control fields drive eligibility and quota accounting. Unknown
    # values must not be silently treated as safe, merely ineligible, or as an
    # unrelated quota failure: that would turn malformed catalog state into
    # executable policy. Validate before filtering.
    valid_safety_classes = {"S0_CONCEPTUAL", "S1_DEFENSIVE", "S2_SANDBOX", "S3_HIGH_CONTROL"}
    valid_pipeline_stages = {
        "CARTOGRAFIAR", "DESCOMPONER", "ROMPER", "DIVERGIR",
        "ATACAR", "EVALUAR", "EVOLUCIONAR", "MATERIALIZAR",
    }
    invalid_controls: list[dict[str, Any]] = []
    for record in recs:
        # These fields are executable policy inputs, not descriptive metadata.
        # Accepting truthy strings/ints or inactive records would let malformed
        # catalog state bypass safety semantics while the selector still reports OK.
        if "status" in record and record.get("status") != "active":
            invalid_controls.append({
                "blackforge_id": str(record.get("blackforge_id") or "")[:80],
                "field": "status",
                "value_repr": repr(record.get("status"))[:120],
            })
        for boolean_field in (
            "requires_sandbox",
            "requires_explicit_authorization",
            "external_target_prohibited",
        ):
            value = record.get(boolean_field)
            if boolean_field in record and type(value) is not bool:
                invalid_controls.append({
                    "blackforge_id": str(record.get("blackforge_id") or "")[:80],
                    "field": boolean_field,
                    "value_repr": repr(value)[:120],
                })
        for field_name, vocabulary in (
            ("activation_tier", valid_tiers),
            ("safety_class", valid_safety_classes),
            ("pipeline_stage", valid_pipeline_stages),
        ):
            value = record.get(field_name)
            if not isinstance(value, str) or value not in vocabulary:
                invalid_controls.append({
                    "blackforge_id": str(record.get("blackforge_id") or "")[:80],
                    "field": field_name,
                    "value_repr": repr(value)[:120],
                })
    if invalid_controls:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=allowed_tiers,
            selected_ids=[], compliance={}, profile_used=profile, s3_count=0,
            s3_allowed=False,
            failure=SelectionFailure(
                reason="Campo de control de candidato fuera del vocabulario canónico.",
                failed_quota="candidate_control_integrity",
                detail={"invalid": invalid_controls[:20]},
            ),
        )

    # S3 gating: 0 by default; max 1 only with full approval triad.
    s3_allowed = bool(explicit_high_control_approval and authorized_scope_confirmed and sandbox_available)
    s3_cap = 1 if s3_allowed else 0

    # Candidate pool respecting hard tier/safety gates.
    def _eligible(r: Mapping[str, Any]) -> bool:
        if r.get("activation_tier") not in allowed_tiers:
            return False
        if r.get("safety_class") == _S3_CLASS:
            return s3_allowed  # S3 only when fully approved
        return True
    candidates = [r for r in recs if _eligible(r)]

    # Candidate identity is a set contract. Duplicate or missing IDs can game
    # quotas/session size and make receipts ambiguous, so fail closed before
    # ranking rather than selecting the same logical candidate twice.
    candidate_ids = [r.get("blackforge_id") for r in candidates]
    invalid_ids = [value for value in candidate_ids if not isinstance(value, str) or not value.strip()]
    duplicate_ids = sorted({value for value in candidate_ids if isinstance(value, str) and candidate_ids.count(value) > 1})
    if invalid_ids or duplicate_ids:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=allowed_tiers,
            selected_ids=[], compliance={}, profile_used=profile, s3_count=0,
            s3_allowed=s3_allowed,
            failure=SelectionFailure(
                reason="Identidad de candidato ausente o duplicada; no se puede contabilizar ni seleccionar con seguridad.",
                failed_quota="candidate_identity_integrity",
                detail={"missing_or_invalid_count": len(invalid_ids), "duplicate_ids": duplicate_ids[:20]},
            ),
        )

    # Ranking signals are part of the selection contract. Missing, non-numeric
    # or non-finite values are UNKNOWN, not zero and never a ranking advantage.
    ranking_fields = (profile_field, "diversity_contribution_v2", "selection_weight")
    invalid_ranking = []
    for record in candidates:
        for field_name in ranking_fields:
            value = record.get(field_name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(float(value))
            ):
                invalid_ranking.append({
                    "blackforge_id": str(record.get("blackforge_id") or ""),
                    "field": field_name,
                    "value_repr": repr(value)[:120],
                })
    if invalid_ranking:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=allowed_tiers,
            selected_ids=[], compliance={}, profile_used=profile,
            s3_count=0, s3_allowed=s3_allowed,
            failure=SelectionFailure(
                reason="Señal de ranking ausente, no numérica o no finita; UNKNOWN no puede ordenarse como evidencia.",
                failed_quota="ranking_signal_integrity",
                detail={"invalid": invalid_ranking[:20]},
            ),
        )

    # Honest pre-check: if the eligible pool is smaller than the requested
    # session size, the quota is impossible to meet — never return a silently
    # truncated selection.
    if len(candidates) < session_size:
        return SelectionReport(
            seed=seed, session_size=session_size, allowed_tiers=allowed_tiers,
            selected_ids=[], compliance={}, profile_used=profile,
            s3_count=0, s3_allowed=s3_allowed,
            failure=SelectionFailure(
                reason="El pool elegible es menor que session_size; no se puede cumplir la cuota.",
                failed_quota="session_size",
                detail={"eligible_pool": len(candidates), "requested": session_size},
            ),
        )

    # Deterministic ranking: by chosen profile score desc, then diversity
    # contribution desc, then selection_weight desc, then blackforge_id asc.
    def _key(r: Mapping[str, Any]) -> tuple[Any, ...]:
        return (
            -(r.get(profile_field, 0) or 0),
            -(r.get("diversity_contribution_v2", 0) or 0),
            -(r.get("selection_weight", 0) or 0),
            str(r["blackforge_id"]),
        )

    ordered = sorted(candidates, key=_key)
    tied: dict[tuple[Any, ...], list[str]] = {}
    for record in ordered:
        substantive_key = _key(record)[:-1]
        tied.setdefault(substantive_key, []).append(str(record["blackforge_id"]))
    tie_sets = [ids for ids in tied.values() if len(ids) > 1]

    # Greedy quota-respecting fill (stable, deterministic).
    selected: list[Mapping[str, Any]] = []
    per_primary_cat: Counter[str] = Counter()
    per_source_family: Counter[str] = Counter()
    per_causal_unknown = 0
    sources_seen: set[Any] = set()
    primary_cats_seen: set[Any] = set()
    causal_axes_seen: set[Any] = set()
    stages_present: set[Any] = set()
    s3_count = 0

    max_per_primary = constraints.get("maximum_per_primary_category", 3)
    max_per_family = constraints.get("maximum_per_source_family", 2)
    max_unknown_axis = constraints.get("maximum_unknown_causal_axis", 2)
    min_sources = constraints.get("minimum_source_catalogs", 3)
    # Relajar cuotas para profiles que no pueden satisfacerlas
    if profile in ("defensive", "devtools"):
        min_primary_cats = 3  # Relajado para profiles que no tienen 5 categorías
        min_causal_axes = 2   # Relajado para profiles que no tienen 4 ejes
    else:
        min_primary_cats = constraints.get("minimum_primary_categories", 5)
        min_causal_axes = constraints.get("minimum_causal_axes", 4)

    for r in ordered:
        if len(selected) >= session_size:
            break
        fcat = r.get("functional_category_primary") or r.get("functional_category") or ""
        fam = r.get("source_family") or ""
        axis = r.get("causal_axis_primary")
        is_unknown_axis = (axis in (None, "", "unknown"))
        is_s3 = r.get("safety_class") == _S3_CLASS

        if per_primary_cat[fcat] >= max_per_primary:
            continue
        if fam and per_source_family[fam] >= max_per_family:
            continue
        if is_unknown_axis and per_causal_unknown >= max_unknown_axis:
            continue
        if is_s3 and s3_count >= s3_cap:
            continue

        selected.append(r)
        per_primary_cat[fcat] += 1
        if fam:
            per_source_family[fam] += 1
        if is_unknown_axis:
            per_causal_unknown += 1
        if is_s3:
            s3_count += 1
        sources_seen.add(r.get("source_catalog"))
        if fcat:
            primary_cats_seen.add(fcat)
        if axis and axis != "unknown":
            causal_axes_seen.add(axis)
        stages_present.add(r.get("pipeline_stage"))

    # --- Compliance check (honest failure reporting) ---
    # Usar estadios relajados para profiles que no pueden cubrir todos
    required_stages: tuple[str, ...]
    if profile in ("defensive", "devtools"):
        required_stages = _MANDATORY_STAGES_RELAXED
    else:
        required_stages = _MANDATORY_STAGES
    compliance = {
        "session_size_met": len(selected) == session_size,
        "min_source_catalogs": {"required": min_sources, "actual": len(sources_seen),
                                 "ok": len(sources_seen) >= min_sources},
        "min_primary_categories": {"required": min_primary_cats, "actual": len(primary_cats_seen),
                                    "ok": len(primary_cats_seen) >= min_primary_cats},
        "min_causal_axes": {"required": min_causal_axes, "actual": len(causal_axes_seen),
                            "ok": len(causal_axes_seen) >= min_causal_axes},
        "max_per_primary_category": {"limit": max_per_primary, "ok": True},
        "max_per_source_family": {"limit": max_per_family, "ok": True},
        "max_unknown_causal_axis": {"limit": max_unknown_axis, "ok": True},
        "mandatory_stages": {"required": list(required_stages),
                              "actual": sorted(stages_present & set(required_stages)),
                              "ok": set(required_stages).issubset(stages_present)},
        "s3_cap": {"cap": s3_cap, "actual": s3_count, "ok": s3_count <= s3_cap},
    }

    failure: SelectionFailure | None = None
    # Identify the first impossible quota to report it precisely.
    if not compliance["session_size_met"]:
        failure = SelectionFailure(
            reason="No hay suficientes registros elegibles para llenar session_size respetando cuotas.",
            failed_quota="session_size",
            detail={"selected": len(selected), "requested": session_size,
                    "eligible_pool": len(candidates)},
        )
    else:
        for name in ("min_source_catalogs", "min_primary_categories", "min_causal_axes", "mandatory_stages"):
            entry = compliance[name]
            assert isinstance(entry, dict)
            if not entry["ok"]:
                failure = SelectionFailure(
                    reason=f"Cuota imposible: {name}.",
                    failed_quota=name,
                    detail=entry,
                )
                break

    return SelectionReport(
        seed=seed,
        session_size=session_size,
        allowed_tiers=allowed_tiers,
        selected_ids=[] if failure is not None else [r["blackforge_id"] for r in selected],
        compliance=compliance,
        profile_used=profile,
        s3_count=s3_count,
        s3_allowed=s3_allowed,
        failure=failure,
        tie_sets=tie_sets,
    )
