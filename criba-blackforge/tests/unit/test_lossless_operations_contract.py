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


def test_quoted_multiline_operations_are_valid_prompt_data() -> None:
    idea = {
        "method1_desc": '"Separar" condiciones\nsin descartar límites ni símbolos \\',
        "method2_desc": '"Transferir" relaciones\nentre ámbitos: presión → demanda',
    }
    prompt = prompt_propuesta("Problema con restricciones", idea, {}, [])
    recovered = json.loads(prompt.split("\nDATOS:\n", 1)[1])["CRUCE"]
    assert recovered == idea
