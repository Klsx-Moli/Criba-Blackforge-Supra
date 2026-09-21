"""ASTRA-024: component dependencies are not a universal reproducibility promise."""

import inspect

from criba.intelligence.outcome_store import TechniqueOutcomeStore


def test_astra_024_state_hash_doc_does_not_claim_global_sufficiency():
    text = inspect.getdoc(TechniqueOutcomeStore.state_hash) or ""
    assert "global" in text.lower()
    assert "not sufficient" in text.lower() or "no es suficiente" in text.lower()
