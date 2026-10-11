"""M2 · sentinel del dossier derivado del núcleo real.

Defecto reproducido por ejecución (2026-10-02), no leído del código: un dossier
construido con ``preparar_dossier`` a partir de una idea real del núcleo
determinista lo rechazaba el schema VALIDADO de SUPRA con 422, porque cuatro
obligaciones del protocolo salían vacías::

    criba_dossier.prueba_discriminante.alternativa_explicativa   (min_length=1)
    criba_dossier.prueba_discriminante.resultado_favorable_mecanismo
    criba_dossier.prueba_discriminante.resultado_favorable_alternativa
    criba_dossier.prueba_discriminante.regla_decision

Es decir: la ruta «núcleo → dossier → SUPRA» estaba muerta de origen, y lo
estaba porque NADIE derivaba esas cuatro. La tentación era rellenarlas con un
texto de relleno; eso convierte una declaración ausente en una declaración
falsa, que es justo lo que este proyecto prohíbe. Aquí cada campo tiene una
única fuente declarada, y si la fuente falta la función falla en voz alta.

Lo que este archivo protege:
  * las 8 obligaciones se satisfacen con contenido real (no con relleno)
  * H2 es el supuesto que el motor dice romper, no un texto inventado
  * `SUPRA_EJECUCUCION_PENDIENTE` y `NO_EJECUTADA` sobreviven a la derivación
  * una idea sin campo declarado falla, no se completa

Sentinela de mutación:
  * ``broken_assumption`` -> un literal -> ``test_alternative_is_...``
  * rellenar el campo faltante con un placeholder -> ``test_missing_source_field_fails``
  * ``estado_prueba`` a PASS -> ``test_dossier_never_claims_an_executed_test``
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from criba.engine import activate  # noqa: E402
from criba.supra_dossier import (  # noqa: E402
    _entry_desde_idea,
    preparar_dossier_desde_idea,
)

PROBLEM = (
    "Reducir el número de permisos excesivos concedidos a un agente sin perder "
    "trazabilidad de las decisiones."
)

PROTOCOL_OBLIGATIONS = (
    "afirmacion_decisiva",
    "alternativa_explicativa",
    "intervencion_prueba",
    "observable",
    "resultado_favorable_mecanismo",
    "resultado_favorable_alternativa",
    "regla_decision",
    "condicion_fracaso",
)


@pytest.fixture(scope="module")
def idea() -> dict:
    packet = activate(PROBLEM)
    return packet["innovation"]["ideas"][0]


def test_every_obligation_is_satisfied_with_declared_content(idea: dict) -> None:
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)
    prueba = dossier["prueba_discriminante"]
    for field in PROTOCOL_OBLIGATIONS:
        assert str(prueba.get(field) or "").strip(), f"obligación vacía: {field}"


def test_every_idea_of_the_core_yields_a_complete_protocol() -> None:
    """Coverage, not one lucky idea: the route must not depend on a sample."""
    problems = (
        PROBLEM,
        "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste.",
        "Evitar que un service mesh se degrade sin invariant verification.",
    )
    empty_seen: list[str] = []
    total = 0
    for problem in problems:
        for core_idea in activate(problem)["innovation"]["ideas"]:
            total += 1
            dossier = preparar_dossier_desde_idea(core_idea, problem)
            prueba = dossier["prueba_discriminante"]
            for field in PROTOCOL_OBLIGATIONS:
                if not str(prueba.get(field) or "").strip():
                    empty_seen.append(f"{core_idea.get('id')}:{field}")
    assert total > 100, f"solo {total} ideas examinadas: la cobertura no es creíble"
    assert not empty_seen, f"obligaciones vacías en {len(empty_seen)} casos: {empty_seen[:5]}"


def test_alternative_is_the_declared_broken_assumption(idea: dict) -> None:
    """H2 is what the engine says it breaks — that is the rival explanation.

    A generic filler here would make the protocol non-discriminant while still
    passing every non-empty assertion.
    """
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)
    alternative = dossier["prueba_discriminante"]["alternativa_explicativa"]
    assert alternative == idea["broken_assumption"].strip()


def test_protocol_declares_the_concrete_axis_moves(idea: dict) -> None:
    """The observable must name the before/after the engine declared.

    Without the concrete moves there is nothing an observation could confirm.
    """
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)
    prueba = dossier["prueba_discriminante"]
    signature = idea["difference_signature"]
    for part in signature.strip("()").split("|"):
        axis, _, _values = part.strip().partition(":")
        assert axis.strip() in prueba["observable"], f"eje ausente del observable: {axis}"
        assert axis.strip() in prueba["regla_decision"]


def test_dossier_never_claims_an_executed_test(idea: dict) -> None:
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"


def test_derivation_preserves_the_engine_own_unvalidated_marker(idea: dict) -> None:
    """The engine marks its mechanism PROPOSED_UNVALIDATED; that must survive."""
    entry = _entry_desde_idea(idea, PROBLEM)
    assert entry["causal_claim"] == idea["causal_claim"]
    assert entry["causal_claim"] == "MECHANISM_PROPOSED_UNVALIDATED"


def test_version_identity_is_computed_by_the_shared_assembler(idea: dict) -> None:
    """One assembler owns versions and identity; this path must not fork it."""
    dossier = preparar_dossier_desde_idea(idea, PROBLEM)
    assert dossier["mechanism_version"].startswith("sha256:")
    assert dossier["protocol_version"].startswith("sha256:")
    assert dossier["candidate_id"] == idea["id"]
    assert dossier["claim_id"].startswith("claim-")
    assert dossier["dossier_id"].startswith("dossier-")


@pytest.mark.parametrize(
    "field",
    [
        "expected_effect",
        "mechanism_causal",
        "mechanism_explanation",
        "broken_assumption",
        "difference_signature",
    ],
)
def test_missing_source_field_fails_instead_of_inventing(idea: dict, field: str) -> None:
    """A missing declaration is UNKNOWN, and UNKNOWN is not a placeholder."""
    broken = {k: v for k, v in idea.items() if k != field}
    with pytest.raises(ValueError):
        preparar_dossier_desde_idea(broken, PROBLEM)


def test_unparsable_axis_signature_is_rejected(idea: dict) -> None:
    """A signature that is not a move cannot become an observable."""
    broken = {**idea, "difference_signature": "(escala_operacion)"}
    with pytest.raises(ValueError, match="difference_signature"):
        preparar_dossier_desde_idea(broken, PROBLEM)


def test_missing_evidence_requirement_is_rejected(idea: dict) -> None:
    broken = {**idea, "causal_variables": {k: v for k, v in idea["causal_variables"].items()
                                          if k != "evidencia_requerida"}}
    with pytest.raises(ValueError, match="evidencia_requerida"):
        preparar_dossier_desde_idea(broken, PROBLEM)
