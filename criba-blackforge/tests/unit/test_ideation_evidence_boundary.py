"""Ideation is not empirical validation; missing data must never be fabricated."""

import json

from criba.interprete.contrato import (
    CRITICA_INSTRUCCIONES,
    INSTRUCCIONES,
    prompt_critica,
    prompt_propuesta,
    validar_propuesta,
)

from verification.interpreter_cases import propuesta


def test_contract_already_accepts_conditional_hypothesis_without_local_evidence():
    candidate = propuesta()  # Explicit synthetic validator fixture, not model output.
    assert candidate["evidencia_citada"] == []
    assert candidate["supuestos"]
    assert validar_propuesta(candidate, {}, []) == []


def test_no_evidence_never_allows_a_fabricated_citation():
    candidate = propuesta()
    candidate["evidencia_citada"] = [1]
    assert any("evidencia_citada" in e for e in validar_propuesta(candidate, {}, []))


def test_prompt_distinguishes_missing_evidence_from_a_reason_to_abstain():
    idea = {"quality": "BASURA", "evidence_context": {"retrieval_status": "UNKNOWN"}}
    prompt = prompt_propuesta("Problema sintético", idea, {}, [])
    assert "La ausencia de evidencia local no es, por sí sola, motivo de abstención." in prompt
    assert "Las etiquetas heurísticas del cruce no son veredictos científicos." in prompt
    assert "Si RESTRICCIONES OBLIGATORIAS está vacío" in prompt
    data = json.loads(prompt.split("\nDATOS:\n", 1)[1])
    assert "quality" not in data["CRUCE"]
    assert data["CRUCE"]["evidence_context"] == idea["evidence_context"]
    assert data["EVIDENCIA LOCAL PERTINENTE"] == []


def test_prompt_omits_internal_heuristic_labels_but_keeps_operations():
    idea = {
        "title": "Cruce sintético",
        "method1": "A",
        "method1_desc": "Operación A",
        "method2": "B",
        "method2_desc": "Operación B",
        "quality": "BASURA",
        "score": 0.01,
        "convergence": {"novelty": 0.0, "value_score": 0.0},
        "genome": {"mechanism": ["unknown"]},
        "cross_operational_records": [{"name": "A", "template": "Operación A"}],
    }
    data = json.loads(prompt_propuesta("Problema", idea, {}, []).split("\nDATOS:\n", 1)[1])
    cruce = data["CRUCE"]
    assert cruce["cross_operational_records"] == idea["cross_operational_records"]
    assert cruce["method1_desc"] == "Operación A"
    assert not {"quality", "score", "convergence", "genome"} & cruce.keys()


def test_prompt_exposes_exact_mandatory_restrictions_in_original_order():
    restrictions = ["No contaminar la red potable", "No aumentar el consumo total de agua"]
    idea = {"bloqueo": {"restricciones_obligatorias": restrictions}}

    prompt = prompt_propuesta("Problema sintético", idea, {}, [])
    data = json.loads(prompt.split("\nDATOS:\n", 1)[1])

    assert data["RESTRICCIONES OBLIGATORIAS"] == restrictions
    assert "mismo texto, orden y cantidad" in " ".join(prompt.split())


def test_critique_checks_honest_assumptions_not_completed_experiments():
    assert (
        "Una hipótesis condicional no exige un experimento ya realizado." in CRITICA_INSTRUCCIONES
    )


def test_proposal_prompt_states_design_objective_and_explicit_cross_use():
    prompt = prompt_propuesta("Mejorar el riego sin aumentar el consumo", {}, {}, [])
    assert "Un objetivo de diseño o mejora es un problema legítimo" in prompt
    assert (
        "El CRUCE no es decorativo: usa al menos una operación concreta de cada técnica"
        in prompt
    )
    assert "cómo cambia el mecanismo del dominio" in prompt


def test_critique_prompt_is_separate_and_keeps_design_and_nonfatal_rules():
    prompt = prompt_critica(
        "Mejorar el riego sin aumentar el consumo",
        {"title": "Cruce sintético"},
        {},
        [],
        {"mecanismo": "Una compuerta regula el paso."},
    )
    assert INSTRUCCIONES not in prompt
    assert CRITICA_INSTRUCCIONES in prompt
    assert "Un objetivo de diseño o mejora es legítimo" in prompt
    assert (
        "Una objeción que no invalide el mecanismo ni la prueba es una limitación, no un rechazo."
        in prompt
    )


def test_legitimate_abstention_remains_rejected_as_a_proposal():
    errors = validar_propuesta(
        {"pertinencia": "ABSTENER", "motivo_abstencion": "No hay un mecanismo específico."}, {}, []
    )
    assert errors == ["abstencion:No hay un mecanismo específico."]
