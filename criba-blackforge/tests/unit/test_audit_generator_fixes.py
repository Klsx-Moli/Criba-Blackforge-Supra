"""Regresiones de la auditoría 2026-10-13 sobre el generador determinista.

Cada test fija un defecto observado en ejecución real (no solo en lectura de código):
anclaje a "¿cómo", dominio por subcadena, genoma constante, base estática en la
puntuación y deduplicación incoherente.
"""
from __future__ import annotations

import pytest

from criba import engine
from criba.engine import _detect_domain, _detect_duplicates, _evaluate_idea, extract_key_concepts

CHURN = "¿Cómo podemos reducir el churn de clientes en una app de suscripción?"
PHISHING = "Diseñar una defensa contra phishing para una pyme sin presupuesto"


# --------------------------------------------------------------- conceptos clave
def test_conceptos_sin_puntuacion_ni_interrogativos() -> None:
    conceptos = extract_key_concepts(CHURN)
    assert conceptos == ["churn", "clientes", "suscripción"]
    assert all(c.isalpha() for c in conceptos)


def test_verbos_de_tarea_no_son_el_tema() -> None:
    assert extract_key_concepts(PHISHING) == ["defensa", "phishing", "pyme", "presupuesto"]


def test_acentos_se_comparan_plegados() -> None:
    # "Cómo" y "como" son la misma palabra vacía.
    assert extract_key_concepts("Cómo como CÓMO") == []


# ---------------------------------------------------------------------- dominio
@pytest.mark.parametrize(
    ("query", "esperado"),
    [
        (CHURN, "negocio"),  # antes: "tecnologia" por "red" dentro de "reducir"
        (PHISHING, "seguridad"),
        ("reducir costes de forma sostenible", "energia"),
        ("organizar una fiesta de cumpleaños", "general"),
    ],
)
def test_dominio_por_palabra_completa(query: str, esperado: str) -> None:
    assert _detect_domain(query) == esperado


def test_subcadenas_ya_no_disparan_dominio() -> None:
    # "api" dentro de "rapido" y "red" dentro de "reducir" no son tecnología.
    assert _detect_domain("hacerlo rapido") == "general"
    assert _detect_domain("reducir el gasto") == "general"
    # Pero las palabras reales sí.
    assert _detect_domain("una API publica") == "tecnologia"
    assert _detect_domain("la red de la oficina") == "tecnologia"


# ------------------------------------------------------------ anclaje y genoma
def test_ideas_ancladas_a_conceptos_reales_y_variados() -> None:
    packet = engine.activate(CHURN)
    anclas = {i["query_anchor"] for i in packet["ideas"]}
    assert anclas <= {"churn", "clientes", "suscripción"}
    assert len(anclas) >= 2
    assert not any(a.startswith("¿") for a in anclas)


def test_genoma_no_es_constante_ni_inunda_la_cola_de_revision() -> None:
    packet = engine.activate(CHURN)
    ideas = packet["ideas"]
    for campo in ("mechanism", "trust_model"):
        valores = {tuple(i["genome"][campo]) for i in ideas}
        assert len(valores) >= 2, f"genoma.{campo} es constante: {valores}"
    # El actor detectado en la consulta llega a la ontología cerrada.
    assert {tuple(i["genome"]["actor"]) for i in ideas} == {("end_user",)}
    # Valores propios del motor no se aparcan como "conceptos nuevos".
    assert packet["innovation"]["unclassified_properties"] == []


def test_propiedades_sin_clasificar_se_deduplican() -> None:
    from criba.genome import normalize_proposal

    g, _ = normalize_proposal({"actor": ["figura-inexistente"]}, source_idea="I01")
    assert len(g.unclassified_properties) == 1  # sanity: el camino de aparcado sigue vivo


# ------------------------------------------------------------------ puntuación
def test_novedad_usa_los_ejes_declarados_no_la_base_estatica() -> None:
    # quien_decide difiere de la base ESTÁTICA, pero la idea declara que no movió nada.
    idea = {
        "causal_variables": {"quien_decide": "usuarios/destinatarios finales"},
        "causal_axes_changed": [],
        "family": "inversion",
        "family2": "sustraccion",
        "extreme": False,
    }
    assert _evaluate_idea(idea)["novelty"] == 0.0


def test_ideas_legacy_sin_ejes_declarados_conservan_el_calculo_previo() -> None:
    idea = {
        "causal_variables": {"topologia": "malla"},  # != base estática "centralizada"
        "family": "a",
        "family2": "b",
        "extreme": False,
    }
    assert _evaluate_idea(idea)["novelty"] > 0.0


# ----------------------------------------------------------------- duplicados
def _idea(i: str, axes: list[str], **cv: str) -> dict:
    return {"id": i, "causal_axes_changed": axes, "causal_variables": cv}


def test_un_solo_eje_con_valores_distintos_no_es_duplicado() -> None:
    a = _idea("I01", ["cuando"], cuando="nunca")
    b = _idea("I02", ["cuando"], cuando="en produccion")
    informe = _detect_duplicates([a, b])
    assert informe[1]["verdict"] != "probable_duplicate"


def test_un_solo_eje_con_mismo_valor_si_es_duplicado() -> None:
    a = _idea("I01", ["cuando"], cuando="nunca")
    b = _idea("I02", ["si_falla"], si_falla="x")
    c = _idea("I03", ["cuando"], cuando="nunca")
    informe = _detect_duplicates([a, b, c])
    assert informe[2]["verdict"] == "probable_duplicate"
    assert informe[2]["vs"] == "I01"


def test_variante_cercana_apunta_a_la_idea_coincidente_no_a_la_ultima_vista() -> None:
    # I03 solapa con I01 (eje "cuando"). Antes, al seguir recorriendo `seen` sin
    # romper el bucle, `vs` quedaba apuntando a la ÚLTIMA idea vista (I02).
    a = _idea("I01", ["cuando", "si_falla"], cuando="x", si_falla="y")
    b = _idea("I02", ["cuando", "topologia"], cuando="x2", topologia="t")
    c = _idea("I03", ["cuando", "quien_decide"], cuando="x3", quien_decide="q")
    informe = _detect_duplicates([a, b, c])
    assert informe[2]["verdict"] == "close_variant"
    assert informe[2]["vs"] == "I01"


def test_el_relleno_no_reintroduce_duplicados_probables() -> None:
    packet = engine.activate(CHURN, supporting_methods=4)
    ids = [i["id"] for i in packet["ideas"]]
    assert len(ids) == len(set(ids))
    assert all(i["duplicate_status"] != "duplicate" for i in packet["ideas"])
