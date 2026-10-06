"""Planning relationships and provenance, not a keyword-based semantic oracle."""
from __future__ import annotations

import hashlib
import json

import pytest
from criba import model_runtime
from criba.model_config import ModelProfile
from criba.supra_dossier import guardar_dossier, preparar_dossier, preparar_dossier_desde_idea
from criba.ui.actions import activate


def entry():
    return {
        "candidate_id": "relational-case",
        "hipotesis": "La intervencion reduce colas mediante cambio de escala",
        "mecanismo": "Cambiar la escala redistribuye la capacidad entre actores diferentes.",
        "prueba_concreta": "Cambiar escala y consultar el estado resultante.",
        "prueba": {
            "alternativa_explicativa": "La capacidad permanece igual tras la intervencion",
            "metrica": "Duracion de la cola en segundos",
            "resultado_favorable_mecanismo": "Disminuye la duracion",
            "resultado_favorable_alternativa": "No cambia la duracion",
        },
    }


def assessment(dossier):
    return dossier.get("interpretacion", {}).get("provenance", {}).get("planning_assessment", {})


def test_valid_json_does_not_establish_relevance_to_another_objective():
    # A structurally coherent queue hypothesis says nothing about recovery.
    # Bind the objective and retain UNKNOWN; do not 'prove' irrelevance by words.
    query = "Recuperar un episodio persistido sin repetir efectos"
    dossier = preparar_dossier(json.loads(json.dumps(entry())), query)
    quality = assessment(dossier)
    assert quality.get("relevance_status") == "UNKNOWN"
    assert quality.get("objective_sha256") == hashlib.sha256(query.encode()).hexdigest()
    assert quality.get("semantic_validation") == "NOT_VALIDATED"


def test_rival_that_restates_the_hypothesis_is_not_discriminant():
    proposal = entry()
    proposal["prueba"]["alternativa_explicativa"] = "  " + proposal["hipotesis"].upper() + "  "
    quality = assessment(preparar_dossier(proposal, "Comparar dos explicaciones"))
    assert "RIVAL_RESTATES_HYPOTHESIS" in quality.get("limitations", [])
    assert quality.get("discriminant_status") == "UNKNOWN"


def test_description_is_not_a_declared_observable_and_equal_predictions_do_not_discriminate():
    proposal = entry()
    del proposal["prueba"]["metrica"]
    proposal["prueba"]["resultado_favorable_alternativa"] = (
        proposal["prueba"]["resultado_favorable_mecanismo"]
    )
    quality = assessment(preparar_dossier(proposal, "Contrastar una intervencion"))
    assert "NO_DECLARED_OBSERVABLE" in quality.get("limitations", [])
    assert "PREDICTIONS_NOT_DISTINCT" in quality.get("limitations", [])


def test_deterministic_core_is_not_reported_as_llm_interpretation():
    query = "Reabrir un proyecto sin duplicar su despacho"
    idea = activate(query)["innovation"]["ideas"][0]
    dossier = preparar_dossier_desde_idea(idea, query)
    provenance = dossier.get("interpretacion", {}).get("provenance", {})
    assert provenance.get("interpreter_backend") == "deterministic_core"
    quality = assessment(dossier)
    assert quality.get("content_origin") == "GENERATED_DETERMINISTIC"
    assert "REPRESENTATION_ONLY_NOT_FUNCTIONAL_TEST" in quality.get("limitations", [])
    assert quality.get("relevance_status") == "UNKNOWN"


def test_closed_json_prefix_with_length_metadata_is_still_rejected(monkeypatch):
    monkeypatch.setattr(model_runtime, "_http_json", lambda *a, **kw: {
        "choices": [{"finish_reason": "length", "message": {"content": '{"ideas": []}'}}],
    })
    with pytest.raises(model_runtime.ModelRuntimeError, match="truncada"):
        model_runtime._generate_once(ModelProfile(), "system", "prompt")


def test_block_reason_is_read_from_persisted_checkpoint_not_inferred_from_http():
    from types import SimpleNamespace

    from criba.ui import actions

    lookup = SimpleNamespace(
        status="blocked", status_scope="WORKFLOW_EXECUTION_ONLY", completion_status="BLOCKED",
        workflow_status="BLOCKED", verification_status="FAIL", scientific_status="NOT_VALIDATED",
        secure_sandbox_status="RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        criba_planning_receipt_status="PRESERVED_NOT_EXECUTED",
        criba_mechanism_execution_status="NOT_EXECUTED", status_source="PERSISTED_STATE",
        persisted_artifact_status="VERIFIED_FROM_ARTIFACT", persisted_artifact_error_kind=None,
        stage="BLOCKED", posture=SimpleNamespace(criba_dossier_receipt=None, checkpoints=[{
            "stage": "BLOCKED", "actor": "system:completion_gate",
            "evidence_summary": (
                "Completion blocked: verification must be PASS; current verdict is FAIL."
            ),
        }]),
    )
    read = actions._supra_lookup_read(lookup)
    assert read.get("block_reason_kind") == "VERIFICATION_GATE"
    assert read.get("block_reason", "").startswith("Completion blocked")


def test_shadow_summary_keeps_planning_scope_and_block_cause_separate():
    from criba.ui import actions

    dossier = preparar_dossier_desde_idea(
        activate("Recuperar un episodio")["innovation"]["ideas"][0], "Recuperar un episodio",
    )
    read = {"receipt": {"interpretacion": dossier["interpretacion"]},
            "workflow_status": "BLOCKED", "block_reason_kind": "VERIFICATION_GATE",
            "block_reason": "La verificacion no acredita el mecanismo"}
    formatter = getattr(actions, "_planning_status_text", None)
    assert callable(formatter), "Shadow has no planning-scope presentation contract"
    text = formatter(read)
    assert "GENERATED_DETERMINISTIC" in text
    assert "pertinencia UNKNOWN" in text
    assert "VERIFICATION_GATE" in text
    assert "La verificacion no acredita el mecanismo" in text


def test_generated_content_cannot_use_the_observed_result_write_path(tmp_path):
    dossier = preparar_dossier(entry(), "Contrastar una intervencion")
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
    with pytest.raises(ValueError, match="registrar_resultado"):
        guardar_dossier({**dossier, "tipo": "resultado_observado"}, tmp_path)
