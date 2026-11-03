"""Adaptador de laboratorio, NO conectado al runtime.

Rehidrata el contenido de un cruce ya seleccionado desde sus registros originales.
No sortea, puntúa, filtra, llama modelos ni abre almacenamiento. Las operaciones
son datos; no constituyen una invención ni evidencia de utilidad.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def prepare_cross(
    idea: dict[str, Any], methods: list[dict[str, Any]],
) -> dict[str, Any]:
    """Conservar íntegramente las dos operaciones sin alterar el sorteo recibido."""
    by_id: dict[str, dict[str, Any]] = {}
    for method in methods:
        method_id = method["id"]
        if method_id in by_id and by_id[method_id] != method:
            raise ValueError(f"conflicting method ID: {method_id}")
        by_id[method_id] = method
    prepared = deepcopy(idea)
    records = []
    for slot in ("method1", "method2"):
        record = by_id[idea[slot + "_id"]]
        prepared[slot + "_desc"] = record["description"]
        records.append(deepcopy(record))
    prepared["cross_operational_records"] = records
    return prepared
