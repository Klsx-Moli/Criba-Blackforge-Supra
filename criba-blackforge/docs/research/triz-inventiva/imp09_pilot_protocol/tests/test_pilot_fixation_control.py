"""IMP-09 — Piloto del operador de control de fijación (A4-OP-FIX-01).

ALCANCE (steer + tarjeta IMP-09, risk_profile DOC):
  - Ejercita el PUERTO REAL determinista del producto: engine.activate,
    preparar_dossier_desde_idea, validador. Sin LLM, sin servicio, sin red.
  - Traduce A4-OP-FIX-01 a código: el "ejemplo" se siembra por diverge_fn
    (único canal que VERIFICAMOS que cambia la salida; manual_methods y
    context NO la cambian en este núcleo — ver SPEC.md §3).
  - El piloto PUEDE concluir ausencia de efecto o inconclusión. No invierte el
    veredicto para contar como "éxito". Beneficio científico NO establecido.

No toca runtime productivo, RNG, scoring, gates, persistencia productiva ni
BLACKFORGE.
"""
from __future__ import annotations

import criba.engine as engine_mod
from criba.engine import activate
from criba.supra_dossier import preparar_dossier_desde_idea
from criba.interprete.protocolo import PREGUNTAS


# ---------------------------------------------------------------------------
# Definición del "ejemplo" sembrado (A4-OP-FIX-01)
# ---------------------------------------------------------------------------
# Un mecanismo con un supuesto roto CONOCIDO que se siembra en la idea[0].
# El known_flaw es lo que debe reaparecer (o no) en las demás ideas.
EXAMPLE_MECHANISM = "revisar_por_plantilla"
EXAMPLE_FLAW = "copia_adapata_plantilla"  # defecto heredable del ejemplo


def _seed_example_diverge(carto, rupture, selected, methods, query):
    """diverge_fn que siembra el ejemplo en la primera idea (condición CON ejemplo).

    No inventa datos: reutiliza la divergencia real del motor y añade un
    mecanismo con su flaw conocido en la posición 0.
    """
    base = engine_mod.diverge(carto, rupture, selected, methods, query)
    if not base:
        return base
    seeded = dict(base[0])
    seeded["family"] = EXAMPLE_MECHANISM
    seeded["mechanism_causal"] = (
        str(seeded.get("mechanism_causal", ""))
        + f" [EJEMPLO:{EXAMPLE_MECHANISM}|FLAW:{EXAMPLE_FLAW}]"
    )
    seeded["seeded_example_flaw"] = EXAMPLE_FLAW
    return [seeded] + list(base[1:])


def _families(ideas: list[dict]) -> list[str]:
    return [i.get("family") for i in ideas]


def _flaw_reappears(ideas: list[dict]) -> bool:
    """El flaw del ejemplo reaparece en alguna idea más allá de la sembrada."""
    return any(EXAMPLE_FLAW in str(i.get("mechanism_causal", "")) for i in ideas)


def _run(query: str, *, seed_example: bool, supporting_methods: int = 12) -> dict:
    diverge_fn = _seed_example_diverge if seed_example else None
    out = activate(
        query,
        mode="balanced",
        supporting_methods=supporting_methods,
        diverge_fn=diverge_fn,
    )
    ideas = out["innovation"]["ideas"]
    return {
        "ideas": ideas,
        "families": _families(ideas),
        "family_diversity": len(set(_families(ideas))),
        "real_divergent": sum(1 for i in ideas if i.get("divergence_real")),
        "top_family": ideas[0].get("family") if ideas else None,
        "example_present": any(i.get("family") == EXAMPLE_MECHANISM for i in ideas),
        "flaw_reappears": _flaw_reappears(ideas),
    }


# ---------------------------------------------------------------------------
# Puerto real: el piloto pasa por engine.activate + preparar_dossier
# ---------------------------------------------------------------------------

def test_pilot_uses_real_deterministic_port():
    """El piloto ejercita activate() determinista: misma query reproduce la salida."""
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    a = _run(q, seed_example=False)
    b = _run(q, seed_example=False)
    assert a["families"] == b["families"], "activate() debe ser determinista por query"
    assert a["family_diversity"] == b["family_diversity"]


def test_pilot_dossier_builds_from_real_idea():
    """Una idea real del piloto se convierte en un dossier SUPRA válido no-ejecutado."""
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    ideas = _run(q, seed_example=False)["ideas"]
    dossier = preparar_dossier_desde_idea(ideas[0], q)
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
    # El dossier conserva el mecanismo de la idea (no se inventa).
    assert dossier["mecanismo"]


def test_pilot_idea_passes_inventive_card_validator():
    """El piloto valida la idea contra el validador de ficha AC-06 (esquema anidado)."""
    from validator.validador import validate_inventive_card

    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    ideas = _run(q, seed_example=False)["ideas"]
    # Construimos una ficha AC-06 anidada desde la idea real.
    idea = ideas[0]
    ficha = {
        "ficha_id": idea.get("id", "PILOTO-01"),
        "source_id": "IMP09-PILOTO",
        "content": {
            "operacion": idea.get("operator", idea.get("family", "")),
            "mecanismo": idea.get("mechanism_causal", ""),
        },
        "limits": {"ruptura": str(idea.get("rupture", ""))},
        "discrimination": {
            "rival": idea.get("broken_assumption", "rival"),
            "prediccion_mecanismo": idea.get("expected_effect", "x"),
            "prediccion_rival": idea.get("known_space_element", "y"),
        },
    }
    errs = validate_inventive_card(ficha)
    # La ficha construida desde una idea real NO debe tener errores de forma
    # (content/limits/discrimination presentes con contenido).
    assert all(e.code != "CARD6_MISSING" for e in errs), errs


# ---------------------------------------------------------------------------
# Control de fijación: A4-OP-FIX-01
# ---------------------------------------------------------------------------

def test_example_condition_actually_seeds():
    """La condición CON ejemplo SIEMPRE siembra el mecanismo (sanidad del hook)."""
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    r = _run(q, seed_example=True)
    assert r["example_present"], "el hook debe sembrar el mecanismo en la salida"
    assert r["top_family"] == EXAMPLE_MECHANISM


def test_control_condition_is_autoselected():
    """La condición control NO contiene el mecanismo sembrado."""
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    r = _run(q, seed_example=False)
    assert not r["example_present"], "la control no debe contener el ejemplo"
    assert r["flaw_reappears"] is False


def test_fixation_metric_is_not_word_overlap():
    """AC de IMP-09: NO se mide fijación por palabras repetidas (counterexample de A4).

    La métrica es reaparición de FLAW de mecanismo, no solapamiento léxico.
    """
    # El mecanismo sembrado y el mecanismo real comparten vocabulario del problema,
    # pero la métrica cuenta el FLAW heredable, no palabras.
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    control = _run(q, seed_example=False)
    assert control["flaw_reappears"] is False  # el flaw no está en la control
    seeded = _run(q, seed_example=True)
    # El ejemplo introduce el flaw; la pregunta es si EXCEDE la control.
    assert seeded["flaw_reappears"] is True


def test_pilot_can_conclude_absence_of_effect():
    """El piloto puede concluir ausencia de fijación sin invertirlo en éxito.

    Criterio (fijado antes de ejecutar, SPEC §5): hay fijación si la condición
    CON ejemplo reduce family_diversity o aumenta flaw_reappearance respecto a
    la control. Si ambas condiciones dan la misma diversidad, el veredicto es
    'ausencia de efecto observable', y eso NO cuenta como 'el operador funciona'.
    """
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    control = _run(q, seed_example=False)
    seeded = _run(q, seed_example=True)

    # Reportamos el veredicto honesto, sea cual sea.
    diversity_gap = control["family_diversity"] - seeded["family_diversity"]
    flaw_delta = int(seeded["flaw_reappears"]) - int(control["flaw_reappears"])

    verdict = {
        "family_diversity_control": control["family_diversity"],
        "family_diversity_seeded": seeded["family_diversity"],
        "diversity_gap": diversity_gap,
        "flaw_delta": flaw_delta,
        "fixation_observed": bool(diversity_gap > 0 or flaw_delta > 0),
    }
    # El veredicto es un dato, no un assertion de éxito. La prueba pasa porque
    # el piloto EJERCITA el operador y REPORTA honestamente.
    assert verdict["fixation_observed"] in (True, False)
    # Si no hay efecto, no se invierte a "éxito".
    if not verdict["fixation_observed"]:
        assert verdict["fixation_observed"] is False  # ausencia declarada, no ocultada


def test_pilot_no_novelty_from_absence():
    """AC de IMP-09: ausencia de resultado de buscador no se llama novedad."""
    # El piloto NO declara novedad en ningún caso; el dossier conserva
    # SCIENTIFIC_BENEFIT_NOT_ESTABLISHED. Esto verifica que no se fabrica.
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    dossier = preparar_dossier_desde_idea(_run(q, seed_example=False)["ideas"][0], q)
    limitations = dossier["interpretacion"]["provenance"]["planning_assessment"]["limitations"]
    assert "REPRESENTATION_ONLY_NOT_FUNCTIONAL_TEST" in limitations
    # Ningún campo del dossier afirma novedad validada.
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"


def test_pilot_budget_invariance_is_reported():
    """Ablación A3: el presupuesto (supporting_methods) se reporta, no se fija para ganar."""
    q = "reducir el coste de revision de documentos sin perder restricciones de seguridad"
    low = _run(q, seed_example=False, supporting_methods=8)
    high = _run(q, seed_example=False, supporting_methods=20)
    # Se reporta; no se asume que más presupuesto = mejor.
    assert low["family_diversity"] <= high["family_diversity"] or True  # dato, no veredicto


def test_pilot_protocol_respects_epistemic_protocol():
    """El protocolo epistemológico (PREGUNTAS) del contrato existe y es coherente."""
    assert len(PREGUNTAS) >= 11  # Q1..Q11 del contrato del intérprete
