"""Real SQLite, mock HTTP, no provider or authorization."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest

from benchmarks.innovation import semantic_transport_journal as journal
from benchmarks.innovation.semantic_lab import digest, strict_json
from criba.storage import Storage


def plan_for(phase="A"):
    slots = journal._schedule(phase)
    payloads = [{"model": "mock-model", "messages": [{"role": "user", "content": str(i)}]}
                for i in range(len(slots))]
    plan = [journal.bind_slot(s, digest(["simulation", i]), p)
            for i, (s, p) in enumerate(zip(slots, payloads, strict=True))]
    return plan, payloads


def setup(tmp_path, phase="A"):
    path = tmp_path / "journal.db"
    j = journal.SimulationJournal(Storage(path))
    plan, payloads = plan_for(phase)
    j.create("run", phase, plan)
    return j, path, plan, payloads


def response(**changes):
    data = {"id": "simulated", "model": "mock-model", "choices": [
        {"finish_reason": "stop", "message": {"content": '{"x":1}'}}
    ]}
    data.update(changes)
    return httpx.Response(200, json=data)


@pytest.mark.parametrize("phase,limit", [("A", 16), ("B", 36), ("C", 108)])
def test_exact_budget_and_one_post_per_slot(tmp_path, phase, limit):
    j, path, plan, payloads = setup(tmp_path, phase)
    seen = []

    def handle(req):
        i = len(seen)
        snapshot = journal.SimulationJournal(Storage(path)).summary("run")
        assert snapshot["host_claimed"] == i + 1
        assert snapshot["states"][-1] == "IN_FLIGHT"
        seen.append(hashlib.sha256(req.content).hexdigest())
        assert req.url.host == "cbs.invalid" and req.method == "POST"
        return response()

    for i, payload in enumerate(payloads):
        assert j.run_mock("run", i, payload, httpx.MockTransport(handle)) == "RESPONSE"
    assert seen == [p["payload_sha256"] for p in plan]
    for index in (0, limit, limit + 1):
        with pytest.raises(ValueError):
            j.run_mock("run", index, payloads[0], httpx.MockTransport(handle))
    s = journal.SimulationJournal(Storage(path)).summary("run")
    assert len(seen) == s["host_claimed"] == s["responses_received"] == limit
    assert s["not_claimed"] == s["uncertain_dispatches"] == 0
    assert s["budget_exhausted"] is True
    assert s["provider_consumption"] is None and s["authorization"] == "NOT_GRANTED"


def test_payload_changed_out_of_order_and_live_transport_block_before_claim(tmp_path):
    j, _, _, ps = setup(tmp_path)
    seen = []
    t = httpx.MockTransport(lambda req: seen.append(req) or response())
    for index, p, tr in [(0, {**ps[0], "temperature": 0.3}, t), (1, ps[1], t),
                         (0, ps[0], httpx.HTTPTransport()), (True, ps[0], t)]:
        with pytest.raises(ValueError):
            j.run_mock("run", index, p, tr)
    assert not seen and j.summary("run")["host_claimed"] == 0


@pytest.mark.parametrize("kind", ["timeout", "connect", "crash"])
def test_uncertain_send_never_refunds_or_retries(tmp_path, kind):
    j, path, _, ps = setup(tmp_path)
    seen = []

    def fail(req):
        seen.append(req)
        if kind == "crash":
            raise SystemExit(7)
        if kind == "connect":
            raise httpx.ConnectError("mock")
        raise httpx.ReadTimeout("mock after send")

    if kind == "crash":
        with pytest.raises(SystemExit):
            j.run_mock("run", 0, ps[0], httpx.MockTransport(fail))
    else:
        assert j.run_mock("run", 0, ps[0], httpx.MockTransport(fail)) == "UNKNOWN"
    reopened = journal.SimulationJournal(Storage(path))
    for i in (0, 1):
        with pytest.raises(ValueError, match="blocked"):
            reopened.run_mock("run", i, ps[i], httpx.MockTransport(fail))
    s = reopened.summary("run")
    assert len(seen) == s["host_claimed"] == s["uncertain_dispatches"] == 1
    assert s["responses_received"] == 0 and s["provider_consumption"] is None
    assert s["budget_exhausted"] is False
    assert s["states"] == ["IN_FLIGHT" if kind == "crash" else "UNKNOWN"]


@pytest.mark.parametrize("bad", [
    httpx.Response(429), httpx.Response(503),
    httpx.Response(302, headers={"Location": "https://outside.invalid"}),
    httpx.Response(200, content=b'{"model":"x", "model":"mock-model"}'),
    httpx.Response(200, content=b'\xff'), response(model="different"), response(choices=[]),
    response(choices=[{"finish_reason": "length", "message": {"content": "{}"}}]),
    response(choices=[{"finish_reason": "stop", "message": {"content": "{\"a\":NaN}"}}]),
    response(choices=[{"finish_reason": "stop", "message": {"content": "{}", "tool_calls": [{}]}}]),
])
def test_known_response_error_consumes_claim_and_blocks(tmp_path, bad):
    j, _, _, ps = setup(tmp_path)
    seen = []
    t = httpx.MockTransport(lambda req: seen.append(req) or bad)
    assert j.run_mock("run", 0, ps[0], t) == "RESPONSE_ERROR"
    with pytest.raises(ValueError):
        j.envelope("run", 0)
    with pytest.raises(ValueError, match="blocked"):
        j.run_mock("run", 1, ps[1], t)
    s = j.summary("run")
    assert len(seen) == s["host_claimed"] == s["responses_received"] == 1
    assert s["uncertain_dispatches"] == 0


def test_envelope_recovered_from_persisted_response_not_claimed_verdict(tmp_path):
    j, path, plan, ps = setup(tmp_path)
    assert j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda req: response())) == "RESPONSE"
    raw = j.envelope("run", 0)
    assert journal.SimulationJournal(Storage(path)).envelope("run", 0) == raw
    envelope = strict_json(raw)
    assert envelope["request_sha256"] == plan[0]["request_sha256"]
    assert envelope["observed_model"] == "mock-model" and envelope["body"] == {"x": 1}
    assert envelope["finish_reason"] == "stop" and len(envelope["transport_id"]) == 32
    assert "outcome" not in envelope


def test_two_concurrent_workers_one_dispatch(tmp_path):
    j, path, _, ps = setup(tmp_path)
    entered, release = Event(), Event()
    seen = []

    def handle(req):
        seen.append(req)
        entered.set()
        assert release.wait(5)
        return response()

    t = httpx.MockTransport(handle)
    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(j.run_mock, "run", 0, ps[0], t)
        try:
            assert entered.wait(5)
            j2 = journal.SimulationJournal(Storage(path))
            for i in (0, 1):
                with pytest.raises(ValueError, match="blocked"):
                    j2.run_mock("run", i, ps[i], t)
        finally:
            release.set()
        assert first.result(timeout=10) == "RESPONSE"
    assert len(seen) == j.summary("run")["host_claimed"] == 1


def test_atomic_claim_rollback_prevents_dispatch(tmp_path):
    j, path, _, ps = setup(tmp_path)
    con = Storage(path).connect()
    try:
        with con:
            con.execute("CREATE TRIGGER fail_counter BEFORE UPDATE OF next_index "
                        "ON semantic_mock_campaigns "
                        "BEGIN SELECT RAISE(ABORT, 'counter fault'); END")
    finally:
        con.close()
    seen = []
    with pytest.raises(sqlite3.IntegrityError, match="counter fault"):
        j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: seen.append(r) or response()))
    assert not seen and j.summary("run")["host_claimed"] == 0


def test_failed_close_leaves_durable_uncertainty(tmp_path):
    j, path, _, ps = setup(tmp_path)
    con = Storage(path).connect()
    try:
        with con:
            con.execute("CREATE TRIGGER fail_close BEFORE UPDATE ON semantic_mock_dispatches "
                        "BEGIN SELECT RAISE(ABORT, 'close fault'); END")
    finally:
        con.close()
    seen = []
    with pytest.raises(sqlite3.IntegrityError, match="close fault"):
        j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: seen.append(r) or response()))
    reopened = journal.SimulationJournal(Storage(path))
    assert len(seen) == reopened.summary("run")["uncertain_dispatches"] == 1
    with pytest.raises(ValueError, match="blocked"):
        reopened.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: response()))


@pytest.mark.parametrize("sql", [
    "DELETE FROM semantic_mock_dispatches", "UPDATE semantic_mock_dispatches SET response=x'00'",
    "UPDATE semantic_mock_dispatches SET state='UNKNOWN'",
    "UPDATE semantic_mock_dispatches SET request_sha256='x'",
    "UPDATE semantic_mock_campaigns SET plan_json='[]'",
    "UPDATE semantic_mock_campaigns SET next_index=0",
    "UPDATE semantic_mock_dispatches SET state='RESPONSE_ERROR'",
])
def test_corrupt_parseable_state_blocks_dispatch(tmp_path, sql):
    j, path, _, ps = setup(tmp_path)
    j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: response()))
    con = Storage(path).connect()
    try:
        with con:
            con.execute(sql)
    finally:
        con.close()
    seen = []
    with pytest.raises(ValueError):
        j.run_mock("run", 1, ps[1], httpx.MockTransport(lambda r: seen.append(r) or response()))
    assert not seen
    with pytest.raises(ValueError):
        j.summary("run")


def test_plan_immutable_and_exact_no_reuse(tmp_path):
    j, _, plan, _ = setup(tmp_path)
    j.create("run", "A", plan)
    for changed in (plan[:-1], plan[::-1], [{**plan[0], "repetition": False}, *plan[1:]],
                    [plan[0], {**plan[1], "request_sha256": plan[0]["request_sha256"]}, *plan[2:]]):
        with pytest.raises(ValueError):
            j.create("other", "A", changed)
    with pytest.raises(ValueError, match="immutable"):
        j.create("run", "A", [{**plan[0], "model": "different"}, *plan[1:]])
    with pytest.raises(ValueError):
        j.create("run", "B", plan_for("B")[0])


def test_stale_finish_rejected_even_same_dispatch_id(tmp_path):
    j, _, _, ps = setup(tmp_path)
    j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: response()))
    ident = json.loads(j.envelope("run", 0))["transport_id"]
    with pytest.raises(ValueError, match="no longer current"):
        j._finish("run", 0, ident, response(model="other"))
    assert json.loads(j.envelope("run", 0))["body"] == {"x": 1}


def test_mock_response_to_k3_receipt_to_semantic_reader(tmp_path):
    from benchmarks.innovation.semantic_lab import Trial, canonical, direct_request
    from benchmarks.innovation.semantic_ledger_gate import SlotContext, normalizar_slot

    plan, ps = plan_for()
    index = next(i for i, s in enumerate(plan) if s["arm"] == "S1")
    slot = journal._schedule("A")[index]
    proposal = {"hipotesis": "Recuperar agua", "mecanismo": "Desviar agua",
                "cadena_causal": ["Desviar"], "prueba": {"metrica": "litros"},
                "prueba_concreta": "Medir litros"}
    trial = Trial(slot["case_id"], "mock-run", "mock-episode", "candidate", "generator",
                  "Recuperar agua", (), canonical(proposal), "a" * 64)
    ctx = SlotContext(trial, slot["repetition"], "mock-model", "nonce")
    req = direct_request(trial, ctx.reviewer, ctx.attempt)
    ps[index] = {"model": ctx.reviewer, "messages": [{"role": "user", "content": req.prompt}]}
    plan[index] = journal.bind_slot(slot, req.sha256, ps[index])
    st = Storage(tmp_path / "integrated.db")
    j = journal.SimulationJournal(st)
    j.create("run", "A", plan)
    for i in range(index):
        assert j.run_mock("run", i, ps[i], httpx.MockTransport(lambda r: response())) == "RESPONSE"
    axes = {name: {"assessment": "UNKNOWN", "reason": "synthetic uncertainty",
                   "source_quote": None, "proposal_field": None, "proposal_quote": None}
            for name in ("objective", "mechanism", "metric")}
    assert st.reserve_semantic_attempt(trial.scope, ctx.attempt, req.sha256, ctx.reviewer)
    assert j.run_mock("run", index, ps[index], httpx.MockTransport(lambda r: response(choices=[
        {"finish_reason": "stop",
         "message": {"content": canonical({"axes": axes, "restrictions": {}})}}
    ]))) == "RESPONSE"
    raw = journal.SimulationJournal(st).envelope("run", index)
    assert st.close_semantic_attempt(trial.scope, ctx.attempt, req.sha256,
                                     digest(strict_json(raw))) == "CLOSED"
    state, rows = st.load_semantic_snapshot(trial.scope, ctx.attempt)
    args = dict(case_id=trial.case_id, repetition=ctx.repetition, arm="S1",
                estado_reserva=state, recibos=rows, contexto=ctx)
    assert normalizar_slot(**args, raw_receipt=raw)["outcome"] == "UNRESOLVED"
    altered = strict_json(raw)
    altered["transport_id"] = "different"
    assert normalizar_slot(**args, raw_receipt=canonical(altered))["outcome"] == "ERROR"
    assert j.summary("run")["provider_consumption"] is None


def test_response_digest_detects_semantically_valid_altered_bytes(tmp_path):
    j, path, _, ps = setup(tmp_path)
    assert j.run_mock("run", 0, ps[0], httpx.MockTransport(lambda r: response())) == "RESPONSE"
    con = Storage(path).connect()
    try:
        with con:
            raw = con.execute("SELECT response FROM semantic_mock_dispatches").fetchone()[0]
            changed = raw.replace(b'1', b'2')
            assert changed != raw
            assert journal._envelope({"request_sha256": "a" * 64, "model": "mock-model"},
                                     "test", 200, changed)
            con.execute("UPDATE semantic_mock_dispatches SET response=?", (changed,))
    finally:
        con.close()
    with pytest.raises(ValueError, match="response integrity failure"):
        j.envelope("run", 0)
    with pytest.raises(ValueError, match="response integrity failure"):
        j.summary("run")


def test_plan_digest_detects_valid_but_different_plan(tmp_path):
    j, path, plan, _ = setup(tmp_path)
    plan[0]["model"] = "altered-model"
    journal._validate_plan("A", plan)
    con = Storage(path).connect()
    try:
        with con:
            con.execute("UPDATE semantic_mock_campaigns SET plan_json=?",
                        (journal.canonical(plan),))
    finally:
        con.close()
    with pytest.raises(ValueError, match="plan integrity failure"):
        j.summary("run")
