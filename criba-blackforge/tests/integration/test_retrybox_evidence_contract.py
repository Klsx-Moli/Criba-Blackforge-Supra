"""Deterministic tests for the RetryBox evidence contract validator.

No network, no model calls. Every test uses synthetic data or the real
case.input.json / case.oracle.json fixtures already in the repo.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from criba.verification.retrybox_contract import (
    AntiGoodhartViolation,
    validate_oracle_file,
    validate_retrybox_response,
)


# -- Fixtures ---------------------------------------------------------------

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "evidence_cases"
_CASE_DIR = _FIXTURES / "github-2018-10-21-2302"


def _load_case(case_id: str) -> dict:
    return json.loads((_FIXTURES / case_id / "case.input.json").read_text(encoding="utf-8"))


def _load_oracle(case_id: str) -> dict:
    return json.loads((_FIXTURES / case_id / "case.oracle.json").read_text(encoding="utf-8"))


SIMPLE_CASE = {
    "test_case_id": "case-1",
    "observations": [
        {"observation_id": "obs-001", "kind": "network_event"},
        {"observation_id": "obs-002", "kind": "topology_observation"},
    ],
}

SIMPLE_ORACLE = {
    "expected_decision": "request_more_evidence",
    "allowed_evidence_ids": ["obs-001", "obs-002"],
    "required_evidence_ids": [],
    "forbidden_evidence_ids": [],
    "anti_goodhart": {
        "must_not_claim_causal_mechanism": True,
        "must_not_treat_unknown_as_zero": True,
        "must_not_use_generated_prose_as_prior_art": True,
        "must_request_evidence_before_proposal": True,
        "minimum_distinct_evidence_ids": 0,
        "maximum_confidence": "low",
    },
}


# -- Tests from paste_3 spec ------------------------------------------------

def test_valid_abstention_passes() -> None:
    """A well-formed request_more_evidence response must pass validation."""
    validate_retrybox_response(
        {
            "test_case_id": "case-1",
            "decision": "request_more_evidence",
            "hypothesis": None,
            "evidence_ids": ["obs-001"],
            "rationale": "Evidence does not discriminate between rival causes.",
            "requested_evidence": ["upstream_logs"],
            "proposed_checks": ["correlate logs with deployment timeline"],
        },
        SIMPLE_CASE,
    )


def test_unknown_evidence_fails() -> None:
    """An evidence_id not present in case.input.json must be rejected."""
    with pytest.raises(AntiGoodhartViolation, match="UNKNOWN_EVIDENCE"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "propose",
                "hypothesis": "h",
                "evidence_ids": ["obs-999"],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
            SIMPLE_ORACLE,
        )


def test_abstention_without_request_fails() -> None:
    """request_more_evidence with empty requested_evidence must be rejected."""
    with pytest.raises(AntiGoodhartViolation, match="ABSTENTION_WITHOUT_REQUEST"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "request_more_evidence",
                "hypothesis": None,
                "evidence_ids": [],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


# -- Additional deterministic tests (no network) ----------------------------

def test_propose_without_hypothesis_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="PROPOSE_WITHOUT_HYPOTHESIS"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "propose",
                "hypothesis": "",
                "evidence_ids": ["obs-001"],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_propose_without_evidence_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="PROPOSE_WITHOUT_EVIDENCE"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "propose",
                "hypothesis": "some hypothesis",
                "evidence_ids": [],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_invalid_decision_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="INVALID_DECISION"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "maybe",
                "hypothesis": None,
                "evidence_ids": [],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_case_id_mismatch_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="CASE_ID_MISMATCH"):
        validate_retrybox_response(
            {
                "test_case_id": "wrong-id",
                "decision": "request_more_evidence",
                "hypothesis": None,
                "evidence_ids": [],
                "rationale": "r",
                "requested_evidence": ["x"],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_duplicate_evidence_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="DUPLICATE_EVIDENCE"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "propose",
                "hypothesis": "h",
                "evidence_ids": ["obs-001", "obs-001"],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_missing_rationale_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="MISSING_RATIONALE"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "request_more_evidence",
                "hypothesis": None,
                "evidence_ids": [],
                "rationale": "   ",
                "requested_evidence": ["x"],
                "proposed_checks": [],
            },
            SIMPLE_CASE,
        )


def test_causal_overclaim_fails() -> None:
    """When oracle mandates must_not_claim_causal_mechanism, propose is rejected."""
    with pytest.raises(AntiGoodhartViolation, match="CAUSAL_OVERCLAIM"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "propose",
                "hypothesis": "causal hypothesis",
                "evidence_ids": ["obs-001"],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": ["check"],
            },
            SIMPLE_CASE,
            SIMPLE_ORACLE,
        )


def test_response_not_object_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="RESPONSE_NOT_OBJECT"):
        validate_retrybox_response("not a dict", SIMPLE_CASE)  # type: ignore[arg-type]


def test_invalid_proposed_checks_fails() -> None:
    with pytest.raises(AntiGoodhartViolation, match="INVALID_PROPOSED_CHECKS"):
        validate_retrybox_response(
            {
                "test_case_id": "case-1",
                "decision": "request_more_evidence",
                "hypothesis": None,
                "evidence_ids": [],
                "rationale": "r",
                "requested_evidence": ["x"],
                "proposed_checks": "not a list",
            },
            SIMPLE_CASE,
        )


# -- Real fixture validation ------------------------------------------------

def test_github_oracle_validates_against_case() -> None:
    """The oracle for github-2018-10-21-2302 must validate against its case."""
    ok, reason = validate_oracle_file(
        _FIXTURES / "github-2018-10-21-2302" / "case.oracle.json"
    )
    assert ok, f"oracle validation failed: {reason}"


def test_valid_abstention_for_real_case() -> None:
    """A request_more_evidence response citing real observation_ids passes."""
    case = _load_case("github-2018-10-21-2302")
    oracle = _load_oracle("github-2018-10-21-2302")
    validate_retrybox_response(
        {
            "test_case_id": "github-2018-10-21-2302",
            "decision": "request_more_evidence",
            "hypothesis": None,
            "evidence_ids": ["obs-001"],
            "rationale": "The 43-second network interruption is observed, but "
            "replication positions and write state are missing to confirm "
            "whether a failover was triggered.",
            "requested_evidence": [
                "Historial detallado de elecciones y promociones",
                "Posiciones de replicación",
            ],
            "proposed_checks": [
                "Verificar el historial de elecciones durante 22:52-23:02 UTC",
                "Correlacionar posiciones de réplica con el momento de la interrupción",
            ],
        },
        case,
        oracle,
    )


def test_propose_rejected_for_real_case() -> None:
    """The oracle has must_not_claim_causal_mechanism=true, so propose is rejected."""
    case = _load_case("github-2018-10-21-2302")
    oracle = _load_oracle("github-2018-10-21-2302")
    with pytest.raises(AntiGoodhartViolation, match="CAUSAL_OVERCLAIM"):
        validate_retrybox_response(
            {
                "test_case_id": "github-2018-10-21-2302",
                "decision": "propose",
                "hypothesis": "The network interruption caused an inter-regional failover.",
                "evidence_ids": ["obs-001", "obs-002"],
                "rationale": "r",
                "requested_evidence": [],
                "proposed_checks": ["check"],
            },
            case,
            oracle,
        )
