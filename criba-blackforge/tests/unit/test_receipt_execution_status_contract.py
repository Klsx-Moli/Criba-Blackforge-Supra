"""Contrato del receipt de scientific_cycle frente al receipt real de SUPRA.

Defecto reproducido: criba.engine.scientific_cycle construye un receipt local
cuyo campo de estado se llama ``criba_mechanism_execution_status``, mientras
que el receipt que SUPRA persiste (supra_agentic.service) usa
``execution_status``. El consumidor ``criba.dossier_workflow`` lee
``execution_status`` y el test de integración
``test_09_scientific_cycle_estados_honestos`` hace
``receipt["execution_status"]`` -> KeyError.

Criterio de aceptación: el receipt devuelto por scientific_cycle debe llevar
``execution_status`` (y conservar el resto de campos), de modo que el
consumidor no muera con KeyError cuando SUPRA sí está disponible.

Se ejecuta sin SUPRA: se falsifica el cliente, porque lo que se verifica es la
forma del receipt que CRIBA construye, no la disponibilidad del servicio.
"""
from __future__ import annotations

import sys

CLAVES_REQUERIDAS = (
    "project_id",
    "dossier_id",
    "candidate_id",
    "mechanism_version",
    "protocol_version",
    "execution_status",
    "scientific_status",
)


def _run():
    from criba.engine import scientific_cycle

    return scientific_cycle(
        "Reducir el impacto de las baterías sin aumentar el coste "
        "ni comprometer el suministro."
    )


def test_receipt_expone_execution_status():
    resultado = _run()
    receipt = resultado.get("receipt")
    assert isinstance(receipt, dict), f"sin receipt: error={resultado.get('error')!r}"
    assert "execution_status" in receipt, (
        "el receipt no expone 'execution_status'; claves="
        f"{sorted(receipt)}"
    )


def test_receipt_satisface_el_contrato_del_consumidor():
    resultado = _run()
    receipt = resultado.get("receipt")
    assert isinstance(receipt, dict), f"sin receipt: error={resultado.get('error')!r}"
    faltan = [c for c in CLAVES_REQUERIDAS if c not in receipt]
    assert not faltan, f"faltan claves en el receipt: {faltan}"


def test_execution_status_es_no_ejecutado():
    """El ciclo es de planificación: nunca puede afirmar ejecución."""
    resultado = _run()
    receipt = resultado.get("receipt")
    assert isinstance(receipt, dict), f"sin receipt: error={resultado.get('error')!r}"
    assert receipt["execution_status"] == "NOT_EXECUTED"


def test_dossier_workflow_acepta_el_receipt_local():
    """bind_local/import usan receipt['execution_status']; con el receipt de
    scientific_cycle no debe fallar por clave ausente."""
    from criba.dossier_workflow import WorkflowError

    resultado = _run()
    receipt = resultado.get("receipt")
    assert isinstance(receipt, dict), f"sin receipt: error={resultado.get('error')!r}"
    try:
        receipt["execution_status"]
    except KeyError as exc:  # pragma: no cover - es el fallo que se corrige
        raise AssertionError(f"el consumidor leería KeyError: {exc}") from exc
    assert issubclass(WorkflowError, Exception)


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if not nombre.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS {nombre}")
        except Exception as exc:
            fallos += 1
            print(f"  FAIL {nombre}: {type(exc).__name__}: {exc}")
    print(f"\nRESULTADO: {fallos} fallos")
    sys.exit(1 if fallos else 0)