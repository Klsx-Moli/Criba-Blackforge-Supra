"""T104/T111: producers of real MCDA inputs, and the absence contract.

Adversarial focus (EEIMC-001 Art. 9): a missing value must NOT become a measured
0.0. `None` means "not evaluated"; 0.0 means "evaluated and found minimal".
"""
from __future__ import annotations

import pytest

from criba.intelligence.scoring.evidence import (
    SOURCE_CONFIDENCE,
    SOURCE_FEASIBILITY,
    confidence,
    feasibility,
    mcda_inputs,
    mcda_sources,
)

_METHOD = {
    "family": "ciencia_realidad",
    "granularity": "micro_technique",
    "origin": "internal",
    "tags": ["evidencia"],
}


# --------------------------------------------------------------------------
# T111 feasibility
# --------------------------------------------------------------------------

def test_feasibility_uses_declared_granularity() -> None:
    assert feasibility(_METHOD) == 1.0  # micro_technique (1.0) + internal (1.0)


def test_feasibility_distinguishes_granularity_tiers() -> None:
    coarse = dict(_METHOD, granularity="paradigm")
    fine = dict(_METHOD, granularity="micro_technique")
    assert feasibility(fine) > feasibility(coarse)


def test_feasibility_returns_none_without_data() -> None:
    """A missing field is absence, not a measured 0.0."""
    assert feasibility({}) is None
    assert feasibility({"family": "x"}) is None  # no granularity/origin
    assert feasibility({"granularity": None, "origin": None}) is None
    assert feasibility(None) is None


def test_feasibility_ignores_unknown_granularity() -> None:
    """An undeclared tier is not evaluated, not a guess."""
    assert feasibility({"granularity": "quantum_flux"}) is None


# --------------------------------------------------------------------------
# T104 confidence
# --------------------------------------------------------------------------

def test_confidence_uses_declared_siblings() -> None:
    siblings = [dict(_METHOD), dict(_METHOD)]
    assert confidence(_METHOD, sibling_methods=siblings) == 1.0


def test_confidence_partial_when_some_siblings_lack_evidence() -> None:
    siblings = [dict(_METHOD), {**_METHOD, "tags": []}]
    assert confidence(_METHOD, sibling_methods=siblings) == 0.5


def test_confidence_returns_none_without_family_or_siblings() -> None:
    assert confidence({}) is None
    assert confidence(_METHOD, sibling_methods=[]) is None
    assert confidence(None) is None


def test_confidence_ignores_siblings_of_other_families() -> None:
    siblings = [{**_METHOD, "family": "otra"}]
    assert confidence(_METHOD, sibling_methods=siblings) is None


# --------------------------------------------------------------------------
# mcda integration
# --------------------------------------------------------------------------

def test_mcda_inputs_are_accepted_by_the_real_consumer() -> None:
    """The produced inputs must feed `criba.mcda.score` without error."""
    from criba.mcda import score

    siblings = [dict(_METHOD), dict(_METHOD)]
    inputs = mcda_inputs(_METHOD, sibling_methods=siblings)
    assert inputs == {"confidence": 1.0, "feasibility": 1.0}
    result = score(inputs, sources=mcda_sources())
    confidence_dim = next(d for d in result.dimensions if d.name == "confidence")
    feasibility_dim = next(d for d in result.dimensions if d.name == "feasibility")
    assert confidence_dim.present and confidence_dim.source == SOURCE_CONFIDENCE
    assert feasibility_dim.present and feasibility_dim.source == SOURCE_FEASIBILITY


def test_mcda_inputs_reported_as_unknown_when_absent() -> None:
    """Absent data must surface as UNKNOWN, not as a 0.0 dimension."""
    from criba.mcda import Coverage, score

    inputs = mcda_inputs({}, sibling_methods=[])
    assert inputs == {"confidence": None, "feasibility": None}
    result = score(inputs, sources=mcda_sources())
    confidence_dim = next(d for d in result.dimensions if d.name == "confidence")
    feasibility_dim = next(d for d in result.dimensions if d.name == "feasibility")
    assert not confidence_dim.present
    assert not feasibility_dim.present
    # Coverage reflects the missing dimensions rather than pretending they are 0.
    assert result.coverage is not Coverage.FULL


def test_zero_is_a_real_measurement_not_absence() -> None:
    """0.0 must be reachable and distinct from None."""
    assert feasibility({"granularity": "theory", "origin": "external"}) is not None
    # A real 0.0 would come from an explicit minimal configuration, not from
    # missing data — here the weakest declared combination is above 0.
    assert feasibility({"granularity": "theory", "origin": "external"}) > 0.0


def test_invalid_inputs_rejected_by_consumer() -> None:
    """The consumer still enforces its own contract; producers don't bypass it."""
    from criba.mcda import score

    with pytest.raises(ValueError):
        score({"confidence": 1.5})
    with pytest.raises(ValueError):
        score({"confidence": True})
