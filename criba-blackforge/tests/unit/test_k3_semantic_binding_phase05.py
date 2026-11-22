"""Experimental proof that lab request identity must bind the actual critique prompt.

No model call, no reference labels sent to a reviewer, no scientific promotion.
The production-contract module is a temporary seam ONLY in isolated sandbox;
in a real checkout these tests import the original production contract.
"""
from __future__ import annotations

import pytest

from benchmarks.innovation import semantic_critic_bridge as bridge
from benchmarks.innovation.semantic_cases import cases, trial_for
from benchmarks.innovation.semantic_lab import (
    blind_request,
    canonical,
    direct_request,
    evaluate,
    read_current,
)


def _inputs(trial):
    return dict(query=trial.query, idea={}, domain=None, evidence=None,
                propuesta={}, reviewer="mock-reviewer", attempt="attempt-01")


def test_unmatched_direct_request_cannot_get_a_claimed_lab_receipt():
    trial = trial_for("CBS500-01-01:incident", "phase05")
    req = direct_request(trial, "mock-reviewer", "attempt-01")
    actual = bridge.mensaje_de_critica(**{
        k: v for k, v in _inputs(trial).items()
        if k in {"query", "idea", "domain", "evidence", "propuesta"}
    })
    assert actual[1]["content"] != req.prompt
    with pytest.raises(ValueError, match="critica_no_vinculada"):
        bridge.preparar_critica(trial, **_inputs(trial))
    assert bridge.request_sha_de_critica(
        trial, reviewer="mock-reviewer", attempt="attempt-01"
    ) == req.sha256


def test_blind_bridge_does_not_dispatch_query_bearing_production_prompt():
    trial = trial_for("CBS500-01-01:incident", "phase05")
    query = trial.query
    msgs = bridge.mensaje_de_critica(**{
        k: v for k, v in _inputs(trial).items()
        if k in {"query", "idea", "domain", "evidence", "propuesta"}
    })
    assert query in msgs[1]["content"]
    assert query not in blind_request(trial, "mock-reviewer", "attempt-01").prompt
    with pytest.raises(ValueError, match="critica_no_vinculada"):
        bridge.preparar_critica(trial, stage="BLIND", **_inputs(trial))


@pytest.mark.parametrize("case_id", [
    "CBS500-01-01:incident", "CBS500-01-01:incident-lexical",
    "CBS500-01-01:aligned", "CBS500-01-01:transfer",
    "CBS500-09-02:aligned", "CBS500-21-01:metric",
])
def test_development_cases_cannot_silently_claim_prod_equals_lab(case_id):
    trial = trial_for(case_id, "phase05")
    with pytest.raises(ValueError, match="critica_no_vinculada"):
        bridge.preparar_critica(trial, **_inputs(trial))


def test_valid_exact_lab_prompt_binding_is_still_possible(monkeypatch):
    trial = trial_for("CBS500-01-01:transfer", "phase05")
    lab = direct_request(trial, "mock-reviewer", "attempt-01")
    monkeypatch.setattr(
        bridge, "mensaje_de_critica", lambda **kw: bridge.mensaje_compuesto(lab.prompt)
    )
    call = bridge.preparar_critica(trial, **_inputs(trial))
    assert call.request_sha256 == lab.sha256
    assert call.mensajes[1]["content"] == lab.prompt
    assert call.message_sha256 == bridge.sha_mensaje_compuesto(call.mensajes)
    assert call.stage == "DIRECT"


def test_aligned_blind_prompt_is_possible_without_destination(monkeypatch):
    trial = trial_for("CBS500-01-01:incident", "phase05")
    lab = blind_request(trial, "mock-reviewer", "attempt-01")
    monkeypatch.setattr(
        bridge, "mensaje_de_critica", lambda **kw: bridge.mensaje_compuesto(lab.prompt)
    )
    call = bridge.preparar_critica(trial, stage="BLIND", **_inputs(trial))
    assert call.request_sha256 == lab.sha256
    assert trial.query not in call.mensajes[1]["content"]


def test_changing_current_trial_breaks_exact_message_binding(monkeypatch):
    trial = trial_for("CBS500-01-01:incident", "phase05")
    lab = direct_request(trial, "mock-reviewer", "attempt-01")
    monkeypatch.setattr(
        bridge, "mensaje_de_critica", lambda **kw: bridge.mensaje_compuesto(lab.prompt)
    )
    altered = trial_for("CBS500-09-02:aligned", "phase05")
    with pytest.raises(ValueError, match="critica_no_vinculada"):
        bridge.preparar_critica(altered, **_inputs(altered))


def test_unexpected_stage_does_not_fallback():
    trial = trial_for("CBS500-01-01:aligned", "phase05")
    with pytest.raises(ValueError, match="stage no soportado"):
        bridge.preparar_critica(trial, stage="COMPARE", **_inputs(trial))


def test_literal_quotes_do_not_prove_truth_on_known_negative():
    case = "CBS500-01-01:incident"
    trial = trial_for(case, "phase05")
    assert next(c["reference"] for c in cases() if c["id"] == case) == "REJECT"
    req = direct_request(trial, "mock-reviewer", "attempt-01")
    projection = trial.proposal

    def fake_vote(source, field):
        return {
            "assessment": "SUPPORTS", "reason": "a confident but wrong assertion",
            "source_quote": source, "proposal_field": field,
            "proposal_quote": projection[field][:16],
        }

    body = {
        "axes": {"objective": fake_vote(trial.query[:16], "mechanism"),
                 "mechanism": fake_vote(trial.query[:16], "mechanism"),
                 "metric": fake_vote(trial.query[:16], "metric")},
        "restrictions": {r: fake_vote(r, "mechanism") for r in trial.restrictions},
    }
    raw = canonical({"request_sha256": req.sha256, "observed_model": req.reviewer,
                     "transport_id": "fake-synthetic", "finish_reason": "stop", "body": body})
    review = evaluate(trial, req, raw)
    assert review["outcome"] == "REVIEW_SUPPORTED"
    assert review["reason"] == "evaluator assertion only"
    reading = read_current(trial, reviewer=req.reviewer, attempt=req.attempt,
                           current_request_sha256=req.sha256, raw=raw)
    assert reading.disposition == "CAUSALLY_ARGUED_CANDIDATE"
    with pytest.raises(TypeError):
        bool(reading)
    assert "score" not in vars(reading) and "reward" not in vars(reading)


def test_keyword_padding_keeps_wrong_mechanism_wrong_in_reference():
    negatives = [r for r in cases() if r["id"].startswith("CBS500-01-01:incident")]
    assert {r["reference"] for r in negatives} == {"REJECT"}
    assert all("registro" in r["proposal"]["mecanismo"] for r in negatives)
    assert all("ducha" in r["query"] for r in negatives)


def test_call_message_snapshot_cannot_be_rewritten_after_hash(monkeypatch):
    trial = trial_for("CBS500-01-01:transfer", "phase05")
    lab = direct_request(trial, "mock-reviewer", "attempt-01")
    monkeypatch.setattr(
        bridge, "mensaje_de_critica", lambda **kw: bridge.mensaje_compuesto(lab.prompt)
    )
    call = bridge.preparar_critica(trial, **_inputs(trial))
    mutable_view = call.mensajes
    mutable_view[1]["content"] = "TAMPER AFTER HASH"
    assert call.mensajes[1]["content"] == lab.prompt
    assert call.message_sha256 == bridge.sha_mensaje_compuesto(call.mensajes)
    assert bridge.sha_mensaje_compuesto(mutable_view) != call.message_sha256
    # The caller still has to bind the final transport payload at dispatch;
    # this accessor only prevents silent mutation of the recorded snapshot.
