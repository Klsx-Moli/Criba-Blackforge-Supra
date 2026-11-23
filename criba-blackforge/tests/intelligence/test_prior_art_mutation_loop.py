"""P10-T10: mutation/re-search loop contract over PriorArtAssessment."""
from __future__ import annotations

from typing import Any

import pytest

from criba.intelligence.contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtMatch,
    SourceQueryResult,
)
from criba.intelligence.enums import PriorArtVerdict
from criba.intelligence.prior_art import (
    AdversarialSearchProtocol,
    CrossDomainScout,
    PriorArtSkeptic,
    PriorArtVerdictEngine,
    run_prior_art_mutation_loop,
)
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport, TransportBudget


class _DummyTransport(Transport):
    def __init__(self) -> None:
        super().__init__(sender=self._send, budget=TransportBudget(max_requests=100))

    def _send(self, url: str, params: dict[str, Any] | None = None,
              timeout: float = 20.0, headers: dict[str, Any] | None = None) -> Response:
        return Response(status=200, text="{}", headers={})


class _DummySource(IntelligenceSource):
    SOURCE_ID = "dummy"
    NAME = "Dummy Source"
    KIND = "test"

    def __init__(self, context: SourceContext):
        super().__init__(context)

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[],
        )


class _SecondDummySource(IntelligenceSource):
    SOURCE_ID = "dummy2"
    NAME = "Second Dummy Source"
    KIND = "science"

    def __init__(self, context: SourceContext):
        super().__init__(context)

    def _search(self, query: str, limit: int = 10, **params: Any) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[],
        )


class _CrossDomainScoutForLoop(CrossDomainScout):
    def __init__(self) -> None:
        transport = _DummyTransport()
        context = SourceContext(transport=transport)
        source1 = _DummySource(context)
        source2 = _SecondDummySource(context)
        super().__init__([source1, source2], budget=transport.budget)


class _CandidateFactory:
    @staticmethod
    def candidate() -> InventionCandidate:
        return InventionCandidate(
            candidate_id="cand_t10_001",
            title="Thermal management via phase change",
            description="A cooling system using phase change material",
            mechanism="Phase change material absorbs heat during melting",
            operators=("T063",),
        )


def _results_with_docs() -> dict[str, SourceQueryResult]:
    """Results where ALL sources have at least one document with provenance."""
    return {
        "dummy": SourceQueryResult(
            source_id="dummy",
            query_text="thermal management",
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id="doc_1",
                    source_id="dummy",
                    title="Phase change cooling",
                    provenance={"url": "https://example.com/patent/1"},
                )
            ],
        ),
        "dummy2": SourceQueryResult(
            source_id="dummy2",
            query_text="thermal management",
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id="doc_2",
                    source_id="dummy2",
                    title="Thermal management survey",
                    provenance={"url": "https://example.com/paper/1"},
                )
            ],
        ),
    }


def _empty_results() -> dict[str, SourceQueryResult]:
    return {
        "dummy": SourceQueryResult(
            source_id="dummy",
            query_text="thermal management",
            ok=True,
            documents=[],
        ),
        "dummy2": SourceQueryResult(
            source_id="dummy2",
            query_text="thermal management",
            ok=True,
            documents=[],
        ),
    }


def test_mutation_loop_fails_closed_when_assessment_is_unresolved() -> None:
    """A mutation loop must not start from an UNRESOLVED assessment."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _empty_results()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    # The loop should reject an UNRESOLVED input
    with pytest.raises(ValueError, match="UNRESOLVED"):
        run_prior_art_mutation_loop(
            candidate=candidate,
            initial_assessment=assessment,
            protocol=protocol,
            scout=scout,
        )


def test_mutation_loop_accepts_partial_prior_art_and_schedules_mutation() -> None:
    """A PARTIAL_PRIOR_ART assessment should allow a bounded mutation round."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    # Create a match to trigger PARTIAL_PRIOR_ART
    match = PriorArtMatch(
        doc=results["dummy"].documents[0],
        similarity=0.7,
        match_kind="literal",
        overlapping_terms=("thermal", "management"),
        scout="PatentScout",
    )
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[match])

    assert assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.verdict in (
        PriorArtVerdict.UNRESOLVED.value,
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    )
    assert "PROVEN_NEW" not in final.verdict


def test_mutation_loop_accepts_survived_search_and_may_mutate() -> None:
    """A SURVIVED_SEARCH assessment should allow mutation within budget."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    # No matches → SURVIVED_SEARCH
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert assessment.verdict == PriorArtVerdict.SURVIVED_SEARCH.value

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id,
        max_prior_art_rounds=2,
        max_mutations_per_candidate=1,
    )

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.verdict in (
        PriorArtVerdict.UNRESOLVED.value,
        PriorArtVerdict.PARTIAL_PRIOR_ART.value,
        PriorArtVerdict.SURVIVED_SEARCH.value,
    )
    assert "PROVEN_NEW" not in final.verdict


def test_mutation_loop_respects_max_rounds() -> None:
    """The loop must not exceed max_prior_art_rounds."""
    protocol = AdversarialSearchProtocol(
        candidate_id=_CandidateFactory.candidate().candidate_id,
        max_prior_art_rounds=1,
        max_mutations_per_candidate=0,
    )

    assert protocol.can_execute(rounds_completed=0, mutations_completed=0)
    assert not protocol.can_execute(rounds_completed=1, mutations_completed=0)

    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    # With max_rounds=1, only one execution allowed
    assert final.rounds_completed <= 1


def test_mutation_loop_respects_mutation_budget() -> None:
    """The loop must not exceed max_mutations_per_candidate."""
    protocol = AdversarialSearchProtocol(
        candidate_id=_CandidateFactory.candidate().candidate_id,
        max_prior_art_rounds=3,
        max_mutations_per_candidate=1,
    )

    assert protocol.can_mutate(mutations_completed=0)
    assert not protocol.can_mutate(mutations_completed=1)

    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    final = run_prior_art_mutation_loop(
        candidate=candidate,
        initial_assessment=assessment,
        protocol=protocol,
        scout=scout,
    )

    assert final.mutations_completed <= 1


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))


@pytest.mark.parametrize("mismatch", ["assessment", "protocol"])
def test_f41_cross_candidate_replay_rejected_before_search(
    mismatch: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A prior match for candidate A cannot be replayed as candidate B."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    match = PriorArtMatch(doc=results["dummy"].documents[0], similarity=0.9)
    initial = PriorArtVerdictEngine().assess(
        candidate, results, skeptic, matches=[match],
    )
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    if mismatch == "assessment":
        initial.candidate_id = "foreign-candidate"
    else:
        protocol = AdversarialSearchProtocol(
            candidate_id="foreign-candidate", max_prior_art_rounds=1,
        )

    monkeypatch.setattr(
        scout, "cross_search",
        lambda *_a, **_kw: pytest.fail("mismatch must not launch a search"),
    )
    with pytest.raises(ValueError, match="CANDIDATE_LINEAGE_MISMATCH"):
        run_prior_art_mutation_loop(
            candidate=candidate, initial_assessment=initial,
            protocol=protocol, scout=scout,
        )


@pytest.mark.parametrize("mutation", [
    "survived_with_matches", "partial_without_matches", "survived_with_gaps",
])
def test_f41_initial_assessment_contradictions_block_replay(
    mutation: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """False coverage and inconsistent initial evidence fail before I/O."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    results = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, results)
    initial = PriorArtVerdictEngine().assess(
        candidate, results, skeptic, matches=[],
    )
    match = PriorArtMatch(doc=results["dummy"].documents[0], similarity=0.9)
    if mutation == "survived_with_matches":
        initial.matches.append(match)
        expected = "INITIAL_MATCHES_CONTRADICTION"
    elif mutation == "partial_without_matches":
        initial.verdict = PriorArtVerdict.PARTIAL_PRIOR_ART.value
        expected = "INITIAL_MATCHES_CONTRADICTION"
    else:
        initial.coverage_limitations = ("source_failure:dummy",)
        expected = "INITIAL_COVERAGE_CONTRADICTION"

    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    monkeypatch.setattr(
        scout, "cross_search",
        lambda *_a, **_kw: pytest.fail("invalid replay must not contact sources"),
    )
    with pytest.raises(ValueError, match=expected):
        run_prior_art_mutation_loop(
            candidate=candidate, initial_assessment=initial,
            protocol=protocol, scout=scout,
        )


@pytest.mark.parametrize("mutate_field", ["title", "abstract", "url"])
def test_f41_reused_document_id_cannot_change_material_content(
    mutate_field: str, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Same source+ID, different content is an unresolved lineage collision."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    observed = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, observed)
    match = PriorArtMatch(doc=observed["dummy"].documents[0], similarity=0.7)
    initial = PriorArtVerdictEngine().assess(
        candidate, observed, skeptic, matches=[match],
    )
    repeated = _results_with_docs()
    setattr(
        repeated["dummy"].documents[0], mutate_field,
        "forged-new-content",
    )
    monkeypatch.setattr(
        scout, "cross_search",
        lambda *_a, **_kw: repeated,
    )
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    with pytest.raises(ValueError, match="DOCUMENT_ID_CONTENT_COLLISION"):
        run_prior_art_mutation_loop(
            candidate=candidate, initial_assessment=initial,
            protocol=protocol, scout=scout,
        )


def test_f41_same_id_same_content_replay_remains_valid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A re-retrieval with only a different timestamp must not be rejected."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    observed = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, observed)
    match = PriorArtMatch(doc=observed["dummy"].documents[0], similarity=0.7)
    initial = PriorArtVerdictEngine().assess(
        candidate, observed, skeptic, matches=[match],
    )
    repeated = _results_with_docs()
    repeated["dummy"].documents[0].provenance = {
        "url": "https://example.com/patent/1",
        "retrieved_at": "2099-01-01T00:00:00Z",
    }
    monkeypatch.setattr(scout, "cross_search", lambda *_a, **_kw: repeated)
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    result = run_prior_art_mutation_loop(
        candidate=candidate, initial_assessment=initial,
        protocol=protocol, scout=scout,
    )
    assert result.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value
    assert result.rounds_completed == 1


def test_f41_replay_uses_snapshot_when_caller_mutates_original_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An adversarial callback cannot rewrite the historical matched document."""
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    observed = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, observed)
    match = PriorArtMatch(doc=observed["dummy"].documents[0], similarity=0.7)
    initial = PriorArtVerdictEngine().assess(
        candidate, observed, skeptic, matches=[match],
    )
    fresh = _results_with_docs()

    def mutate_original_then_return(*_args: Any, **_kwargs: Any):
        initial.matches[0].doc.title = "external post-handoff mutation"
        return fresh

    monkeypatch.setattr(scout, "cross_search", mutate_original_then_return)
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    result = run_prior_art_mutation_loop(
        candidate=candidate, initial_assessment=initial,
        protocol=protocol, scout=scout,
    )
    assert initial.matches[0].doc.title == "external post-handoff mutation"
    assert result.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value


def test_f41_invalid_match_container_rejected_before_source_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = _CandidateFactory.candidate()
    scout = _CrossDomainScoutForLoop()
    observed = _results_with_docs()
    skeptic = PriorArtSkeptic().review(candidate, observed)
    initial = PriorArtVerdictEngine().assess(
        candidate, observed, skeptic,
        matches=[PriorArtMatch(doc=observed["dummy"].documents[0])],
    )
    initial.matches = (match for match in initial.matches)
    monkeypatch.setattr(
        scout, "cross_search",
        lambda *_a, **_kw: pytest.fail("invalid input must not contact sources"),
    )
    protocol = AdversarialSearchProtocol(
        candidate_id=candidate.candidate_id, max_prior_art_rounds=1,
    )
    with pytest.raises(TypeError, match="INITIAL_MATCHES_INVALID"):
        run_prior_art_mutation_loop(
            candidate=candidate, initial_assessment=initial,
            protocol=protocol, scout=scout,
        )
