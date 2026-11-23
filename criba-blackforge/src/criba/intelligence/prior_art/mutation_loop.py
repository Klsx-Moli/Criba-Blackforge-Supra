"""P10-T10: bounded mutation/re-search loop over a PriorArtAssessment.

El loop consume la salida de P10-T09 (PriorArtAssessment) y re-busca con
variantes mutadas del mecanismo-candidato. No infiere PROVEN_NEW ni novedad;
reclasifica UNRESOLVED como fail-closed. Reusa el motor determinista de
CrossDomainScout -> PriorArtSkeptic -> PriorArtVerdictEngine.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass

from ..contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    QueryVariant,
)
from ..enums import PriorArtVerdict
from .protocol import AdversarialSearchProtocol
from .scouts import CrossDomainScout
from .skeptic import PriorArtSkeptic
from .verdict import PriorArtVerdictEngine


@dataclass(frozen=True)
class MutationResult:
    """Resultado final del loop de mutación/re-busqueda."""

    verdict: str
    rounds_completed: int
    mutations_completed: int
    queries_executed: tuple[str, ...]
    assessments_by_round: tuple[str, ...]


def _mutate_query(candidate: InventionCandidate, round_idx: int) -> QueryVariant:
    """Produce un QueryVariant mutado del mecanismo del candidato.

    Es determinista y dependiente del round para que las corridas sean
    reproducibles sin proveedor ni red.
    """
    base = candidate.mechanism or candidate.title or candidate.description
    if not base.strip():
        base = candidate.candidate_id
    mutated_text = base.strip()
    if round_idx == 0:
        return QueryVariant(text=mutated_text, origin="original")
    suffixes = (" alternative", " improvement", " variant", " approach", " method")
    suffix = suffixes[(round_idx - 1) % len(suffixes)]
    return QueryVariant(text=mutated_text + suffix, origin="mutation")


def _material_document_identity(doc: EvidenceDocument) -> tuple[object, ...]:
    """Stable content fields for SAME source/doc_id, excluding retrieval time.

    This is an intra-run collision sentinel, not a content authenticity proof.
    Legacy dict provenance is read defensively without promoting it to FACT.
    """
    provenance = doc.provenance
    if isinstance(provenance, Mapping):
        provenance_url = provenance.get("url", "")
        provenance_hash = provenance.get("raw_hash", "")
    else:
        provenance_url = getattr(provenance, "url", "")
        provenance_hash = getattr(provenance, "raw_hash", "")
    return (
        doc.source_id, doc.doc_id, doc.title, doc.kind, doc.published,
        doc.url, doc.abstract,
        tuple(
            (getattr(fragment, "text", None), getattr(fragment, "locator", None))
            for fragment in doc.fragments
        ),
        provenance_url, provenance_hash,
    )


def _execute_round(
    candidate: InventionCandidate,
    scout: CrossDomainScout,
    protocol: AdversarialSearchProtocol,
    skeptic: PriorArtSkeptic,
    verdict_engine: PriorArtVerdictEngine,
    variant: QueryVariant,
    prior_matches: Sequence[PriorArtMatch],
) -> PriorArtAssessment:
    """Ejecuta un round de busqueda + esceptico + veredicto sobre un variante."""
    results = scout.cross_search(variant, limit_per_source=5)
    # A prior-round match is allowed even when not retrieved again. But if a
    # later round reuses the SAME (source_id, doc_id) with different material
    # content, silently carrying the older match gives ambiguous lineage.
    # Fail closed without requiring a previous document to reappear.
    for prior_match in prior_matches:
        source_result = results.get(prior_match.doc.source_id)
        if source_result is None:
            continue
        for current_doc in source_result.documents:
            if current_doc.doc_id == prior_match.doc.doc_id and (
                _material_document_identity(current_doc)
                != _material_document_identity(prior_match.doc)
            ):
                raise ValueError("DOCUMENT_ID_CONTENT_COLLISION")
    report = skeptic.review(candidate, results)
    return verdict_engine.assess(candidate, results, report, matches=list(prior_matches))


def run_prior_art_mutation_loop(
    *,
    candidate: InventionCandidate,
    initial_assessment: PriorArtAssessment,
    protocol: AdversarialSearchProtocol,
    scout: CrossDomainScout,
) -> MutationResult:
    """Ejecuta el loop de mutación/re-busqueda de P10-T10.

    Contract (desde test_prior_art_mutation_loop.py):

    1. Si el assessment inicial es UNRESOLVED, falla cerrado con ValueError
       (match "UNRESOLVED"). No se muta ni se re-busca.
    2. Si el assessment es PARTIAL_PRIOR_ART o SURVIVED_SEARCH, se permite
       al menos un round de búsqueda, respetando max_prior_art_rounds y
       max_mutations_per_candidate del protocolo.
    3. El veredicto final nunca es PROVEN_NEW; siempre es UNRESOLVED,
       PARTIAL_PRIOR_ART o SURVIVED_SEARCH.
    4. El resultado conserva rounds_completed y mutations_completed acotados.

    Precedente: ADR P10-T09 prohíbe inferir PROVEN_NEW. El motor de veredicto
    P10-T09 falla cerrado sobre gaps; el loop solo re-busca variantes mutadas
    cuando la cobertura es suficiente (sin limitaciones).
    """
    # Three independently supplied IDs describe ONE scientific candidate.
    # Do not start a source search using an assessment (and its prior matches)
    # from another candidate, even if the assessment claims a valid verdict.
    if not isinstance(candidate, InventionCandidate):
        raise TypeError("candidate must be InventionCandidate")
    if not isinstance(initial_assessment, PriorArtAssessment):
        raise TypeError("initial_assessment must be PriorArtAssessment")
    if not isinstance(protocol, AdversarialSearchProtocol):
        raise TypeError("protocol must be AdversarialSearchProtocol")
    if not isinstance(scout, CrossDomainScout):
        raise TypeError("scout must be CrossDomainScout")
    if (
        candidate.candidate_id != initial_assessment.candidate_id
        or candidate.candidate_id != protocol.candidate_id
    ):
        raise ValueError("CANDIDATE_LINEAGE_MISMATCH")
    # UNRESOLVED remains a separate explicit fail-closed boundary below.
    if initial_assessment.verdict != PriorArtVerdict.UNRESOLVED.value:
        if initial_assessment.coverage_limitations:
            raise ValueError("INITIAL_COVERAGE_CONTRADICTION")
        if initial_assessment.verdict == PriorArtVerdict.SURVIVED_SEARCH.value:
            if initial_assessment.matches:
                raise ValueError("INITIAL_MATCHES_CONTRADICTION")
        if initial_assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value:
            if not initial_assessment.matches:
                raise ValueError("INITIAL_MATCHES_CONTRADICTION")
    if initial_assessment.verdict == PriorArtVerdict.UNRESOLVED.value:
        raise ValueError(
            f"P10-T10 refuses to mutate from UNRESOLVED assessment "
            f"(candidate={candidate.candidate_id}): fail-closed, no mutation "
            f"until evidence coverage is sufficient."
        )

    if initial_assessment.verdict not in (
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    ):
        raise ValueError(
            f"P10-T10 does not accept verdict '{initial_assessment.verdict}'; "
            f"only PARTIAL_PRIOR_ART or SURVIVED_SEARCH may be re-searched."
        )

    skeptic = PriorArtSkeptic()
    verdict_engine = PriorArtVerdictEngine()

    if not isinstance(initial_assessment.matches, list) or any(
        not isinstance(match, PriorArtMatch) for match in initial_assessment.matches
    ):
        raise TypeError("INITIAL_MATCHES_INVALID")

    rounds_completed = 0
    mutations_completed = 0
    all_queries: list[str] = list(initial_assessment.queries_executed)
    assessments: list[str] = [initial_assessment.verdict]
    # The assessment and its documents are mutable dataclasses. Preserve a
    # private snapshot for multi-round replay so a caller cannot rewrite an
    # earlier match while cross_search is running.
    current_matches = tuple(deepcopy(initial_assessment.matches))
    current_verdict = initial_assessment.verdict

    while protocol.can_execute(
        rounds_completed=rounds_completed,
        mutations_completed=mutations_completed,
    ):
        should_mutate = (
            protocol.can_mutate(mutations_completed=mutations_completed)
            and current_verdict == PriorArtVerdict.SURVIVED_SEARCH.value
        )

        if should_mutate:
            mutations_completed += 1

        round_idx = mutations_completed
        variant = _mutate_query(candidate, round_idx)
        all_queries.append(variant.text)

        assessment = _execute_round(
            candidate, scout, protocol, skeptic, verdict_engine,
            variant, current_matches,
        )

        rounds_completed += 1
        current_verdict = assessment.verdict
        assessments.append(current_verdict)
        current_matches = tuple(assessment.matches)

        all_queries.extend(assessment.queries_executed)

        if current_verdict == PriorArtVerdict.UNRESOLVED.value:
            break

    return MutationResult(
        verdict=current_verdict,
        rounds_completed=rounds_completed,
        mutations_completed=mutations_completed,
        queries_executed=tuple(dict.fromkeys(all_queries)),
        assessments_by_round=tuple(assessments),
    )
