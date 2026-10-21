"""Append-only retry ledger for external model interactions.

JSON Lines format. Each line is a self-contained JSON object with
schema_version, timestamp, and event-specific fields.

Security: never logs Authorization headers, API keys, or full prompts.
Sensitive strings are hashed (SHA-256) before recording.

Default path: artifacts/retry_ledger.jsonl
Override via CRIBA_RETRY_LEDGER_PATH env var.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "retry_ledger.v1"

_EVENT_FIELDS = {
    "external_model_request": [
        "schema_version", "recorded_at_unix", "run_id", "case_id",
        "model", "attempt", "payload_sha256",
    ],
    "external_model_rate_limited": [
        "schema_version", "recorded_at_unix", "run_id", "case_id",
        "model", "attempt", "status_code", "retry_after",
    ],
    "external_model_response": [
        "schema_version", "recorded_at_unix", "run_id", "case_id",
        "model", "attempt", "status_code", "finish_reason",
        "content_present", "response_sha256",
    ],
    "retrybox_contract_result": [
        "schema_version", "recorded_at_unix", "run_id", "case_id",
        "model", "attempt", "contract_ok", "error",
    ],
}


class RetryLedger:
    """Append-only JSON Lines ledger for tracking external model retries and contract results."""

    def __init__(self, path: str | Path | None = None) -> None:
        env_path = os.environ.get("CRIBA_RETRY_LEDGER_PATH")
        self.path = Path(path) if path else (
            Path(env_path) if env_path else Path("artifacts/retry_ledger.jsonl")
        )

    def _append(self, event: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(event, ensure_ascii=False, sort_keys=True)
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    @staticmethod
    def _hash(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def record_request(
        self,
        *,
        run_id: str,
        case_id: str,
        model: str,
        attempt: int,
        payload: dict[str, Any] | str | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "recorded_at_unix": int(time.time()),
            "event_type": "external_model_request",
            "run_id": run_id,
            "case_id": case_id,
            "model": model,
            "attempt": attempt,
        }
        if payload is not None:
            raw = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False, sort_keys=True)
            event["payload_sha256"] = self._hash(raw)
        self._append(event)

    def record_rate_limited(
        self,
        *,
        run_id: str,
        case_id: str,
        model: str,
        attempt: int,
        status_code: int,
        retry_after: str | float | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "recorded_at_unix": int(time.time()),
            "event_type": "external_model_rate_limited",
            "run_id": run_id,
            "case_id": case_id,
            "model": model,
            "attempt": attempt,
            "status_code": status_code,
        }
        if retry_after is not None:
            event["retry_after"] = retry_after
        self._append(event)

    def record_response(
        self,
        *,
        run_id: str,
        case_id: str,
        model: str,
        attempt: int,
        status_code: int | None = None,
        finish_reason: str | None = None,
        content_present: bool,
        response: dict[str, Any] | str | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "recorded_at_unix": int(time.time()),
            "event_type": "external_model_response",
            "run_id": run_id,
            "case_id": case_id,
            "model": model,
            "attempt": attempt,
            "content_present": content_present,
        }
        if status_code is not None:
            event["status_code"] = status_code
        if finish_reason is not None:
            event["finish_reason"] = finish_reason
        if response is not None:
            raw = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False, sort_keys=True)
            event["response_sha256"] = self._hash(raw)
        self._append(event)

    def record_contract_result(
        self,
        *,
        run_id: str,
        case_id: str,
        model: str,
        attempt: int,
        contract_ok: bool,
        error: str | None = None,
        decision: str | None = None,
        evidence_ids: list[str] | None = None,
    ) -> None:
        event: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "recorded_at_unix": int(time.time()),
            "event_type": "retrybox_contract_result",
            "run_id": run_id,
            "case_id": case_id,
            "model": model,
            "attempt": attempt,
            "contract_ok": contract_ok,
        }
        if error is not None:
            event["error"] = error
        if decision is not None:
            event["decision"] = decision
        if evidence_ids is not None:
            event["evidence_ids"] = evidence_ids
        self._append(event)


def read_ledger(path: str | Path) -> list[dict[str, Any]]:
    """Read all entries from a JSONL ledger file."""
    path = Path(path)
    if not path.is_file():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            entries.append(json.loads(line))
    return entries
