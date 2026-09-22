"""Immutable public posture projection for out-of-band observation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

TRACE_SCHEMA_VERSION = "astra-supra-public-trace/1"
TRACE_SOURCE = "SUPRA"


@dataclass(frozen=True, slots=True)
class SealedTrace:
    schema_version: str
    source: str
    run_id: str
    payload_sha256: str
    payload_json: str

    def payload(self) -> dict[str, Any]:
        decoded = json.loads(self.payload_json)
        if not isinstance(decoded, dict):
            raise ValueError("sealed trace payload must decode to an object")
        return cast(dict[str, Any], decoded)


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _public_execution(raw: object) -> dict[str, Any]:
    item = _mapping(raw)
    return {
        "execution_id": str(item.get("execution_id") or ""),
        "execution_semantics_version": item.get("execution_semantics_version"),
        "candidate_id": str(item.get("candidate_id") or ""),
        "mechanism_version": str(item.get("mechanism_version") or ""),
        "claim_id": str(item.get("claim_id") or ""),
        "protocol_version": str(item.get("protocol_version") or ""),
        "observed_result": item.get("observed_result"),
        "action_type": item.get("action_type"),
        "passed": item.get("passed"),
        "error_type": item.get("error_type"),
        "duration_ms": item.get("duration_ms"),
        "execution_classification": item.get("execution_classification"),
        "result_scope": item.get("result_scope"),
        "scientific_validation": item.get("scientific_validation"),
        "process_isolated": item.get("process_isolated"),
        "secure_for_untrusted_code": item.get("secure_for_untrusted_code"),
        "identity_bound": item.get("identity_bound"),
    }


def project_public_posture(posture: Mapping[str, Any]) -> dict[str, Any]:
    """Whitelist public decisional state; exclude objective/prompts/free-form logs."""

    selected = _mapping(posture.get("selected_candidate"))
    verification = _mapping(posture.get("verification"))
    final_output = _mapping(posture.get("final_output"))
    executions = posture.get("restricted_execution_results")
    checkpoints = posture.get("checkpoints")

    projected = {
        "project_id": str(posture.get("project_id") or ""),
        "stage": str(posture.get("stage") or ""),
        "selected_candidate": {
            "candidate_id": str(selected.get("candidate_id") or ""),
            "paradigm_type": str(selected.get("paradigm_type") or ""),
            "divergence_score": selected.get("divergence_score"),
            "feasibility_score": selected.get("feasibility_score"),
        },
        "verification": {
            "verdict": verification.get("verdict"),
            "verification_scope": verification.get("verification_scope"),
            "measurement_kind": verification.get("measurement_kind"),
            "confidence_score": verification.get("confidence_score"),
            "confidence_semantics": verification.get("confidence_semantics"),
        },
        "restricted_execution_results": [_public_execution(item) for item in executions]
        if isinstance(executions, list)
        else [],
        "checkpoints": [
            {
                "checkpoint_id": str(item.get("checkpoint_id") or ""),
                "stage": str(item.get("stage") or ""),
                "title": str(item.get("title") or ""),
                "actor": str(item.get("actor") or ""),
            }
            for item in checkpoints
            if isinstance(item, Mapping)
        ]
        if isinstance(checkpoints, list)
        else [],
        "final_output": {
            key: final_output.get(key)
            for key in (
                "workflow_status",
                "verification_status",
                "verification_scope",
                "restricted_execution_status",
                "restricted_execution_identity_bound",
                "scientific_status",
                "h0_status",
                "hash_semantics",
                "discriminant_protocol_status",
                "independent_confirmation_status",
                "learning_update_status",
                "derived_execution_state_revalidated",
            )
            if key in final_output
        },
    }
    if not projected["project_id"]:
        raise ValueError("public trace requires a stable project_id")
    return projected


def seal_public_posture(posture: Mapping[str, Any]) -> SealedTrace:
    public = project_public_posture(posture)
    payload_json = json.dumps(
        public,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return SealedTrace(
        schema_version=TRACE_SCHEMA_VERSION,
        source=TRACE_SOURCE,
        run_id=str(public["project_id"]),
        payload_sha256=digest,
        payload_json=payload_json,
    )


def sealed_trace_record(trace: SealedTrace) -> dict[str, str]:
    return {
        "schema_version": trace.schema_version,
        "source": trace.source,
        "run_id": trace.run_id,
        "payload_sha256": trace.payload_sha256,
        "payload_json": trace.payload_json,
    }


def load_sealed_trace(record: Mapping[str, Any]) -> SealedTrace:
    trace = SealedTrace(
        schema_version=str(record.get("schema_version") or ""),
        source=str(record.get("source") or ""),
        run_id=str(record.get("run_id") or ""),
        payload_sha256=str(record.get("payload_sha256") or ""),
        payload_json=str(record.get("payload_json") or ""),
    )
    if trace.schema_version != TRACE_SCHEMA_VERSION:
        raise ValueError("unsupported public trace schema")
    if trace.source != TRACE_SOURCE:
        raise ValueError("unsupported public trace source")
    if not trace.run_id:
        raise ValueError("sealed trace is missing run_id")
    actual = hashlib.sha256(trace.payload_json.encode("utf-8")).hexdigest()
    if actual != trace.payload_sha256:
        raise ValueError("sealed trace integrity mismatch")
    if str(trace.payload().get("project_id") or "") != trace.run_id:
        raise ValueError("sealed trace run_id does not match project identity")
    return trace
