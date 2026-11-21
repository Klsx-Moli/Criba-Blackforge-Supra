from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from criba.verification.retrybox_contract import AntiGoodhartViolation, validate_oracle_file, validate_retrybox_response
from criba.verification.retry_ledger import RetryLedger, read_ledger


def case():
    return {"test_case_id": "case-1", "observations": [{"observation_id": "obs-1"}]}


def response(decision="request_more_evidence"):
    return {
        "test_case_id": "case-1", "decision": decision,
        "hypothesis": "provisional" if decision == "propose" else None,
        "evidence_ids": ["obs-1"], "rationale": "Need discrimination",
        "requested_evidence": ["read-only logs"], "proposed_checks": ["compare timelines"],
    }


def oracle():
    return {
        "test_case_id": "case-1", "expected_decision": "request_more_evidence",
        "allowed_evidence_ids": ["obs-1"], "required_evidence_ids": [],
        "expected_requested_evidence": ["logs"], "anti_goodhart": {"must_not_claim_causal_mechanism": True},
    }


@pytest.mark.parametrize("decision", ["request_more_evidence", "propose"])
def test_valid_decisions_still_pass(decision):
    assert validate_retrybox_response(response(decision), case()) is None


@pytest.mark.parametrize("value", ["provisional", "", " ", 0, 1, True, [], {}, ["h"]])
def test_abstention_cannot_hide_hypothesis(value):
    data = response()
    data["hypothesis"] = value
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(data, case())


def test_abstention_must_include_explicit_null_hypothesis():
    data = response()
    del data["hypothesis"]
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(data, case())


@pytest.mark.parametrize("field", ["requested_evidence", "proposed_checks"])
@pytest.mark.parametrize("values", [[""], [" "], [None], [False], [1], [{}], [[]], ["x", "x"]])
def test_list_items_are_unique_nonblank_strings(field, values):
    data = response()
    data[field] = values
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(data, case())


def test_proposal_requires_at_least_one_check():
    data = response("propose")
    data["proposed_checks"] = []
    with pytest.raises(AntiGoodhartViolation, match="PROPOSE_WITHOUT_CHECKS"):
        validate_retrybox_response(data, case())


@pytest.mark.parametrize("decision", [[], {}, ["propose"], set(), None, True])
def test_malformed_decision_has_typed_violation(decision):
    data = response()
    data["decision"] = decision
    with pytest.raises(AntiGoodhartViolation, match="INVALID_DECISION"):
        validate_retrybox_response(data, case())


@pytest.mark.parametrize("value", [None, [], 0, "bad"])
def test_case_must_be_object(value):
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), value)


@pytest.mark.parametrize("value", [None, [], "", " ", True])
def test_case_identity_is_not_optional(value):
    data = response()
    data["test_case_id"] = value
    source = case()
    source["test_case_id"] = value
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(data, source)


@pytest.mark.parametrize("value", [
    None, {}, "obs", [None], [{}], [{"observation_id": []}],
    [{"observation_id": ""}], [{"observation_id": "obs-1"}, {"observation_id": "obs-1"}],
])
def test_malformed_observations_are_rejected(value):
    source = case()
    source["observations"] = value
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), source)


@pytest.mark.parametrize("value", [[], "bad", 1, False])
def test_malformed_runtime_oracle_is_typed(value):
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), case(), value)


@pytest.mark.parametrize("value", [None, [], "bad", 1])
def test_oracle_anti_section_is_object(value):
    source = oracle()
    source["anti_goodhart"] = value
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), case(), source)


@pytest.mark.parametrize("value", ["false", "true", 1, None])
def test_oracle_causal_flag_is_boolean(value):
    source = oracle()
    source["anti_goodhart"]["must_not_claim_causal_mechanism"] = value
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), case(), source)


def test_oracle_cannot_be_applied_to_another_case():
    source = oracle()
    source["test_case_id"] = "case-2"
    with pytest.raises(AntiGoodhartViolation):
        validate_retrybox_response(response(), case(), source)


def write_pair(tmp_path, source=None, reference=None):
    (tmp_path / "case.input.json").write_text(json.dumps(case() if source is None else source), encoding="utf-8")
    target = tmp_path / "case.oracle.json"
    target.write_text(json.dumps(oracle() if reference is None else reference), encoding="utf-8")
    return target


@pytest.mark.parametrize("name", [
    "missing_oracle", "missing_case", "oracle_json", "case_json", "oracle_null",
    "oracle_list", "case_list", "expected_decision", "missing_decision", "allowed_string",
    "allowed_mixed", "allowed_duplicate", "required_string", "empty_request", "request_nonstrings",
    "identity", "duplicate_keys", "nan_constant",
])
def test_oracle_file_returns_false_instead_of_pass_or_crash(tmp_path, name):
    path = write_pair(tmp_path)
    if name == "missing_oracle":
        path.unlink()
    elif name == "missing_case":
        (tmp_path / "case.input.json").unlink()
    elif name == "oracle_json":
        path.write_text("{")
    elif name == "case_json":
        (tmp_path / "case.input.json").write_text("{")
    elif name == "oracle_null":
        path.write_text("null")
    elif name == "oracle_list":
        path.write_text("[]")
    elif name == "case_list":
        (tmp_path / "case.input.json").write_text("[]")
    elif name == "duplicate_keys":
        path.write_text('{"expected_decision":"propose","expected_decision":"request_more_evidence","expected_requested_evidence":["logs"]}')
    elif name == "nan_constant":
        path.write_text('{"expected_decision":"request_more_evidence","expected_requested_evidence":["logs"],"extra":NaN}')
    else:
        ref = oracle()
        if name == "expected_decision":
            ref["expected_decision"] = "maybe"
        elif name == "missing_decision":
            del ref["expected_decision"]
        elif name == "allowed_string":
            ref["allowed_evidence_ids"] = ""
        elif name == "allowed_mixed":
            ref["allowed_evidence_ids"] = [[]]
        elif name == "allowed_duplicate":
            ref["allowed_evidence_ids"] = ["obs-1", "obs-1"]
        elif name == "required_string":
            ref["required_evidence_ids"] = ""
        elif name == "empty_request":
            ref["expected_requested_evidence"] = []
        elif name == "request_nonstrings":
            ref["expected_requested_evidence"] = [False]
        elif name == "identity":
            ref["test_case_id"] = "case-2"
        path.write_text(json.dumps(ref))
    ok, reason = validate_oracle_file(path)
    assert ok is False and isinstance(reason, str) and reason


def test_valid_oracle_file(tmp_path):
    assert validate_oracle_file(write_pair(tmp_path)) == (True, "PASS")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf")])
def test_ledger_never_appends_nonstandard_json(tmp_path, value):
    ledger = RetryLedger(tmp_path / "audit.jsonl")
    ledger.record_request(run_id="r", case_id="c", model="m", attempt=1)
    before = ledger.path.read_bytes()
    with pytest.raises(ValueError):
        ledger.record_rate_limited(run_id="r", case_id="c", model="m", attempt=1, status_code=429, retry_after=value)
    assert ledger.path.read_bytes() == before


@pytest.mark.parametrize("method,field", [
    ("record_response", "content_present"), ("record_contract_result", "contract_ok"),
])
@pytest.mark.parametrize("value", ["false", "true", 0, 1, None])
def test_ledger_boolean_channels_do_not_accept_truthy_values(tmp_path, method, field, value):
    ledger = RetryLedger(tmp_path / "audit.jsonl")
    with pytest.raises(ValueError):
        getattr(ledger, method)(run_id="r", case_id="c", model="m", attempt=1, **{field: value})
    assert not ledger.path.exists()


@pytest.mark.parametrize("secret", [
    "Authorization: Bearer PRIVATE_SENTINEL", "api_key=PRIVATE_SENTINEL",
    "UNKNOWN_EVIDENCE:['PRIVATE_SENTINEL']",
])
def test_arbitrary_contract_error_details_are_hashed_not_written(tmp_path, secret):
    ledger = RetryLedger(tmp_path / "audit.jsonl")
    ledger.record_contract_result(run_id="r", case_id="c", model="m", attempt=1, contract_ok=False, error=secret)
    assert "PRIVATE_SENTINEL" not in ledger.path.read_text()
    data = read_ledger(ledger.path)[0]
    assert len(data["error_sha256"]) == 64
    assert data["error"] in {"REDACTED_ERROR", "UNKNOWN_EVIDENCE"}


@pytest.mark.parametrize("line", [
    "null", "[]", '"text"', "1", "true", '{"n":NaN}', '{"a":1,"a":2}', "{",
])
def test_ledger_reader_rejects_corrupt_or_nonobject_records(tmp_path, line):
    path = tmp_path / "audit.jsonl"
    path.write_text(line + "\n")
    with pytest.raises(ValueError, match="line 1"):
        read_ledger(path)


def test_reader_does_not_hide_directory_as_empty(tmp_path):
    with pytest.raises(OSError):
        read_ledger(tmp_path)


def test_missing_ledger_is_empty(tmp_path):
    assert read_ledger(tmp_path / "absent") == []


def test_read_errors_do_not_repeat_record_secrets(tmp_path):
    path = tmp_path / "audit.jsonl"
    path.write_text('{"PRIVATE_SENTINEL":')
    with pytest.raises(ValueError) as caught:
        read_ledger(path)
    assert "PRIVATE_SENTINEL" not in str(caught.value)


def test_threaded_append_preserves_all_events(tmp_path):
    path = tmp_path / "audit.jsonl"
    def worker(worker_id):
        ledger = RetryLedger(path)
        for attempt in range(1, 81):
            ledger.record_request(run_id=f"worker-{worker_id}", case_id="c", model="m", attempt=attempt)
    with ThreadPoolExecutor(max_workers=8) as pool:
        list(pool.map(worker, range(8)))
    rows = read_ledger(path)
    assert len(rows) == 640
    assert len({(row["run_id"], row["attempt"]) for row in rows}) == 640
