"""F10: a mislabeled proposal never starts dossier IO or a SUPRA worker."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from criba.ui import actions
from criba import supra_dossier


def candidate():
    return {
        "candidate_id": "synthetic",
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "Recuperar agua",
        "mecanismo": "Desviar agua hacia un depósito",
        "prueba_concreta": "medir litros",
        "interpretacion_error": "",
        "prueba": {
            "metrica": "litros",
            "baseline": "sin desvío",
            "umbral": "10 litros",
            "condicion_fracaso": "sin reducción",
            "alternativa_explicativa": "caudal cambiante",
            "resultado_favorable_mecanismo": "se desvían litros",
            "resultado_favorable_alternativa": "no cambia el total",
        },
    }


@pytest.mark.parametrize("mutation", [
    "empty_mechanism", "empty_hypothesis", "missing_protocol",
    "missing_metric", "declared_timeout", "unknown", "rejected_critic",
    "duplicate_identity",
])
def test_bad_batch_rejected_before_any_dossier_io_or_worker(monkeypatch, mutation):
    bad = deepcopy(candidate())
    if mutation == "empty_mechanism":
        bad["mecanismo"] = ""
    elif mutation == "empty_hypothesis":
        bad["hipotesis"] = ""
    elif mutation == "missing_protocol":
        bad.pop("prueba")
    elif mutation == "missing_metric":
        bad["prueba"].pop("metrica")
    elif mutation == "declared_timeout":
        bad["interpretacion_error"] = "timeout"
    elif mutation == "unknown":
        bad["estado_interpretacion"] = "UNKNOWN"
    elif mutation == "rejected_critic":
        bad["critica"] = {"evaluation_status": "REJECTED"}
    elif mutation == "duplicate_identity":
        pass
    entries = [candidate(), bad]
    if mutation != "duplicate_identity":
        # An invalid later entry must block the batch before saving the first.
        bad["candidate_id"] = "other"
    calls = []
    monkeypatch.setattr(
        supra_dossier, "guardar_dossier",
        lambda *args, **kwargs: calls.append("WRITE") or None,
    )
    monkeypatch.setattr(
        actions, "_start_worker",
        lambda *args, **kwargs: calls.append("START"),
    )
    monkeypatch.setattr(
        actions, "show_error",
        lambda *args, **kwargs: calls.append("ERROR"),
    )
    win = SimpleNamespace(invent_sheet={"query": "recuperar agua", "entries": entries})
    actions.on_desarrollar_supra(win)
    assert calls == ["ERROR"]
    assert "dossiers" not in win.invent_sheet

def test_second_dossier_preparation_failure_writes_nothing(monkeypatch):
    first = candidate()
    second = deepcopy(candidate())
    second["candidate_id"] = "second"
    calls = []
    def prepare(entry, *args, **kwargs):
        calls.append(("PREPARE", entry["candidate_id"]))
        if entry["candidate_id"] == "second":
            raise ValueError("synthetic assembly failure")
        return {"dossier_id": "first"}
    monkeypatch.setattr(supra_dossier, "preparar_dossier", prepare)
    monkeypatch.setattr(
        supra_dossier, "guardar_dossier",
        lambda *args, **kwargs: calls.append(("WRITE",)) or None,
    )
    monkeypatch.setattr(
        actions, "_start_worker",
        lambda *args, **kwargs: calls.append(("START",)),
    )
    monkeypatch.setattr(
        actions, "show_error",
        lambda *args, **kwargs: calls.append(("ERROR",)),
    )
    win = SimpleNamespace(invent_sheet={"query": "problem", "entries": [first, second]})
    actions.on_desarrollar_supra(win)
    assert calls == [("PREPARE", "synthetic"), ("PREPARE", "second"), ("ERROR",)]
    assert "dossiers" not in win.invent_sheet
