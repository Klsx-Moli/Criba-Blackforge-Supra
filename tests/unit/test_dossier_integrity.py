"""Regresiones de atribución: datos sintéticos, sin validar ideas reales."""
import hashlib
import json
from copy import deepcopy

import pytest

from criba.supra_dossier import (
    guardar_dossier, lecciones_previas, preparar_dossier, registrar_resultado,
)


def dossier(mechanism="MECANISMO_ANTERIOR"):
    return preparar_dossier(
        {
            "candidate_id": "candidate-repetido",
            "run_id": "r1",
            "hipotesis": "el mecanismo modifica la cola",
            "mecanismo": mechanism,
            "prueba_concreta": "aplicar el mecanismo y medir la cola",
            "observable": "tiempo medio de cola",
            "resultado_favorable_mecanismo": "la cola disminuye",
            "resultado_favorable_alternativa": "la cola no disminuye",
            "regla_decision": "positivo si la cola disminuye",
        },
        "reducir cola de atencion",
        alternativa_explicativa="la cola cambia por demanda externa",
    )


def write_legacy(directory, records):
    path = directory / "dossiers.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return path


def observed(d):
    receipt = {
        "candidate_id": d.get("candidate_id", ""),
        "mechanism_version": d.get("mechanism_version", ""),
        "claim_id": d.get("claim_id", ""),
        "protocol_version": d.get("protocol_version", ""),
        "execution_id": "exec-synthetic",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    observation_id = hashlib.sha256(
        f"{d['dossier_id']}|exec-synthetic|{d.get('protocol_version', '')}".encode("utf-8")
    ).hexdigest()
    return {
        "tipo": "resultado_observado",
        "observation_id": observation_id,
        "revision_index": 0,
        "first_registered_at": "2026-01-01T00:00:00+00:00",
        "registrado_at": "2026-01-01T00:00:00+00:00",
        "dossier_id": d["dossier_id"],
        **{k: receipt[k] for k in ("candidate_id", "mechanism_version", "claim_id", "protocol_version", "execution_id")},
        "observed_result": "positivo",
        "execution_receipt": receipt,
        "receipt_authority": "EXECUTION_RESOLVER",
        "result_semantics_version": 3,
        "protocol_complete": True,
        "learning_eligible": True,
        "accreditation": "ACCREDITED_EXECUTION",
        "resultado": "positivo",
        "condiciones": "DATOS SINTETICOS",
    }


def test_each_preparation_has_own_identity():
    a, b = dossier(), dossier()
    assert a["dossier_id"] != b["dossier_id"]
    assert a["candidate_id"] == b["candidate_id"] == "candidate-repetido"
    assert a["run_id"] == b["run_id"] == "r1"


def test_positive_does_not_migrate_to_new_mechanism(tmp_path):
    a, b = dossier(), dossier("MECANISMO_NUEVO")
    guardar_dossier(a, tmp_path)
    receipt = {
        "candidate_id": a["candidate_id"],
        "mechanism_version": a["mechanism_version"],
        "claim_id": a["claim_id"],
        "protocol_version": a["protocol_version"],
        "execution_id": "exec-a",
        "observed_result": "positivo",
        "result_scope": "EXPERIMENTAL_OBSERVATION",
    }
    registrar_resultado(
        a["dossier_id"], "positivo", execution_id="exec-a",
        protocol_version=a["protocol_version"], execution_receipt=receipt,
        execution_resolver=lambda execution_id: receipt if execution_id == "exec-a" else None,
        directory=tmp_path,
    )
    guardar_dossier(b, tmp_path)
    lessons = " ".join(lecciones_previas("atencion", tmp_path))
    assert "MECANISMO_ANTERIOR" in lessons
    assert "MECANISMO_NUEVO" not in lessons


@pytest.mark.parametrize("field", ["mecanismo", "problema", "prueba_discriminante"])
def test_conflicting_save_preserves_bytes(tmp_path, field):
    a = dossier()
    path = guardar_dossier(a, tmp_path)
    before = path.read_bytes()
    b = deepcopy(a)
    b[field] = "contexto modificado"
    with pytest.raises(ValueError):
        guardar_dossier(b, tmp_path)
    assert path.read_bytes() == before


def test_legacy_ambiguity_never_clears_and_other_history_survives(tmp_path):
    a, valid = dossier(), dossier("MECANISMO_VALIDO")
    a["dossier_id"], valid["dossier_id"] = "legacy-conflict", "legacy-valid"
    b = {**a, "mecanismo": "MECANISMO_NUEVO"}
    path = write_legacy(tmp_path, [a, observed(a), b, a, valid, observed(valid)])
    before = path.read_bytes()
    with pytest.warns(RuntimeWarning, match="ambigu"):
        lessons = lecciones_previas("atencion", tmp_path)
    assert len(lessons) == 1 and "MECANISMO_VALIDO" in lessons[0]
    assert path.read_bytes() == before


def test_legacy_reexport_only_timestamp_change_is_unambiguous(tmp_path):
    a = dossier()
    write_legacy(tmp_path, [a, observed(a), {**a, "creado_at": "otro instante"}])
    lessons = lecciones_previas("atencion", tmp_path)
    assert len(lessons) == 1 and "MECANISMO_ANTERIOR" in lessons[0]


def test_orphan_result_cannot_be_recorded(tmp_path):
    with pytest.raises(ValueError):
        registrar_resultado("no-existe", "positivo", directory=tmp_path)
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_legacy_conflict_blocks_resave_and_result(tmp_path):
    a = dossier()
    path = write_legacy(tmp_path, [a, {**a, "problema": "otro problema"}, a])
    before = path.read_bytes()
    with pytest.raises(ValueError):
        guardar_dossier(a, tmp_path)
    with pytest.raises(ValueError):
        registrar_resultado(a["dossier_id"], "positivo", directory=tmp_path)
    assert path.read_bytes() == before


def test_malformed_orphan_and_nonobject_rows_do_not_create_lessons(tmp_path):
    path = write_legacy(tmp_path, [None, [], 42, {"dossier_id": ""},
                                  observed({"dossier_id": "no-existe"})])
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{partial\n")
    assert lecciones_previas("", tmp_path) == []


def test_identical_save_is_idempotent(tmp_path):
    a = dossier()
    path = guardar_dossier(a, tmp_path)
    before = path.read_bytes()
    guardar_dossier({**a, "creado_at": "otra fecha"}, tmp_path)
    assert path.read_bytes() == before
