"""Servicio «Actualizar fuentes»: adquisición real → deduplicación → informe.

Mandato §6: el botón adquiere información, la normaliza, deduplica, guarda y
muestra resultados REALES (nuevos/modificados/duplicados/errores por fuente).
Sin porcentajes sintéticos ni éxito sin adquisición. Reutilizable desde GUI,
CLI, API y MCP. El modo offline se resuelve en el transporte: aquí solo se
declara y el informe muestra el bloqueo, nunca «0 errores».
"""

from __future__ import annotations

import copy
import hashlib
import json
import queue
import threading
import time
import uuid
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from .contracts import EvidenceDocument
from .sources import build_sources, default_context
from .sources.adapters import CrossrefSource, GitHubSource
from .sources.security_feeds import CisaKevSource, MitreAttackSource
from .sources.transport import TransportBudget
from .storage.store import IntelligenceStore

# Perfiles de actualización (mandato §6)
PROFILE_GENERAL = ("crossref", "github", "wikipedia", "google_patents")
PROFILE_BLACKFORGE = ("cisa_kev", "mitre_attack")
PROFILE_EXTRA = ("openalex", "arxiv", "epo", "clinicaltrials", "nsf_awards")


def default_store() -> IntelligenceStore | None:
    """Almacén de evidencia por defecto (%LOCALAPPDATA%/CRIBA-Blackforge).

    Compartido por GUI, CLI, API y MCP para que el intérprete reciba
    evidencia local en todos los recorridos. None si no puede abrirse.
    """
    import os
    from pathlib import Path

    try:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
        base.mkdir(parents=True, exist_ok=True)
        return IntelligenceStore(base / "intelligence.sqlite3")
    except Exception:  # noqa: BLE001 — sin almacén, ejecución sin evidencia local
        return None


def _doc_identity(doc: EvidenceDocument) -> str:
    """Identidad documental: ¿es el mismo recurso upstream?

    Preferencia: identificador estable del adaptador (CVE/DOI/Txxx — los
    doc_id generados aleatoriamente NO son identidad) → URL canónica →
    source+título como último recurso. NO describe el contenido.
    """
    if doc.doc_id and not doc.doc_id.startswith(
        ("doc_", "oa_", "gh_", "cr_", "ct_", "nsf_", "ax_", "pat_", "kev_", "attack_")
    ):
        return f"{doc.source_id}|id:{doc.doc_id}"
    if doc.url:
        return f"{doc.source_id}|url:{doc.url}"
    return f"{doc.source_id}|title:{_norm(doc.title)}"


def _norm(value: Any) -> str:
    """Normalización determinista: colapsa espacios, casefold."""
    return " ".join(str(value or "").split()).casefold()


def _doc_content_fingerprint(doc: EvidenceDocument) -> str:
    """Huella de CONTENIDO sustantivo (megaprompt §18-§20): cambia si y solo
    si cambia el contenido lógico del documento. Excluye explícitamente los
    campos volátiles: retrieved_at, timestamps, ids aleatorios de fragmento,
    previous_hash y metadatos no estables.

    Serialización canónica: JSON con claves ordenadas y separadores compactos,
    UTF-8; fragmentos ordenados por su TEXTO normalizado (no por id aleatorio).
    """
    fragments = sorted(_norm(f.text) for f in doc.fragments if _norm(f.text))
    canonical = {
        "title": _norm(doc.title),
        "kind": _norm(doc.kind),
        "published": _norm(doc.published),
        "language": _norm(doc.language),
        "abstract": _norm(doc.abstract),
        "fragments": fragments,
    }
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _doc_fingerprint(doc: EvidenceDocument) -> str:
    """Compatibilidad con llamadas existentes: huella de contenido."""
    return _doc_content_fingerprint(doc)


def _build_profile(
    profile: str,
    *,
    offline: bool,
    extra: bool = False,
    credentials: dict[str, str] | None = None,
    cache: IntelligenceStore | None = None,
    budget: TransportBudget | None = None,
) -> list[Any]:
    context = default_context(cache=cache, credentials=credentials, offline=offline, budget=budget)
    if profile == "blackforge":
        return [CisaKevSource(context), MitreAttackSource(context)]
    sources = build_sources(context, extra=extra)
    if profile == "general":
        # Scholarship/code + encyclopedic/patent coverage, all key-less.
        # Optional/credential-dependent registries keep their explicit opt-in.
        ids = {source.source_id() for source in sources}
        sources.extend(
            cls(context) for cls in (CrossrefSource, GitHubSource) if cls.SOURCE_ID not in ids
        )
        order = {"crossref": 0, "github": 1}
        return sorted(sources, key=lambda s: order.get(s.SOURCE_ID, 9))
    return sources


def refresh_sources(
    queries: list[str],
    *,
    profile: str = "general",
    store: IntelligenceStore | None = None,
    offline: bool = False,
    extra: bool = False,
    credentials: dict[str, str] | None = None,
    per_query_limit: int = 5,
    sources: list[Any] | None = None,
    max_workers: int = 3,
    on_progress: Callable[[dict[str, Any]], None] | None = None,
    cancel_event: threading.Event | None = None,
    budget: TransportBudget | None = None,
) -> dict[str, Any]:
    """Ejecuta la actualización y devuelve un informe con cantidades reales.

    Cada documento se deduplica por URL/contenido contra el almacén:
    ``nuevo`` / ``modificado`` / ``duplicado``. Los fallos de fuente se
    muestran como errores; un error NO equivale a «sin resultados».
    """
    if not queries or all(not q.strip() for q in queries):
        raise ValueError("se necesita al menos una consulta no vacía")
    if (
        not isinstance(max_workers, int)
        or isinstance(max_workers, bool)
        or not 1 <= max_workers <= 8
    ):
        raise ValueError("max_workers debe estar entre 1 y 8")
    if (
        not isinstance(per_query_limit, int)
        or isinstance(per_query_limit, bool)
        or not 1 <= per_query_limit <= 50
    ):
        raise ValueError("per_query_limit debe estar entre 1 y 50")
    clean_queries = list(dict.fromkeys(" ".join(q.split()) for q in queries if q.strip()))
    run_store = store  # None → adquisición sin persistencia (informe puro)
    shared_budget = budget or TransportBudget(max_requests=40, max_runtime_s=120.0)
    active_sources = (
        sources
        if sources is not None
        else _build_profile(
            profile,
            offline=offline,
            extra=extra,
            credentials=credentials,
            cache=run_store,
            budget=shared_budget,
        )
    )
    cancellation = cancel_event or threading.Event()
    for source in active_sources:
        transport = getattr(getattr(source, "context", None), "transport", None)
        if transport is not None and hasattr(transport, "cancel_event"):
            transport.cancel_event = cancellation

    started = time.monotonic()
    per_source: list[dict[str, Any]] = [
        {
            "source_id": source.source_id(),
            "ok": 0,
            "documents": 0,
            "nuevos": 0,
            "modificados": 0,
            "duplicados": 0,
            "errores": 0,
            "errors": [],
            "offline_blocked": False,
            "completed_queries": 0,
            "total_queries": len(clean_queries),
            "http_requests": 0,
            "request_count_complete": True,
            "cached_queries": 0,
            "network_queries": 0,
            "persistence_errors": 0,
            "unpersisted_documents": 0,
            "retrieved_at": [],
            "state": "pending",
        }
        for source in active_sources
    ]
    seen: dict[str, str] = {}
    events: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=max_workers * 2)
    completed_queries = 0
    total_queries = len(clean_queries) * len(active_sources)
    progress_errors: list[str] = []

    def emit(phase: str, index: int | None = None, **details: Any) -> None:
        event = {
            "phase": phase,
            "source_id": per_source[index]["source_id"] if index is not None else "",
            "state": per_source[index]["state"]
            if index is not None
            else details.get("state", "running"),
            "completed_queries": completed_queries,
            "total_queries": total_queries,
            **details,
        }
        if index is not None:
            event["source_completed_queries"] = per_source[index]["completed_queries"]
            event["source_total_queries"] = len(clean_queries)
            event["summary"] = copy.deepcopy(per_source[index])
        if on_progress is not None:
            try:
                on_progress(event)
            except Exception as exc:  # noqa: BLE001 - a presentation failure cannot discard evidence
                progress_errors.append(type(exc).__name__)

    def acquire(index: int, source: Any) -> None:
        events.put({"phase": "source_started", "index": index})
        try:
            for query in clean_queries:
                if cancellation.is_set():
                    break
                events.put({"phase": "query_started", "index": index, "query": query})
                transport = getattr(getattr(source, "context", None), "transport", None)
                before = getattr(transport, "thread_request_count", None)
                try:
                    result = source.search(query, limit=per_query_limit)
                    error = ""
                except Exception as exc:  # noqa: BLE001 - independent sources continue after failure
                    result, error = None, f"{type(exc).__name__}: {exc}"
                after = getattr(transport, "thread_request_count", None)
                measured = before is not None and after is not None
                request_count = (
                    after - before
                    if before is not None and after is not None
                    else getattr(result, "request_count", 0)
                )
                info = dict(getattr(source, "last_search_info", {}))
                events.put(
                    {
                        "phase": "query_result",
                        "index": index,
                        "query": query,
                        "result": result,
                        "error": error,
                        "http_requests": request_count,
                        "request_count_complete": measured or result is not None,
                        "info": info,
                    }
                )
        finally:
            events.put({"phase": "source_finished", "index": index})

    emit(
        "started",
        source_ids=[item["source_id"] for item in per_source],
        queries=clean_queries,
        persistence_enabled=run_store is not None,
    )
    finished_sources = 0
    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="criba-source") as executor:
        futures = [
            executor.submit(acquire, index, source) for index, source in enumerate(active_sources)
        ]
        while finished_sources < len(active_sources):
            event = events.get()
            index, phase = event["index"], event["phase"]
            summary = per_source[index]
            if phase == "source_started":
                summary["state"] = "querying"
                emit(phase, index)
            elif phase == "query_started":
                emit(phase, index, query=event["query"])
            elif phase == "source_finished":
                finished_sources += 1
                if cancellation.is_set() or summary["completed_queries"] < len(clean_queries):
                    summary["state"] = "cancelled"
                elif summary["errores"]:
                    summary["state"] = "partial" if summary["ok"] else "error"
                else:
                    summary["state"] = "success"
                emit("source_completed", index)
            else:
                completed_queries += 1
                summary["completed_queries"] += 1
                summary["http_requests"] += event["http_requests"]
                summary["request_count_complete"] &= event["request_count_complete"]
                info, query, result = event["info"], event["query"], event["result"]
                for error in info.get("cache_errors", []):
                    summary["errors"].append(f"{query}: {error}")
                    summary["errores"] += 1
                if result is None or not result.ok:
                    error = event["error"] or result.error or "sin respuesta"
                    summary["errores"] += 1
                    summary["errors"].append(f"{query}: {error}")
                    summary["offline_blocked"] |= "OFFLINE" in error.upper()
                else:
                    summary["documents"] += len(result.documents)
                    summary["cached_queries"] += int(bool(info.get("cache_hit")))
                    summary["network_queries"] += int(event["http_requests"] > 0)
                    query_failed = False
                    for doc in result.documents:
                        try:
                            identity, fp = _doc_identity(doc), _doc_fingerprint(doc)
                            if doc.provenance and doc.provenance.retrieved_at:
                                summary["retrieved_at"].append(doc.provenance.retrieved_at)
                            if seen.get(identity) == fp:
                                summary["duplicados"] += 1
                                continue
                            if run_store is not None:
                                status = _persist(run_store, doc, fp)
                                summary[status] += 1
                            else:
                                summary["unpersisted_documents"] += 1
                            seen[identity] = fp
                        except Exception as exc:  # noqa: BLE001 - failed storage is never counted as success
                            query_failed = True
                            summary["errores"] += 1
                            summary["persistence_errors"] += 1
                            summary["unpersisted_documents"] += 1
                            summary["errors"].append(
                                f"{query}: persistencia {type(exc).__name__}: {exc}"
                            )
                    if not query_failed:
                        summary["ok"] += 1
                emit("query_completed", index, query=query)
        for future in futures:
            future.result()

    totals = {
        "consultas": completed_queries,
        "documentos": sum(s["documents"] for s in per_source),
        **{
            key: sum(s[key] for s in per_source)
            for key in (
                "nuevos",
                "modificados",
                "duplicados",
                "errores",
                "http_requests",
                "cached_queries",
                "network_queries",
                "persistence_errors",
                "unpersisted_documents",
            )
        },
    }
    cancelled = cancellation.is_set()
    state = (
        "cancelled"
        if cancelled
        else "partial"
        if totals["errores"] and any(s["ok"] for s in per_source)
        else "error"
        if totals["errores"] or not active_sources
        else "success"
    )

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
        "profile": profile,
        "run_id": uuid.uuid4().hex,
        "state": state,
        "offline": offline,
        "queries": clean_queries,
        "elapsed_s": round(time.monotonic() - started, 2),
        "per_source": per_source,
        "totals": totals,
        "total_queries": total_queries,
        "cancelled_queries": total_queries - completed_queries,
        "persistence_enabled": run_store is not None,
        "persisted": run_store is not None and not totals["persistence_errors"],
        "report_persisted": run_store is not None,
        "progress_errors": progress_errors,
        "network_acquisition": totals["network_queries"] > 0,
    }
    if run_store is not None:
        try:
            run_store.save_refresh_report(report)
        except Exception as exc:  # noqa: BLE001 - report failure must be visible too
            report["report_persisted"] = False
            report["state"] = "partial" if any(s["ok"] for s in per_source) else "error"
            report["report_error"] = f"{type(exc).__name__}: {exc}"
            totals["errores"] += 1
    emit("completed", state=report["state"], report=copy.deepcopy(report))
    return report


def _persist(store: IntelligenceStore, doc: EvidenceDocument, fp: str) -> str:
    """Guarda el documento clasificándolo nuevo/modificado/duplicado."""
    identity = _doc_identity(doc)
    unstable = "|id:" not in identity
    deterministic_id = "evidence_" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:32]
    existing = (
        store.find_document_identity(doc.source_id, doc_id=doc.doc_id) if not unstable else None
    )
    if existing is None:
        existing = store.find_document_identity(doc.source_id, doc_id=deterministic_id)
    if existing is None and unstable and doc.url:
        existing = store.find_document_identity(doc.source_id, url=doc.url)
    if existing:
        if existing.get("content_hash") == fp:
            # Refresh acquisition provenance (cache retains its original date).
            doc.doc_id = existing["doc_id"]
            metadata = json.loads(existing.get("metadata") or "{}")
            previous_provenance = json.loads(existing.get("provenance") or "{}")
            provenance = doc.provenance.to_dict() if doc.provenance else previous_provenance
            if not provenance.get("retrieved_at") and previous_provenance.get("retrieved_at"):
                provenance = previous_provenance
            store.update_document_provenance(
                doc.doc_id,
                provenance,
                {**metadata, **doc.metadata},
            )
            return "duplicados"
        doc.doc_id = existing["doc_id"]  # misma identidad, contenido nuevo
        doc.metadata = {**doc.metadata, "previous_hash": existing.get("content_hash")}
        store.save_document({**doc.to_dict(), "content_hash": fp})
        return "modificados"
    if unstable or store.get_document(doc.doc_id) is not None:
        doc.doc_id = deterministic_id
    store.save_document({**doc.to_dict(), "content_hash": fp})
    return "nuevos"


def format_report(report: dict[str, Any]) -> str:
    """Líneas legibles con las cantidades reales del informe."""
    t = report["totals"]
    lines = [
        f"Actualizar fuentes ({report['profile']}{' · OFFLINE' if report['offline'] else ''})",
        f"Consultas: {t['consultas']} · Documentos: {t['documentos']} · "
        f"Nuevos: {t['nuevos']} · Modificados: {t['modificados']} · "
        f"Duplicados: {t['duplicados']} · Errores: {t['errores']}",
    ]
    for s in report["per_source"]:
        state = (
            f"{s['source_id']}: {s['documents']} docs "
            f"({s['nuevos']} nuevos, {s['duplicados']} duplicados)"
        )
        if s["offline_blocked"]:
            state += " · BLOQUEADO por modo offline"
        if s["errors"]:
            state += f" · errores: {'; '.join(s['errors'][:3])}"
        lines.append("  " + state)
    return "\n".join(lines)
