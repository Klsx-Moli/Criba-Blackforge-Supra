"""Real SQLite preservation of interpreted proposals, without model/network doubles."""

from __future__ import annotations

from criba.storage import Storage


def test_save_and_reopen_preserves_complete_invention_sheet(tmp_path):
    sheet = {
        "run_id": "invent-42-synthetic",
        "query": "Reducir el desperdicio de agua en una ducha doméstica",
        "seed": 42,
        "mode": "stratified",
        "entries": [
            {
                "id": "idea-42",
                "title": "Circuito previo de recuperación",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "Recuperar el agua fría inicial en un depósito reutilizable.",
                "mecanismo": (
                    "Una válvula deriva el flujo antes de alcanzar la temperatura deseada."
                ),
                "cross_operational_records": [
                    {
                        "id": "A3-OP-GEN-01",
                        "operator_record": {
                            "counterexample": (
                                "El depósito no puede contaminar la red de agua potable."
                            ),
                            "execution_status": "NOT_EXECUTED",
                        },
                    }
                ],
                "interpretacion_provenance": {"model_requested": "fixture-no-model"},
            }
        ],
        "totals": {
            "ideas": 1,
            "pending_interpretation": 0,
            "unresolved": 1,
            "partial_prior_art": 0,
            "survived_search": 0,
        },
    }
    database = tmp_path / "inventions.sqlite3"
    ident = Storage(database).save_invention(sheet, selected_index=0)
    recovered = Storage(database).get(ident)
    assert recovered["packet"]["kind"] == "invention_sheet"
    assert recovered["packet"]["sheet"] == sheet
    assert recovered["packet"]["selected_index"] == 0
    assert recovered["status"] == "PROPUESTA"
    assert recovered["query"] == sheet["query"]
    assert Storage(database).list_sessions()[0]["id"] == ident
