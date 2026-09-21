"""Deterministic descriptive detectors permitted in initial STANDARD."""

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


def _executions(trace: SealedTrace) -> list[dict[str, Any]]:
    raw = trace.payload().get("restricted_execution_results")
    return [item for item in raw if isinstance(item, dict)] if isinstance(raw, list) else []


def traceability_integrity(trace: SealedTrace) -> list[Diagnostic]:
    payload = trace.payload()
    selected = payload.get("selected_candidate")
    selected_id = (
        str(selected.get("candidate_id") or "") if isinstance(selected, dict) else ""
    )
    executions = _executions(trace)
    execution_ids = [str(item.get("execution_id") or "") for item in executions]
    duplicate_execution_ids = sorted(
        item
        for item, count in Counter(execution_ids).items()
        if item and count > 1
    )
    missing_identity = [
        index
        for index, item in enumerate(executions)
        if not all(
            str(item.get(field) or "").strip()
            for field in (
                "execution_id",
                "candidate_id",
                "mechanism_version",
                "claim_id",
                "protocol_version",
            )
        )
    ]
    mismatched_candidate = [
        str(item.get("execution_id") or "")
        for item in executions
        if selected_id
        and item.get("identity_bound") is True
        and str(item.get("candidate_id") or "") != selected_id
    ]
    return [
        Diagnostic(
            detector_id="traceability_integrity",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="execution_identity_coverage",
            status="OBSERVED",
            message="Explicit execution identity links checked on exported fields.",
            details={
                "selected_candidate_id_present": bool(selected_id),
                "execution_count": len(executions),
                "duplicate_execution_ids": duplicate_execution_ids,
                "missing_identity_indexes": missing_identity,
                "bound_candidate_mismatches": mismatched_candidate,
                "claim_scope": "exported_identity_links_only",
            },
        )
    ]


def descriptive_distributions(trace: SealedTrace) -> list[Diagnostic]:
    executions = _executions(trace)
    pass_counts = Counter(
        "PASS" if item.get("passed") is True else "FAIL"
        if item.get("passed") is False
        else "UNKNOWN"
        for item in executions
    )
    durations = [
        float(item["duration_ms"])
        for item in executions
        if isinstance(item.get("duration_ms"), (int, float))
    ]
    verification = trace.payload().get("verification")
    verdict = verification.get("verdict") if isinstance(verification, dict) else None
    return [
        Diagnostic(
            detector_id="descriptive_distributions",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="execution_distribution",
            status="OBSERVED" if executions else "NOT_EVALUATED",
            message="Execution/verification distributions recorded descriptively only.",
            details={
                "execution_count": len(executions),
                "result_counts": dict(sorted(pass_counts.items())),
                "duration_count": len(durations),
                "duration_min_ms": min(durations) if durations else None,
                "duration_max_ms": max(durations) if durations else None,
                "duration_mean_ms": (sum(durations) / len(durations)) if durations else None,
                "verification_verdict": verdict,
                "claim_scope": "descriptive_only",
            },
        )
    ]


def execution_record_consistency(trace: SealedTrace) -> list[Diagnostic]:
    payload = trace.payload()
    stage = str(payload.get("stage") or "")
    executions = _executions(trace)
    latest = executions[-1] if executions else None
    final_output = payload.get("final_output")
    final = final_output if isinstance(final_output, dict) else {}

    latest_bound_pass = bool(
        latest and latest.get("passed") is True and latest.get("identity_bound") is True
    )
    conflicts: list[str] = []
    if stage == "RESTRICTED_EXECUTION_VERIFIED" and not latest_bound_pass:
        conflicts.append("verified_stage_without_latest_bound_pass")

    expected_status = (
        "BOUND_PASS"
        if latest_bound_pass
        else "BOUND_FAIL"
        if latest and latest.get("identity_bound") is True
        else "UNBOUND"
        if latest
        else "NOT_RUN"
    )
    cached_status = final.get("restricted_execution_status")
    if cached_status is not None and cached_status != expected_status:
        conflicts.append("cached_restricted_status_mismatch")

    return [
        Diagnostic(
            detector_id="execution_record_consistency",
            detector_version="1",
            trace_sha256=trace.payload_sha256,
            kind="execution_record",
            status="CONFLICT" if conflicts else "OBSERVED",
            message="Execution-derived state compared with exported latest-attempt semantics.",
            details={
                "conflicts": conflicts,
                "expected_restricted_status": expected_status,
                "cached_restricted_status": cached_status,
                "claim_scope": "record_consistency_only",
            },
        )
    ]


DEFAULT_DETECTORS: tuple[DetectorSpec, ...] = (
    DetectorSpec("traceability_integrity", "1", traceability_integrity),
    DetectorSpec("descriptive_distributions", "1", descriptive_distributions),
    DetectorSpec("execution_record_consistency", "1", execution_record_consistency),
)
