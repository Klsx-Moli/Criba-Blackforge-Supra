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
from unittest.mock import patch

from criba.integrations.supra_client import SupraProjectResult

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

    # Sustituir solo el cliente remoto: CRIBA genera el dossier y construye
    # su propio receipt. No depende de un SUPRA en el puerto del usuario.
    def planned_result(*, project_id, **_kwargs):
        return SupraProjectResult(
            project_id=project_id, status="blocked", completion_status="BLOCKED",
            stage="RESTRICTED_EXECUTION_VERIFIED", workflow_status="RESTRICTED_EXECUTION_VERIFIED",
            verification_status="FAIL", scientific_status="NOT_VALIDATED",
            criba_planning_receipt_status="PRESERVED_NOT_EXECUTED",
            criba_mechanism_execution_status="NOT_EXECUTED", posture={},
        )

    with patch("criba.integrations.SupraClient", autospec=True) as factory:
        client = factory.return_value
        client.run_project.side_effect = planned_result
        result = scientific_cycle(
            "Reducir el impacto de las baterías sin aumentar el coste "
            "ni comprometer el suministro."
        )
        assert result["error"] is None, result["error"]
        client.run_project.assert_called_once()
        client.get_project.assert_called_once_with(result["receipt"]["project_id"])
        client.close.assert_called_once_with()
    return result


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


def test_alias_de_estado_conserva_el_campo_legacy():
    """La proyección local conserva ambas claves; no es el receipt persistido."""
    resultado = _run()
    receipt = resultado.get("receipt")
    assert isinstance(receipt, dict), f"sin receipt: error={resultado.get('error')!r}"
    assert receipt["execution_status"] == receipt["criba_mechanism_execution_status"]


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