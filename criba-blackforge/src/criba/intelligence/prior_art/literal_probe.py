"""F42: bounded literal candidate-mechanism evidence probe (NOT semantic proof).

Exact full-token occurrences are a screening cue only. Quoting, negation,
differing mechanisms and missing text make materiality UNKNOWN. Zero literal
hits MUST NOT be presented as no prior art or as a novelty result.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from typing import Any

from ..contracts import (
    EvidenceDocument,
    EvidenceFragment,
    InventionCandidate,
    ProvenanceRecord,
    SourceQueryResult,
)

_METHOD = "full_mechanism_token_sequence_v1"
_MAX_TOKENS = 128
_MAX_TEXT_CHARS = 32768
_MAX_FRAGMENTS = 20
_MAX_DOCUMENTS = 64
_WORDS = re.compile(r"[^\W_]+", re.UNICODE)


def _tokens(text: str) -> tuple[str, ...]:
    return tuple(
        token.casefold()
        for token in _WORDS.findall(unicodedata.normalize("NFKC", text))
    )


def _contains_exact(tokens: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    if not pattern or len(pattern) > len(tokens):
        return False
    # NUL cannot occur inside any regex-normalized token. Separators on
    # BOTH ends preserve word boundaries while Python's substring search
    # avoids repeated O(n * phrase_length) tuple comparisons.
    separator = chr(0)
    needle = separator + separator.join(pattern) + separator
    haystack = separator + separator.join(tokens) + separator
    return needle in haystack


@dataclass(frozen=True)
class LiteralCandidate:
    source_id: str
    doc_id: str
    field: str
    locator: str = ""


@dataclass(frozen=True)
class LiteralProbeResult:
    status: str
    mechanism_digest: str
    candidates: tuple[LiteralCandidate, ...]
    documents_scanned: int
    documents_unscanned: int
    sources_failed: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "method": _METHOD,
            "status": self.status,
            "mechanism_digest": self.mechanism_digest,
            "candidates": [asdict(candidate) for candidate in self.candidates],
            "documents_scanned": self.documents_scanned,
            "documents_unscanned": self.documents_unscanned,
            "sources_failed": self.sources_failed,
            # Even a full literal match is not an evidence-supported finding
            # that mechanisms, novelty or patent claims are equivalent.
            "materiality_assessed": False,
        }


def probe_literal_mechanism(
    candidate: InventionCandidate,
    results: Mapping[str, SourceQueryResult],
    *,
    max_documents: int = _MAX_DOCUMENTS,
) -> LiteralProbeResult:
    """Locate exact normalized mechanism phrases in bounded attributed text.

    Scans title/abstract/fragments from successful sources with traceable
    provenance. Never scans metadata, makes network calls or assigns scores.
    All invalid/skipped inputs remain explicitly NOT_ASSESSED.
    """
    if not isinstance(candidate, InventionCandidate):
        raise TypeError("candidate must be InventionCandidate")
    if not isinstance(results, Mapping):
        raise TypeError("results must be a mapping")
    if (
        type(max_documents) is not int
        or not 1 <= max_documents <= _MAX_DOCUMENTS
    ):
        raise ValueError("max_documents must be a positive integer at most 64")

    mechanism = candidate.mechanism if isinstance(candidate.mechanism, str) else ""
    phrase = _tokens(mechanism[:_MAX_TEXT_CHARS])
    valid_phrase = (
        len(mechanism) <= _MAX_TEXT_CHARS
        and 4 <= len(phrase) <= _MAX_TOKENS
    )
    digest = hashlib.sha256(
        " ".join(phrase).encode("utf-8")
    ).hexdigest() if valid_phrase else ""
    if not valid_phrase:
        return LiteralProbeResult("INDETERMINATE", digest, (), 0, 0, 0)

    candidates: list[LiteralCandidate] = []
    scanned = 0
    unscanned = 0
    failures = 0
    processed = 0
    for source_id, result in sorted(
        results.items(),
        key=lambda item: item[0] if isinstance(item[0], str) else "",
    ):
        if (
            not isinstance(source_id, str)
            or not source_id
            or source_id != source_id.strip()
            or len(source_id) > 128
            or not isinstance(result, SourceQueryResult)
            or result.source_id != source_id
            or type(result.ok) is not bool
            or not isinstance(result.documents, list)
            or not result.ok
        ):
            failures += 1
            continue
        if not result.documents:
            failures += 1
            continue
        # Never select an arbitrary body when a source repeats the same ID.
        # This is a preflight for the standalone probe (the verdict engine
        # has its own source-ID collision guard).
        identity_counts = Counter(
            doc.doc_id for doc in result.documents
            if isinstance(doc, EvidenceDocument) and isinstance(doc.doc_id, str)
        )
        ordered_docs = sorted(
            result.documents,
            key=lambda doc: doc.doc_id
            if isinstance(doc, EvidenceDocument) and isinstance(doc.doc_id, str)
            else "",
        )
        for index, doc in enumerate(ordered_docs):
            if processed >= max_documents:
                unscanned += len(ordered_docs) - index
                break
            processed += 1
            if not isinstance(doc, EvidenceDocument):
                unscanned += 1
                continue
            key = (source_id, doc.doc_id) if isinstance(doc.doc_id, str) else None
            provenance = doc.provenance
            if (
                key is None or not doc.doc_id
                or doc.doc_id != doc.doc_id.strip()
                or len(doc.doc_id) > 256
                or doc.source_id != source_id
                or identity_counts[doc.doc_id] != 1
                or not isinstance(provenance, ProvenanceRecord)
                or provenance.source_id != source_id
                or not isinstance(provenance.url, str)
                or not provenance.url.strip()
                or not isinstance(doc.title, str)
                or not isinstance(doc.abstract, str)
                or not isinstance(doc.fragments, list)
                or len(doc.fragments) > _MAX_FRAGMENTS
                or len(doc.title) > _MAX_TEXT_CHARS
                or len(doc.abstract) > _MAX_TEXT_CHARS
                or any(
                    not isinstance(fragment, EvidenceFragment)
                    or not isinstance(fragment.text, str)
                    or len(fragment.text) > _MAX_TEXT_CHARS
                    or not isinstance(fragment.locator, str)
                    or len(fragment.locator) > 256
                    for fragment in doc.fragments
                )
            ):
                unscanned += 1
                continue
            scanned += 1
            fields = [
                ("abstract", doc.abstract, ""),
                ("title", doc.title, ""),
            ]
            fields.extend(
                ("fragment", fragment.text, fragment.locator if isinstance(fragment.locator, str) else "")
                for fragment in doc.fragments
            )
            for field, text, locator in fields:
                if _contains_exact(_tokens(text), phrase):
                    candidates.append(LiteralCandidate(source_id, doc.doc_id, field, locator))
                    break  # at most one literal candidate per source document

    if candidates:
        status = "POTENTIAL_LITERAL_OVERLAP"
    elif scanned and not unscanned and not failures:
        status = "NO_LITERAL_OVERLAP_IN_SCANNED_TEXT"
    else:
        status = "INDETERMINATE"
    return LiteralProbeResult(
        status, digest, tuple(candidates), scanned, unscanned, failures,
    )
