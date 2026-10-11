"""Concurrency and transactional integrity for real source refresh paths."""

from __future__ import annotations

import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from criba.intelligence.contracts import EvidenceDocument, EvidenceFragment
from criba.intelligence.sources.transport import (
    BudgetExceeded,
    Response,
    Transport,
    TransportBudget,
)
from criba.intelligence.storage.store import IntelligenceStore


def test_shared_transport_budget_is_atomic_and_thread_accounting_is_exact():
    budget = TransportBudget(max_requests=7)
    calls = []
    lock = threading.Lock()

    def sender(*args, **kwargs):
        with lock:
            calls.append(1)
        return Response(200, "{}")

    transport = Transport(sender=sender, budget=budget, max_retries=0)

    def acquire(_):
        before = transport.thread_request_count
        try:
            transport.get("https://example.test")
            ok = True
        except BudgetExceeded:
            ok = False
        return ok, transport.thread_request_count - before

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(acquire, range(50)))
    assert budget.requests_made == len(calls) == 7
    assert sum(ok for ok, _ in results) == sum(n for _, n in results) == 7


def test_request_retry_count_includes_failed_attempt(monkeypatch):
    monkeypatch.setattr("criba.intelligence.sources.transport.time.sleep", lambda delay: None)
    calls = []

    def sender(*args, **kwargs):
        calls.append(1)
        return Response(503 if len(calls) == 1 else 200, "{}")

    transport = Transport(sender=sender)
    assert transport.get("https://example.test").status == 200
    assert transport.thread_request_count == transport.budget.requests_made == 2


def test_long_server_rate_limit_is_reported_without_early_retry():
    calls = []

    def sender(*args, **kwargs):
        calls.append(1)
        return Response(429, "rate limited", {"Retry-After": "300"})

    transport = Transport(sender=sender)
    assert transport.get("https://example.test").status == 429
    assert len(calls) == transport.thread_request_count == 1


def test_document_update_removes_old_fts_terms_and_fragments(tmp_path):
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    original = EvidenceDocument(
        doc_id="stable",
        title="Obsolete cooling",
        abstract="photonic",
        fragments=[EvidenceFragment("old fragment")],
    )
    store.save_document(original.to_dict())
    rowid = store._conn.execute(
        "SELECT rowid FROM intel_documents WHERE doc_id='stable'"
    ).fetchone()[0]
    updated = EvidenceDocument(
        doc_id="stable",
        title="Battery storage",
        abstract="electrochemical",
        fragments=[EvidenceFragment("new fragment")],
    )
    store.save_document(updated.to_dict())
    assert store.search_documents("photonic") == []
    assert store.search_documents("electrochemical")[0]["doc_id"] == "stable"
    assert store.get_document("stable")["fragments"] == [
        {
            "fragment_id": updated.fragments[0].fragment_id,
            "text": "new fragment",
            "locator": "",
            "language": "en",
            "epistemic_state": "INFERENCE",
        }
    ]
    assert (
        store._conn.execute("SELECT rowid FROM intel_documents WHERE doc_id='stable'").fetchone()[0]
        == rowid
    )


def test_failed_document_batch_rolls_back_document_fts_and_fragments(tmp_path):
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    stable = EvidenceDocument(
        doc_id="stable",
        title="Original cooling",
        abstract="original",
        fragments=[EvidenceFragment("original fragment", fragment_id="shared")],
    )
    store.save_document(stable.to_dict())
    collision = EvidenceDocument(
        doc_id="second",
        title="Failed update",
        abstract="broken",
        fragments=[EvidenceFragment("collision", fragment_id="shared")],
    )
    with pytest.raises(sqlite3.IntegrityError):
        store.save_documents([collision.to_dict()])
    assert store.get_document("second") is None
    assert store.get_document("stable")["fragments"][0]["text"] == "original fragment"
    assert store.search_documents("broken") == []
    assert store.search_documents("original")[0]["doc_id"] == "stable"


def test_concurrent_cache_writes_and_document_updates_do_not_commit_partial_transactions(tmp_path):
    store = IntelligenceStore(tmp_path / "intel.sqlite3")

    def cache_work(n):
        store.cache_set(f"query:{n}", [n])
        return store.cache_get(f"query:{n}")

    def document_work(n):
        store.save_document(EvidenceDocument(doc_id=f"doc-{n}", title=f"Record {n}").to_dict())
        return n

    with ThreadPoolExecutor(max_workers=6) as executor:
        cache_futures = [executor.submit(cache_work, n) for n in range(30)]
        doc_futures = [executor.submit(document_work, n) for n in range(30)]
        assert [future.result() for future in cache_futures] == [[n] for n in range(30)]
        assert [future.result() for future in doc_futures] == list(range(30))
    assert store._conn.execute("SELECT count(*) FROM intel_documents").fetchone()[0] == 30
