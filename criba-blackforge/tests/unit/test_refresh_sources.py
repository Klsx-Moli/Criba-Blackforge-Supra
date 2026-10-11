"""Tests del servicio «Actualizar fuentes» (mandato §6, Fase 2).

Cantidades reales, deduplicación honesta y offline que bloquea sin fingir
éxito. Todo con fuentes stub: cero red.
"""

from __future__ import annotations

import pytest
from criba.intelligence.contracts import EvidenceDocument, ProvenanceRecord, SourceQueryResult
from criba.intelligence.refresh import format_report, refresh_sources
from criba.intelligence.sources.transport import OfflineBlocked, Transport
from criba.intelligence.storage.store import IntelligenceStore


class _StubSource:
    """Fuente determinista inyectable: cuenta consultas, devuelve docs fijos."""

    SOURCE_ID = "stub"

    def __init__(self, documents: list[EvidenceDocument], fail_on: str | None = None) -> None:
        self._documents = documents
        self._fail_on = fail_on
        self.queries: list[str] = []

    def source_id(self) -> str:
        return self.SOURCE_ID

    def search(self, query: str, limit: int = 5, **params: object) -> SourceQueryResult:
        self.queries.append(query)
        if self._fail_on and self._fail_on in query:
            return SourceQueryResult(
                source_id=self.SOURCE_ID, query_text=query, ok=False, error="HTTP 503"
            )
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[d for d in self._documents if d.title][:limit],
        )


def _doc(url: str, title: str = "T") -> EvidenceDocument:
    return EvidenceDocument(
        source_id="stub",
        title=title,
        kind="paper",
        url=url,
        provenance=ProvenanceRecord(source_id="stub", url=url, method="api"),
    )


def test_report_shows_real_counts(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    source = _StubSource([_doc("https://x/1"), _doc("https://x/2")])
    report = refresh_sources(["q1"], store=store, sources=[source])
    assert report["totals"]["documentos"] == 2
    assert report["totals"]["nuevos"] == 2
    assert report["per_source"][0]["ok"] == 1
    assert source.queries == ["q1"]


def test_duplicates_and_modifications_are_classified(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    doc_a = _doc("https://x/1", "titulo uno")
    refresh_sources(["q"], store=store, sources=[_StubSource([doc_a, doc_a])])
    doc_a2 = _doc("https://x/1", "titulo uno CAMBIADO")
    doc_b = _doc("https://x/2", "otro")
    report = refresh_sources(["q"], store=store, sources=[_StubSource([doc_a2, doc_b])])
    t = report["totals"]
    assert t["duplicados"] == 0  # el dup interno de la 1ª pasada no llega a la 2ª
    assert t["modificados"] == 1  # misma URL, contenido distinto
    assert t["nuevos"] == 1
    # y tras repetir todo idéntico: todo duplicado
    report3 = refresh_sources(["q"], store=store, sources=[_StubSource([doc_b])])
    assert report3["totals"]["duplicados"] == 1


def test_source_error_is_not_absence_of_results() -> None:
    source = _StubSource([_doc("https://x/1")], fail_on="malo")
    report = refresh_sources(["bueno", "malo"], sources=[source])
    summary = report["per_source"][0]
    assert summary["errores"] == 1
    assert summary["documents"] >= 1
    assert any("HTTP 503" in e for e in summary["errors"])


def test_offline_blocks_stub_transport() -> None:
    transport = Transport(offline=True)
    with pytest.raises(OfflineBlocked):
        transport.get("https://example.org")


def test_offline_report_declares_block(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    report = refresh_sources(["q"], profile="general", store=store, offline=True)
    wiki = next(s for s in report["per_source"] if s["source_id"] == "wikipedia")
    assert wiki["offline_blocked"]
    assert report["totals"]["documentos"] == 0


def test_format_report_mentions_real_numbers(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "intel.sqlite3"))
    report = refresh_sources(["q"], store=store, sources=[_StubSource([_doc("https://x/9")])])
    text = format_report(report)
    assert "Nuevos: 1" in text
    assert "Errores: 0" in text


def test_refresh_rejects_blank_queries() -> None:
    with pytest.raises(ValueError):
        refresh_sources(["  "], sources=[])


# ---------------------------------------------------------------------------
# CH1-CH7 (megaprompt §21): huella de contenido vs identidad documental
# ---------------------------------------------------------------------------

from criba.intelligence.contracts import EvidenceFragment  # noqa: E402
from criba.intelligence.refresh import _doc_content_fingerprint, _doc_identity  # noqa: E402


def _rich_doc(**overrides):
    base = {
        "doc_id": "kev-2026-1111",
        "source_id": "cisa_kev",
        "title": "CVE-2026-1111: inyección de comandos",
        "kind": "kev_entry",
        "published": "2026-09-01",
        "language": "en",
        "url": "https://nvd.nist.gov/view/vuln/detail?vulnId=CVE-2026-1111",
        "abstract": "Parchear el dispositivo afectado.",
        "fragments": [
            EvidenceFragment(text="Actualizar a la versión 9.1", locator="requiredAction")
        ],
    }
    base.update(overrides)
    return EvidenceDocument(**base)


def test_ch1_identical_content_same_hash() -> None:
    assert _doc_content_fingerprint(_rich_doc()) == _doc_content_fingerprint(_rich_doc())


def test_ch2_abstract_change_changes_hash_and_classifies_modified(tmp_path) -> None:
    a = _rich_doc()
    b = _rich_doc(abstract="Parchear el dispositivo afectado URGENTEMENTE.")
    assert _doc_content_fingerprint(a) != _doc_content_fingerprint(b)
    store = IntelligenceStore(str(tmp_path / "i.sqlite3"))
    refresh_sources(["q"], store=store, sources=[_StubSource([a])])
    report = refresh_sources(["q"], store=store, sources=[_StubSource([b])])
    assert report["totals"]["modificados"] == 1


def test_ch3_fragment_change_changes_hash() -> None:
    a = _rich_doc()
    b = _rich_doc(
        fragments=[EvidenceFragment(text="Actualizar a la versión 9.2", locator="requiredAction")]
    )
    assert _doc_content_fingerprint(a) != _doc_content_fingerprint(b)


def test_ch4_volatile_provenance_does_not_change_hash() -> None:
    a = _rich_doc()
    b = _rich_doc()
    b.provenance = ProvenanceRecord(
        source_id="cisa_kev", url=b.url, method="api", retrieved_at="2099-01-01T00:00:00Z"
    )
    assert _doc_content_fingerprint(a) == _doc_content_fingerprint(b)


def test_ch5_random_fragment_id_does_not_change_hash() -> None:
    a = _rich_doc()
    b = _rich_doc(
        fragments=[
            EvidenceFragment(
                text="Actualizar a la versión 9.1",
                locator="requiredAction",
                fragment_id="frag-totalmente-distinto-1234",
            )
        ]
    )
    assert _doc_content_fingerprint(a) == _doc_content_fingerprint(b)


def test_ch6_identical_reacquisition_is_duplicate(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "i.sqlite3"))
    refresh_sources(["q"], store=store, sources=[_StubSource([_rich_doc()])])
    report = refresh_sources(["q"], store=store, sources=[_StubSource([_rich_doc()])])
    assert report["totals"]["duplicados"] == 1
    assert report["totals"]["nuevos"] == 0


def test_ch7_identity_preserved_when_content_changes(tmp_path) -> None:
    store = IntelligenceStore(str(tmp_path / "i.sqlite3"))
    refresh_sources(["q"], store=store, sources=[_StubSource([_rich_doc()])])
    changed = _rich_doc(abstract="Contenido sustantivo nuevo.")
    refresh_sources(["q"], store=store, sources=[_StubSource([changed])])
    stored = store.get_document(changed.doc_id)
    assert stored is not None  # misma identidad documental
    assert stored["abstract"] == "Contenido sustantivo nuevo."


def test_identity_prefers_stable_upstream_id_over_url() -> None:
    assert _doc_identity(_rich_doc()) == "cisa_kev|id:kev-2026-1111"
    no_id = _rich_doc(doc_id="doc_aleatorio_123")
    assert (
        _doc_identity(no_id)
        == "cisa_kev|url:https://nvd.nist.gov/view/vuln/detail?vulnId=CVE-2026-1111"
    )


def test_explicit_empty_sources_does_not_enable_network(monkeypatch) -> None:
    monkeypatch.setattr(
        "criba.intelligence.refresh._build_profile",
        lambda *a, **k: pytest.fail("unexpected source build"),
    )
    report = refresh_sources(["query"], sources=[])
    assert report["per_source"] == [] and report["totals"]["consultas"] == 0
    assert report["state"] == "error"


def test_queries_deduplicated_and_duplicate_totals_match(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    source = _StubSource([_doc("https://x/1"), _doc("https://x/1")])
    report = refresh_sources([" q   one ", "q one", "q two"], store=store, sources=[source])
    assert source.queries == ["q one", "q two"]
    assert report["queries"] == ["q one", "q two"]
    assert report["totals"]["documentos"] == 4
    assert report["totals"]["nuevos"] == 1
    assert report["totals"]["duplicados"] == 3
    assert sum(s["duplicados"] for s in report["per_source"]) == 3


def test_independent_sources_overlap_and_report_keeps_source_order() -> None:
    import threading

    barrier = threading.Barrier(3)

    class ParallelSource(_StubSource):
        def __init__(self, sid):
            super().__init__([])
            self.SOURCE_ID = sid

        def search(self, query, limit=5, **params):
            barrier.wait(timeout=3)
            return super().search(query, limit=limit)

    events = []
    report = refresh_sources(
        ["q"],
        sources=[ParallelSource(str(n)) for n in range(3)],
        max_workers=3,
        on_progress=events.append,
    )
    assert [s["source_id"] for s in report["per_source"]] == ["0", "1", "2"]
    assert report["totals"]["consultas"] == 3
    assert events[0]["source_ids"] == ["0", "1", "2"]
    assert events[-1]["phase"] == "completed"
    assert events[-1]["completed_queries"] == events[-1]["total_queries"] == 3
    assert all(
        event["summary"]["state"] == "success"
        for event in events
        if event["phase"] == "source_completed"
    )


def test_progress_is_after_real_persistence_and_failure_is_not_success(
    tmp_path, monkeypatch
) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")

    def fail_save(*args, **kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr(store, "save_document", fail_save)
    events = []
    report = refresh_sources(
        ["q"], sources=[_StubSource([_doc("https://x/1")])], store=store, on_progress=events.append
    )
    assert report["state"] == "error" and not report["persisted"]
    assert report["totals"]["nuevos"] == 0
    assert report["totals"]["persistence_errors"] == 1
    ended = next(event for event in events if event["phase"] == "query_completed")
    assert ended["summary"]["ok"] == 0
    assert "disk unavailable" in ended["summary"]["errors"][0]


def test_cancellation_stops_followup_queries_without_success() -> None:
    import threading

    cancellation = threading.Event()

    class CancellingSource(_StubSource):
        def search(self, query, limit=5, **params):
            cancellation.set()
            return super().search(query, limit=limit)

    source = CancellingSource([])
    report = refresh_sources(["one", "two"], sources=[source], cancel_event=cancellation)
    assert source.queries == ["one"]
    assert report["state"] == "cancelled" and report["cancelled_queries"] == 1
    assert report["per_source"][0]["state"] == "cancelled"


def test_shared_url_different_sources_do_not_collide(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    a, b = _doc("https://same"), _doc("https://same")
    a.source_id, b.source_id = "a", "b"
    report = refresh_sources(["q"], store=store, sources=[_StubSource([a, b])])
    assert report["totals"]["nuevos"] == 2
    assert a.doc_id != b.doc_id


def test_generated_adapter_ids_do_not_overwrite_unrelated_documents(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    a, b = _doc("https://a"), _doc("https://b")
    a.doc_id = b.doc_id = "gh_00000001"
    refresh_sources(["q"], store=store, sources=[_StubSource([a])])
    refresh_sources(["q"], store=store, sources=[_StubSource([b])])
    assert store.get_document(a.doc_id)["url"] == "https://a"
    assert store.get_document(b.doc_id)["url"] == "https://b"


def test_stable_id_distinguishes_resources_with_same_url(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    a, b = _doc("https://catalog"), _doc("https://catalog")
    a.doc_id, b.doc_id = "upstream-a", "upstream-b"
    report = refresh_sources(["q"], store=store, sources=[_StubSource([a, b])])
    assert report["totals"]["nuevos"] == 2


def test_general_refresh_covers_science_code_patents_and_context(monkeypatch) -> None:
    monkeypatch.delenv("CRIBA_IIE_EXTRA_SOURCES", raising=False)
    report = refresh_sources(["q"], profile="general", offline=True)
    assert [s["source_id"] for s in report["per_source"]] == [
        "crossref",
        "github",
        "wikipedia",
        "google_patents",
    ]
    assert report["totals"]["http_requests"] == 0 and report["state"] == "error"


def test_cache_reuse_keeps_nested_evidence_and_original_date(tmp_path) -> None:
    import json

    from criba.intelligence.sources import default_context
    from criba.intelligence.sources.transport import Response
    from criba.intelligence.sources.wikipedia import WikipediaSource

    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    context = default_context(cache=store)
    calls = []

    def sender(*args, **kwargs):
        calls.append(1)
        return Response(
            200,
            json.dumps(
                {
                    "query": {
                        "search": [{"title": "Cooling", "pageid": 42, "snippet": "Passive cooling"}]
                    }
                }
            ),
        )

    context.transport._sender = sender
    source = WikipediaSource(context)
    first = refresh_sources(["cooling"], store=store, sources=[source])
    source.context.offline = True
    second = refresh_sources(["cooling"], store=store, sources=[source], offline=True)
    assert len(calls) == 1
    assert first["totals"]["http_requests"] == 1 and second["totals"]["http_requests"] == 0
    assert second["totals"]["cached_queries"] == second["totals"]["duplicados"] == 1
    assert first["per_source"][0]["retrieved_at"] == second["per_source"][0]["retrieved_at"]
    assert store.get_document("wp_42")["fragments"][0]["text"] == "Passive cooling"


def test_latest_reports_do_not_overwrite_same_second(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    first = refresh_sources(["first"], store=store, sources=[])
    second = refresh_sources(["second"], store=store, sources=[])
    assert first["run_id"] != second["run_id"]
    assert store.get_latest_refresh_report()["queries"] == ["second"]
    assert (
        store._conn.execute(
            "SELECT count(*) FROM intel_cache WHERE cache_key LIKE 'refresh:%'"
        ).fetchone()[0]
        == 2
    )


def test_duplicate_updates_provenance_without_replacing_fragment_ids(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    first = _rich_doc()
    first.provenance = ProvenanceRecord(source_id="cisa_kev", retrieved_at="2026-10-01T00:00:00Z")
    refresh_sources(["q"], store=store, sources=[_StubSource([first])])
    fragment_id = store.get_document(first.doc_id)["fragments"][0]["fragment_id"]
    reacquired = _rich_doc()
    reacquired.provenance = ProvenanceRecord(
        source_id="cisa_kev", retrieved_at="2026-10-05T00:00:00Z"
    )
    report = refresh_sources(["q"], store=store, sources=[_StubSource([reacquired])])
    stored = store.get_document(first.doc_id)
    assert report["totals"]["duplicados"] == 1
    assert stored["provenance"]["retrieved_at"] == "2026-10-05T00:00:00Z"
    assert stored["fragments"][0]["fragment_id"] == fragment_id


def test_duplicate_without_provenance_keeps_last_known_acquisition(tmp_path) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    first = _rich_doc()
    first.provenance = ProvenanceRecord(source_id="cisa_kev", retrieved_at="2026-10-01T00:00:00Z")
    refresh_sources(["q"], store=store, sources=[_StubSource([first])])
    report = refresh_sources(["q"], store=store, sources=[_StubSource([_rich_doc()])])
    assert report["totals"]["duplicados"] == 1
    assert store.get_document(first.doc_id)["provenance"]["retrieved_at"] == "2026-10-01T00:00:00Z"


def test_legacy_cache_without_retrieval_date_remains_unknown() -> None:
    from criba.intelligence.sources.protocol import document_from_dict

    restored = document_from_dict(
        {"doc_id": "legacy", "source_id": "stub", "provenance": {"source_id": "stub"}}
    )
    assert restored.provenance.retrieved_at == ""


@pytest.mark.parametrize("prefix", ["oa", "gh", "cr", "ct", "nsf", "ax", "pat"])
def test_reacquired_adapter_id_does_not_create_new_resource(tmp_path, prefix) -> None:
    store = IntelligenceStore(tmp_path / "intel.sqlite3")
    first, second = _doc("https://same/resource"), _doc("https://same/resource")
    first.doc_id, second.doc_id = f"{prefix}_00000001", f"{prefix}_00000002"
    refresh_sources(["q"], store=store, sources=[_StubSource([first])])
    report = refresh_sources(["q"], store=store, sources=[_StubSource([second])])
    assert report["totals"]["duplicados"] == 1 and report["totals"]["nuevos"] == 0
