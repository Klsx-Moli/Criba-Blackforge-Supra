"""F42: literal-overlap screening is real, bounded, and never scientific proof."""
from __future__ import annotations

from dataclasses import replace

import pytest

from criba.intelligence.contracts import (
    EvidenceDocument,
    EvidenceFragment,
    InventionCandidate,
    ProvenanceRecord,
    SourceQueryResult,
)
from criba.intelligence.prior_art.literal_probe import probe_literal_mechanism

_MECHANISM = "válvula que impide recirculación de permisos"


def _candidate(mechanism: str = _MECHANISM) -> InventionCandidate:
    return InventionCandidate(
        candidate_id="cand_f42", title="Contraste textual",
        description="Invento pendiente de validación",
        mechanism=mechanism,
    )


def _doc(
    doc_id: str = "paper1",
    *,
    source: str = "science",
    title: str = "Unrelated reference",
    abstract: str = "",
    fragments: list[EvidenceFragment] | None = None,
) -> EvidenceDocument:
    return EvidenceDocument(
        doc_id=doc_id, source_id=source, title=title, abstract=abstract,
        fragments=list(fragments or []),
        provenance=ProvenanceRecord(
            source_id=source, method="api", url=f"https://{source}.invalid/{doc_id}",
        ),
    )


def _source(
    docs: list[EvidenceDocument], *, source_id: str = "science", ok: bool = True,
) -> SourceQueryResult:
    return SourceQueryResult(
        source_id=source_id, query_text="search", ok=ok, documents=docs,
    )


def test_f42_exact_full_mechanism_phrase_is_a_review_candidate_not_a_verdict() -> None:
    doc = _doc(abstract="La VÁLVULA, que impide RECIRCULACIÓN de permisos funciona.")
    result = probe_literal_mechanism(_candidate(), {"science": _source([doc])}).to_dict()
    assert result["status"] == "POTENTIAL_LITERAL_OVERLAP"
    assert result["method"] == "full_mechanism_token_sequence_v1"
    assert result["candidates"] == [
        {"source_id": "science", "doc_id": "paper1", "field": "abstract", "locator": ""},
    ]
    assert result["documents_scanned"] == 1
    assert result["documents_unscanned"] == 0
    assert result["materiality_assessed"] is False
    assert len(result["mechanism_digest"]) == 64


@pytest.mark.parametrize("text", [
    "La válvula que impide recirculación de permisoss funciona",
    "La válvula que impide la recirculación de permisos funciona",
    "La válvula que impide recirculación de permisos reversos no equivale al candidato"
])
def test_f42_partial_tokens_do_not_claim_full_literal_overlap(text: str) -> None:
    # The last case is an EXACT hit in a larger sentence, but only a review
    # candidate, not material equivalence; distinguish from the other two.
    result = probe_literal_mechanism(
        _candidate(), {"science": _source([_doc(abstract=text)])},
    ).to_dict()
    expected = (
        "POTENTIAL_LITERAL_OVERLAP" if "permisos reversos" in text
        else "NO_LITERAL_OVERLAP_IN_SCANNED_TEXT"
    )
    assert result["status"] == expected
    assert result["materiality_assessed"] is False


def test_f42_do_not_join_title_and_abstract_or_read_untrusted_metadata() -> None:
    d = _doc(title="válvula que impide", abstract="recirculación de permisos")
    d.metadata = {"promotional": _MECHANISM}
    result = probe_literal_mechanism(_candidate(), {"science": _source([d])})
    assert result.status == "NO_LITERAL_OVERLAP_IN_SCANNED_TEXT"
    assert result.candidates == ()


def test_f42_fragment_locator_is_kept_without_exposing_raw_evidence() -> None:
    d = _doc(fragments=[
        EvidenceFragment(text=f"Texto: {_MECHANISM}", locator="section:2"),
    ])
    payload = probe_literal_mechanism(_candidate(), {"science": _source([d])}).to_dict()
    assert payload["candidates"][0]["field"] == "fragment"
    assert payload["candidates"][0]["locator"] == "section:2"
    assert _MECHANISM not in str(payload)


@pytest.mark.parametrize("invalid", ["no-provenance", "wrong-source", "no-url", "large"])
def test_f42_missing_or_unreadable_evidence_is_unknown_not_zero(invalid: str) -> None:
    d = _doc(abstract=_MECHANISM)
    if invalid == "no-provenance":
        d.provenance = None
    elif invalid == "wrong-source":
        d.provenance.source_id = "foreign"
    elif invalid == "no-url":
        d.provenance.url = ""
    else:
        d.abstract = "x" * 32769
    payload = probe_literal_mechanism(
        _candidate(), {"science": _source([d])},
    ).to_dict()
    assert payload["status"] == "INDETERMINATE"
    assert payload["documents_scanned"] == 0
    assert payload["documents_unscanned"] == 1
    assert payload["candidates"] == []


def test_f42_failed_source_never_yields_review_candidate() -> None:
    result = probe_literal_mechanism(
        _candidate(), {"science": _source([_doc(abstract=_MECHANISM)], ok=False)},
    )
    assert result.status == "INDETERMINATE"
    assert result.sources_failed == 1
    assert result.candidates == ()


@pytest.mark.parametrize("mechanism", ["", "one two", "x " * 129, "a" * 32769])
def test_f42_trivial_or_unbounded_mechanisms_remain_indeterminate(
    mechanism: str,
) -> None:
    result = probe_literal_mechanism(
        _candidate(mechanism), {"science": _source([_doc(abstract=_MECHANISM)])},
    )
    assert result.status == "INDETERMINATE"
    assert result.mechanism_digest == ""
    assert result.documents_scanned == 0


def test_f42_bounded_scan_never_promotes_truncated_no_match_to_absence() -> None:
    documents = [_doc("a", abstract="no match")]
    documents.append(_doc("b", abstract=_MECHANISM))
    result = probe_literal_mechanism(
        _candidate(), {"science": _source(documents)}, max_documents=1,
    )
    assert result.status == "INDETERMINATE"
    assert result.documents_scanned == 1
    assert result.documents_unscanned == 1
    assert result.candidates == ()


@pytest.mark.parametrize("limit", [0, -1, True, 1.2])
def test_f42_invalid_scan_budget_is_rejected(limit: object) -> None:
    with pytest.raises(ValueError, match="max_documents"):
        probe_literal_mechanism(_candidate(), {}, max_documents=limit)


def test_f42_duplicate_doc_id_cannot_pad_number_of_candidates() -> None:
    documents = [_doc("same", abstract=_MECHANISM), _doc("same", title=_MECHANISM)]
    result = probe_literal_mechanism(_candidate(), {"science": _source(documents)})
    assert len(result.candidates) == 1
    assert result.documents_scanned == 1
    assert result.documents_unscanned == 1
    assert result.status == "POTENTIAL_LITERAL_OVERLAP"


def test_f42_sources_and_documents_reordering_does_not_change_output() -> None:
    first = _source([_doc("b", abstract=_MECHANISM), _doc("a", abstract="no match")])
    second = _source([_doc("2", source="patents", abstract=_MECHANISM)], source_id="patents")
    baseline = probe_literal_mechanism(
        _candidate(), {"science": first, "patents": second},
    ).to_dict()
    first_reordered = _source(list(reversed(first.documents)))
    reordered = probe_literal_mechanism(
        _candidate(), {"patents": second, "science": first_reordered},
    ).to_dict()
    assert reordered == baseline
