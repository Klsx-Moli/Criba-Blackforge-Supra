"""Datos de prueba compartidos para los tests de K3.

Se construyen desde ``semantic_cases`` para no duplicar el corpus ni las
propuestas: si el caso legitimo cambia, estos tests siguen su contrato.

OJO: ``PARENTS`` es una tupla de tuplas planas con la forma
``(id, query, mecanismo, metrica, restricciones)``. Indexar ``[1][0]`` sobre
la query devolveria el primer caracter, no la primera frase.
"""

from __future__ import annotations

from typing import Any

from .semantic_cases import PARENTS, _proposal

# Caso legitimo de la ducha: el mismo del incidente P0, en su version oficial.
_CASO = PARENTS[0]

QUERY: str = _CASO[1]
MECANISMO: str = _CASO[2]
METRICA: str = _CASO[3]
RESTRICCIONES: tuple[str, ...] = tuple(_CASO[4])

IDEA: dict[str, Any] = {
    "title": "Reutilizar agua fria del precalentamiento",
    "method1": "Desvio",
    "method2": "Deposito intermedio",
    "bloqueo": {"restricciones_obligatorias": list(RESTRICCIONES)},
}

PROPUESTA: dict[str, Any] = _proposal(MECANISMO, METRICA, RESTRICCIONES)

EVIDENCE: list[dict[str, Any]] = [
    {"title": "agua fria en el arranque de la ducha",
     "abstract": "El agua fria del precalentamiento llega al desague."},
]


def evidence() -> list[dict[str, Any]]:
    """Nombre de funcion para evitar el shadowing del modulo de contrato."""
    return EVIDENCE