"""SQLite -> frozen S1 request -> strict receipt reader; no inference."""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from benchmarks.innovation.semantic_lab import Trial, canonical, digest, strict_json
from benchmarks.innovation.semantic_ledger_gate import (
    SlotContext,
    normalizar_lote,
    normalizar_slot,
    validar_registros,
)
from criba.storage import Storage


def context(case="C:1", rep=0, attempt="attempt-1", episode="ep-1"):
    proposal = {
        "hipotesis": "Recuperar agua de ducha",
        "mecanismo": "Desviar agua fría a depósito separado",
        "cadena_causal": ["Desviar", "Recuperar"],
        "prueba": {"metrica": "litros recuperados"},
        "prueba_concreta": "Medir litros",
    }
    trial = Trial(case, "run-1", episode, "candidate-1", "generator", "Recuperar agua fría",
                  ("Separar agua potable",), canonical(proposal), "a" * 64)
    return SlotContext(trial, rep, "judge", attempt)


def receipt(ctx, assessment="SUPPORTS", **overrides):
    def vote(field, quote, source=None):
        return {"assessment": assessment, "reason": "fixture sintética",
                "source_quote": source or ctx.trial.query,
                "proposal_field": field, "proposal_quote": quote}
    body = {
        "axes": {
            "objective": vote("hypothesis", "Recuperar agua"),
            "mechanism": vote("mechanism", "Desviar agua fría"),
            "metric": vote("metric", "litros recuperados"),
        },
        "restrictions": {
            "Separar agua potable": vote("mechanism", "depósito separado", "Separar agua potable"),
        },
    }
    return canonical({"request_sha256": ctx.request_sha256, "observed_model": ctx.reviewer,
                      "transport_id": "synthetic-transport", "finish_reason": "stop", "body": body,
                      **overrides})


def persist(st, ctx, raw):
    scope, attempt, request = ctx.trial.scope, ctx.attempt, ctx.request_sha256
    assert st.reserve_semantic_attempt(scope, attempt, request, ctx.reviewer)
    assert st.close_semantic_attempt(scope, attempt, request, digest(strict_json(raw))) == "CLOSED"
    return st.load_semantic_snapshot(scope, attempt)


def read(ctx, state, rows, raw):
    return normalizar_slot(case_id=ctx.trial.case_id, repetition=ctx.repetition, arm="S1",
                           estado_reserva=state, recibos=rows, contexto=ctx, raw_receipt=raw)


@pytest.mark.parametrize("assessment,expected", [
    ("SUPPORTS", "SUPPORT"), ("CONTRADICTS", "REJECT"), ("UNKNOWN", "UNRESOLVED"),
])
def test_real_snapshot_and_envelope_survive_reopen(tmp_path, assessment, expected):
    db = tmp_path / "ledger.db"
    ctx = context()
    raw = receipt(ctx, assessment)
    persist(Storage(db), ctx, raw)
    state, rows = Storage(db).load_semantic_snapshot(ctx.trial.scope, ctx.attempt)
    assert rows[0]["status"] == "ACTIVE"  # Actual insertion state, not a guessed CLOSED.
    assert read(ctx, state, rows, raw)["outcome"] == expected
    assert read(ctx, state, rows, raw)["physical_calls"] == 1  # Proxy only.


def test_pointer_selects_exact_receipt_not_first_request(tmp_path):
    st = Storage(tmp_path / "ledger.db")
    ctx = context()
    raw = receipt(ctx, "CONTRADICTS")
    state, rows = persist(st, ctx, raw)
    wrong = {**rows[0], "body_sha256": "0" * 64, "status": "STALE",
             "body": {"veredicto": "SUPPORT"}}
    assert read(ctx, state, [wrong, *rows], raw)["outcome"] == "REJECT"
    assert read(ctx, state, [*rows, wrong], raw)["outcome"] == "REJECT"


@pytest.mark.parametrize("field,value", [
    ("scope", "other"), ("attempt", "other"), ("reviewer", "other"),
    ("request_sha256", "0" * 64), ("receipt_sha256", "0" * 64),
    ("closed_at", None), ("status", "STALE"),
])
def test_wrong_reservation_is_error(tmp_path, field, value):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    assert read(ctx, {**state, field: value}, rows, raw)["outcome"] == "ERROR"


@pytest.mark.parametrize("field,value", [
    ("scope", "other"), ("attempt", "other"), ("request_sha256", "0" * 64),
    ("body_sha256", "0" * 64), ("status", "STALE"), ("status", "CLOSED"),
])
def test_wrong_row_is_error(tmp_path, field, value):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    assert read(ctx, state, [{**rows[0], field: value}], raw)["outcome"] == "ERROR"


@pytest.mark.parametrize("mutation", ["digest", "duplicate", "model", "truncated", "label", "quote"])
def test_changed_or_invalid_envelope_is_error_even_if_digest_matches(tmp_path, mutation):
    ctx = context()
    raw = receipt(ctx)
    if mutation == "digest":
        changed = receipt(ctx, "CONTRADICTS")
    elif mutation == "duplicate":
        changed = raw[:-1] + ',"finish_reason":"stop"}'
    elif mutation == "model":
        changed = receipt(ctx, observed_model="wrong")
    elif mutation == "truncated":
        changed = receipt(ctx, finish_reason="length")
    elif mutation == "label":
        changed = receipt(ctx, body={"veredicto": "SUPPORT"})
    else:
        data = json.loads(raw)
        data["body"]["axes"]["metric"]["proposal_quote"] = "fabricated quote"
        changed = canonical(data)
    st = Storage(tmp_path / "ledger.db")
    stored = raw if mutation in ("digest", "duplicate") else changed
    state, rows = persist(st, ctx, stored)
    assert read(ctx, state, rows, changed)["outcome"] == "ERROR"


def test_missing_duplicate_or_flattened_receipt_is_error(tmp_path):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    for invalid_rows, envelope in (([], raw), (rows * 2, raw), (rows, None),
                                   ([{**rows[0], "body": {"veredicto": "SUPPORT"}}], None)):
        result = read(ctx, state, invalid_rows, envelope)
        assert result["outcome"] == "ERROR"
        assert result["physical_calls"] == 0  # No accepted receipt, not proof of zero usage.


def test_different_episode_same_case_cannot_reuse_receipt(tmp_path):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    assert read(context(episode="ep-2"), state, rows, raw)["outcome"] == "ERROR"


def test_wrong_slot_and_unimplemented_s0_are_errors(tmp_path):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    for case, rep, arm in (("other", 0, "S1"), ("C:1", 1, "S1"), ("C:1", 0, "S0")):
        result = normalizar_slot(case_id=case, repetition=rep, arm=arm, estado_reserva=state,
                                 recibos=rows, contexto=ctx, raw_receipt=raw)
        assert result["outcome"] == "ERROR"


def test_no_same_request_across_repetitions(tmp_path):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    ctx2 = replace(ctx, repetition=1)
    assert ctx2.request_sha256 != ctx.request_sha256
    assert read(ctx2, state, rows, raw)["outcome"] == "ERROR"
    slots = [ctx.slot, ctx2.slot]
    records = normalizar_lote(slots, dict.fromkeys(slots, state), dict.fromkeys(slots, rows),
                              contextos_por_slot={ctx.slot: ctx, ctx2.slot: ctx2},
                              raw_por_slot=dict.fromkeys(slots, raw))
    assert [r["outcome"] for r in records] == ["SUPPORT", "ERROR"]


def test_duplicate_request_in_batch_rejected(tmp_path):
    ctx = context()
    raw = receipt(ctx)
    state, rows = persist(Storage(tmp_path / "ledger.db"), ctx, raw)
    with pytest.raises(ValueError, match="reused across slots"):
        normalizar_lote([ctx.slot, ctx.slot], {ctx.slot: state}, {ctx.slot: rows},
                        contextos_por_slot={ctx.slot: ctx}, raw_por_slot={ctx.slot: raw})


def test_re_reservation_supersedes_old_receipt(tmp_path):
    st = Storage(tmp_path / "ledger.db")
    ctx = context()
    raw = receipt(ctx)
    persist(st, ctx, raw)
    new = replace(ctx, reviewer="new-reviewer")
    assert st.reserve_semantic_attempt(new.trial.scope, new.attempt, new.request_sha256, new.reviewer)
    new_raw = receipt(new, "CONTRADICTS")
    assert st.close_semantic_attempt(new.trial.scope, new.attempt, new.request_sha256,
                                     digest(strict_json(new_raw))) == "CLOSED"
    state, rows = st.load_semantic_snapshot(new.trial.scope, new.attempt)
    assert read(ctx, state, rows, raw)["outcome"] == "ERROR"
    assert read(new, state, rows, new_raw)["outcome"] == "REJECT"


def test_parseable_corrupt_fields_return_errors_instead_of_crashing():
    clean = {"case_id": "C:1", "repetition": 0, "arm": "S1",
             "outcome": "ERROR", "physical_calls": 0}
    for field, value in (("case_id", []), ("repetition", True), ("repetition", 3),
                         ("arm", {}), ("outcome", []), ("physical_calls", True)):
        assert validar_registros([{**clean, field: value}])


def test_orphan_metadata_or_unknown_status_not_run_is_not_asserted():
    for state, rows in ((None, [{}]), ({"status": "garbage"}, []),
                        ({"status": "ACTIVE", "receipt_sha256": "x"}, [])):
        result = normalizar_slot(case_id="C:1", repetition=0, arm="S1",
                                 estado_reserva=state, recibos=rows)
        assert result["outcome"] == "ERROR"


def test_superseded_request_cannot_return_after_reopen(tmp_path):
    db = tmp_path / "aba.db"
    st = Storage(db)
    a, b = "a" * 64, "b" * 64
    assert st.reserve_semantic_attempt("s", "att", a, "judge")
    assert st.reserve_semantic_attempt("s", "att", b, "judge")
    reopened = Storage(db)
    with pytest.raises(ValueError, match="superada"):
        reopened.reserve_semantic_attempt("s", "att", a, "judge")
    assert reopened.close_semantic_attempt("s", "att", a, "c" * 64) == "STALE"
    assert reopened.semantic_attempt_status("s", "att")["request_sha256"] == b
    assert reopened.semantic_attempt_status("s", "att")["status"] == "ACTIVE"


def test_prior_receipt_blocks_legacy_reactivation(tmp_path):
    db = tmp_path / "legacy.db"
    st = Storage(db)
    a, b = "a" * 64, "b" * 64
    st.reserve_semantic_attempt("s", "att", a, "judge")
    st.close_semantic_attempt("s", "att", a, "c" * 64)
    st.reserve_semantic_attempt("s", "att", b, "judge")
    con = st.connect()
    try:
        with con:
            con.execute("DROP TABLE semantic_superseded_requests")  # emulate old schema
    finally:
        con.close()
    reopened = Storage(db)
    with pytest.raises(ValueError, match="superada"):
        reopened.reserve_semantic_attempt("s", "att", a, "judge")
    assert reopened.semantic_attempt_status("s", "att")["request_sha256"] == b


def test_same_request_cannot_silently_change_reviewer(tmp_path):
    st = Storage(tmp_path / "reviewer.db")
    st.reserve_semantic_attempt("s", "att", "a" * 64, "judge")
    with pytest.raises(ValueError, match="reviewer"):
        st.reserve_semantic_attempt("s", "att", "a" * 64, "other")
    assert st.semantic_attempt_status("s", "att")["reviewer"] == "judge"


@pytest.mark.parametrize("stale_first", [False, True])
def test_cross_request_digest_collision_is_conflict(tmp_path, stale_first):
    st = Storage(tmp_path / "collision.db")
    a, b, h = "a" * 64, "b" * 64, "c" * 64
    st.reserve_semantic_attempt("s", "att", a, "judge")
    st.reserve_semantic_attempt("s", "att", b, "judge")
    if stale_first:
        assert st.close_semantic_attempt("s", "att", a, h) == "STALE"
        with pytest.raises(ValueError, match="otra peticion"):
            st.close_semantic_attempt("s", "att", b, h)
        assert st.semantic_attempt_status("s", "att")["status"] == "ACTIVE"
        assert st.close_semantic_attempt("s", "att", b, "d" * 64) == "CLOSED"
    else:
        assert st.close_semantic_attempt("s", "att", b, h) == "CLOSED"
        with pytest.raises(ValueError, match="otra peticion"):
            st.close_semantic_attempt("s", "att", a, h)
        assert st.semantic_attempt_status("s", "att")["receipt_sha256"] == h
    assert st.semantic_attempt_status("s", "att")["status"] == "CLOSED"


def test_missing_winning_row_not_recreated_by_idempotent_close(tmp_path):
    st = Storage(tmp_path / "corrupt.db")
    req, h = "a" * 64, "b" * 64
    st.reserve_semantic_attempt("s", "att", req, "judge")
    st.close_semantic_attempt("s", "att", req, h)
    con = st.connect()
    try:
        with con:
            con.execute("DELETE FROM semantic_receipts")  # fault injection only
    finally:
        con.close()
    with pytest.raises(ValueError, match="inconsistente"):
        st.close_semantic_attempt("s", "att", req, h)
    assert st.load_semantic_receipts("s", "att") == []


def test_reader_sees_one_sqlite_snapshot_during_concurrent_re_reserve(tmp_path, monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    db = tmp_path / "snapshot.db"
    st = Storage(db)
    ctx = context()
    raw = receipt(ctx)
    original_state, original_rows = persist(st, ctx, raw)
    read_boundary, writer_done = Event(), Event()
    connect = st.connect

    class Connection:
        def __init__(self, inner):
            self.inner = inner

        def execute(self, sql, *args):
            cursor = self.inner.execute(sql, *args)
            if sql.startswith("SELECT scope, attempt, request_sha256, reviewer"):
                return Cursor(cursor)
            return cursor

        def close(self):
            self.inner.close()

    class Cursor:
        def __init__(self, inner):
            self.inner = inner

        def fetchone(self):
            row = self.inner.fetchone()
            read_boundary.set()
            assert writer_done.wait(5), "writer blocked or failed before second SELECT"
            return row

    def writer():
        assert read_boundary.wait(5), "reader did not reach reservation SELECT"
        new = replace(ctx, reviewer="new")
        try:
            persist(Storage(db), new, receipt(new, "CONTRADICTS"))
        finally:
            writer_done.set()

    with monkeypatch.context() as mp:
        mp.setattr(st, "connect", lambda: Connection(connect()))
        with ThreadPoolExecutor(max_workers=2) as pool:
            f = pool.submit(writer)
            snapshot = st.load_semantic_snapshot(ctx.trial.scope, ctx.attempt)
            f.result(timeout=10)
    assert snapshot == (original_state, original_rows)
    current = st.load_semantic_snapshot(ctx.trial.scope, ctx.attempt)
    assert current != snapshot
    assert read(ctx, *current, raw)["outcome"] == "ERROR"


def test_true_reader_to_gate_with_frozen_manifest(tmp_path):
    import runpy
    from pathlib import Path

    path = Path(__file__).resolve().parents[3] / "docs/research/semantic-correspondence/g0-draft"
    gate = runpy.run_path(str(path / "pilot_gate.py"))
    slots = [(row["case_id"], row["repetition"], row["arm"]) for row in gate["schedule"]("A")]
    slot = next(s for s in slots if s[2] == "S1")
    ctx = context(case=slot[0], rep=slot[1])
    raw = receipt(ctx, "CONTRADICTS")
    state, rows = persist(Storage(tmp_path / "gate.db"), ctx, raw)
    records = normalizar_lote(slots, {slot: state}, {slot: rows},
                              contextos_por_slot={slot: ctx}, raw_por_slot={slot: raw})
    assert validar_registros(records) == []
    assert next(r for r in records if (r["case_id"], r["repetition"], r["arm"]) == slot)["outcome"] == "REJECT"
    summary = gate["summarize"]("A", records)
    assert summary["status"] == "INCOMPLETE"
    assert summary["p0_status"] == "OPEN"
    assert summary["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
