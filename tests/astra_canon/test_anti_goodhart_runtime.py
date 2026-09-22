"""Executable Anti-Goodhart sentinels for observational STANDARD.

These tests prove code-boundary non-interference properties only. They do not
claim deployment/resource isolation (G3), so product STANDARD remains disabled.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from criba import engine
from criba.anti_goodhart.detectors import DetectorSpec
from criba.anti_goodhart.gate import (
    GateEvidence,
    ObserverMode,
    StandardDisabledError,
    gate_evidence_satisfies,
    scope_fingerprint,
    standard_allowed,
)
from criba.anti_goodhart.observer import _observe_trace_after_gate, observe_trace
from criba.anti_goodhart.records import Diagnostic
from criba.anti_goodhart.store import ObserverStore
from criba.anti_goodhart.trace import (
    load_sealed_trace,
    project_public_packet,
    seal_public_packet,
    sealed_trace_record,
)

ROOT = Path(__file__).resolve().parents[2]
QUERY = "¿Cómo proteger APIs de ataques de inyección?"


def _packet(run_id: str = "run-1") -> dict[str, object]:
    return {
        "schema": "CRIBA",
        "schema_version": "1",
        "activation_id": run_id,
        "original_query": "SECRET_QUERY_SHOULD_NOT_EXPORT",
        "model_instruction": "SECRET_PROMPT_SHOULD_NOT_EXPORT",
        "selected_current": {"id": "C1", "score": 0.5},
        "supporting_methods": [
            {"id": "M1", "family": "f1", "axis": "a1", "reason": "private prose"}
        ],
        "decision": {
            "pipeline_action": "PROTOTIPAR",
            "recommended_status": "AMPLIAR PRUEBA",
            "confidence": 0.5,
        },
        "metrics": {
            "potential_novelty": 60,
            "divergence": 70,
            "feasibility": 80,
            "controlled_risk": 40,
            "reversibility": 74,
            "uncertainty": 56,
            "mean_value_score": 0.4,
            "conf_code_executes": 1.0,
            "conf_causal_root": "INFERRED_NOT_PROVEN",
        },
        "innovation": {
            "top_ideas": ["I1"],
            "hcm_context": {"secret": "not public"},
            "ideas": [
                {
                    "id": "I1",
                    "family": "f1",
                    "family2": "f2",
                    "source_method": "M1",
                    "duplicate_status": "distinct",
                    "causal_claim": "MECHANISM_PROPOSED_UNVALIDATED",
                    "causal_axes_changed": ["a1"],
                    "description": "PRIVATE FREE FORM IDEA TEXT",
                    "convergence": {
                        "evidence": 0.2,
                        "novelty": 0.3,
                        "cost": 0.4,
                        "value_score": 0.15,
                    },
                    "evidence": {"value": 0.2, "status": "OBSERVED", "source": "runtime"},
                    "genome": {"id": "G1"},
                }
            ],
        },
    }


def _scope() -> str:
    return scope_fingerprint(
        runtime_version="test-runtime",
        export_schema="astra-public-trace/1",
        detector_versions=["traceability_integrity:1", "descriptive_distributions:1"],
        isolation_profile="test-isolated-worker",
    )


def _full_gate() -> GateEvidence:
    scope = _scope()
    return GateEvidence(
        scope_fingerprint=scope,
        g1_pass=True,
        g2_pass=True,
        g3_pass=True,
        g4_pass=True,
        all_applicable_rows_executed=True,
        sensitivity_controls_pass=True,
        deployment_scope_matches=True,
    )


def _normalized_engine_packet(packet: dict[str, object]) -> dict[str, object]:
    cloned = copy.deepcopy(packet)
    cloned.pop("activation_id", None)
    cloned.pop("timestamp", None)
    return cloned


def test_g1_public_trace_is_deterministic_immutable_and_excludes_forbidden_inputs() -> None:
    packet = _packet()
    source_before = copy.deepcopy(packet)
    first = seal_public_packet(packet)
    second = seal_public_packet(packet)
    assert first == second

    payload = first.payload()
    serialized = first.payload_json
    assert "SECRET_QUERY_SHOULD_NOT_EXPORT" not in serialized
    assert "SECRET_PROMPT_SHOULD_NOT_EXPORT" not in serialized
    assert "PRIVATE FREE FORM IDEA TEXT" not in serialized
    assert "hcm_context" not in serialized
    assert "original_query" not in payload
    assert "model_instruction" not in payload

    packet["decision"] = {"pipeline_action": "MUTATED_AFTER_SEAL"}
    assert first.payload()["decision"]["pipeline_action"] == "PROTOTIPAR"
    assert source_before != packet


def test_g1_projection_requires_stable_episode_identity() -> None:
    packet = _packet()
    packet["activation_id"] = ""
    with pytest.raises(ValueError, match="stable activation_id"):
        project_public_packet(packet)


def test_activation_rule_is_binary_scope_bound_and_defaults_disabled() -> None:
    scope = _scope()
    assert gate_evidence_satisfies(None, current_scope_fingerprint=scope) is False
    assert gate_evidence_satisfies(_full_gate(), current_scope_fingerprint=scope) is True
    assert gate_evidence_satisfies(_full_gate(), current_scope_fingerprint="changed-scope") is False
    assert standard_allowed(_full_gate(), current_scope_fingerprint=scope) is False

    stale = GateEvidence(
        scope_fingerprint=scope,
        g1_pass=True,
        g2_pass=True,
        g3_pass=False,
        g4_pass=True,
        all_applicable_rows_executed=True,
        sensitivity_controls_pass=True,
        deployment_scope_matches=True,
    )
    assert gate_evidence_satisfies(stale, current_scope_fingerprint=scope) is False


def test_off_mode_creates_no_observer_state(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    root = tmp_path / "observer"
    result = observe_trace(
        trace,
        store=ObserverStore(root),
        mode=ObserverMode.OFF,
    )
    assert result.inserted_diagnostics == 0
    assert result.failures == ()
    assert not root.exists()


def test_standard_public_api_stays_disabled_even_with_complete_gate(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    with pytest.raises(StandardDisabledError, match="STANDARD_DISABLED"):
        observe_trace(
            trace,
            store=ObserverStore(tmp_path / "observer"),
            mode=ObserverMode.STANDARD,
            gate_evidence=_full_gate(),
            current_scope_fingerprint=_scope(),
        )


def test_g2_duplicate_delivery_is_idempotent_and_does_not_mutate_trace(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    original = trace.payload_json
    store = ObserverStore(tmp_path / "observer")

    first = _observe_trace_after_gate(
        trace,
        store=store,
    )
    second = _observe_trace_after_gate(
        trace,
        store=store,
    )

    assert first.inserted_diagnostics == 3
    assert second.inserted_diagnostics == 0
    assert second.duplicate_diagnostics == 3
    assert len(store.read_diagnostics()) == 3
    assert trace.payload_json == original


def test_g2_detector_exception_is_confined_and_secret_message_not_persisted(
    tmp_path: Path,
) -> None:
    trace = seal_public_packet(_packet())

    def broken_detector(_trace):
        raise RuntimeError("SENTINEL_SECRET_DO_NOT_PERSIST")

    detector = DetectorSpec("broken", "1", broken_detector)
    store = ObserverStore(tmp_path / "observer")
    result = _observe_trace_after_gate(
        trace,
        store=store,
        detectors=(detector,),
    )

    assert result.failures == ("broken:RuntimeError",)
    persisted = (tmp_path / "observer" / "observer_failures.jsonl").read_text(
        encoding="utf-8"
    )
    assert "RuntimeError" in persisted
    assert "SENTINEL_SECRET_DO_NOT_PERSIST" not in persisted


def test_g2_diagnostic_volume_changes_only_observer_domain(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    before = trace.payload_json

    def many_diagnostics(current_trace):
        return [
            Diagnostic(
                detector_id="volume",
                detector_version="1",
                trace_sha256=current_trace.payload_sha256,
                kind=f"sample-{index}",
                status="OBSERVED",
                message="descriptive sample",
                details={"index": index},
            )
            for index in range(100)
        ]

    result = _observe_trace_after_gate(
        trace,
        store=ObserverStore(tmp_path / "observer"),
        detectors=(DetectorSpec("volume", "1", many_diagnostics),),
    )
    assert result.inserted_diagnostics == 100
    assert trace.payload_json == before


def test_g4_observer_store_restart_restores_only_observer_records(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    root = tmp_path / "observer"
    _observe_trace_after_gate(
        trace,
        store=ObserverStore(root),
    )

    restarted = ObserverStore(root)
    diagnostics = restarted.read_diagnostics()
    assert len(diagnostics) == 3
    assert all(item["trace_sha256"] == trace.payload_sha256 for item in diagnostics)


def test_g2_g4_product_runtime_has_no_observer_import_path() -> None:
    critical = [
        "src/criba/engine.py",
        "src/criba/lottery.py",
        "src/criba/inventar.py",
        "src/criba/model_runtime.py",
        "src/criba/diversity_selector.py",
        "src/criba/intelligence/outcome_store.py",
    ]
    for relative in critical:
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "anti_goodhart" not in source, f"observer entered decisional path: {relative}"

    detector_source = (
        ROOT / "src" / "criba" / "anti_goodhart" / "detectors.py"
    ).read_text(encoding="utf-8")
    assert "import random" not in detector_source
    assert "from random" not in detector_source


def test_g4_two_decisions_remain_identical_after_out_of_band_observation(
    tmp_path: Path,
) -> None:
    control = engine.activate(QUERY)
    observed = engine.activate(QUERY)
    trace = seal_public_packet(observed)
    _observe_trace_after_gate(
        trace,
        store=ObserverStore(tmp_path / "observer"),
    )
    after = engine.activate(QUERY)

    assert _normalized_engine_packet(control) == _normalized_engine_packet(observed)
    assert _normalized_engine_packet(control) == _normalized_engine_packet(after)


def test_sensitivity_control_detects_intentional_decisional_contamination() -> None:
    baseline = engine.activate(QUERY)
    contaminated = copy.deepcopy(baseline)
    contaminated["decision"]["pipeline_action"] = "INTENTIONAL_CONTAMINATION"
    assert _normalized_engine_packet(baseline) != _normalized_engine_packet(contaminated)


def test_observer_storage_failure_is_confined_to_o_domain(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    before = trace.payload_json

    class BrokenStore(ObserverStore):
        def append_diagnostic(self, diagnostic):
            raise OSError("SENTINEL_STORAGE_SECRET")

    result = _observe_trace_after_gate(
        trace,
        store=BrokenStore(tmp_path / "observer"),
    )
    assert result.inserted_diagnostics == 0
    assert result.failures == (
        "observer_store:OSError",
        "observer_store:OSError",
        "observer_store:OSError",
    )
    assert trace.payload_json == before

def test_sealed_trace_rejects_forged_source_identity() -> None:
    trace = seal_public_packet(_packet())
    record = sealed_trace_record(trace)
    record["source"] = "FORGED_SOURCE"
    with pytest.raises(ValueError, match="source"):
        load_sealed_trace(record)


def test_tampered_parseable_record_cannot_suppress_valid_diagnostic(tmp_path: Path) -> None:
    trace = seal_public_packet(_packet())
    diagnostic = Diagnostic(
        detector_id="poison-sentinel",
        detector_version="1",
        trace_sha256=trace.payload_sha256,
        kind="integrity",
        status="OBSERVED",
        message="canonical diagnostic",
        details={"value": 1},
    )
    store = ObserverStore(tmp_path / "observer")
    store.root.mkdir(parents=True, exist_ok=True)
    tampered = diagnostic.to_record()
    tampered["message"] = "tampered but parseable"
    store.diagnostics_path.write_text(
        json.dumps(tampered, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert store.append_diagnostic(diagnostic) is True
    canonical = [
        item
        for item in store.read_diagnostics()
        if item.get("message") == "canonical diagnostic"
    ]
    assert len(canonical) == 1

