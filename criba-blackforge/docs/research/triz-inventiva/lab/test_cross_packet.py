"""Contrato aislado: el azar escoge el cruce; no debe amputar sus operaciones."""
from __future__ import annotations

import copy
import importlib
import importlib.util
import json

from criba.interprete.contrato import prompt_propuesta
from criba.lottery import LotteryEngine


def _methods():
    return [
        {
            "id": "LAB-LENTE-A", "title": "Separación temporal", "family": "restricciones",
            "description": "Examinar condiciones temporales sin eliminar requisitos. " * 8
            + "OPERACION_FINAL_A: separar los picos de consumo con almacenamiento intermedio.",
        },
        {
            "id": "LAB-LENTE-B", "title": "Red capilar", "family": "analogias",
            "description": "Relacionar distribución de recursos y puntos de entrega. " * 8
            + "OPERACION_FINAL_B: redistribuir el recurso por derivaciones locales.",
        },
    ]


def _prepare(idea, methods, **kwargs):
    assert importlib.util.find_spec("lab.cross_packet") is not None, (
        "Falta el adaptador aislado que conserva las operaciones del cruce"
    )
    return importlib.import_module("lab.cross_packet").prepare_cross(idea, methods, **kwargs)


def test_full_operations_reach_existing_prompt_without_changing_the_draw():
    methods = _methods()
    engine = LotteryEngine.from_methods(methods, seed=0, storage=None)
    idea = engine.generate_ideas_from_batch(engine.methods)[0]
    # Fixture legacy explícito: tras IMP-10-A el productor real ya no recorta.
    # Este adaptador de laboratorio sigue cubriendo entradas históricas truncadas.
    idea["method1_desc"] = idea["method1_desc"][:200]
    idea["method2_desc"] = idea["method2_desc"][:200]
    before = copy.deepcopy(idea)
    rng_before = engine.rng.getstate()
    # Compatibilidad con la representación legacy truncada, identificada arriba.
    assert "OPERACION_FINAL_A" not in idea["method1_desc"]
    prepared = _prepare(idea, methods)
    prompt = prompt_propuesta("Reducir consumo de agua manteniendo el servicio", prepared, {}, [])
    data = json.loads(prompt.split("\nDATOS:\n", 1)[1])
    assert data["CRUCE"]["method1_desc"] == methods[0]["description"]
    assert data["CRUCE"]["method2_desc"] == methods[1]["description"]
    assert "OPERACION_FINAL_A" in prompt and "OPERACION_FINAL_B" in prompt
    assert idea == before
    assert engine.rng.getstate() == rng_before
    for key in ("method1_id", "method2_id", "quality", "score", "causal_variables"):
        assert prepared[key] == before[key]


def test_conflicting_method_identity_is_rejected_instead_of_last_writer_wins():
    import pytest

    methods = _methods()
    idea = {"method1_id": methods[0]["id"], "method2_id": methods[1]["id"]}
    duplicate = {**methods[0], "description": "Otra operación bajo el mismo ID"}
    with pytest.raises(ValueError, match="conflicting method ID"):
        _prepare(idea, methods + [duplicate])
