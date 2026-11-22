"""F10 integration contracts; execute in a complete CRIBA checkout.

All fixtures are synthetic. No model, network or SUPRA call occurs.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from criba.invention_acceptance import exigir_entrada_interpretada
from criba.storage import Storage
from criba.supra_dossier import preparar_dossier

PROOF = {
    "metrica": "litros desviados",
    "baseline": "sin recuperación",
    "umbral": "10 litros",
    "condicion_fracaso": "sin desvío",
    "alternativa_explicativa": "fluctuación de caudal",
    "resultado_favorable_mecanismo": "desvío medido",
    "resultado_favorable_alternativa": "sin variación",
}


def entry():
    return {
        "candidate_id": "synthetic-c10",
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "Recuperar agua inicial",
        "mecanismo": "La válvula deriva agua a un circuito separado.",
        "prueba_concreta": "medir litros separados",
        "interpretacion_error": "",
        "prueba": deepcopy(PROOF),
    }


def test_archive_minimal_proposal_stays_readable_without_invented_protocol(tmp_path):
    store = Storage(tmp_path / "archive.sqlite3")
    minimal = {"estado_interpretacion": "PROPUESTA",
               "hipotesis": "h", "mecanismo": "m"}
    sheet = {"query": "problema", "entries": [minimal], "run_id": "synthetic"}
    ident = store.save_invention(sheet)
    recovered = Storage(tmp_path / "archive.sqlite3").get(ident)
    assert recovered["packet"]["sheet"] == sheet
    assert recovered["status"] == "PROPUESTA"
    with pytest.raises(ValueError):
        exigir_entrada_interpretada(minimal, para_supra=True)


@pytest.mark.parametrize("field,value", [
    ("estado_interpretacion", "PENDIENTE_INTERPRETACION"),
    ("hipotesis", ""),
    ("mecanismo", ""),
    ("interpretacion_error", "timeout"),
    ("interprete_result", {"estado": "PENDIENTE_INTERPRETACION", "error": ""}),
])
def test_archive_does_not_label_corrupt_entry_a_proposal(tmp_path, field, value):
    store = Storage(tmp_path / "archive.sqlite3")
    corrupt = entry()
    corrupt[field] = value
    with pytest.raises(ValueError):
        store.save_invention({"query": "problema", "entries": [corrupt]})
    assert store.list_sessions() == []


def test_preparar_dossier_refuses_invalid_declared_state_without_file_write():
    bad = entry()
    bad["estado_interpretacion"] = "PENDIENTE_INTERPRETACION"
    with pytest.raises(ValueError):
        preparar_dossier(bad, "recuperar agua")
    bad = entry()
    bad["prueba"].pop("baseline")
    with pytest.raises(ValueError, match="prueba_sin:baseline"):
        preparar_dossier(bad, "recuperar agua")


def test_preparar_dossier_keeps_unexecuted_semantics_for_valid_declared_entry():
    dossier = preparar_dossier(entry(), "recuperar agua")
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
    assert dossier["candidate_id"] == "synthetic-c10"


def test_core_legacy_assembly_remains_a_proposed_protocol():
    core = entry()
    core.pop("estado_interpretacion")
    dossier = preparar_dossier(core, "recuperar agua")
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert dossier["prueba_discriminante"]["estado_prueba"] == "NO_EJECUTADA"
