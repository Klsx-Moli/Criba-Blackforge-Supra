"""F09: a concurrent cache winner is never trusted without a second check.

The test forces the read -> propose -> store-dedup -> read race. It uses the
real JuezInterprete and cache contract but no model, HTTP, Qt or paid service.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from criba.interprete.contrato import (
    PROMPT_VERSION,
    SCHEMA_VERSION,
    SYSTEM,
    prompt_propuesta,
)
from criba.interprete.juez import JuezInterprete
from criba.interprete.puerto import hash_salida
from criba.interprete.store import InterpreteStore
from verification.interpreter_cases import resultado


IDEA = {
    "id": "phase09-c1",
    "method1": "Poka-Yoke",
    "method2": "Retroalimentación",
    "description": "Revisar campos ausentes antes de confirmar citas.",
    "causal_axes_changed": ["flujo", "feedback"],
    "convergence": {"novelty": 0.75},
}
QUERY = "Revisar registros antes de confirmar citas"


class FakePort:
    model = "phase09-mock"
    generation_parameters = {"temperature": 0.0}

    def __init__(self, *, mutates: bool = False) -> None:
        self.calls = 0
        self.mutates = mutates

    def proponer(self, query, idea, domain=None, evidence=None):
        self.calls += 1
        if self.mutates:
            idea["containment_class"] = "MUTATED_AFTER_SEND"
        return resultado(raw_output="FRESH_RESULT")


class RacingStore:
    def __init__(self, winner, *, hit_first: bool = False):
        self.winner = winner
        self.hit_first = hit_first
        self.reads = 0
        self.writes = 0

    def get_verdict(self, idea_id, modelo, *, run_id=None, seed=None):
        assert idea_id == IDEA["id"] and modelo == FakePort.model
        assert run_id == "run-09" and seed == 23
        self.reads += 1
        return self.winner if self.hit_first or self.reads > 1 else None

    def record_decision(self, *, activation_id, idea, modelo, run_id, seed):
        assert activation_id == "activation-09"
        self.writes += 1
        return {"status": "deduplicated"}


def winner_row(idea=None):
    idea = IDEA if idea is None else idea
    campos = resultado().to_campos()
    row = {
        "veredicto": "PROPUESTA",
        "evaluation_status": "CRITIQUED",
        "schema_version": SCHEMA_VERSION,
        "prompt_version": PROMPT_VERSION,
        "response": {
            "interpretation": {
                "interprete_verdict": "PROPUESTA",
                "interprete_evaluation_status": "CRITIQUED",
                "interprete_analisis": "",
                "interprete_result": campos,
                "interprete_raw_output": "WINNER_RESULT",
                "interprete_score": None,
            },
        },
        "provenance": {
            "generation_parameters": dict(FakePort.generation_parameters),
            "prompt_sha256": hash_salida(SYSTEM + prompt_propuesta(QUERY, idea, None, [])),
        },
    }
    assert InterpreteStore.cache_valido(row, idea, [])
    return row


def run_judge(row, *, hit_first=False, mutates=False):
    port = FakePort(mutates=mutates)
    store = RacingStore(row, hit_first=hit_first)
    judge = JuezInterprete(interpreter=port)
    judge.store = store
    # Isolate the cache race from candidate selection; no search or ranking.
    class IdentityPrefilter:
        @staticmethod
        def apply(ideas):
            return {"candidates": ideas, "stats": {}}
    judge.prefilter = IdentityPrefilter()
    result = judge.interpretar_lote(
        QUERY, [deepcopy(IDEA)], "activation-09", "run-09", 23,
    )["interpretados"][0]
    return result, port, store


@pytest.mark.parametrize("mutation", [
    "row_pending", "inner_pending", "inner_not_evaluated",
    "inner_timeout", "result_timeout", "wrong_prompt",
    "wrong_parameters", "missing_provenance", "malformed_response", "missing_row",
])
def test_unusable_winner_never_overrides_current_response(mutation):
    row = winner_row()
    if mutation == "row_pending":
        row["veredicto"] = "PENDIENTE_INTERPRETACION"
    elif mutation == "inner_pending":
        row["response"]["interpretation"]["interprete_verdict"] = "PENDIENTE_INTERPRETACION"
    elif mutation == "inner_not_evaluated":
        row["response"]["interpretation"]["interprete_evaluation_status"] = "NOT_EVALUATED"
    elif mutation == "inner_timeout":
        row["response"]["interpretation"]["interprete_analisis"] = "timeout"
    elif mutation == "result_timeout":
        row["response"]["interpretation"]["interprete_result"]["error"] = "timeout"
    elif mutation == "wrong_prompt":
        row["provenance"]["prompt_sha256"] = "0" * 64
    elif mutation == "wrong_parameters":
        row["provenance"]["generation_parameters"] = {"temperature": 999}
    elif mutation == "missing_provenance":
        row["provenance"] = None
    elif mutation == "malformed_response":
        row["response"] = {"interpretation": {}}
    else:
        row = None

    result, port, store = run_judge(row)
    assert result["interprete_raw_output"] == "FRESH_RESULT"
    assert result["interprete_verdict"] == "PROPUESTA"
    assert result["_registro"] == {
        "status": "unregistered",
        "reason": "concurrent_winner_not_reusable",
    }
    assert port.calls == store.writes == 1 and store.reads == 2


def test_winner_reused_only_after_revalidating_same_request():
    result, port, store = run_judge(winner_row())
    assert result["interprete_raw_output"] == "WINNER_RESULT"
    assert result["_registro"]["status"] == "deduplicated"
    assert port.calls == store.writes == 1 and store.reads == 2


def test_cache_hit_before_generation_does_not_call_provider():
    result, port, store = run_judge(winner_row(), hit_first=True)
    assert result["interprete_raw_output"] == "WINNER_RESULT"
    assert result["_registro"]["status"] == "deduplicated"
    assert port.calls == store.writes == 0 and store.reads == 1


def test_interpreter_mutation_cannot_change_identity_used_for_second_read():
    result, port, store = run_judge(winner_row(), mutates=True)
    assert result["interprete_raw_output"] == "WINNER_RESULT"
    assert result["_registro"]["status"] == "deduplicated"
    assert port.calls == store.writes == 1 and store.reads == 2
