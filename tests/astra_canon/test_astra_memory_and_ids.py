"""ASTRA-022/023: duplicate IDs and memory fallback remain explicit."""

import inspect

from criba.diversity_selector import _adaptive_bonus
from criba.inventar import invent


class PriorStore:
    def prior(self, **kwargs):
        return (0.25, 1, "p")


class BrokenStore:
    def prior(self, **kwargs):
        raise OSError("unavailable")


def candidate(ids):
    return {"technique_ids": ids, "classes": ["f"], "family": "f"}


def test_astra_022_duplicate_technique_ids_do_not_multiply_prior():
    one = _adaptive_bonus(candidate(["T1"]), PriorStore(), "CRIBA", "c")
    repeated = _adaptive_bonus(candidate(["T1", "T1", "T1"]), PriorStore(), "CRIBA", "c")
    assert repeated == one


def test_astra_023_memory_states_distinguish_disabled_no_data_error_and_zero():
    assert _adaptive_bonus(candidate(["T1"]), None, "CRIBA", "c")[1] == "memory:disabled"
    assert _adaptive_bonus(candidate(["T1"]), BrokenStore(), "CRIBA", "c")[1].startswith(
        "memory:error:"
    )

    class NoData:
        def prior(self, **kwargs):
            return (0.0, 0, "sin_datos")

    class ZeroPrior:
        def prior(self, **kwargs):
            return (0.0, 1, "observed-zero")

    assert _adaptive_bonus(candidate(["T1"]), NoData(), "CRIBA", "c")[1] == "memory:no_data"
    assert (
        "memory:valid_zero_prior"
        in _adaptive_bonus(candidate(["T1"]), ZeroPrior(), "CRIBA", "c")[1]
    )


def test_astra_023_adaptive_false_scope_does_not_claim_all_history_is_disabled():
    documentation = inspect.getdoc(invent) or ""
    assert "OutcomeStore/UCB influence only" in documentation
    assert "does not disable ``history_storage``" in documentation
