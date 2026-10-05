"""IIE source protocol (P03-T01, blueprint §33).

IntelligenceSource: capabilities() / search() / fetch() / health().
States: AVAILABLE, DEGRADED, UNCONFIGURED, RATE_LIMITED, UNAVAILABLE, DISABLED.

Adapters are THIN: they build requests and normalize responses into
EvidenceDocument dicts. Transport (retries/rate/budget/cache) is injected —
tests never touch the network (§101).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from ..contracts import (
    EpistemicState,
    EvidenceDocument,
    EvidenceFragment,
    ProvenanceRecord,
    SourceQueryResult,
)

__all__ = ["IntelligenceSource", "SourceContext", "document_from_dict"]


def document_from_dict(payload: dict[str, Any]) -> EvidenceDocument:
    """Restore nested evidence contracts without replacing acquisition times."""
    data = dict(payload)
    data["fragments"] = [
        EvidenceFragment(
            **{
                **fragment,
                "epistemic_state": EpistemicState(fragment.get("epistemic_state", "INFERENCE")),
            }
        )
        if isinstance(fragment, dict)
        else fragment
        for fragment in data.get("fragments", [])
    ]
    provenance = data.get("provenance")
    if isinstance(provenance, dict):
        # A legacy/missing acquisition date is unknown, never "now".
        data["provenance"] = ProvenanceRecord(
            **{**provenance, "retrieved_at": provenance.get("retrieved_at", "")}
        )
    return EvidenceDocument(**data)


@dataclass
class SourceContext:
    """Injected dependencies for a source adapter (no globals)."""

    transport: Any  # Transport protocol: get(url, params) -> Response
    cache_get: Callable[[str], Any] | None = None
    cache_set: Callable[[str, Any, float], None] | None = None
    credentials: dict[str, str] = field(default_factory=dict)
    offline: bool = False  # defense in depth: gate also here

    def has_credential(self, name: str) -> bool:
        return bool(self.credentials.get(name))


class IntelligenceSource:
    """Base class. Subclasses set SOURCE_ID/NAME/KIND and implement
    _search()/health(); they must NOT import httpx directly."""

    SOURCE_ID: str = "abstract"
    NAME: str = "abstract"
    KIND: str = "abstract"
    BASE_URL: str = ""
    REQUIRES_CREDENTIALS: tuple[str, ...] = ()
    RATE_LIMIT_S: float = 1.0  # min seconds between requests
    TIMEOUT_S: float = 20.0

    def __init__(self, context: SourceContext):
        self.context = context
        self._last_request_ts: float = 0.0
        self.last_search_info: dict[str, Any] = {}

    # -- public API (§33) ----------------------------------------------------
    def capabilities(self) -> list[str]:
        return ["search"]

    def source_id(self) -> str:
        return self.SOURCE_ID

    def health(self) -> str:
        missing = [c for c in self.REQUIRES_CREDENTIALS if not self.context.has_credential(c)]
        if missing:
            return "UNCONFIGURED"
        return "AVAILABLE"

    def search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        """Template method: cache-first (§34), rate-limit, budget, then _search."""
        import time as _t

        self.last_search_info = {"cache_hit": False, "cache_errors": []}
        cache_key = f"src:{self.SOURCE_ID}:q:{query}:n:{limit}:{sorted(params.items())}"
        if self.context.cache_get is not None:
            try:
                cached = self.context.cache_get(cache_key)
                if cached is not None:
                    res = SourceQueryResult(source_id=self.SOURCE_ID, query_text=query, ok=True)
                    res.documents = [document_from_dict(d) for d in cached]
                    self.last_search_info["cache_hit"] = True
                    return res
            except (TypeError, ValueError, KeyError) as exc:
                self.last_search_info["cache_errors"].append(f"cache read: {exc}")

        # Offline gate (cache local ya servido): ninguna fuente puede red.
        if getattr(self.context, "offline", False):
            return SourceQueryResult(
                source_id=self.SOURCE_ID,
                query_text=query,
                ok=False,
                error="OFFLINE_BLOCKED",
            )

        now = _t.monotonic()
        wait = self._last_request_ts + self.RATE_LIMIT_S - now
        if wait > 0:
            _t.sleep(min(wait, self.RATE_LIMIT_S))
        self._last_request_ts = _t.monotonic()

        started = _t.monotonic()
        requests_before = getattr(self.context.transport, "thread_request_count", None)
        result = self._search(query, limit=limit, **params)
        requests_after = getattr(self.context.transport, "thread_request_count", None)
        if requests_before is not None and requests_after is not None:
            result.request_count = requests_after - requests_before
        result.elapsed_s = _t.monotonic() - started
        result.query_text = query

        if result.ok and self.context.cache_set is not None:
            try:
                self.context.cache_set(cache_key, [d.to_dict() for d in result.documents], 86400.0)
            except Exception as exc:  # noqa: BLE001 - acquisition is retained, cache failure is reported
                self.last_search_info["cache_errors"].append(f"cache write: {exc}")
        return result

    # -- subclass hook --------------------------------------------------------
    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        raise NotImplementedError

    def fetch(self, doc_id: str) -> EvidenceDocument | None:
        if getattr(self.context, "offline", False):
            return None
        return None
