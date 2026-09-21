"""ASTRA-005/026: evidence scope, selection ledger, and honest call accounting."""

import json

from criba.inventar import append_ledger


def _sheet():
    entry = {
        "candidate_id": "c-final",
        "run_id": "r",
        "title": "final",
        "estado_interpretacion": "PROPUESTA",
        "mecanismo": "m",
        "score": 0.7,
        "score_kind": "heuristica_local",
        "classes": ["f"],
        "methods": ["m1"],
        "aportacion_por_tecnica": [],
        "hipotesis": "h",
        "prueba_concreta": "p",
        "ruta_desbloqueo": "",
        "supuestos": [],
        "estado_antecedentes": "pendiente_de_busqueda",
        "evidence_retrieved": [{"doc_id": "d1"}],
        "evidence_delivered": [{"doc_id": "d1"}],
        "evidence_documented_as_used": [],
        "evidencia_local_usada": [{"doc_id": "d1"}],
        "prior_art": {"verdict": "UNRESOLVED", "queries": [], "detail": ""},
    }
    return {
        "generated_at": "2026-01-01T00:00:00+00:00",
        "query": "q",
        "seed": 1,
        "seed_source": "explicit",
        "run_id": "r",
        "mode": "stratified",
        "rounds": 1,
        "reproducibility_dependencies": {
            "closure_complete": False,
            "seed": 1,
            "known_unclosed_dependencies": ["code_version"],
        },
        "domain_coupling": {},
        "totals": {},
        "entries": [entry],
        "ficha_bloqueo": {"bloqueo": "b"},
        "seleccion_finalista": {
            "initial_candidate_pool": [{"idea_id": "c-initial"}],
            "initial_finalists": ["c-old"],
            "revision_post_interpretacion": {
                "intentos": [{"reemplazado_id": "c-old", "sustituto_id": "c-final"}],
                "candidate_development_attempts": 2,
                "model_requests": None,
                "model_requests_authoritative": False,
            },
            "finalists": ["c-final"],
            "opportunity_accounting": {
                "generated_candidates": 10,
                "selection_candidates_considered": 5,
                "budget_complete": False,
                "scope": "LOCAL_PIPELINE_ACCOUNTING_ONLY",
            },
        },
    }


def test_astra_005_ledger_does_not_call_retrieved_evidence_used(tmp_path):
    path = append_ledger(_sheet(), ledger_dir=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    entry = record["entries"][0]
    assert entry["evidence_retrieved"] == entry["evidence_delivered"]
    assert entry["evidence_documented_as_used"] == []
    assert entry["evidencia_local_usada_semantics"] == "DEPRECATED_ALIAS_FOR_EVIDENCE_DELIVERED"


def test_astra_026_ledger_reconstructs_selection_and_marks_call_count_authority(tmp_path):
    path = append_ledger(_sheet(), ledger_dir=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    audit = record["selection_audit"]
    assert audit["initial_candidate_pool"] == [{"idea_id": "c-initial"}]
    assert audit["initial_finalists"] == ["c-old"]
    assert audit["replacement_attempts"]
    assert audit["final_finalists"] == ["c-final"]
    assert audit["blocking_sheet"] == {"bloqueo": "b"}
    assert audit["call_accounting"]["model_requests"] is None
    assert audit["call_accounting"]["model_requests_authoritative"] is False


def test_astra_024_026_ledger_declares_incomplete_dependency_and_budget_closure(tmp_path):
    path = append_ledger(_sheet(), ledger_dir=tmp_path)
    record = json.loads(path.read_text(encoding="utf-8").splitlines()[-1])
    deps = record["reproducibility_dependencies"]
    assert deps["closure_complete"] is False
    assert deps["seed"] == 1
    assert "code_version" in deps["known_unclosed_dependencies"]
    opportunities = record["selection_audit"]["opportunity_accounting"]
    assert opportunities["generated_candidates"] == 10
    assert opportunities["selection_candidates_considered"] == 5
    assert opportunities["budget_complete"] is False
