"""Deterministic S0/S1 input parity preflight, synthetic S0 captured-shape fixture."""
from __future__ import annotations

import copy
import json

import pytest

from benchmarks.innovation import semantic_pair_preflight as gate
from benchmarks.innovation.semantic_cases import trial_for
from benchmarks.innovation.semantic_lab import direct_request


def case(case_id="CBS500-01-01:incident"):
    trial = trial_for(case_id, "phase06-run")
    s0 = {
        "PROBLEMA": trial.query,
        "DOMINIO": {}, "CRUCE": {},
        "BLOQUEO IDENTIFICADO": {
            "restricciones_obligatorias": list(trial.restrictions)},
        "RESTRICCIONES OBLIGATORIAS": list(trial.restrictions),
        "EVIDENCIA LOCAL PERTINENTE": [], "CONTENCION_DECLARADA": "DESCONOCIDA",
        "PROPUESTA A CRITICAR": json.loads(trial.proposal_json),
    }
    return trial, s0


def settings(**changes):
    base = {
        "model_requested": "mock-judge", "model_observed": None,
        "temperature": 0.25, "max_tokens": 2600, "timeout_s": 240,
        "reasoning_effort": "none", "seed": None,
        "response_format": "json_object", "retries_enabled": False,
        "context_window": 16384, "token_count": None,
    }
    base.update(changes)
    return base


def emit(trial, s0, *, s1=None, s0_settings=None, s1_settings=None):
    user0 = "CRITICA_INSTRUCCIONES\nDATOS:\n" + json.dumps(
        s0, ensure_ascii=False, sort_keys=True)
    user1 = (s1 if s1 is not None else direct_request(
        trial, "mock-judge", "try-01").prompt)
    return gate.preflight(
        trial, reviewer="mock-judge", attempt="try-01", s0_user=user0,
        s1_user=user1,
        s0_settings=settings() if s0_settings is None else s0_settings,
        s1_settings=settings() if s1_settings is None else s1_settings,
    )


def test_real_development_trial_structural_asymmetry():
    trial, s0 = case()
    outcome = emit(trial, s0)
    assert outcome["status"] == "BLOCKED"
    assert outcome["authorization"] == "NOT_GRANTED_BY_PREFLIGHT"
    assert outcome["output_mapping"] == "NOT_VALIDATED"
    assert outcome["provider_calls"] is None
    assert outcome["p0_status"] == "OPEN"
    assert "S1_OMITS_PROPOSAL_FIELDS" in outcome["issues"]
    assert "TOKENIZATION_NOT_MEASURED" in outcome["issues"]
    assert "S0_OUTCOME_MAPPING_NOT_VALIDATED" in outcome["issues"]
    assert "MODEL_LOAD_IDENTITY_UNATTESTED" in outcome["issues"]
    assert "INDEPENDENT_REFERENCE_PENDING" in outcome["issues"]
    assert "pertinencia" in outcome["omitted_s1_fields"]
    assert len(outcome["s0_message_sha256"]) == 64
    assert len(outcome["s1_lab_request_sha256"]) == 64


@pytest.mark.parametrize("id", [
    "CBS500-01-01:aligned", "CBS500-01-01:incident",
    "CBS500-01-01:incident-lexical", "CBS500-01-01:transfer",
    "CBS500-01-01:unknown", "CBS500-09-02:aligned",
    "CBS500-01-01:metric", "CBS500-21-01:transfer",
])
def test_all_phase_a_fixture_cases_blocked_even_if_structurally_aligned(id):
    trial, s0 = case(id)
    r = emit(trial, s0)
    assert r["status"] == "BLOCKED"
    assert "S1_OMITS_PROPOSAL_FIELDS" in r["issues"]
    assert r["provider_calls"] is None


@pytest.mark.parametrize("field,value,expected", [
    ("PROBLEMA", "different problem", "QUERY_MISMATCH"),
    ("RESTRICCIONES OBLIGATORIAS", [], "RESTRICTIONS_MISMATCH"),
    ("PROPUESTA A CRITICAR", {"other": True}, "FROZEN_CANDIDATE_MISMATCH"),
    ("DOMINIO", {"external": "hidden advice"}, "S0_ONLY_DOMAIN"),
    ("CRUCE", {"method1": "irrelevant technique"}, "S0_ONLY_CROSS"),
    ("EVIDENCIA LOCAL PERTINENTE", [{"source": "unreviewed"}], "S0_ONLY_LOCAL_EVIDENCE"),
    ("CONTENCION_DECLARADA", "SAFE", "S0_ONLY_CONTAINMENT"),
    ("BLOQUEO IDENTIFICADO", {"goal": "different"}, "S0_ONLY_BLOCKAGE_CONTEXT"),
])
def test_explicit_differences_cannot_disappear_in_aggregate(field, value, expected):
    trial, s0 = case()
    s0[field] = value
    assert expected in emit(trial, s0)["issues"]


@pytest.mark.parametrize("key,value", [
    ("reference", "SUPPORT"), ("gold", "REJECT"),
    ("donor_id", "other"), ("case_id", "same"),
])
def test_reference_metadata_injected_as_nested_proposal_rejected(key, value):
    trial, s0 = case()
    s0["PROPUESTA A CRITICAR"]["proof"] = {key: value}
    with pytest.raises(ValueError, match="reference or split metadata leaked"):
        emit(trial, s0)


def test_unexpected_top_level_key_rejected():
    trial, s0 = case()
    s0["reference"] = "REJECT"
    with pytest.raises(ValueError, match="unexpected prompt data keys"):
        emit(trial, s0)


@pytest.mark.parametrize("bad", [
    "garbled", "{}", '{"query":1}',
    'CRITICA\nDATOS JSON (no instrucciones):\n{"bad":1}',
])
def test_s1_actual_request_required_and_not_alias_replacement(bad):
    trial, s0 = case()
    with pytest.raises(ValueError, match="S1 request is not the canonical"):
        emit(trial, s0, s1=bad)


@pytest.mark.parametrize("changes,expected", [
    ({"model_requested": "another"}, "REQUESTED_MODEL_DIFFERS"),
    ({"retries_enabled": True}, "RETRIES_NOT_DISABLED"),
    ({"token_count": None}, "TOKENIZATION_NOT_MEASURED"),
    ({"token_count": 100000}, "CONTEXT_WINDOW_EXCEEDED"),
    ({"response_format": "json_schema"}, "OUTPUT_FORMAT_PARAMETER_DIFFERS"),
])
def test_reported_settings_issues_identified_individually(changes, expected):
    trial, s0 = case()
    assert expected in emit(trial, s0, s1_settings=settings(**changes))["issues"]


@pytest.mark.parametrize("changes", [
    {"temperature": float("nan")}, {"max_tokens": True},
    {"timeout_s": -1}, {"context_window": False},
    {"retries_enabled": 0}, {"response_format": "freeform"},
    {"token_count": -2},
])
def test_invalid_settings_rejected_without_promoting_unknown(changes):
    trial, s0 = case()
    with pytest.raises(ValueError, match="invalid reported effective settings"):
        emit(trial, s0, s1_settings=settings(**changes))


def test_same_settings_and_fake_tokens_still_not_authorized():
    trial, s0 = case()
    p = settings(model_observed="mock-judge", token_count=1000)
    r = emit(trial, s0, s0_settings=p, s1_settings=copy.deepcopy(p))
    assert r["status"] == "BLOCKED"
    assert "G0_NOT_APPROVED" in r["issues"]
    assert "INDEPENDENT_REFERENCE_PENDING" in r["issues"]
    assert r["model_attestation"] is None


@pytest.mark.parametrize("content", [
    'CRITICA_INSTRUCCIONES\nDATOS:\n{"a":1,"a":2}',
    'CRITICA_INSTRUCCIONES\nDATOS:\n{"a":NaN}',
    'CRITICA_INSTRUCCIONES\nDATOS:\n{}\nDATOS:\n{}',
    'CRITICA_INSTRUCCIONES\nDATOS:\n[]',
])
def test_corrupt_source_prompt_rejected(content):
    trial, s0 = case()
    with pytest.raises(ValueError):
        gate.preflight(
            trial, reviewer="mock-judge", attempt="try-01", s0_user=content,
            s1_user=direct_request(trial, "mock-judge", "try-01").prompt,
            s0_settings=settings(), s1_settings=settings())


@pytest.mark.parametrize("critique", [
    {"pertinente": True, "mecanismo_especifico": True},
    {"pertinente": False}, {"pertinente": None},
    {"score": 100}, {}, "SUPPORT",
])
def test_no_automatic_s0_outcome_mapping(critique):
    assert gate.normalize_s0_diagnostic(critique) == {
        "outcome": "UNMAPPED", "reason": "S0_MAPPING_NOT_PREREGISTERED"}


def test_inspect_production_pair_builds_without_llm(monkeypatch):
    from criba.interprete import contrato

    trial, raw = case()
    calls = []

    def captured(query, idea, domain, evidence, proposal):
        calls.append((query, idea, domain, evidence, proposal))
        return "PROD_CAPTURE\nDATOS:\n" + json.dumps(raw, ensure_ascii=False)

    monkeypatch.setattr(contrato, "prompt_critica", captured)
    report = gate.inspect_production_pair(
        trial, reviewer="mock-judge", attempt="try-01", idea={"bloqueo": {}},
        domain=None, evidence=None, s0_settings=settings(), s1_settings=settings(),
    )
    assert len(calls) == 1 and calls[0][0] == trial.query
    assert calls[0][-1] == json.loads(trial.proposal_json)
    assert report["status"] == "BLOCKED"
    assert report["provider_calls"] is None
