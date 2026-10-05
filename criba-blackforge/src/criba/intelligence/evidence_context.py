"""Bounded local retrieval for proposals; acquisition is not validation.

The snapshot freezes what a run actually delivered. Lexical overlap selects
documents for inspection, without asserting their truth or semantic relevance.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MAX_DOCUMENTS = 3
_STOP_WORDS = frozenset(
    "a al algo and are as at be by como con cual de del desde donde el en es esta "
    "este for from how in is la las lo los mas me mejorar mejora methods metodo "
    "metodos o of on or para por que reducir se sin su sus the to un una uno unos "
    "unas what which with y your quiero necesito generar ideas innovation "
    "can could should would improve reducing reduction tiempo time".split()
)


def _tokens(text: str, limit: int | None = 24) -> list[str]:
    normalized = "".join(
        char
        for char in unicodedata.normalize("NFKD", text.casefold())
        if not unicodedata.combining(char)
    )
    tokens = list(
        dict.fromkeys(
            token
            for token in re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)
            if len(token) >= 3 and not token.isdigit() and token not in _STOP_WORDS
        )
    )
    return tokens[:limit] if limit is not None else tokens


def fts_query(query: str) -> str:
    """Quote tokenizer-derived terms so punctuation cannot become FTS syntax."""
    return " OR ".join(f'"{token}"' for token in _tokens(query))


def _text(value: object, maximum: int) -> str:
    return value.strip()[:maximum] if isinstance(value, str) else ""


def _url(value: object) -> str:
    raw = _text(value, 2000)
    try:
        parts = urlsplit(raw)
        if parts.scheme not in {"https", "http"} or not parts.hostname:
            return ""
        hostname = parts.hostname
        if ":" in hostname:
            hostname = f"[{hostname}]"
        netloc = hostname + (f":{parts.port}" if parts.port else "")
        sensitive = {"token", "api_key", "apikey", "key", "authorization", "signature"}
        query = urlencode(
            [
                (key, val)
                for key, val in parse_qsl(parts.query, keep_blank_values=True)
                if key.casefold() not in sensitive
            ]
        )
        return urlunsplit((parts.scheme, netloc, parts.path, query, ""))[:1000]
    except ValueError:
        return ""


def _acquisition_context(store: Any, query: str) -> dict[str, Any]:
    context: dict[str, Any] = {
        "status": "UNKNOWN",
        "coverage": "UNKNOWN",
        "scientific_validation": "NOT_VALIDATED",
        "detail": "No recorded acquisition report; no documents does not establish novelty.",
    }
    try:
        report = store.get_latest_refresh_report()
    except Exception:  # noqa: BLE001 — failed acquisition history means unknown coverage
        return context
    if not isinstance(report, dict):
        return context
    queries = report.get("queries")
    query_terms = set(_tokens(query))
    query_match = (
        bool(query_terms)
        and isinstance(queries, list)
        and any(
            isinstance(item, str) and bool(query_terms.intersection(_tokens(item)))
            for item in queries
        )
    )
    per_source = report.get("per_source")
    sources = []
    if isinstance(per_source, list):
        for row in per_source[:16]:
            if not isinstance(row, dict):
                continue
            errors = row.get("errors")
            sources.append(
                {
                    "source_id": _text(row.get("source_id"), 100),
                    "successful_queries": row.get("ok") if type(row.get("ok")) is int else None,
                    "failed_queries": row.get("errores")
                    if type(row.get("errores")) is int
                    else None,
                    "errors": [_text(error, 240) for error in errors[:3]]
                    if isinstance(errors, list)
                    else [],
                    "offline_blocked": row.get("offline_blocked") is True,
                    "cached_queries": row.get("cached_queries")
                    if type(row.get("cached_queries")) is int
                    else None,
                    "network_queries": row.get("network_queries")
                    if type(row.get("network_queries")) is int
                    else None,
                }
            )
    context.update(
        {
            "status": _text(report.get("status") or report.get("state"), 80) or "RECORDED",
            "generated_at": _text(report.get("generated_at"), 80),
            "profile": _text(report.get("profile"), 80),
            "query_overlap": query_match,
            "network_acquisition": report.get("network_acquisition")
            if type(report.get("network_acquisition")) is bool
            else None,
            "persisted": report.get("persisted") if type(report.get("persisted")) is bool else None,
            # Neither a successful fetch nor a keyword overlap demonstrates exhaustive coverage.
            "coverage": "UNKNOWN",
            "sources": sources,
            "detail": "Latest recorded acquisition; lexical overlap only. Failed and unsearched "
            "sources leave coverage unknown. Fetched content is not independently validated.",
        }
    )
    return context


def retrieve_evidence_context(query: str, store: Any = None) -> dict[str, Any]:
    """Read at most 3 relevant local docs with source identity and retrieval date.

    ``store=None`` intentionally means no storage. Callers that want the shared
    application database must open it explicitly and own/close that connection.
    """
    context: dict[str, Any] = {
        "retrieval_status": "STORE_UNAVAILABLE" if store is None else "NO_MATCH",
        "retrieval_method": "BOUNDED_LEXICAL_TITLE_ABSTRACT",
        "documents": [],
        "acquisition": {
            "status": "UNKNOWN",
            "coverage": "UNKNOWN",
            "scientific_validation": "NOT_VALIDATED",
        },
    }
    if store is None:
        return context
    context["acquisition"] = _acquisition_context(store, query)
    terms = set(_tokens(query))
    if not terms:
        context["retrieval_status"] = "NO_SEARCH_TERMS"
        return context
    try:
        rows = store.search_documents(fts_query(query), limit=12) or []
        documents: list[dict[str, Any]] = []
        for row in rows[:12]:
            if not isinstance(row, dict):
                continue
            title, abstract = _text(row.get("title"), 300), _text(row.get("abstract"), 1600)
            matching = sorted(terms.intersection(_tokens(title + " " + abstract, limit=None)))
            if not matching:
                continue
            provenance = row.get("provenance")
            provenance = provenance if isinstance(provenance, dict) else {}
            documents.append(
                {
                    "doc_id": _text(row.get("doc_id"), 160),
                    "source_id": _text(row.get("source_id") or provenance.get("source_id"), 100),
                    "title": title,
                    "abstract": abstract,
                    "url": _url(row.get("url")),
                    "published": _text(row.get("published"), 80),
                    "retrieved_at": _text(provenance.get("retrieved_at"), 80) or "UNKNOWN",
                    "content_hash": _text(row.get("content_hash"), 128),
                    "matching_terms": matching,
                    "epistemic_status": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
                    "excerpt_truncated": len(str(row.get("abstract") or "")) > 1600,
                }
            )
            if len(documents) >= MAX_DOCUMENTS:
                break
        context["documents"] = documents
        context["retrieval_status"] = "RETRIEVED" if documents else "NO_MATCH"
    except Exception as exc:  # noqa: BLE001 — retrieval cannot fabricate evidence or abort proposals
        context["retrieval_status"] = "RETRIEVAL_FAILED"
        context["error_type"] = type(exc).__name__
    return context
