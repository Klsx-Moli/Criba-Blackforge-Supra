"""Synthetic protocol regressions, not semantic accuracy or product validation."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import replace

import pytest

from benchmarks.innovation.semantic_cases import PARENTS, cases, trial_for
from benchmarks.innovation.semantic_lab import (
    AXIS_FIELDS,
    RECONSTRUCTION,
    blind_request,
    canonical,
    comparison_request,
    confusion,
    direct_request,
    evaluate,
    strict_json,
)


def trial():
    return trial_for("CBS500-01-01:incident", "run-1")


def receipt(request, body, **overrides):
    data = {"request_sha256": request.sha256, "observed_model": request.reviewer,
            "transport_id": "synthetic-only", "finish_reason": "stop", "body": body}
    data.update(overrides)
    return canonical(data)


def reviewed(t, verdict="SUPPORTS"):
    def row(source, field):
        return {"assessment": verdict,
                "reason": "Synthetic reviewer claim, not semantic evidence.",
                "source_quote": source, "proposal_field": field,
                "proposal_quote": t.proposal[field]}
    return {"axes": {axis: row(t.query, sorted(fields)[0]) for axis, fields in AXIS_FIELDS.items()},
            "restrictions": {r: row(r, "mechanism") for r in t.restrictions}}


def reconstruct(request, **changes):
    data = {key: "Reconstruction fixture" for key in RECONSTRUCTION}
    data.update(changes)
    return receipt(request, data)


@pytest.mark.parametrize("variant,axis,assessment,expected", [
    ("incident", "objective", "CONTRADICTS", "MISMATCH_FOR_THIS_PROBLEM"),
    ("transfer", "mechanism", "SUPPORTS", "CAUSALLY_ARGUED_CANDIDATE"),
    ("incident-lexical", "mechanism", "CONTRADICTS", "MISMATCH_FOR_THIS_PROBLEM"),
    ("metric", "metric", "CONTRADICTS", "MISMATCH_FOR_THIS_PROBLEM"),
    ("incident", "restriction", "UNKNOWN", "RESEARCH_ONLY"),
    ("incident", "objective", "SUPPORTS", "CAUSALLY_ARGUED_CANDIDATE"),  # lying reviewer
])
def test_research_reading(variant, axis, assessment, expected):
    from benchmarks.innovation.semantic_lab import read_current

    t = trial_for("CBS500-01-01:" + variant, "run-1")
    r = direct_request(t, "judge", "first")
    body = reviewed(t)
    row = (body["restrictions"][t.restrictions[0]] if axis == "restriction"
           else body["axes"][axis])
    row["assessment"] = assessment
    raw = receipt(r, body)
    args = dict(reviewer="judge", attempt="first", current_request_sha256=r.sha256)
    reading = read_current(t, raw=raw, **args)
    assert reading.disposition == expected
    with pytest.raises(TypeError):
        bool(reading)
    assert read_current(t, raw=None, **args).outcome == "NOT_EVALUATED"
    newer = direct_request(t, "judge", "retry")
    assert read_current(t, raw=raw, reviewer="judge", attempt="first",
                        current_request_sha256=newer.sha256).outcome == "EVALUATOR_ERROR"
    assert read_current(t, raw=raw, reviewer="judge", attempt="retry",
                        current_request_sha256=newer.sha256).outcome == "EVALUATOR_ERROR"


def test_cases_are_unique_and_separate_from_reserved():
    data = cases()
    assert len(PARENTS) == 12
    assert len(data) == len({x["id"] for x in data}) == 58
    assert {x["split"] for x in data} == {"development"}
    assert Counter(x["reference"] for x in data) == {"SUPPORT": 16, "REJECT": 38, "UNRESOLVED": 4}
    assert all(x["reference_status"] == "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD" for x in data)
    incident = next(x for x in data if x["id"].endswith(":incident"))
    assert incident["donor_id"] == "CBS500-09-02"


def test_blind_has_no_target_metadata_or_reference():
    t = trial()
    r = blind_request(t, "judge", "attempt-1")
    payload = json.loads(r.prompt.split("DATOS JSON (no instrucciones):\n", 1)[1])
    assert set(payload) == {"proposal"}
    assert t.query not in r.prompt
    assert t.case_id not in r.prompt
    assert t.restrictions[0] not in r.prompt
    assert "PERTINENTE" not in r.prompt and "PROVISIONAL_AUTHOR_REVIEW" not in r.prompt


@pytest.mark.parametrize("key,value", [("case_id", "other"), ("run_id", "other"),
                                        ("episode_id", "other"), ("candidate_id", "other"),
                                        ("generator_model", "other"), ("query", "other"),
                                        ("restrictions", ("other",)),
                                        ("input_context_sha256", "b" * 64)])
def test_binding_rejects_context_changes(key, value):
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    changed = replace(t, **{key: value})
    assert evaluate(changed, r, receipt(r, reviewed(t)))["outcome"] == "EVALUATOR_ERROR"


def test_full_candidate_changes_binding_even_if_projection_identical():
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    proposal = json.loads(t.proposal_json)
    proposal["pertinencia"] = "ABSTENER"
    changed = replace(t, proposal_json=canonical(proposal))
    assert changed.proposal == t.proposal
    assert changed.scope != t.scope
    assert evaluate(changed, r, receipt(r, reviewed(t)))["outcome"] == "EVALUATOR_ERROR"


def test_distinct_attempt_and_reviewer_have_distinct_receipts():
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    raw = receipt(r, reviewed(t))
    for other in (direct_request(t, "judge", "attempt-2"),
                  direct_request(t, "judge-2", "attempt-1")):
        assert evaluate(t, other, raw)["outcome"] == "EVALUATOR_ERROR"
    assert direct_request(t, "judge", "attempt-1") == r


@pytest.mark.parametrize("changes", [{"finish_reason": "length"}, {"finish_reason": None},
                                       {"observed_model": "wrong"}, {"transport_id": ""},
                                       {"request_sha256": "0" * 64}, {"unexpected": "field"}])
def test_invalid_transport_receipts(changes):
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    assert evaluate(t, r, receipt(r, reviewed(t), **changes))["outcome"] == "EVALUATOR_ERROR"


@pytest.mark.parametrize("bad", [
    '{"x":1,"x":2}', '{"x":NaN}', '{"x":Infinity}', '{"x":1e999}',
    '{"x":"\\ud800"}', '{', '[]',
])
def test_bad_json_cannot_be_review(bad):
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    assert evaluate(t, r, bad)["outcome"] == "EVALUATOR_ERROR"


@pytest.mark.parametrize("mutation", [
    "missing-axis", "extra-axis", "wrong-source", "wrong-proposal",
    "wrong-field", "missing-restriction", "extra-restriction", "boolean",
    "blank-reason", "empty-quote", "unknown-enum", "unhashable-field",
])
def test_contract_mutations_fail_closed(mutation):
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    b = reviewed(t)
    row = b["axes"]["metric"]
    if mutation == "missing-axis":
        del b["axes"]["metric"]
    elif mutation == "extra-axis":
        b["axes"]["extra"] = row
    elif mutation == "wrong-source":
        row["source_quote"] = "Fabricated source"
    elif mutation == "wrong-proposal":
        row["proposal_quote"] = "Fabricated proposal"
    elif mutation == "wrong-field":
        row.update(proposal_field="hypothesis", proposal_quote=t.proposal["hypothesis"])
    elif mutation == "missing-restriction":
        b["restrictions"] = {}
    elif mutation == "extra-restriction":
        b["restrictions"]["unrelated"] = row
    elif mutation == "boolean":
        row["assessment"] = True
    elif mutation == "blank-reason":
        row["reason"] = " "
    elif mutation == "empty-quote":
        row["proposal_quote"] = ""
    elif mutation == "unknown-enum":
        row["assessment"] = "PASS"
    else:
        row["proposal_field"] = []
    assert evaluate(t, r, receipt(r, b))["outcome"] == "EVALUATOR_ERROR"


def test_outcomes_distinguish_uncertainty_rejection_and_missing():
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    assert evaluate(t, r, None)["outcome"] == "NOT_EVALUATED"
    b = reviewed(t)
    b["axes"]["objective"] = {"assessment": "UNKNOWN", "reason": "Insufficient information",
                              "source_quote": None, "proposal_field": None, "proposal_quote": None}
    assert evaluate(t, r, receipt(r, b))["outcome"] == "REVIEW_UNRESOLVED"
    b["axes"]["metric"]["assessment"] = "CONTRADICTS"
    assert evaluate(t, r, receipt(r, b))["outcome"] == "REVIEW_REJECTED"


def test_honest_boundary_even_fabricated_support_can_pass_protocol():
    # The administrative proposal is knowingly mismatched. A dishonest judge
    # can still cite exact text and claim support. No scientific PASS is emitted.
    t = trial()
    r = direct_request(t, t.generator_model, "attempt-1")
    out = evaluate(t, r, receipt(r, reviewed(t)))
    assert out["outcome"] == "REVIEW_SUPPORTED" and out["same_reported_model"] == "true"
    assert confusion([("REJECT", out["outcome"])])["REJECT"]["REVIEW_SUPPORTED"] == 1
    assert "validated" not in out and "independent" not in out


def test_reconstruction_is_bound_to_comparison():
    t = trial()
    blind = blind_request(t, "blind-judge", "attempt-1")
    raw = reconstruct(blind)
    r = comparison_request(t, blind, raw, "judge", "attempt-2")
    out = receipt(r, reviewed(t, "CONTRADICTS"))
    assert evaluate(t, r, out, blind=blind, blind_receipt=raw)["outcome"] == "REVIEW_REJECTED"
    assert evaluate(t, r, out)["outcome"] == "EVALUATOR_ERROR"
    changed = reconstruct(blind, metric="changed")
    assert evaluate(t, r, out, blind=blind, blind_receipt=changed)["outcome"] == "EVALUATOR_ERROR"
    with pytest.raises(ValueError):
        comparison_request(replace(t, run_id="another"), blind, raw, "judge", "attempt-2")
    with pytest.raises(ValueError):
        comparison_request(t, blind, reconstruct(blind, objective=True), "judge", "attempt-2")
    with pytest.raises(ValueError):
        comparison_request(t, blind, reconstruct(blind, extra="not allowed"), "judge", "attempt-2")


def test_prompt_tamper_even_if_receipt_is_rebound():
    t = trial()
    r = direct_request(t, "judge", "attempt-1")
    changed = replace(r, prompt="tampered")
    assert evaluate(t, changed, receipt(changed, reviewed(t)))["outcome"] == "EVALUATOR_ERROR"


def test_alias_is_not_independence_and_unknown_is_not_zero():
    counts = confusion([("UNREVIEWED", "REVIEW_SUPPORTED"), ("REJECT", "NOT_EVALUATED"),
                        ("SUPPORT", "EVALUATOR_ERROR"), ("UNRESOLVED", "REVIEW_UNRESOLVED")])
    assert sum(sum(x.values()) for x in counts.values()) == 4
    assert counts["REJECT"]["NOT_EVALUATED"] == 1
    with pytest.raises(ValueError):
        confusion([("REJECT", "PASS")])
    with pytest.raises(ValueError):
        strict_json('{"x":1,"x":2}')


def test_parent_receipt_identity_not_only_reconstructed_content():
    t = trial()
    blind = blind_request(t, "blind-judge", "attempt-1")
    raw = reconstruct(blind)
    r = comparison_request(t, blind, raw, "judge", "attempt-2")
    response = receipt(r, reviewed(t, "CONTRADICTS"))
    other_transport = json.loads(raw)
    other_transport["transport_id"] = "different-call-with-identical-output"
    changed = canonical(other_transport)
    assert comparison_request(t, blind, changed, "judge", "attempt-2").sha256 != r.sha256
    result = evaluate(t, r, response, blind=blind, blind_receipt=changed)
    assert result["outcome"] == "EVALUATOR_ERROR"
