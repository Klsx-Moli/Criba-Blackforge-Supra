"""Anti-Goodhart sentinels: recorded blind-review consensus is not scientific truth."""
from __future__ import annotations

from copy import deepcopy

import pytest

from scripts.evaluate_product_value import SCHEMA, evaluate_pairs


def _manifest() -> dict:
    return {
        "schema": SCHEMA,
        "protocol_sha256": "sha256:" + "e" * 64,
        "cases": [
            {
                "case_id": "water-1", "split": "confirmatory", "domain": "water",
                "arms": {
                    "A": {"system": "CRIBA_SUPRA", "artifact_sha256": "sha256:" + "a" * 64},
                    "B": {"system": "DIRECT_LLM", "artifact_sha256": "sha256:" + "b" * 64},
                },
            },
            {
                "case_id": "other-2", "split": "exploratory", "domain": "energy",
                "arms": {
                    "A": {"system": "DIRECT_LLM", "artifact_sha256": "sha256:" + "c" * 64},
                    "B": {"system": "CRIBA_SUPRA", "artifact_sha256": "sha256:" + "d" * 64},
                },
            },
        ],
    }


def _review(case: str, reviewer: str, choice: str, *, blind: bool = True) -> dict:
    return {
        "case_id": case, "reviewer_id": reviewer, "choice": choice,
        "blind_declared": blind, "evidence_ref": "review-export-123",
    }


def _reviews(*rows) -> dict:
    return {"schema": SCHEMA, "reviews": list(rows)}


def test_absent_review_is_unknown_not_zero_or_win():
    r = evaluate_pairs(_manifest(), _reviews())
    assert r["unresolved"] == 1
    assert r["paired_win_rate"] is None
    assert r["criba_wins"] == r["direct_llm_wins"] == 0
    assert r["scientific_advantage"] == "NOT_ESTABLISHED"


def test_two_blind_declared_reviewers_count_one_descriptive_win():
    r = evaluate_pairs(_manifest(), _reviews(
        _review("water-1", "judge1", "A"),
        _review("water-1", "judge2", "A"),
    ))
    assert r["criba_wins"] == 1
    assert r["paired_win_rate"] == 1.0
    assert r["blinding_verified_independently"] is False
    assert r["preregistration_verified"] is False
    assert r["scientific_advantage"] == "NOT_ESTABLISHED"


def test_disagreement_and_abstention_remain_unknown():
    for alternative in ("B", "ABSTAIN"):
        r = evaluate_pairs(_manifest(), _reviews(
            _review("water-1", "judge1", "A"),
            _review("water-1", "judge2", alternative),
        ))
        assert r["unresolved"] == 1
        assert r["paired_win_rate"] is None


def test_unblinded_review_cannot_be_promoted_to_win():
    r = evaluate_pairs(_manifest(), _reviews(
        _review("water-1", "judge1", "A"),
        _review("water-1", "judge2", "A", blind=False),
    ))
    assert r["unresolved"] == 1
    assert r["criba_wins"] == 0


def test_exploratory_cases_never_enter_confirmatory_numerator():
    r = evaluate_pairs(_manifest(), _reviews(
        _review("other-2", "judge1", "B"),
        _review("other-2", "judge2", "B"),
    ))
    assert r["confirmatory_count"] == 1
    assert r["cases"][1]["status"] == "EXPLORATORY_NOT_SCORED"
    assert r["paired_win_rate"] is None


def test_losing_to_direct_llm_is_recorded_not_relabelled():
    r = evaluate_pairs(_manifest(), _reviews(
        _review("water-1", "judge1", "B"),
        _review("water-1", "judge2", "B"),
    ))
    assert r["criba_wins"] == 0
    assert r["direct_llm_wins"] == 1
    assert r["paired_win_rate"] == 0.0


def test_tie_is_not_a_win_for_either_side():
    r = evaluate_pairs(_manifest(), _reviews(
        _review("water-1", "judge1", "TIE"),
        _review("water-1", "judge2", "TIE"),
    ))
    assert r["ties"] == 1
    assert r["paired_win_rate"] is None


@pytest.mark.parametrize("mutation", ["duplicate", "same_system", "same_artifact", "duplicate_pair", "bad_sha", "bad_split", "fake_missing"])
def test_invalid_or_padded_pair_is_rejected(mutation):
    m = _manifest()
    a = m["cases"][0]
    b = m["cases"][1]
    if mutation == "duplicate":
        b["case_id"] = a["case_id"]
    elif mutation == "same_system":
        a["arms"]["B"]["system"] = "CRIBA_SUPRA"
    elif mutation == "same_artifact":
        a["arms"]["B"]["artifact_sha256"] = a["arms"]["A"]["artifact_sha256"]
    elif mutation == "duplicate_pair":
        b["arms"]["A"]["artifact_sha256"] = a["arms"]["B"]["artifact_sha256"]
        b["arms"]["B"]["artifact_sha256"] = a["arms"]["A"]["artifact_sha256"]
    elif mutation == "bad_sha":
        a["arms"]["A"]["artifact_sha256"] = "sha256:xyz"
    elif mutation == "bad_split":
        a["split"] = "holdout-not-registered"
    else:
        del a["arms"]["A"]
    with pytest.raises(ValueError):
        evaluate_pairs(m, _reviews())


@pytest.mark.parametrize("mutation", ["same_reviewer", "bad_choice", "unknown_case", "unblinded_not_bool", "missing_evidence", "leak"])
def test_invalid_review_fails_closed(mutation):
    rows = [_review("water-1", "judge1", "A"), _review("water-1", "judge2", "A")]
    if mutation == "same_reviewer":
        rows[1]["reviewer_id"] = "judge1"
    elif mutation == "bad_choice":
        rows[1]["choice"] = "CRIBA"
    elif mutation == "unknown_case":
        rows[1]["case_id"] = "unknown-3"
    elif mutation == "unblinded_not_bool":
        rows[1]["blind_declared"] = "true"
    elif mutation == "missing_evidence":
        rows[1]["evidence_ref"] = ""
    else:
        rows[1]["system"] = "CRIBA_SUPRA"
    with pytest.raises(ValueError):
        evaluate_pairs(_manifest(), _reviews(*rows))


def test_order_of_reviews_does_not_change_outcome():
    rows = [_review("water-1", "j2", "A"), _review("water-1", "j1", "A")]
    a = evaluate_pairs(_manifest(), _reviews(*rows))
    b = evaluate_pairs(deepcopy(_manifest()), _reviews(*reversed(rows)))
    assert a == b
