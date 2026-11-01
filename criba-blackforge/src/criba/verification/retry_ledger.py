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
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any


SCHEMA_VERSION = "retry_ledger.v1"
_APPEND_LOCK = threading.Lock()


@contextmanager
def _process_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        if os.name == "nt":
            import msvcrt

            if os.fstat(fd).st_size == 0:
                os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)


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
        for field in ("content_present", "contract_ok"):
            if field in event and type(event[field]) is not bool:
                raise ValueError(f"{field} must be boolean")
        line = json.dumps(event, ensure_ascii=False, sort_keys=True, allow_nan=False)
        data = (line + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        lock_path = self.path.with_name(self.path.name + ".lock")
        with _APPEND_LOCK, _process_lock(lock_path):
            with open(self.path, "ab") as f:
                f.write(data)
                f.flush()

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
            if not isinstance(error, str):
                raise ValueError("error must be a string")
            code = error.partition(":")[0]
            known_codes = {
                "CASE_ID_MISMATCH", "INVALID_DECISION", "UNKNOWN_EVIDENCE",
                "DUPLICATE_EVIDENCE", "MISSING_RATIONALE", "PROPOSE_WITHOUT_HYPOTHESIS",
                "PROPOSE_WITHOUT_EVIDENCE", "ABSTENTION_WITHOUT_REQUEST",
                "INVALID_PROPOSED_CHECKS", "CAUSAL_OVERCLAIM", "FORBIDDEN_FIELD_USED",
                "UNKNOWN_PROMOTED", "RESPONSE_NOT_OBJECT", "INVALID_EVIDENCE_IDS",
                "INVALID_EVIDENCE_ID_TYPE", "INVALID_REQUESTED_EVIDENCE",
                "PROPOSE_WITHOUT_CHECKS", "MISSING_HYPOTHESIS", "ABSTENTION_WITH_HYPOTHESIS",
                "INVALID_CASE", "INVALID_CASE_ID", "INVALID_OBSERVATIONS",
                "INVALID_OBSERVATION", "INVALID_OBSERVATION_ID", "DUPLICATE_OBSERVATION_ID",
                "INVALID_ORACLE", "INVALID_ORACLE_ANTI_GOODHART", "INVALID_ORACLE_CAUSAL_FLAG",
                "INVALID_ORACLE_FORBIDDEN_FIELDS", "ORACLE_CASE_ID_MISMATCH",
            }
            event["error"] = code if code in known_codes else "REDACTED_ERROR"
            if event["error"] != error:
                event["error_sha256"] = self._hash(error)
        if decision is not None:
            event["decision"] = decision
        if evidence_ids is not None:
            event["evidence_ids"] = evidence_ids
        self._append(event)


def _reject_constant(value: str) -> Any:
    raise ValueError("nonfinite JSON constant")


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def read_ledger(path: str | Path) -> list[dict[str, Any]]:
    """Read JSON objects strictly; missing is empty, corrupt is never empty."""
    path = Path(path)
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except UnicodeError:
        raise ValueError("ledger is not valid UTF-8") from None
    entries: list[dict[str, Any]] = []
    for number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
            if not isinstance(value, dict):
                raise ValueError("record is not an object")
        except ValueError:
            raise ValueError(f"invalid ledger record at line {number}") from None
        entries.append(value)
    return entries
