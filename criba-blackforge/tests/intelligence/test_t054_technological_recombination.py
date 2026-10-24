"""T054 technological recombination: contract and evidence-bounded behaviour."""
from __future__ import annotations

import pytest

from criba.intelligence.contracts import EvidenceDocument
from criba.intelligence.invention.recombination import recombine_technologies


def _doc(doc_id: str, technologies: dict) -> EvidenceDocument:
    return EvidenceDocument(doc_id=doc_id, metadata={"technologies": technologies})


def test_t054_proposes_only_from_explicit_technology_metadata() -> None:
    """Prose without the explicit mapping contributes nothing."""
    prose = EvidenceDocument(doc_id="prose", abstract="combine lasers and mirrors")
    assert recombine_technologies([prose]) == []


def test_t054_requires_two_declared_technologies() -> None:
    """A single technology has nothing to recombine with."""
    assert recombine_technologies([_doc("d1", {"laser": {}})]) == []


def test_t054_pairs_declared_technologies() -> None:
    """Both technologies must come from explicit corpus declarations."""
    docs = [
        _doc("d1", {"laser": {"wavelength": "ir"}}),
        _doc("d2", {"mirror": {"coating": "gold"}}),
    ]
    candidates = recombine_technologies(docs)
    assert candidates, "T054 must propose a recombination"
    assert all(c.operators == ("T054",) for c in candidates)
    assert any("laser" in c.title and "mirror" in c.title for c in candidates)
    assert all("titanium" not in c.title for c in candidates)


def test_t054_never_invents_technologies_from_text() -> None:
    """A document whose text mentions technologies but declares none is ignored."""
    doc = EvidenceDocument(
        doc_id="d1", abstract="the laser and the mirror", metadata={"concepts": ["a"]}
    )
    assert recombine_technologies([doc]) == []


def test_t054_deterministic_and_limited() -> None:
    """Same corpus, same proposals (modulo candidate_id); limit honoured."""
    docs = [
        _doc("d1", {"laser": {}}),
        _doc("d2", {"mirror": {}}),
        _doc("d3", {"grating": {}}),
    ]
    first = recombine_technologies(docs)
    second = recombine_technologies(docs)
    assert [c.title for c in first] == [c.title for c in second]
    assert len(recombine_technologies(docs, limit=1)) == 1


def test_t054_rejects_invalid_input() -> None:
    with pytest.raises(TypeError):
        recombine_technologies("not-a-sequence")
    with pytest.raises(TypeError):
        recombine_technologies([EvidenceDocument(doc_id="d1"), "not-a-document"])
    with pytest.raises(ValueError):
        recombine_technologies([], limit=-1)
    with pytest.raises(TypeError):
        recombine_technologies([], limit=True)
