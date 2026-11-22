"""Offline-only rehearsal of K3 transport accounting in the existing Storage DB.

Claims consume a slot BEFORE dispatch. A crash or exception leaves uncertainty,
not a refundable call. Mock HTTP responses do not authenticate a provider.
No production wiring, live HTTP transport, approval or scientific verdict here.
"""
from __future__ import annotations

import hashlib
import runpy
import sqlite3
import uuid
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import httpx

from benchmarks.innovation.semantic_lab import canonical, digest, strict_json
from criba.storage import Storage

_GATE = (Path(__file__).resolve().parents[3]
         / "docs/research/semantic-correspondence/g0-draft/pilot_gate.py")
_LIMITS = {"A": 16, "B": 36, "C": 108}
_STATES = {"IN_FLIGHT", "UNKNOWN", "RESPONSE", "RESPONSE_ERROR"}
_MAX_RESPONSE = 250_000


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _is_sha(value: Any) -> bool:
    return (isinstance(value, str) and len(value) == 64
            and all(c in "0123456789abcdef" for c in value))


def _schedule(phase: str) -> list[dict[str, Any]]:
    if phase not in _LIMITS:
        raise ValueError("invalid simulation phase")
    rows = runpy.run_path(str(_GATE))["schedule"](phase)
    if len(rows) != _LIMITS[phase]:
        raise ValueError("unexpected gate schedule")
    return rows


def _payload_bytes(payload: Mapping[str, Any]) -> bytes:
    if not isinstance(payload, dict) or payload.get("stream", False) is not False:
        raise ValueError("expected non-streaming JSON payload")
    if not isinstance(payload.get("model"), str) or not payload["model"].strip():
        raise ValueError("missing requested model")
    return canonical(payload).encode("utf-8")


def bind_slot(slot: Mapping[str, Any], request_sha256: str,
              payload: Mapping[str, Any]) -> dict[str, Any]:
    """Freeze host-provided request identity and exact bytes, not truth or authorization."""
    return {**slot, "request_sha256": request_sha256,
            "payload_sha256": _sha(_payload_bytes(payload)), "model": payload["model"]}


def _validate_plan(phase: str, plan: Any) -> None:
    expected = _schedule(phase)
    if not isinstance(plan, list) or len(plan) != len(expected):
        raise ValueError("invalid complete plan")
    seen: set[str] = set()
    for row, slot in zip(plan, expected, strict=True):
        keys = {*slot, "request_sha256", "payload_sha256", "model"}
        if not isinstance(row, dict) or set(row) != keys:
            raise ValueError("invalid plan row")
        if (type(row["repetition"]) is not int or
                any(row[k] != v for k, v in slot.items()) or
                not _is_sha(row["request_sha256"]) or not _is_sha(row["payload_sha256"]) or
                not isinstance(row["model"], str) or not row["model"].strip()):
            raise ValueError("invalid plan binding")
        if row["request_sha256"] in seen:
            raise ValueError("request reused across planned slots")
        seen.add(row["request_sha256"])


def _envelope(binding: Mapping[str, Any], dispatch_id: str, status: int, raw: bytes) -> str:
    if not 200 <= status < 300 or len(raw) > _MAX_RESPONSE:
        raise ValueError("response not usable")
    data = strict_json(raw.decode("utf-8"))
    if not isinstance(data, dict) or data.get("model") != binding["model"]:
        raise ValueError("response model report mismatch")
    choices = data.get("choices")
    if not isinstance(choices, list) or len(choices) != 1:
        raise ValueError("expected one choice")
    choice = choices[0]
    if not isinstance(choice, dict) or choice.get("finish_reason") != "stop":
        raise ValueError("incomplete response")
    msg = choice.get("message")
    if not isinstance(msg, dict) or msg.get("tool_calls") or msg.get("refusal"):
        raise ValueError("not a single text response")
    body = strict_json(msg.get("content"))
    if not isinstance(body, dict):
        raise ValueError("expected JSON object")
    return canonical({"request_sha256": binding["request_sha256"],
                      "observed_model": data["model"], "transport_id": dispatch_id,
                      "finish_reason": "stop", "body": body})


class SimulationJournal:
    """Explicitly initialized, append-only dispatch rehearsal using Storage.connect."""

    def __init__(self, storage: Storage) -> None:
        self.storage = storage
        with self._transaction() as con:
            con.execute("""CREATE TABLE IF NOT EXISTS semantic_mock_campaigns (
                campaign TEXT PRIMARY KEY, phase TEXT NOT NULL, plan_json TEXT NOT NULL,
                plan_sha256 TEXT NOT NULL, next_index INTEGER NOT NULL DEFAULT 0)""")
            con.execute("""CREATE TABLE IF NOT EXISTS semantic_mock_dispatches (
                campaign TEXT NOT NULL, slot_index INTEGER NOT NULL,
                dispatch_id TEXT NOT NULL UNIQUE,
                request_sha256 TEXT NOT NULL, payload_sha256 TEXT NOT NULL,
                state TEXT NOT NULL, status_code INTEGER, response BLOB, response_sha256 TEXT,
                PRIMARY KEY(campaign, slot_index),
                FOREIGN KEY(campaign) REFERENCES semantic_mock_campaigns(campaign))""")

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        con = self.storage.connect()
        try:
            with con:
                con.execute("BEGIN IMMEDIATE")
                yield con
        finally:
            con.close()

    def create(self, campaign: str, phase: str, plan: list[dict[str, Any]]) -> None:
        if not isinstance(campaign, str) or not campaign.strip():
            raise ValueError("missing campaign id")
        _validate_plan(phase, plan)
        frozen = canonical(plan)
        sha = _sha(frozen.encode("utf-8"))
        with self._transaction() as con:
            con.execute("INSERT OR IGNORE INTO semantic_mock_campaigns VALUES(?,?,?,?,0)",
                        (campaign, phase, frozen, sha))
            old = con.execute("SELECT phase,plan_sha256,plan_json FROM semantic_mock_campaigns "
                              "WHERE campaign=?", (campaign,)).fetchone()
            if tuple(old) != (phase, sha, frozen):
                raise ValueError("campaign plan immutable")

    def _read(
        self, con: sqlite3.Connection, campaign: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        record = con.execute("SELECT * FROM semantic_mock_campaigns WHERE campaign=?",
                             (campaign,)).fetchone()
        if record is None:
            raise ValueError("unknown campaign")
        plan = strict_json(record["plan_json"])
        if digest(plan) != record["plan_sha256"] or canonical(plan) != record["plan_json"]:
            raise ValueError("plan integrity failure")
        _validate_plan(record["phase"], plan)
        rows = [dict(row) for row in con.execute(
            "SELECT * FROM semantic_mock_dispatches WHERE campaign=? ORDER BY slot_index",
            (campaign,))]
        if (type(record["next_index"]) is not int or record["next_index"] != len(rows)
                or len(rows) > len(plan)):
            raise ValueError("dispatch count inconsistent")
        for i, row in enumerate(rows):
            binding = plan[i]
            if (row["slot_index"] != i or row["request_sha256"] != binding["request_sha256"]
                    or row["payload_sha256"] != binding["payload_sha256"]
                    or row["state"] not in _STATES or not row["dispatch_id"]
                    or (i < len(rows) - 1 and row["state"] != "RESPONSE")):
                raise ValueError("dispatch identity or sequence inconsistent")
            raw = row["response"]
            if row["state"] in ("IN_FLIGHT", "UNKNOWN"):
                if any(row[k] is not None for k in ("status_code", "response", "response_sha256")):
                    raise ValueError("unexpected response metadata")
            else:
                if (type(row["status_code"]) is not int or not isinstance(raw, bytes)
                        or _sha(raw) != row["response_sha256"]):
                    raise ValueError("response integrity failure")
                try:
                    _envelope(binding, row["dispatch_id"], row["status_code"], raw)
                    actual = "RESPONSE"
                except (ValueError, TypeError, RecursionError, OverflowError):
                    actual = "RESPONSE_ERROR"
                if row["state"] != actual:
                    raise ValueError("response status inconsistent")
        return plan, rows

    def _claim(self, campaign: str, index: int, payload_sha: str) -> str:
        with self._transaction() as con:
            plan, rows = self._read(con, campaign)
            if any(row["state"] != "RESPONSE" for row in rows):
                raise ValueError("campaign blocked by error or uncertain dispatch")
            if type(index) is not int or index != len(rows) or index >= len(plan):
                raise ValueError("slot replay, out of order or budget exhausted")
            binding = plan[index]
            if payload_sha != binding["payload_sha256"]:
                raise ValueError("payload changed")
            dispatch_id = uuid.uuid4().hex
            con.execute("INSERT INTO semantic_mock_dispatches VALUES(?,?,?,?,?,?,NULL,NULL,NULL)",
                        (campaign, index, dispatch_id, binding["request_sha256"],
                         payload_sha, "IN_FLIGHT"))
            con.execute(
                "UPDATE semantic_mock_campaigns SET next_index=next_index+1 WHERE campaign=?",
                (campaign,))
            return dispatch_id  # context manager commits before returning

    def _finish(self, campaign: str, index: int, dispatch_id: str,
                response: httpx.Response | None) -> str:
        with self._transaction() as con:
            plan, rows = self._read(con, campaign)
            if (type(index) is not int or not 0 <= index < len(rows)
                    or rows[index]["dispatch_id"] != dispatch_id
                    or rows[index]["state"] != "IN_FLIGHT"):
                raise ValueError("dispatch no longer current")
            if response is None:
                state, status, raw, sha = "UNKNOWN", None, None, None
            else:
                status, raw = response.status_code, response.content
                sha = _sha(raw)
                try:
                    _envelope(plan[index], dispatch_id, status, raw)
                    state = "RESPONSE"
                except (ValueError, TypeError, RecursionError, OverflowError):
                    state = "RESPONSE_ERROR"
            cur = con.execute(
                "UPDATE semantic_mock_dispatches SET state=?,status_code=?,response=?,"
                "response_sha256=? WHERE campaign=? AND slot_index=? AND dispatch_id=? "
                "AND state='IN_FLIGHT'",
                (state, status, raw, sha, campaign, index, dispatch_id))
            if cur.rowcount != 1:
                raise ValueError("dispatch changed before close")
            return state

    def run_mock(self, campaign: str, index: int, payload: dict[str, Any],
                 transport: httpx.MockTransport) -> str:
        """One mock POST, no retries, redirects, proxies or live provider access."""
        if type(transport) is not httpx.MockTransport:
            raise ValueError("only exact MockTransport allowed; live inference forbidden")
        raw = _payload_bytes(payload)
        dispatch_id = self._claim(campaign, index, _sha(raw))
        try:
            with httpx.Client(
                transport=transport, trust_env=False, follow_redirects=False
            ) as client:
                response = client.post("https://cbs.invalid/v1/chat/completions", content=raw,
                                       headers={"Content-Type": "application/json"})
        except Exception:
            # A host exception cannot tell us whether a real provider consumed a call.
            return self._finish(campaign, index, dispatch_id, None)
        return self._finish(campaign, index, dispatch_id, response)

    def envelope(self, campaign: str, index: int) -> str:
        """Recover exact simulation envelope; does not establish model identity or truth."""
        with self._transaction() as con:
            plan, rows = self._read(con, campaign)
            if (type(index) is not int or not 0 <= index < len(rows)
                    or rows[index]["state"] != "RESPONSE"):
                raise ValueError("no usable response")
            row = rows[index]
            return _envelope(plan[index], row["dispatch_id"], row["status_code"], row["response"])

    def summary(self, campaign: str) -> dict[str, Any]:
        with self._transaction() as con:
            plan, rows = self._read(con, campaign)
            states = [r["state"] for r in rows]
            return {"mode": "MOCK_ONLY", "planned_slots": len(plan), "host_claimed": len(rows),
                    "responses_received": sum(s in ("RESPONSE", "RESPONSE_ERROR") for s in states),
                    "uncertain_dispatches": sum(s in ("IN_FLIGHT", "UNKNOWN") for s in states),
                    "not_claimed": len(plan) - len(rows), "states": states,
                    "blocked": any(s != "RESPONSE" for s in states),
                    "budget_exhausted": len(rows) == len(plan),
                    "provider_consumption": None, "authorization": "NOT_GRANTED"}
