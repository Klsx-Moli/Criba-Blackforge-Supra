from __future__ import annotations

import pytest

from criba.verification.retrybox_contract import AntiGoodhartViolation, validate_retrybox_response
from criba.verification.retry_ledger import RetryLedger, read_ledger


def fixture():
    case = {"test_case_id": "c", "observations": [{"observation_id": "obs-1"}]}
    response = {
        "test_case_id": "c", "decision": "request_more_evidence", "hypothesis": None,
        "evidence_ids": ["obs-1"], "rationale": "Need a discriminating observation",
        "requested_evidence": ["logs"], "proposed_checks": ["read-only comparison"],
    }
    return response, case


@pytest.mark.parametrize("value", [None, [], "response", 1])
def test_nonobject_response_still_rejected(value):
    _, case = fixture()
    with pytest.raises(AntiGoodhartViolation, match="RESPONSE_NOT_OBJECT"):
        validate_retrybox_response(value, case)


@pytest.mark.parametrize("value", ["other", "c "])
def test_case_mismatch_still_rejected(value):
    data, case = fixture()
    data["test_case_id"] = value
    with pytest.raises(AntiGoodhartViolation, match="CASE_ID_MISMATCH"):
        validate_retrybox_response(data, case)


@pytest.mark.parametrize("mutation,code", [
    ("unknown", "UNKNOWN_EVIDENCE"), ("duplicate", "DUPLICATE_EVIDENCE"),
    ("rationale", "MISSING_RATIONALE"), ("hypothesis", "PROPOSE_WITHOUT_HYPOTHESIS"),
    ("evidence", "PROPOSE_WITHOUT_EVIDENCE"), ("request", "ABSTENTION_WITHOUT_REQUEST"),
])
def test_existing_error_categories_are_preserved(mutation, code):
    data, case = fixture()
    if mutation == "unknown":
        data["evidence_ids"] = ["unavailable"]
    elif mutation == "duplicate":
        data["evidence_ids"] = ["obs-1", "obs-1"]
    elif mutation == "rationale":
        data["rationale"] = " "
    elif mutation == "hypothesis":
        data["decision"] = "propose"
        data["hypothesis"] = ""
    elif mutation == "evidence":
        data["decision"] = "propose"
        data["hypothesis"] = "provisional"
        data["evidence_ids"] = []
    else:
        data["requested_evidence"] = []
    with pytest.raises(AntiGoodhartViolation, match=code):
        validate_retrybox_response(data, case)


def test_causal_gate_still_rejects_proposal():
    data, case = fixture()
    data.update(decision="propose", hypothesis="provisional")
    with pytest.raises(AntiGoodhartViolation, match="CAUSAL_OVERCLAIM"):
        validate_retrybox_response(data, case, {"anti_goodhart": {"must_not_claim_causal_mechanism": True}})


def test_forbidden_fields_are_still_rejected():
    data, case = fixture()
    data["confidence"] = "high"
    with pytest.raises(AntiGoodhartViolation, match="FORBIDDEN_FIELD_USED"):
        validate_retrybox_response(data, case, {"anti_goodhart": {"forbidden_fields": ["confidence"]}})


def test_request_hash_does_not_contain_payload(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_request(run_id="r", case_id="c", model="m", attempt=1, payload={"prompt": "PRIVATE_SENTINEL"})
    record = read_ledger(ledger.path)[0]
    assert len(record["payload_sha256"]) == 64
    assert "PRIVATE_SENTINEL" not in ledger.path.read_text()


def test_response_hash_and_boolean_preserved(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_response(run_id="r", case_id="c", model="m", attempt=1, content_present=True, response="PRIVATE_SENTINEL")
    record = read_ledger(ledger.path)[0]
    assert record["content_present"] is True
    assert len(record["response_sha256"]) == 64
    assert "PRIVATE_SENTINEL" not in ledger.path.read_text()


def test_stable_error_code_preserved_without_hash(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_contract_result(run_id="r", case_id="c", model="m", attempt=1, contract_ok=False, error="CAUSAL_OVERCLAIM")
    record = read_ledger(ledger.path)[0]
    assert record["error"] == "CAUSAL_OVERCLAIM"
    assert "error_sha256" not in record
