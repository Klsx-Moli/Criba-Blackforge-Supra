"""Unit tests for the retry ledger.

Uses temporary files — no network, no external state.
"""
from __future__ import annotations

import json

from criba.verification.retry_ledger import (
    RetryLedger,
    SCHEMA_VERSION,
    read_ledger,
)


def test_append_request(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_request(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=1,
        payload={"query": "test"},
    )
    entries = read_ledger(ledger.path)
    assert len(entries) == 1
    e = entries[0]
    assert e["schema_version"] == SCHEMA_VERSION
    assert e["event_type"] == "external_model_request"
    assert e["run_id"] == "run-1"
    assert e["case_id"] == "case-1"
    assert e["model"] == "model-a"
    assert e["attempt"] == 1
    assert "payload_sha256" in e
    assert "Authorization" not in json.dumps(e)
    assert "api_key" not in json.dumps(e).lower()


def test_record_429(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_rate_limited(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=2,
        status_code=429,
        retry_after="30",
    )
    entries = read_ledger(ledger.path)
    assert len(entries) == 1
    e = entries[0]
    assert e["event_type"] == "external_model_rate_limited"
    assert e["status_code"] == 429
    assert e["retry_after"] == "30"
    # No secrets
    assert "Authorization" not in json.dumps(e)


def test_record_response_content_false(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_response(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=1,
        status_code=200,
        finish_reason="stop",
        content_present=False,
    )
    entries = read_ledger(ledger.path)
    assert len(entries) == 1
    e = entries[0]
    assert e["event_type"] == "external_model_response"
    assert e["content_present"] is False
    assert "response_sha256" not in e  # no response to hash
    assert "Authorization" not in json.dumps(e)


def test_record_contract_result_with_error(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_contract_result(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=1,
        contract_ok=False,
        error="UNKNOWN_EVIDENCE:['obs-999']",
        decision="propose",
        evidence_ids=["obs-999"],
    )
    entries = read_ledger(ledger.path)
    assert len(entries) == 1
    e = entries[0]
    assert e["event_type"] == "retrybox_contract_result"
    assert e["contract_ok"] is False
    assert "UNKNOWN_EVIDENCE" in e["error"]


def test_no_secrets_in_ledger(tmp_path):
    ledger = RetryLedger(tmp_path / "ledger.jsonl")
    ledger.record_request(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=1,
        payload={"prompt": "secret api_key=sk-12345 Authorization: Bearer xyz"},
    )
    ledger.record_response(
        run_id="run-1",
        case_id="case-1",
        model="model-a",
        attempt=1,
        content_present=True,
        response={"choices": [{"message": {"content": '{"api_key":"leaked"'}}]},
    )
    entries = read_ledger(ledger.path)
    blob = json.dumps(entries)
    assert "sk-12345" not in blob
    assert "Bearer xyz" not in blob
    assert "api_key" not in blob.lower()
    # Only hashes of payloads/responses should be stored.
    for e in entries:
        if "payload_sha256" in e:
            assert len(e["payload_sha256"]) == 64
        if "response_sha256" in e:
            assert len(e["response_sha256"]) == 64
