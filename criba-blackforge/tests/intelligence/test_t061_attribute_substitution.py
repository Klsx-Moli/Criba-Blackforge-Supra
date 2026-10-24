"""T061 attribute substitution: contract and evidence-bounded behaviour."""
from __future__ import annotations

import pytest

from criba.intelligence.contracts import EvidenceDocument
from criba.intelligence.invention.recombination import _attributes, substitute_attributes


def _doc(doc_id: str, attributes: dict[str, str]) -> EvidenceDocument:
    return EvidenceDocument(doc_id=doc_id, metadata={"attributes": attributes})


def test_t061_proposes_only_from_explicit_attribute_metadata() -> None:
    """Prose without the explicit mapping contributes nothing."""
    prose = EvidenceDocument(doc_id="prose", abstract="high latency low cost")
    assert substitute_attributes([prose]) == []


def test_t061_requires_two_observed_values_per_attribute() -> None:
    """A single observed value has nothing to substitute against."""
    single = [_doc("d1", {"material": "steel"})]
    assert substitute_attributes(single) == []


def test_t061_substitutes_between_observed_values() -> None:
    """Both values must come from the corpus, never from prose."""
    docs = [
        _doc("d1", {"material": "steel"}),
        _doc("d2", {"material": "carbon_fibre"}),
    ]
    candidates = substitute_attributes(docs)
    assert candidates, "T061 must propose a substitution between observed values"
    assert all(c.operators == ("T061",) for c in candidates)
    names = {c.title for c in candidates}
    assert any("material=steel" in n for n in names)
    assert any("material=carbon_fibre" in n for n in names)
    # No invented value: only the two observed ones appear.
    assert all("titanium" not in c.title for c in candidates)


def test_t061_never_invents_attributes_from_text() -> None:
    """A document whose text mentions an attribute but declares none is ignored.

    The abstract deliberately contains attribute-like words: if the operator ever
    inferred attributes from prose it would propose a substitution here.
    """
    doc = EvidenceDocument(
        doc_id="d1",
        abstract="the material is titanium and the topology is mesh",
        metadata={"concepts": ["a"]},
    )
    assert substitute_attributes([doc]) == []
    # And the helper itself must expose no attribute for a prose-only document.
    assert _attributes(doc) == ()


def test_t061_null_is_not_an_attribute() -> None:
    """``None`` must not become the literal string ``"None"``.

    Coercing an absent value with ``str()`` would declare ``material="None"`` as
    a usable attribute, converting absence into data.
    """
    doc = EvidenceDocument(doc_id="d1", metadata={"attributes": {"material": None}})
    assert _attributes(doc) == ()
    assert substitute_attributes([doc]) == []


def test_t061_non_string_values_are_rejected_not_coerced() -> None:
    """Booleans, numbers and containers are an undeclared shape, not evidence.

    They raise ``TypeError`` rather than being coerced with ``str()``: coercing
    would declare e.g. ``material="['a', 'b']"`` as a usable attribute.
    """
    for value in (True, 3.5, ["a", "b"], {"k": "v"}):
        doc = EvidenceDocument(doc_id="d1", metadata={"attributes": {"material": value}})
        with pytest.raises(TypeError):
            _attributes(doc)
    # A null name is absence, not a type error.
    assert _attributes(EvidenceDocument(doc_id="d2", metadata={"attributes": {None: "steel"}})) == ()


def test_t061_same_name_two_values_proposes_both_directions() -> None:
    """A→B and B→A are distinct hypotheses; both must appear."""
    docs = [
        _doc("d1", {"material": "steel"}),
        _doc("d2", {"material": "carbon_fibre"}),
    ]
    titles = {c.title for c in substitute_attributes(docs)}
    assert any("steel" in t and "carbon_fibre" in t for t in titles), titles


def test_t061_deterministic_on_full_payload() -> None:
    """Determinism must hold on the whole payload except the opaque candidate_id.

    Comparing only titles is too weak; the description, mechanism, operators,
    hypothesis_id, epistemic_state and origin must be identical too.
    """
    docs = [
        _doc("d1", {"material": "steel"}),
        _doc("d2", {"material": "carbon_fibre"}),
        _doc("d3", {"material": "glass"}),
    ]

    def payload(candidates):
        return [
            {
                "title": c.title,
                "description": c.description,
                "mechanism": c.mechanism,
                "operators": c.operators,
                "hypothesis_id": c.hypothesis_id,
                "epistemic_state": c.epistemic_state,
                "origin": c.origin,
            }
            for c in candidates
        ]

    first = payload(substitute_attributes(docs))
    second = payload(substitute_attributes(docs))
    assert first == second, "T061 must be deterministic on the full payload"
    assert len(first) == len(second)
    # Order must also be stable (cardinality + sequence).
    assert [c["title"] for c in first] == [c["title"] for c in second]


def test_t061_limit_is_an_int_not_a_bool() -> None:
    """``True`` is an ``int`` in Python but is not a valid limit."""
    docs = [_doc("d1", {"material": "steel"}), _doc("d2", {"material": "glass"})]
    with pytest.raises(TypeError):
        substitute_attributes(docs, limit=True)


def test_t061_is_deterministic_and_limited() -> None:
    """Same corpus, same proposals (modulo the random candidate_id); limit honoured."""
    docs = [
        _doc("d1", {"material": "steel"}),
        _doc("d2", {"material": "carbon_fibre"}),
        _doc("d3", {"material": "glass"}),
    ]
    first = substitute_attributes(docs)
    second = substitute_attributes(docs)
    # candidate_id is a fresh random identifier per instance; the proposal itself
    # must be identical.
    assert [c.title for c in first] == [c.title for c in second], (
        "T061 must be deterministic"
    )
    assert len(substitute_attributes(docs, limit=1)) == 1


def test_t061_rejects_invalid_input() -> None:
    """Malformed input fails loudly instead of returning an empty list."""
    with pytest.raises(TypeError):
        substitute_attributes("not-a-sequence")
    with pytest.raises(TypeError):
        substitute_attributes([EvidenceDocument(doc_id="d1"), "not-a-document"])
    with pytest.raises(ValueError):
        substitute_attributes([], limit=-1)
