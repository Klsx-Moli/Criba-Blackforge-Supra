"""Regresiones reales del cruce al prompt; sin red ni persistencia del producto."""
from __future__ import annotations

import json

import pytest
from criba.interprete.contrato import prompt_propuesta
from criba.lottery import LotteryEngine


@pytest.mark.parametrize("seed", [0, 1, 42])
def test_complete_operations_survive_lottery_and_prompt(seed: int) -> None:
    methods = [
        {
            "id": "lossless-a", "title": "Separación temporal", "family": "restricciones",
            "description": "Aplicar la operación sin perder restricciones. " * 20
            + "COLA_A: separar la demanda de su suministro inmediato.",
        },
        {
            "id": "lossless-b", "title": "Transferencia relacional", "family": "analogias",
            "description": "Transferir relaciones entre roles, no nombres. " * 20
            + "COLA_B: conectar el depósito intermedio con los puntos de uso.",
        },
    ]
    engine = LotteryEngine.from_methods(methods, seed=seed, storage=None)
    idea = engine.generate_ideas_from_batch(engine.methods)[0]
    prompt = prompt_propuesta("Reducir consumo manteniendo el servicio", idea, {}, [])
    recovered = json.loads(prompt.split("\nDATOS:\n", 1)[1])["CRUCE"]
    assert recovered["method1_desc"] == engine.methods[0]["description"]
    assert recovered["method2_desc"] == engine.methods[1]["description"]
    assert "COLA_A" in prompt and "COLA_B" in prompt
    assert idea["method1_id"] == "lossless-a"
    assert idea["method2_id"] == "lossless-b"
    assert idea["method1_desc"] == methods[0]["description"]
    assert idea["method2_desc"] == methods[1]["description"]

    # Metamorphic replay: the same seed must preserve scores, identity, and RNG state.
    replay = LotteryEngine.from_methods(methods, seed=seed, storage=None)
    replay_idea = replay.generate_ideas_from_batch(replay.methods)[0]
    assert idea == replay_idea
    assert engine.rng.getstate() == replay.rng.getstate()
    state_after_generation = engine.rng.getstate()
    prompt_propuesta("Reducir consumo manteniendo el servicio", idea, {}, [])
    assert engine.rng.getstate() == state_after_generation


def test_quoted_multiline_operations_are_valid_prompt_data() -> None:
    idea = {
        "method1_desc": '"Separar" condiciones\nsin descartar límites ni símbolos \\',
        "method2_desc": '"Transferir" relaciones\nentre ámbitos: presión → demanda',
    }
    prompt = prompt_propuesta("Problema con restricciones", idea, {}, [])
    recovered = json.loads(prompt.split("\nDATOS:\n", 1)[1])["CRUCE"]
    assert recovered == idea
