"""Deterministic descriptive detectors allowed in initial STANDARD."""

from __future__ import annotations

from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from .records import Diagnostic
from .trace import SealedTrace


@dataclass(frozen=True, slots=True)
class DetectorSpec:
    detector_id: str
    version: str
    run: Callable[[SealedTrace], list[Diagnostic]]


def _ideas(trace: SealedTrace) -> list[dict[str, Any]]:
    payload = trace.payload()
    raw = payload.get("ideas")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def traceability_integrity(trace: SealedTrace) -> list[Diagnostic]:
    ideas = _ideas(trace)
    ids = [str(item.get("id") or "") for item in ideas]
    missing_ids = [index for index, idea_id in enumerate(ids) if not idea_id]
    duplicate_ids = sorted(
        idea_id for idea_id, count in Counter(ids).items() if idea_id and count > 1
    )
    payload = trace.payload()
    top_raw = payload.get("top_ideas")
    top_ids = [str(item) for item in top_raw] if isinstance(top_raw, list) else []
    unresolved_top = sorted(item for item in top_ids if item and item not in set(ids))

    return [
        Diagnostic(
            detector_id="traceability_integrity",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="traceability_coverage",
            status="OBSERVED",
            message="Explicit identity/provenance checks executed over exported fields.",
            details={
                "idea_count": len(ideas),
                "missing_id_indexes": missing_ids,
                "duplicate_ids": duplicate_ids,
                "unresolved_top_idea_ids": unresolved_top,
                "claim_scope": "exported_identity_links_only",
            },
        )
    ]


def descriptive_distributions(trace: SealedTrace) -> list[Diagnostic]:
    ideas = _ideas(trace)
    families = Counter(str(item.get("family") or "") for item in ideas)
    values: list[float] = []
    for item in ideas:
        convergence = item.get("convergence")
        if not isinstance(convergence, dict):
            continue
        value = convergence.get("value_score")
        if isinstance(value, (int, float)):
            values.append(float(value))

    return [
        Diagnostic(
            detector_id="descriptive_distributions",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="distribution_description",
            status="OBSERVED" if ideas else "NOT_EVALUATED",
            message=(
                "Descriptive distributions recorded without pathology thresholds or "
                "Goodhart attribution."
            ),
            details={
                "idea_count": len(ideas),
                "family_counts": dict(sorted(families.items())),
                "value_score_count": len(values),
                "value_score_min": min(values) if values else None,
                "value_score_max": max(values) if values else None,
                "value_score_mean": (sum(values) / len(values)) if values else None,
                "claim_scope": "descriptive_only",
            },
        )
    ]


def execution_record_consistency(trace: SealedTrace) -> list[Diagnostic]:
    payload = trace.payload()
    decision = payload.get("decision")
    if not isinstance(decision, dict):
        return [
            Diagnostic(
                detector_id="execution_record_consistency",
                detector_version="1",
                trace_sha256=trace.payload_sha256,
                kind="decision_record",
                status="UNKNOWN",
                message="Decision record unavailable in public trace.",
                details={"claim_scope": "record_consistency_only"},
            )
        ]

    missing = [
        key
        for key in ("pipeline_action", "recommended_status")
        if decision.get(key) in (None, "")
    ]
    return [
        Diagnostic(
            detector_id="execution_record_consistency",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="decision_record",
            status="CONFLICT" if missing else "OBSERVED",
            message="Decision record checked against explicit exported-field requirements.",
            details={
                "missing_required_fields": missing,
                "claim_scope": "record_consistency_only",
            },
        )
    ]


DEFAULT_DETECTORS: tuple[DetectorSpec, ...] = (
    DetectorSpec("traceability_integrity", "1", traceability_integrity),
    DetectorSpec("descriptive_distributions", "1", descriptive_distributions),
    DetectorSpec("execution_record_consistency", "1", execution_record_consistency),
)
