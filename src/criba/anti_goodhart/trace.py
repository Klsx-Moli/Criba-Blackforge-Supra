"""Immutable, versioned public trace export for out-of-band observation."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, cast

TRACE_SCHEMA_VERSION = "astra-public-trace/1"
TRACE_SOURCE = "CRIBA_BLACKFORGE"

_FORBIDDEN_PUBLIC_KEYS = frozenset(
    {
        "original_query",
        "model_instruction",
        "response_contract",
        "hcm_context",
        "hidden_labels",
        "hidden_evaluation",
        "confirmatory_results",
        "private_chain_of_thought",
        "prompt",
        "prompts",
        "retrieved_context",
    }
)


@dataclass(frozen=True, slots=True)
class SealedTrace:
    """Content-addressed immutable representation of a public runtime snapshot."""

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


def _public_idea(raw: object) -> dict[str, Any]:
    idea = _mapping(raw)
    convergence = _mapping(idea.get("convergence"))
    evidence = _mapping(idea.get("evidence"))
    genome = _mapping(idea.get("genome"))
    return {
        "id": str(idea.get("id") or ""),
        "family": str(idea.get("family") or ""),
        "family2": str(idea.get("family2") or ""),
        "source_method": str(idea.get("source_method") or ""),
        "duplicate_status": str(idea.get("duplicate_status") or ""),
        "causal_claim": str(idea.get("causal_claim") or ""),
        "causal_axes_changed": list(idea.get("causal_axes_changed") or []),
        "convergence": {
            "evidence": convergence.get("evidence"),
            "novelty": convergence.get("novelty"),
            "cost": convergence.get("cost"),
            "value_score": convergence.get("value_score"),
        },
        "evidence": {
            "value": evidence.get("value"),
            "status": evidence.get("status"),
            "source": evidence.get("source"),
        },
        "genome_id": str(genome.get("id") or ""),
    }


def project_public_packet(packet: Mapping[str, Any]) -> dict[str, Any]:
    """Project only already-public decisional outputs needed by STANDARD.

    Query text, prompts, retrieved context, hidden/confirmatory material and
    free-form idea descriptions are deliberately excluded.
    """

    innovation = _mapping(packet.get("innovation"))
    decision = _mapping(packet.get("decision"))
    metrics = _mapping(packet.get("metrics"))
    selected_current = _mapping(packet.get("selected_current"))
    supporting_methods = packet.get("supporting_methods")
    ideas = innovation.get("ideas")

    projected: dict[str, Any] = {
        "runtime_schema": packet.get("schema"),
        "runtime_schema_version": packet.get("schema_version"),
        "activation_id": str(packet.get("activation_id") or ""),
        "selected_current": {
            "id": str(selected_current.get("id") or ""),
            "score": selected_current.get("score"),
        },
        "supporting_methods": [
            {
                "id": str(item.get("id") or ""),
                "family": str(item.get("family") or ""),
                "axis": str(item.get("axis") or ""),
            }
            for item in supporting_methods
            if isinstance(item, Mapping)
        ]
        if isinstance(supporting_methods, list)
        else [],
        "decision": {
            "pipeline_action": decision.get("pipeline_action"),
            "recommended_status": decision.get("recommended_status"),
            "confidence": decision.get("confidence"),
        },
        "metrics": {
            "potential_novelty": metrics.get("potential_novelty"),
            "divergence": metrics.get("divergence"),
            "feasibility": metrics.get("feasibility"),
            "controlled_risk": metrics.get("controlled_risk"),
            "reversibility": metrics.get("reversibility"),
            "uncertainty": metrics.get("uncertainty"),
            "mean_value_score": metrics.get("mean_value_score"),
            "conf_code_executes": metrics.get("conf_code_executes"),
            "conf_causal_root": metrics.get("conf_causal_root"),
        },
        "top_ideas": list(innovation.get("top_ideas") or []),
        "ideas": [_public_idea(item) for item in ideas]
        if isinstance(ideas, list)
        else [],
    }

    if not projected["activation_id"]:
        raise ValueError("public trace requires a stable activation_id")
    forbidden = _FORBIDDEN_PUBLIC_KEYS.intersection(projected)
    if forbidden:
        raise ValueError(f"forbidden public trace keys: {sorted(forbidden)}")
    return projected


def seal_public_packet(
    packet: Mapping[str, Any],
    *,
    source: str = TRACE_SOURCE,
) -> SealedTrace:
    """Create a deterministic content-addressed trace after a run completes."""

    public = project_public_packet(packet)
    payload_json = json.dumps(
        public,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    digest = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    return SealedTrace(
        schema_version=TRACE_SCHEMA_VERSION,
        source=source,
        run_id=str(public["activation_id"]),
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
    if not trace.run_id:
        raise ValueError("sealed trace is missing run_id")
    actual = hashlib.sha256(trace.payload_json.encode("utf-8")).hexdigest()
    if actual != trace.payload_sha256:
        raise ValueError("sealed trace integrity mismatch")
    payload = trace.payload()
    if str(payload.get("activation_id") or "") != trace.run_id:
        raise ValueError("sealed trace run_id does not match payload identity")
    return trace
