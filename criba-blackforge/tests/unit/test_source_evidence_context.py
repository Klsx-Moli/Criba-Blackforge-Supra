"""Refresh → persisted corpus → actual proposal/critic transport, without network."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from criba.constants import FEATURES
from criba.intelligence.contracts import EvidenceDocument, ProvenanceRecord, SourceQueryResult
from criba.intelligence.evidence_context import fts_query, retrieve_evidence_context
from criba.intelligence.refresh import refresh_sources
from criba.intelligence.storage.store import IntelligenceStore
from criba.interprete import openai_compatible as oc
from criba.interprete.juez import JuezInterprete
from criba.interprete.pipeline import build_interprete_block
from criba.inventar import _default_proponer, invent
from criba.storage import Storage

from verification.interpreter_cases import critica, propuesta

IDEA = {
    "id": "source-c1",
    "method1": "Poka-Yoke",
    "method2": "Retroalimentación",
    "description": "Revisar registros antes de confirmar citas.",
    "causal_axes_changed": ["flujo", "feedback"],
    "convergence": {"novelty": 0.75},
}


@pytest.fixture
def corpus(tmp_path):
    store = IntelligenceStore(tmp_path / "evidence.sqlite3")
    yield store
    store.close()


def _save(
    store, *, doc_id="doc-citas", abstract="Campos incompletos generan retornos por registro."
):
    store.save_document(
        {
            "doc_id": doc_id,
            "source_id": "crossref",
            "title": "Registro de citas clínicas",
            "url": "https://example.test/paper/citas",
            "abstract": abstract,
            "content_hash": "hash-of-source-content",
            "provenance": {"source_id": "crossref", "retrieved_at": "2026-10-05T08:00:00Z"},
        }
    )


def _transport(monkeypatch):
    sent: list[dict[str, Any]] = []

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            sent.append(json)
            data = propuesta() if len(sent) % 2 else critica()
            if len(sent) % 2:
                data["evidencia_citada"] = [1]
            return httpx.Response(
                200,
                json={
                    "model": "test-model",
                    "choices": [
                        {
                            "finish_reason": "stop",
                            "message": {"content": __import__("json").dumps(data)},
                        }
                    ],
                },
            )

    monkeypatch.setattr(oc.httpx, "Client", Client)
    return sent


def test_fts_punctuation_accents_and_common_terms_do_not_break_retrieval(corpus):
    _save(corpus)
    corpus.save_document(
        {
            "doc_id": "unrelated",
            "title": "Mejorar tiempo en astronomía",
            "abstract": "Innovación para generar ideas sobre galaxias.",
        }
    )
    snapshot = retrieve_evidence_context(
        '¿Cómo reducir retornos? Citas-clínicas "registro"', corpus
    )
    assert snapshot["retrieval_status"] == "RETRIEVED"
    assert [doc["doc_id"] for doc in snapshot["documents"]] == ["doc-citas"]
    assert "reducir" not in fts_query("reducir tiempo de registro")
    assert fts_query('Citas-clínicas "registro"') == '"citas" OR "clinicas" OR "registro"'


def test_delivery_is_bounded_and_provenance_is_not_replaced_with_current_time(corpus):
    for index in range(5):
        _save(corpus, doc_id=f"document-{index}", abstract="Registro de citas " + "x " * 2000)
    docs = retrieve_evidence_context("registro citas", corpus)["documents"]
    assert len(docs) == 3
    assert all(len(doc["abstract"]) <= 1600 and doc["excerpt_truncated"] for doc in docs)
    assert all(doc["retrieved_at"] == "2026-10-05T08:00:00Z" for doc in docs)
    assert all(doc["source_id"] == "crossref" and doc["url"] for doc in docs)
    assert all(
        doc["epistemic_status"] == "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED" for doc in docs
    )


def test_missing_provenance_stays_unknown_and_url_secrets_are_not_delivered(corpus):
    corpus.save_document(
        {
            "doc_id": "legacy",
            "title": "Registro citas",
            "url": "https://username:password@example.test/path?token=secret&view=paper",
        }
    )
    doc = retrieve_evidence_context("registro", corpus)["documents"][0]
    assert doc["retrieved_at"] == "UNKNOWN"
    assert doc["url"] == "https://example.test/path?view=paper"
    assert "secret" not in json.dumps(doc) and "password" not in json.dumps(doc)


def test_unavailable_and_failing_store_leave_evidence_unknown():
    assert retrieve_evidence_context("citas")["retrieval_status"] == "STORE_UNAVAILABLE"

    class BrokenStore:
        def get_latest_refresh_report(self):
            raise RuntimeError("bad history")

        def search_documents(self, *_args, **_kwargs):
            raise RuntimeError("bad database")

    snapshot = retrieve_evidence_context("citas", BrokenStore())
    assert snapshot["retrieval_status"] == "RETRIEVAL_FAILED"
    assert snapshot["documents"] == []
    assert snapshot["acquisition"]["coverage"] == "UNKNOWN"
    assert snapshot["error_type"] == "RuntimeError"


def test_failed_acquisition_never_means_exhaustive_search(corpus):
    corpus.save_refresh_report(
        {
            "generated_at": "2026-10-05T08:05:00Z",
            "profile": "general",
            "status": "partial",
            "queries": ["registro citas"],
            "per_source": [
                {"source_id": "crossref", "ok": 1, "errores": 0, "errors": []},
                {"source_id": "github", "ok": 0, "errores": 1, "errors": ["HTTP 429"]},
            ],
        }
    )
    acquisition = retrieve_evidence_context("registro citas", corpus)["acquisition"]
    assert acquisition["query_overlap"] is True
    assert acquisition["coverage"] == "UNKNOWN"
    assert acquisition["scientific_validation"] == "NOT_VALIDATED"
    assert acquisition["sources"][1]["errors"] == ["HTTP 429"]


def test_refreshed_evidence_reaches_proposal_critic_and_invention_ledger(corpus, monkeypatch):
    doc = EvidenceDocument(
        doc_id="doi:sample",
        source_id="crossref",
        title="Registro de citas clínicas",
        abstract="Campos incompletos generan retornos por registro.",
        url="https://example.test/paper",
        provenance=ProvenanceRecord("crossref", retrieved_at="2026-10-05T08:00:00Z"),
    )

    class Source:
        def source_id(self):
            return "crossref"

        def search(self, query, limit=5):
            return SourceQueryResult("crossref", query, True, documents=[doc])

    refresh_sources(["registro citas"], store=corpus, sources=[Source()])
    sent = _transport(monkeypatch)
    interpreter = oc.OpenAICompatibleInterpreter(model="test-model")

    def propose(query, idea, domain, evidence=None):
        return _default_proponer(query, idea, domain, evidence=evidence, interprete=interpreter)

    sheet = invent(
        "Reducir retornos por registro de citas",
        seed=3,
        rounds=1,
        batch_size=4,
        top=1,
        sources=[],
        store=corpus,
        history_storage=False,
        proponer=propose,
    )
    entry = sheet["entries"][0]
    assert entry["estado_interpretacion"] == "PROPUESTA"
    assert len(sent) == 2
    for payload in sent:
        prompt = payload["messages"][1]["content"]
        assert "doi:sample" in prompt and "crossref" in prompt
        assert "2026-10-05T08:00:00Z" in prompt and "UNKNOWN" in prompt
    assert entry["evidence_delivered"][0]["doc_id"] == "doi:sample"
    assert entry["evidence_documented_as_used"] == entry["evidence_delivered"]
    assert entry["evidence_context"]["acquisition"]["coverage"] == "UNKNOWN"
    assert entry["judge"]["independent_validation"] is False


def test_engine_delivers_sources_and_changed_source_content_invalidates_cache(
    corpus, tmp_path, monkeypatch
):
    monkeypatch.setitem(FEATURES, "interprete_serendipia", True)
    _save(corpus)
    sent = _transport(monkeypatch)
    context = {
        "seed": 7,
        "database": str(tmp_path / "decisions.sqlite3"),
        "evidence_store": corpus,
        "interpreter": oc.OpenAICompatibleInterpreter(model="test-model"),
    }
    first = build_interprete_block("registro citas", [IDEA], context)
    assert first["interpretados"][0]["veredicto"] == "PROPUESTA"
    second = build_interprete_block("registro citas", [IDEA], context)
    assert second["interpretados"][0]["registro"] == "deduplicated"
    assert len(sent) == 2
    _save(corpus, abstract="Registro de citas: retornos persisten aunque se corrijan los campos.")
    third = build_interprete_block("registro citas", [IDEA], context)
    assert third["interpretados"][0]["registro"] == "recorded"
    assert len(sent) == 4
    assert "retornos persisten" in sent[2]["messages"][1]["content"]
    assert (
        first["interpretados"][0]["provenance"]["prompt_sha256"]
        != (third["interpretados"][0]["provenance"]["prompt_sha256"])
    )


def test_direct_judge_cache_revalidates_citations_against_delivered_documents(
    corpus, tmp_path, monkeypatch
):
    _save(corpus)
    sent = _transport(monkeypatch)
    evidence = retrieve_evidence_context("registro citas", corpus)["documents"]
    judge = JuezInterprete(
        storage=Storage(tmp_path / "judge.db"),
        interpreter=oc.OpenAICompatibleInterpreter(model="test-model"),
    )
    first = judge.interpretar_lote("registro citas", [IDEA], "a", "r", 7, evidence=evidence)
    second = judge.interpretar_lote("registro citas", [IDEA], "a", "r", 7, evidence=evidence)
    assert first["interpretados"][0]["interprete_verdict"] == "PROPUESTA"
    assert second["interpretados"][0]["_registro"]["status"] == "deduplicated"
    assert len(sent) == 2
    missing = judge.interpretar_lote("registro citas", [IDEA], "a", "r", 7, evidence=[])
    assert missing["interpretados"][0]["interprete_verdict"] == "PENDIENTE_INTERPRETACION"
    assert len(sent) == 3, "an out-of-range citation fails before critique"


def test_engine_flag_off_does_not_open_evidence_database(monkeypatch):
    monkeypatch.setitem(FEATURES, "interprete_serendipia", False)

    def fail():
        raise AssertionError("feature disabled must not open evidence storage")

    monkeypatch.setattr("criba.intelligence.refresh.default_store", fail)
    assert build_interprete_block("registro", [IDEA], {}) == {"applied": False}
