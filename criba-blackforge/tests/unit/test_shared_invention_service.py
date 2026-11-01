"""Shared desktop service and existing lottery modes: no provider/network calls."""

from __future__ import annotations

from types import SimpleNamespace

from criba.inventar import invent
from criba.invention_service import run_invention


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
