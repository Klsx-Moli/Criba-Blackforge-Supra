"""F3 — el pool del lote debe entregar al selector lo que el contrato exige.

RED (reproducido 2026-10-22): `LotteryEngine.generate_ideas_from_batch` exponía
``family1``/``family2`` pero NO ``family``; `select_finalists` lee
``candidate.get("family")`` y recibía ``None`` (``None == None`` contaba como
familia repetida) y el genoma quedaba vacío, de modo que la distancia estructural
era siempre 0. Los datos ya existían en el productor (``family1``/``family2`` y
``causal_variables``); el consumidor del contrato exigía conservarlos.

El genoma se restaura desde el productor canónico `engine._genome_from_vector`
sobre la base canónica `_BASE_VALUES` — **no** se fabrica desde títulos/longitud.
"""
from __future__ import annotations

from criba.catalog import methods as catalog_methods
from criba.diversity_selector import select_finalists
from criba.lottery import LotteryEngine

_Q = "Detectar abuso de permisos en agentes de software autónomos"


def _pool(seed: int = 7):
    engine = LotteryEngine.from_methods(catalog_methods(), seed=seed)
    engine.run_round(mode="stratified", batch_size=8, query=_Q)
    return engine, engine.get_top_ideas(16)


def test_pool_expone_family_que_el_selector_consume() -> None:
    """El selector lee ``family``; el pool debe exponerla, no solo family1."""
    _, pool = _pool()
    assert pool, "el pool no puede estar vacío"
    for idea in pool:
        assert idea.get("family"), (
            f"F3: la idea pierde 'family' (el selector la consume): "
            f"family1={idea.get('family1')!r}"
        )


def test_family_conservada_y_consistente_con_family1() -> None:
    """``family`` debe ser fiel a la familia canónica, no un valor inventado."""
    _, pool = _pool()
    for idea in pool:
        assert idea["family"] == idea.get("family1"), (
            "family debe derivar de la familia canónica del productor"
        )


def test_pool_expone_genoma_canónico() -> None:
    """El genoma debe venir del productor canónico, no de un campo vacío."""
    _, pool = _pool()
    with_genome = [i for i in pool if i.get("genome")]
    assert with_genome, "F3: ningún candidato expone genoma"
    for idea in with_genome:
        assert isinstance(idea["genome"], dict)
        # El genoma canónico tiene estas cinco dimensiones.
        for key in ("actor", "mechanism", "topology", "trust_model", "time_model"):
            assert key in idea["genome"], f"F3: genoma sin dimensión '{key}'"


def test_genoma_no_se_fabrica_desde_titulos() -> None:
    """El genoma no puede depender del texto del título/descripción."""
    _, pool = _pool()
    for idea in pool:
        if not idea.get("genome"):
            continue
        genome = idea["genome"]
        # Las dimensiones del genoma canónico son listas de tokens de ontología,
        # no el título ni la descripción.
        for key, values in genome.items():
            assert isinstance(values, list), f"F3: genoma['{key}'] no es lista"
            assert all(isinstance(v, str) for v in values)
            assert idea.get("title") not in values, "genoma fabricado desde título"
            assert idea.get("description") not in values, "genoma desde descripción"


def test_select_finalists_ve_family_no_none() -> None:
    """Con el pool corregido, el selector compara familias reales, no None."""
    _, pool = _pool()
    selected, _report = select_finalists(pool, 4)
    assert selected, "no se seleccionó ningún candidato"
    for cand in selected:
        assert cand.get("family") is not None, (
            "F3: el selector recibe family=None pese a estar disponible"
        )


def test_family1_family2_se_conservan_sin_perdida() -> None:
    """La corrección no elimina los campos previos del productor."""
    _, pool = _pool()
    for idea in pool:
        assert "family1" in idea and "family2" in idea
        assert "family" in idea
        assert "causal_variables" in idea
