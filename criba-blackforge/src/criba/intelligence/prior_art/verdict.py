"""P10-T09: deterministic prior-art verdicts from bounded evidence."""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

from ..contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    SourceQueryResult,
)
from ..enums import PriorArtVerdict
from .skeptic import PriorArtSkepticReport


class PriorArtVerdictEngine:
    """Classify bounded evidence without inferring novelty from its absence."""

    def assess(
        self,
        candidate: InventionCandidate,
        results: Mapping[str, SourceQueryResult],
        skeptic: PriorArtSkepticReport,
        *,
        matches: Sequence[PriorArtMatch],
    ) -> PriorArtAssessment:
        """Return a conservative, deterministic prior-art assessment."""
        if not isinstance(candidate, InventionCandidate):
            raise TypeError("candidate must be an InventionCandidate")
        if not isinstance(results, Mapping) or not results:
            raise ValueError("results must be a non-empty mapping")
        if not isinstance(skeptic, PriorArtSkepticReport):
            raise TypeError("skeptic must be a PriorArtSkepticReport")
        if skeptic.candidate_id != candidate.candidate_id:
            raise ValueError("skeptic candidate_id must match candidate")
        # This verdict engine is public and is also called directly by the
        # mutation loop. A rejecting or fabricated skeptic report must never
        # be upgraded to SURVIVED_SEARCH merely because citations exist.
        if (
            not isinstance(skeptic.verdict, str)
            or skeptic.verdict not in ("requires_experiment", "survives_with_conditions")
        ):
            raise ValueError("SKEPTIC_VERDICT_INVALID")
        # The skeptic normally validates these producers, but this public
        # engine also accepts direct calls. In particular ok="false" is a
        # truthy string: never promote that fake success to source coverage.
        ordered_results = tuple(
            sorted(
                results.items(),
                key=lambda item: item[0] if isinstance(item[0], str) else "",
            )
        )
        for source_id, result in ordered_results:
            if not isinstance(source_id, str) or not isinstance(result, SourceQueryResult):
                raise TypeError("results must map source IDs to SourceQueryResult instances")
            if not source_id or source_id != source_id.strip():
                raise ValueError("SOURCE_ID_INVALID")
            if result.source_id != source_id:
                raise ValueError("result source_id must match its mapping key")
            if not isinstance(result.query_text, str) or not result.query_text.strip():
                raise ValueError("SOURCE_QUERY_INVALID")
            if type(result.ok) is not bool:
                raise TypeError("SOURCE_OK_NOT_BOOLEAN")
            if not isinstance(result.documents, list):
                raise TypeError("SOURCE_DOCUMENTS_NOT_LIST")
            seen_doc_ids: set[str] = set()
            for document in result.documents:
                if not isinstance(document, EvidenceDocument):
                    raise TypeError("SOURCE_DOCUMENT_TYPE_INVALID")
                if (
                    not isinstance(document.doc_id, str)
                    or not document.doc_id
                    or document.doc_id != document.doc_id.strip()
                    or document.source_id != source_id
                ):
                    raise ValueError("SOURCE_DOCUMENT_IDENTITY_INVALID")
                if document.doc_id in seen_doc_ids:
                    # Even an identical duplicate is not independent evidence.
                    # Different bodies under one ID are worse: ambiguous lineage.
                    raise ValueError("SOURCE_DOCUMENT_ID_COLLISION")
                seen_doc_ids.add(document.doc_id)

        structural_gaps = [
            f"source_failure:{source_id}"
            for source_id, result in ordered_results
            if not result.ok
        ]
        structural_gaps.extend(
            f"empty_source:{source_id}"
            for source_id, result in ordered_results
            if result.ok and not result.documents
        )
        structural_gaps.extend(
            f"missing_provenance:{source_id}:{document.doc_id}"
            for source_id, result in ordered_results
            for document in result.documents
            if result.ok and document.provenance is None
        )
        coverage_limitations = tuple(
            sorted({*skeptic.evidence_gaps, *structural_gaps})
        )
        # A report claiming experimental gaps while listing none is a
        # contradictory consumer input. Reject it rather than promote it.
        if skeptic.verdict == "requires_experiment" and not coverage_limitations:
            raise ValueError("SKEPTIC_VERDICT_CONTRADICTION")
        # A one-shot iterator is exhausted by the validation pass; sorting
        # it afterwards would silently erase every match and yield a false
        # SURVIVED_SEARCH. The documented contract is a replayable Sequence.
        if isinstance(matches, (str, bytes, bytearray)) or not isinstance(matches, Sequence):
            raise TypeError("matches must be a replayable sequence")
        if any(not isinstance(match, PriorArtMatch) for match in matches):
            raise TypeError("matches must contain PriorArtMatch instances")
        for match in matches:
            if not isinstance(match.doc, EvidenceDocument):
                raise TypeError("PriorArtMatch.doc must be EvidenceDocument")
            # A match may be carried forward across mutation rounds. Its
            # doc_id need not occur in this round, but its source must remain
            # within the same source universe. Arbitrary external documents
            # must not create PARTIAL_PRIOR_ART.
            if (
                not isinstance(match.doc.source_id, str)
                or match.doc.source_id not in results
                or not isinstance(match.doc.doc_id, str)
                or not match.doc.doc_id
                or match.doc.doc_id != match.doc.doc_id.strip()
            ):
                raise ValueError("MATCH_SOURCE_IDENTITY_INVALID")
            similarity = match.similarity
            if (
                isinstance(similarity, bool)
                or not isinstance(similarity, (int, float))
                or (isinstance(similarity, float) and not math.isfinite(similarity))
                or not 0 <= similarity <= 1
            ):
                raise ValueError("MATCH_SIMILARITY_INVALID")
        ordered_matches = sorted(
            matches,
            key=lambda match: (
                match.doc.source_id,
                match.doc.doc_id,
                match.match_kind,
                match.similarity,
            ),
        )
        if coverage_limitations:
            verdict = PriorArtVerdict.UNRESOLVED.value
        elif ordered_matches:
            verdict = PriorArtVerdict.PARTIAL_PRIOR_ART.value
        else:
            verdict = PriorArtVerdict.SURVIVED_SEARCH.value

        queries_executed = tuple(
            dict.fromkeys(result.query_text for _, result in ordered_results)
        )
        return PriorArtAssessment(
            candidate_id=candidate.candidate_id,
            verdict=verdict,
            matches=list(ordered_matches),
            coverage_limitations=coverage_limitations,
            queries_executed=queries_executed,
        )
