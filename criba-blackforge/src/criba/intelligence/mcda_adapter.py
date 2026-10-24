"""S06 adapter: Shadow idea -> canonical MCDA (T104/T111 producer).

Responsabilidad única: dado un candidate/idea de Shadow y el catálogo real de
CRIBA, resolver el method candidato (por ``method_ids`` o ``family``) y producir
la entrada MCDA canónica consumida por ``criba.mcda.score``.

- Producer T104/T111: ``criba.intelligence.scoring.evidence.mcda_inputs``.
- Consumer canónico: ``criba.mcda.score`` (DOMAIN 11, deterministico).
- Datos: ``criba.catalog.methods`` (catálogo runtime aprobado, corpus real).

Honestidad (EEIMC-001 Art. 9):
  - ``None`` == "no evaluado" (ausencia), NUNCA un 0.0 medido.
  - confidence(T104) ratio de siblings con tags en el mismo family.
  - feasibility(T111) promedio de granularity/origin.
  - Ambos devuelven ``None`` cuando falta la información mínima.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from criba.catalog import methods as _catalog_methods
from criba.intelligence.scoring.evidence import mcda_inputs, mcda_sources
from criba.mcda import MCDAResult, score

__all__ = ["score_idea"]


def _resolve_method(idea: Mapping[str, Any], catalog: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
    """Resuelve el method candidato REAL desde el catálogo aprobado.

    Orden de preferencia: ``method_ids[0]`` -> join por ``id``; si falla,
    el primer method del mismo ``family`` que tenga family declarada.
    Devuelve ``None`` si no hay resolución (ausencia, no invención).
    """
    method_ids = idea.get("method_ids") or []
    catalog_ids = {str(m.get("id")): m for m in catalog if m.get("id") is not None}
    if method_ids and str(method_ids[0]) in catalog_ids:
        return catalog_ids[str(method_ids[0])]
    family = idea.get("family") or ""
    if family:
        for m in catalog:
            if m.get("family") == family:
                return m
    return None


def _family_siblings(method: Mapping[str, Any], catalog: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    """Los siblings son methods del MISMO family (contrato T104 confidence)."""
    family = method.get("family")
    if not isinstance(family, str) or not family.strip():
        return []
    return [m for m in catalog if m.get("family") == family]


def score_idea(
    idea: Mapping[str, Any],
    *,
    catalog: Sequence[Mapping[str, Any]] | None = None,
) -> MCDAResult | None:
    """Produce el MCDAResult canónico para un idea de Shadow (T104/T111).

    - ``None`` si el idea no resuelve a un method con family (ausencia real,
      no un 0.0 por defecto).
    - En caso contrario invoca el producer T104/T111 sobre corpus real y el
      consumer ``criba.mcda.score`` con provenance declarado.
    """
    catalog = list(catalog) if catalog is not None else list(_catalog_methods())
    method = _resolve_method(idea, catalog)
    if method is None or not method.get("family"):
        return None
    siblings = _family_siblings(method, catalog)
    if not siblings:
        return None

    inputs = mcda_inputs(method, sibling_methods=siblings)
    # mcda_inputs ya aplica el contrato None: si family/siblings vacíos,
    # confidence=None; si granularity/origin faltan, feasibility=None.
    result = score(inputs, sources=mcda_sources())
    return result
