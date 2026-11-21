"""M2 exports the displayed interpreted proposal, not an unrelated core axis.

Synthetic port responses exercise routing only; they are not model/science evidence.
"""
from types import SimpleNamespace

import pytest
from criba.ui.actions import _prepare_dossier_for_selected_idea, activate

from verification.interpreter_cases import resultado


def window():
    query = "Reducir retornos por registros incompletos"
    entries = [
        {**resultado().to_campos(), "candidate_id": f"interpreted-{i}",
         "estado_interpretacion": "PROPUESTA", "mecanismo": f"Mecanismo declarado {i}"}
        for i in range(2)
    ]
    return SimpleNamespace(
        problem=query, packet=activate(query),
        invent_sheet={"query": query, "entries": entries},
        candidates=SimpleNamespace(interpretation_index=1),
    )


def test_m2_exports_the_displayed_interpreted_proposal():
    win = window()
    entry = win.invent_sheet["entries"][1]
    dossier = _prepare_dossier_for_selected_idea(win)
    assert dossier["candidate_id"] == entry["candidate_id"]
    assert dossier["mecanismo"] == entry["mecanismo"]
    assert dossier["prueba_discriminante"]["observable"] == (
        entry["prueba"]["metrica"]
    )
    assessment = dossier["interpretacion"]["provenance"]["planning_assessment"]
    assert assessment["content_origin"] == "DECLARED_UNVERIFIED"
    assert assessment["relevance_status"] == "UNKNOWN"
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"


@pytest.mark.parametrize(
    "fault",
    ["objective", "pending", "negative_index", "empty_entries",
     "missing_metric", "missing_identity"],
)
def test_interpreted_route_rejects_unbound_or_incomplete_proposal(fault):
    win = window()
    entry = win.invent_sheet["entries"][1]
    if fault == "objective":
        win.problem = "Otro objetivo"
    elif fault == "pending":
        entry["estado_interpretacion"] = "PENDIENTE_INTERPRETACION"
    elif fault == "negative_index":
        win.candidates.interpretation_index = -1
    elif fault == "empty_entries":
        win.invent_sheet["entries"] = []
    elif fault == "missing_metric":
        del entry["prueba"]["metrica"]
    elif fault == "missing_identity":
        del entry["candidate_id"]
    with pytest.raises(ValueError):
        _prepare_dossier_for_selected_idea(win)
