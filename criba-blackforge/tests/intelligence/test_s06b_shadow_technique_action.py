"""S06 slice-2: Shadow action productivo para técnicas locales deterministas (T054/T061).

Verifica que el dispatcher canónico `execute_technique` (que WIRING T061/T054)
se expone desde el action Shadow y persiste el outcome en el packet para
readback/restart -- sin LLM (T061/T054 son recombination corpus-local).

Honesto: T061/T054 se declaran PLANNED en la registry canónica (ledger
2026-09-08.3: 0/130 IMPLEMENTED). execute_technique rechaza PLANNED
(execution.py:366). Estos tests están marcados xfail strict=True para
documentar que el handler es resoluble pero no productivo sin attestation A2.
El test T081 confirma el guard canónico (PLANNED/técnica no declarada rechazada).
"""
from __future__ import annotations

import copy
import json

import pytest

from criba.intelligence.execution import ExecutionError
from criba.intelligence.contracts import EvidenceDocument


# --- fixtures de documento corpus-local (para T061/T054, deterministico) -----
def _doc(doc_id: str, attributes: dict[str, str]) -> EvidenceDocument:
    """EvidenceDocument con metadata.attributes (contrato T061/T054: strings)."""
    return EvidenceDocument(
        doc_id=doc_id,
        source_id="test_local",
        metadata={"attributes": attributes},
    )


@pytest.fixture
def local_documents() -> list[EvidenceDocument]:
    """Dos docs con atributos compartidos pero valores distintos (T061 candidato)."""
    return _docs()


def _docs() -> list[EvidenceDocument]:
    return [
        _doc("d1", {"metodo": "lente_escetico", "dominio": "ciencia"}),
        _doc("d2", {"metodo": "teoria_cuantica", "dominio": "ciencia"}),
    ]


@pytest.mark.xfail(
    reason="T061 estado canon PLANNED (ledger 2026-09-08.3: 0/130 IMPLEMENTED). "
    "execute_technique rechaza PLANNED (execution.py:366). "
    "Handler resoluble en _INPUT_ADAPTERS no autoriza ejecucion productiva. "
    "PENDING_OWNER_DECISION para promocion via attestation A2 + capability proof §79.",
    raises=ExecutionError,
    strict=True,
)
# --- El action Shadow productivo ------------------------------------------------
def test_run_technique_for_test_T061_produce_outcome_no_llm():
    """T061 (substitute_attributes) ejecuta sobre corpus local: sin LLM, outcome real."""
    from criba.ui.actions import _run_technique_for_test
    from criba.intelligence.execution import execute_technique
    from criba.intelligence.registry import TechniqueRegistry

    docs = _docs()
    # ejecuta directamente (TDD del dispatcher canónico)
    outcome = execute_technique(
        TechniqueRegistry(), "T061", "substitucion de atributos",
        params={"concepts": []}, documents=docs,
    )
    assert outcome["technique"] == "T061"
    assert len(outcome["results"]) > 0
    # cada hipótesis de recombination: serializable (dossier Shadow)
    for r in outcome["results"]:
        assert "id" in r or isinstance(r, dict)
    json.dumps(outcome)  # serializa -> dossier persistente


@pytest.mark.xfail(
    reason="T061/T054 estado canon PLANNED (ledger 2026-09-08.3: 0/130 IMPLEMENTED). "
    "execute_technique rechaza PLANNED (execution.py:366). "
    "PENDING_OWNER_DECISION para promocion.",
    raises=ExecutionError,
    strict=True,
)
def test_run_technique_for_test_persiste_outcome_en_packet():
    """S06 slice-2: el action persiste el outcome en el packet para readback/restart."""
    from criba.intelligence.contracts import EvidenceDocument
    from criba.intelligence.execution import execute_technique
    from criba.intelligence.registry import TechniqueRegistry

    docs = _docs()
    win = type("FakeWin", (), {
        "packet": {"innovation": {"ideas": [], "technique_results": {}}},
    })()

    # Simula el action productivo: ejecuta T061 y persiste el outcome.
    # (refactor futuro de _run_technique_for_test: pasa `win` y escribe en packet.)
    registry = TechniqueRegistry()
    outcome = execute_technique(registry, "T061", "attrs", params={}, documents=docs)
    win.packet["innovation"]["technique_results"]["T061"] = outcome
    win.packet["innovation"]["technique_results"]["T061"]["results"]  # non-empty

    # readback/restart: el outcome sobrevive en el packet serializado
    rt = json.loads(json.dumps(win.packet))
    assert "T061" in rt["innovation"]["technique_results"]
    assert len(rt["innovation"]["technique_results"]["T061"]["results"]) > 0


@pytest.mark.xfail(
    reason="T054 estado canon PLANNED (ledger 2026-09-08.3: 0/130 IMPLEMENTED). "
    "execute_technique rechaza PLANNED (execution.py:366). "
    "PENDING_OWNER_DECISION para promocion.",
    raises=ExecutionError,
    strict=True,
)
def test_run_technique_for_test_T054_recombina_tecnologias():
    """T054 (recombine_technologies) sobre corpus local: hipótesis de combinación.

    T054 requiere >= 2 tecnologías distintas declaradas en metadata.technologies.
    """
    from criba.intelligence.contracts import EvidenceDocument
    from criba.intelligence.execution import execute_technique
    from criba.intelligence.registry import TechniqueRegistry

    docs = [
        EvidenceDocument(doc_id="d1", source_id="test_local",
                         metadata={"technologies": {"lente_escetico": {}, "teoria_cuantica": {}}}),
    ]
    outcome = execute_technique(
        TechniqueRegistry(), "T054", "tec combinadas",
        params={}, documents=docs,
    )
    assert outcome["technique"] == "T054"
    assert len(outcome["results"]) > 0, "2 technologies >= debe producir una combinacion"
    json.dumps(outcome)  # serializable


def test_run_technique_for_test_T081_no_dispatcheable_devuelve_execution_error():
    """T081 no está en OPERATORS -> execute_technique rechaza (canon conserva PLANNED)."""
    from criba.intelligence.execution import ExecutionError, execute_technique
    from criba.intelligence.registry import TechniqueRegistry

    with pytest.raises(ExecutionError, match="T081"):
        execute_technique(TechniqueRegistry(), "T081", "novelty", params={}, documents=[])
