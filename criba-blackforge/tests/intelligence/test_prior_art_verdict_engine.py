"""P10-T09: deterministic prior-art verdict engine contract."""
from __future__ import annotations

import pytest

from criba.intelligence import prior_art
from criba.intelligence.contracts import (
    EvidenceDocument,
    InventionCandidate,
    PriorArtAssessment,
    PriorArtMatch,
    ProvenanceRecord,
    QueryVariant,
    SourceQueryResult,
)
from criba.intelligence.enums import PriorArtVerdict
from criba.intelligence.prior_art import (
    CrossDomainScout,
    PriorArtSkeptic,
    PriorArtVerdictEngine,
)
from criba.intelligence.sources.protocol import IntelligenceSource, SourceContext
from criba.intelligence.sources.transport import Response, Transport


class _Source(IntelligenceSource):
    RATE_LIMIT_S = 0.0

    def __init__(self, source_id: str, kind: str) -> None:
        super().__init__(
            SourceContext(
                transport=Transport(sender=lambda *args, **kwargs: Response(200, "{}"))
            )
        )
        self.SOURCE_ID = source_id
        self.KIND = kind

    def _search(self, query: str, limit: int = 10, **params: object) -> SourceQueryResult:
        return SourceQueryResult(
            source_id=self.SOURCE_ID,
            query_text=query,
            ok=True,
            documents=[
                EvidenceDocument(
                    doc_id=f"doc_{self.SOURCE_ID}",
                    source_id=self.SOURCE_ID,
                    title=f"{self.SOURCE_ID} evidence",
                    provenance=ProvenanceRecord(
                        source_id=self.SOURCE_ID,
                        url=f"https://{self.SOURCE_ID}.invalid/evidence",
                        method="api",
                    ),
                )
            ],
        )


def _candidate() -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_thermal",
        title="Thermal management transfer",
        description="Apply a documented heat-transfer mechanism in a new context.",
        mechanism="transfer a verified heat-transfer mechanism",
    )


def test_verdict_engine_runs_the_real_t07_t08_handoff_without_claiming_novelty() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)

    assessment = PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])

    assert isinstance(assessment, PriorArtAssessment)
    assert assessment.candidate_id == candidate.candidate_id
    assert assessment.verdict == PriorArtVerdict.SURVIVED_SEARCH.value
    assert assessment.matches == []
    assert assessment.coverage_limitations == ()
    assert assessment.queries_executed == ("thermal management",)
    scout.validate_downstream_handoff(
        results,
        skeptic=skeptic,
        verdict=assessment.verdict,
    )


def test_verdict_engine_fails_closed_when_the_skeptic_report_hides_empty_source_coverage() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[],
    )
    observed = PriorArtSkeptic().review(candidate, results)
    hidden_gap_report = type(observed)(
        **{**observed.to_dict(), "evidence_gaps": (), "verdict": "survives_with_conditions"}
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        hidden_gap_report,
        matches=[],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("empty_source:science",)


def test_verdict_engine_returns_partial_prior_art_for_a_normalized_match() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    match = PriorArtMatch(
        doc=results["science"].documents[0],
        similarity=0.01,
        match_kind="literal",
        scout="ScienceScout",
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[match],
    )

    assert assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value
    assert assessment.matches == [match]


def test_verdict_engine_orders_matches_deterministically() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    science_match = PriorArtMatch(doc=results["science"].documents[0], scout="ScienceScout")
    code_match = PriorArtMatch(doc=results["code"].documents[0], scout="CodeScout")

    forward = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[science_match, code_match],
    )
    reverse = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[code_match, science_match],
    )

    assert [match.doc.doc_id for match in forward.matches] == ["doc_code", "doc_science"]
    assert forward.matches == reverse.matches


def test_verdict_engine_rejects_a_malformed_match() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)

    with pytest.raises(TypeError, match="PriorArtMatch"):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[object()])


def test_verdict_engine_is_part_of_the_public_prior_art_contract() -> None:
    assert prior_art.PriorArtVerdictEngine is PriorArtVerdictEngine
    assert "PriorArtVerdictEngine" in prior_art.__all__


def test_verdict_engine_does_not_let_a_match_override_a_coverage_gap() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[],
    )
    skeptic = PriorArtSkeptic().review(candidate, results)
    match = PriorArtMatch(doc=results["code"].documents[0], scout="CodeScout")

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        skeptic,
        matches=[match],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("empty_source:science",)


def test_verdict_engine_fails_closed_when_the_skeptic_report_hides_missing_provenance() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science",
        query_text="thermal management",
        ok=True,
        documents=[
            EvidenceDocument(
                doc_id="doc_science",
                source_id="science",
                title="Evidence without provenance",
            )
        ],
    )
    observed = PriorArtSkeptic().review(candidate, results)
    hidden_gap_report = type(observed)(
        **{**observed.to_dict(), "evidence_gaps": (), "verdict": "survives_with_conditions"}
    )

    assessment = PriorArtVerdictEngine().assess(
        candidate,
        results,
        hidden_gap_report,
        matches=[],
    )

    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value
    assert assessment.coverage_limitations == ("missing_provenance:science:doc_science",)


@pytest.mark.parametrize(
    "mutation",
    ["reject", "rejected", "PROVEN_NEW", "UNKNOWN", "", None, []],
)
def test_verdict_engine_rejects_fabricated_or_negative_skeptic_verdicts(
    mutation,
) -> None:
    """F38 sentinel: genuine citations must not turn REJECT into support."""
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    legitimate = PriorArtSkeptic().review(candidate, results)
    assert legitimate.verdict == "survives_with_conditions"
    assert legitimate.evidence_gaps == ()

    forged = type(legitimate)(
        **{**legitimate.to_dict(), "verdict": mutation},
    )
    with pytest.raises(ValueError, match="SKEPTIC_VERDICT_INVALID"):
        PriorArtVerdictEngine().assess(
            candidate, results, forged, matches=[],
        )


def test_verdict_engine_rejects_skeptic_with_unexplained_experiment_verdict() -> None:
    """A hidden reason for 'requires experiment' is UNKNOWN, not zero gaps."""
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    report = PriorArtSkeptic().review(candidate, results)
    contradictory = type(report)(
        **{**report.to_dict(), "verdict": "requires_experiment"},
    )
    with pytest.raises(ValueError, match="SKEPTIC_VERDICT_CONTRADICTION"):
        PriorArtVerdictEngine().assess(
            candidate, results, contradictory, matches=[],
        )


def test_valid_skeptic_with_real_gaps_remains_unresolved_after_f38() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    results["science"] = SourceQueryResult(
        source_id="science", query_text="thermal management",
        ok=True, documents=[],
    )
    skeptic = PriorArtSkeptic().review(candidate, results)
    assert skeptic.verdict == "requires_experiment"
    assert skeptic.evidence_gaps
    assessment = PriorArtVerdictEngine().assess(
        candidate, results, skeptic, matches=[],
    )
    assert assessment.verdict == PriorArtVerdict.UNRESOLVED.value


@pytest.mark.parametrize("similarity", [
    float("nan"), float("inf"), float("-inf"), -0.1, 1.1,
    True, False, "0.5", None, [],
])
def test_verdict_engine_rejects_unbounded_or_untyped_match_similarity(
    similarity,
) -> None:
    """F39: a forged score must not be accepted as scientific evidence."""
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    invalid_match = PriorArtMatch(
        doc=results["science"].documents[0], similarity=similarity,
    )
    with pytest.raises(ValueError, match="MATCH_SIMILARITY_INVALID"):
        PriorArtVerdictEngine().assess(
            candidate, results, skeptic, matches=[invalid_match],
        )


@pytest.mark.parametrize("similarity", [0, 0.0, 0.5, 1, 1.0])
def test_verdict_engine_retains_valid_similarity_boundaries(
    similarity,
) -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    valid_match = PriorArtMatch(
        doc=results["science"].documents[0], similarity=similarity,
    )
    assessment = PriorArtVerdictEngine().assess(
        candidate, results, skeptic, matches=[valid_match],
    )
    assert assessment.verdict == PriorArtVerdict.PARTIAL_PRIOR_ART.value
    assert assessment.matches == [valid_match]


def test_verdict_engine_rejects_malformed_match_document() -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    with pytest.raises(TypeError, match="PriorArtMatch.doc"):
        PriorArtVerdictEngine().assess(
            candidate, results, skeptic,
            matches=[PriorArtMatch(doc={"foreign": True})],
        )


def test_verdict_engine_rejects_one_shot_matches_instead_of_erasing_them() -> None:
    """F39 mutation: a generator was consumed by type checking before sort."""
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    valid = PriorArtMatch(
        doc=results["science"].documents[0], similarity=0.9,
    )
    one_shot = (match for match in [valid])
    with pytest.raises(TypeError, match="replayable sequence"):
        PriorArtVerdictEngine().assess(
            candidate, results, skeptic, matches=one_shot,
        )


@pytest.mark.parametrize("invalid", [None, "not-a-sequence", b"bad"])
def test_verdict_engine_rejects_non_sequence_matches(invalid) -> None:
    scout = CrossDomainScout([
        _Source("science", "science"),
        _Source("code", "code"),
    ])
    candidate = _candidate()
    results = scout.cross_search(QueryVariant("thermal management"))
    skeptic = PriorArtSkeptic().review(candidate, results)
    with pytest.raises(TypeError, match="replayable sequence"):
        PriorArtVerdictEngine().assess(
            candidate, results, skeptic, matches=invalid,
        )


@pytest.mark.parametrize("bad_ok", ["false", "true", 0, 1, None, []])
def test_f40_direct_verdict_rejects_nonboolean_source_success(
    bad_ok,
) -> None:
    """Mutating ok after a valid skeptic must never create false coverage."""
    candidate = _candidate()
    results = {
        source_id: SourceQueryResult(
            source_id=source_id, query_text="thermal management", ok=True,
            documents=[
                EvidenceDocument(
                    doc_id=f"doc_{source_id}", source_id=source_id,
                    title="fixture", provenance=ProvenanceRecord(
                        source_id=source_id,
                        url=f"https://{source_id}.invalid/evidence",
                        method="api",
                    ),
                ),
            ],
        )
        for source_id in ("science", "code")
    }
    skeptic = PriorArtSkeptic().review(candidate, results)
    assert skeptic.verdict == "survives_with_conditions"
    results["science"].ok = bad_ok
    with pytest.raises(TypeError, match="SOURCE_OK_NOT_BOOLEAN"):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])


@pytest.mark.parametrize("bad_docs", [None, "text", {"doc_id": "fake"}, [object()]])
def test_f40_direct_verdict_rejects_corrupt_document_collection(
    bad_docs,
) -> None:
    candidate = _candidate()
    results = {
        "science": SourceQueryResult(
            source_id="science", query_text="thermal management", ok=True,
            documents=[EvidenceDocument(
                doc_id="doc_ok", source_id="science",
                provenance=ProvenanceRecord(source_id="science"),
            )],
        ),
    }
    skeptic = PriorArtSkeptic().review(candidate, results)
    results["science"].documents = bad_docs
    expected = (
        "SOURCE_DOCUMENT_TYPE_INVALID"
        if isinstance(bad_docs, list)
        else "SOURCE_DOCUMENTS_NOT_LIST"
    )
    with pytest.raises(TypeError, match=expected):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])


@pytest.mark.parametrize("bad_source,bad_doc_id", [
    ("foreign", "same"), ("", "same"), ("science", ""),
    ("science", " a "), (None, "same"),
])
def test_f40_direct_verdict_rejects_forged_document_lineage(
    bad_source, bad_doc_id,
) -> None:
    candidate = _candidate()
    results = {
        "science": SourceQueryResult(
            source_id="science", query_text="thermal management", ok=True,
            documents=[EvidenceDocument(
                doc_id="same", source_id="science",
                provenance=ProvenanceRecord(source_id="science"),
            )],
        ),
    }
    skeptic = PriorArtSkeptic().review(candidate, results)
    results["science"].documents[0].source_id = bad_source
    results["science"].documents[0].doc_id = bad_doc_id
    with pytest.raises(ValueError, match="SOURCE_DOCUMENT_IDENTITY_INVALID"):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])


def test_f40_direct_verdict_rejects_missing_query_even_if_skeptic_is_old() -> None:
    candidate = _candidate()
    results = {
        "science": SourceQueryResult(
            source_id="science", query_text="thermal management", ok=True,
            documents=[EvidenceDocument(
                doc_id="doc_ok", source_id="science",
                provenance=ProvenanceRecord(source_id="science"),
            )],
        ),
    }
    skeptic = PriorArtSkeptic().review(candidate, results)
    results["science"].query_text = ""
    with pytest.raises(ValueError, match="SOURCE_QUERY_INVALID"):
        PriorArtVerdictEngine().assess(candidate, results, skeptic, matches=[])


def test_f40_direct_verdict_valid_coverage_still_survives_search() -> None:
    candidate = _candidate()
    results = {
        source_id: SourceQueryResult(
            source_id=source_id, query_text="thermal management", ok=True,
            documents=[EvidenceDocument(
                doc_id=f"doc_{source_id}", source_id=source_id,
                provenance=ProvenanceRecord(source_id=source_id),
            )],
        )
        for source_id in ("science", "code")
    }
    skeptic = PriorArtSkeptic().review(candidate, results)
    assessed = PriorArtVerdictEngine().assess(
        candidate, results, skeptic, matches=[],
    )
    assert assessed.verdict == PriorArtVerdict.SURVIVED_SEARCH.value
