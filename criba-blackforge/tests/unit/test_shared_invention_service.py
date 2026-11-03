"""Shared desktop service and existing lottery modes: no provider/network calls."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from criba.blackforge_catalog import records as bf_records
from criba.catalog import methods as catalog_methods
from criba.inventar import invent
from criba.invention_service import run_invention
from criba.lottery import VALID_LOTTERY_MODES


def _combined_blackforge_and_operator_records() -> list[dict]:
    """Catálogo real combinado que usa la ventana BLACKFORGE al ejecutar."""
    records = [dict(record) for record in bf_records()]
    records.extend(
        dict(record)
        for record in catalog_methods()
        if "operator_record" in record
    )
    return records


def _offline_proposer(
    query: str,
    idea: dict,
    domain: dict | None,
    evidence: list[dict] | None = None,
) -> dict:
    return {
        "estado": "PROPUESTA",
        "hipotesis": "hipótesis de prueba",
        "mecanismo": "mecanismo de prueba",
        "aportacion_por_tecnica": [],
        "supuestos": [],
        "prueba_concreta": "medir el efecto frente al caso base",
        "critica": {},
    }


@pytest.mark.parametrize("mode", sorted(VALID_LOTTERY_MODES))
def test_shared_engine_honors_every_lottery_mode_with_blackforge_records(mode: str) -> None:
    sheet = invent(
        "reducir el consumo de agua en el riego agricola",
        methods=_combined_blackforge_and_operator_records(),
        seed=42,
        rounds=1,
        batch_size=8,
        top=1,
        offline=True,
        history_storage=False,
        proponer=_offline_proposer,
        mode=mode,
    )
    assert sheet["mode"] == mode
    assert len(sheet["entries"]) == 1
    entry = sheet["entries"][0]
    assert entry["estado_interpretacion"] == "PROPUESTA"
    assert entry["mecanismo"] == "mecanismo de prueba"
    assert entry["method_ids"]
    assert entry["cross_operational_records"]
    assert entry["prior_art"]["verdict"] == "UNRESOLVED"


def test_stratified_shared_run_uses_the_combined_blackforge_catalog() -> None:
    """BLACKFORGE participa en el sorteo estratificado mixto (ver lottery)."""
    records = _combined_blackforge_and_operator_records()
    engine_ids = {str(record["blackforge_id"]) for record in records[:723]}
    operator_ids = {
        str(record.get("id")) for record in records[723:]
    }
    assert len(records) == 750
    assert len(engine_ids) == 723
    assert operator_ids

    sheet = invent(
        "reducir el consumo de agua en el riego agricola",
        methods=records,
        seed=42,
        rounds=1,
        batch_size=12,
        top=1,
        offline=True,
        history_storage=False,
        proponer=_offline_proposer,
        mode="stratified",
    )
    assert sheet["mode"] == "stratified"
    entry = sheet["entries"][0]
    assert entry["estado_interpretacion"] == "PROPUESTA"
    assert entry["method_ids"]
    assert entry["cross_operational_records"]


@pytest.mark.parametrize("mode", sorted(VALID_LOTTERY_MODES))
def test_shared_service_forwards_every_lottery_mode(mode: str, monkeypatch) -> None:
    captured: dict = {}

    def fake_invent(problem, **kwargs):
        captured.update(kwargs)
        return {"entries": [], "selection_audit": {}}

    monkeypatch.setattr("criba.inventar.invent", fake_invent)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _sheet: "ledger.jsonl")
    monkeypatch.setattr(
        "criba.interprete.seleccion.construir_interprete",
        lambda *_args, **_kwargs: SimpleNamespace(model="fixture"),
    )
    monkeypatch.setattr(
        "criba.interprete.seleccion.estado_interprete",
        lambda _interpreter: {"backend": "fixture"},
    )
    sheet = run_invention(
        "problema sintetico", backend="openai_compatible",
        mode=mode, seed=7, history_storage=False,
    )
    assert captured.get("mode", "stratified") == mode
    assert captured["seed"] == 7
    assert captured["history_storage"] is False
    assert sheet["interpreter"] == {"backend": "fixture"}


def test_existing_lottery_mode_is_honored_by_shared_invention_flow():
    records = [
        {
            "id": "mode-a",
            "title": "Separar el suministro",
            "description": "Separar el suministro temporal.",
            "family": "restricciones",
            "thinking_class": "ruptura",
        },
        {
            "id": "mode-b",
            "title": "Reutilizar el flujo",
            "description": "Reutilizar un flujo sobrante.",
            "family": "recombinacion",
            "thinking_class": "generacion",
        },
    ]
    sheet = invent(
        "Problema sintético",
        methods=records,
        seed=42,
        rounds=1,
        batch_size=2,
        top=1,
        offline=True,
        history_storage=False,
        mode="pure",
    )
    assert sheet["mode"] == "pure"
    assert len(sheet["entries"]) == 1
    assert sheet["entries"][0]["estado_interpretacion"] == "PENDIENTE_INTERPRETACION"


def test_shared_service_forwards_mode_and_seed(monkeypatch):
    captured = {}

    def fake_invent(problem, **kwargs):
        captured.update(kwargs)
        return {"entries": [], "selection_audit": {}}

    monkeypatch.setattr("criba.inventar.invent", fake_invent)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _sheet: "ledger.jsonl")
    monkeypatch.setattr(
        "criba.interprete.seleccion.construir_interprete",
        lambda *_args, **_kwargs: SimpleNamespace(model="fixture"),
    )
    monkeypatch.setattr(
        "criba.interprete.seleccion.estado_interprete",
        lambda _interpreter: {"backend": "fixture"},
    )
    sheet = run_invention(
        "problema sintetico", backend="openai_compatible",
        mode="alternating", seed=7, history_storage=False,
    )
    assert captured["mode"] == "alternating"
    assert captured["seed"] == 7
    assert captured["history_storage"] is False
    assert sheet["interpreter"] == {"backend": "fixture"}
