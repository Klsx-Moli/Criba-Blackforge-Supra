"""S06 — Primer slice Shadow -> T104/T111 -> MCDA.

El adapter `score_idea` resuelve, desde el catalog real de métodos, el method
candidato declarado por un idea de Shadow y produce la entrada MCDA canónica
para `criba.mcda.score`. No inventa datos: lee el catalog runtime de CRIBA
(`criba.catalog.methods`) y reutiliza el producer `mcda_inputs` (T104/T111).

Honestidad: None (ausencia) != 0.0 (medido). El composite sólo computa sobre
dimensiones presentes; la cobertura expone cuántas faltan.
"""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest

# El adapter se escribe bajo este módulo (único punto de integración Shadow->T104/T111).
_ADAPTER_MOD = "criba.intelligence.mcda_adapter"


@pytest.fixture(scope="module")
def adapter():
    """Import diferido: el adapter es el artefacto S06. Falso fixture-only cuando
    no existe aún (TDD rojo)."""
    spec = importlib.util.find_spec(_ADAPTER_MOD)
    if spec is None:
        pytest.skip(f"adapter {_ADAPTER_MOD} no implementado aún (S06 pendiente)")
    return importlib.import_module(_ADAPTER_MOD)


# --- corpus real de catálogo --------------------------------------------------
def _catalog() -> list[dict]:
    from criba.catalog import methods
    return methods()


def _sibling_method(family: str, with_tags: bool, catalog: list[dict]) -> dict:
    """Un method del mismo family, con/sin tags según se pida, del catalog real."""
    for m in catalog:
        if m.get("family") == family:
            has_tags = bool(m.get("tags"))
            if with_tags and has_tags:
                return m
            if (not with_tags) and (not has_tags):
                return m
    pytest.skip(f"catalog sin method{' con' if with_tags else ' sin'} tags para family={family}")


def _candidate_method(catalog: list[dict]) -> dict:
    """Primer method con family+tags+granularity+origin del catalog real."""
    for m in catalog:
        if m.get("family") and m.get("tags") and m.get("granularity") and m.get("origin"):
            return m
    pytest.skip("catalog sin method candidato suficientemente especificado")


def _idea_with(method: dict) -> dict:
    """Construye un idea de Shadow con method_ids apuntando al method real."""
    return {
        "id": "idea-test",
        "title": "caso real de catalog",
        "family": method["family"],
        "family1": method["family"],
        "family2": "",
        "method_ids": [method["id"]],
        "genome": {},
        "convergence": {},
    }


# --- tests --------------------------------------------------------------------
def test_score_idea_con_catalog_real_produce_dimensiones_con_sources(adapter):
    """Con corpus REAL: confidence/feasibility presentes con provenance T104/T111."""
    catalog = _catalog()
    method = _candidate_method(catalog)
    idea = _idea_with(method)
    result = adapter.score_idea(idea, catalog=catalog)
    assert result is not None, "con datos reales debe producir un score"
    dims = {d.name: d for d in result.dimensions}
    assert dims["confidence"].present and dims["confidence"].source == "T104:corpus_confidence"
    assert dims["feasibility"].present and dims["feasibility"].source == "T111:granularity_feasibility"
    assert 0.0 <= result.composite <= 1.0


def test_score_idea_usa_siblings_reales_del_mismo_family(adapter):
    """T104 confidence depende del ratio de siblings con tags en el mismo family."""
    catalog = _catalog()
    method = _candidate_method(catalog)
    idea = _idea_with(method)
    result = adapter.score_idea(idea, catalog=catalog)
    conf_dim = next(d for d in result.dimensions if d.name == "confidence")
    assert conf_dim.present  # hay al menos 1 sibling con tags
    # La cobertura incluye T104/T111 (2 de 11); el resto ausente -> WEAK/PARTIAL.
    assert result.coverage.value in ("PARTIAL", "WEAK")


def test_score_idea_ausencia_no_es_cero(adapter):
    """Sin method resoluble (idea sin method_ids/family): None, no 0.0."""
    result = adapter.score_idea({"id": "x", "method_ids": [], "family": ""}, catalog=_catalog())
    assert result is None


def test_score_idea_method_id_inexistente_cae_a_family_real(adapter):
    """Un method_id inexistente con family real resuelve por family (fallback
    canónico) y produce score sobre corpus real. method_ids es secundario: el
    family del candidate es información real, no un error a negar."""
    idea = {"id": "x", "method_ids": ["no_existe_9999"], "family": "ciencia_realidad"}
    result = adapter.score_idea(idea, catalog=_catalog())
    assert result is not None, "family real debe producir score (method_id no resuelve)"
    assert result.coverage.value in ("PARTIAL", "WEAK")


def test_score_idea_serializable_a_dict(adapter):
    """El resultado MCDA debe serializarse para el dossier Shadow (to_dict)."""
    catalog = _catalog()
    method = _candidate_method(catalog)
    idea = _idea_with(method)
    result = adapter.score_idea(idea, catalog=catalog)
    assert result is not None
    d = result.to_dict()
    assert {"composite", "coverage", "present_count", "dimensions", "unknown_dimensions"} <= set(d)
    assert d["unknown_dimensions"]


def test_score_idea_no_inventa_family_ni_valores(adapter):
    """Un idea cuyo family no hay match en catalog: None (no 0.0 por defecto)."""
    idea = {"id": "x", "method_ids": [], "family": "familia_imposible_zzz"}
    result = adapter.score_idea(idea, catalog=_catalog())
    assert result is None


def test_score_idea_rechaza_method_fuera_de_rango(adapter):
    """Si confidence/feasibility salen del [0,1], el consumer debe rechazar (ValueError),
    no clampear silenciosamente."""
    from criba.mcda import score
    # method con datos que producirían >1 NO es posible con el producer real; aquí
    # se verifica el contrato del consumer directamente (defensa de integridad).
    with pytest.raises(ValueError):
        score({"confidence": 1.5})
