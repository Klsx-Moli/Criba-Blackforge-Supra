"""Tests del puente ledger K3 -> pilot_gate (punto 3 del encargo).

Sin proveedor y sin red. Se comprueba que el adaptador:
  - produce EXACTAMENTE las 5 claves que exige el gate;
  - nunca inventa un veredicto: sin recibo cerrado -> NOT_RUN o ERROR;
  - cuenta llamadas fisicas por recibo, no por veredicto;
  - respeta el caso exigido: el intento tardio (STALE) no se cuenta como
    exito del intento vigente.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from benchmarks.innovation.semantic_ledger_gate import (
    CAMPOS,
    normalizar_lote,
    normalizar_slot,
    validar_registros,
)

REVIEW = "judge-local"
SHA1 = "1" * 64
SHA2 = "2" * 64

# Ruta al gate real, para comparar el contrato sin duplicarlo a mano.
GATE_DIR = Path(r"C:/ASTRA_WORK/cbs-g0-review/docs/research/semantic-correspondence/g0-draft")


def _reserva(status="ACTIVE", request=SHA1, receipt=None):
    return {
        "attempt": "intento-1",
        "request_sha256": request,
        "reviewer": REVIEW,
        "status": status,
        "created_at": "2026-11-22T00:00:00+00:00",
        "closed_at": None,
        "receipt_sha256": receipt,
    }


def _recibo(request=SHA1, cuerpo=None, status="CLOSED"):
    return {
        "request_sha256": request,
        "body_sha256": "b" * 64,
        "status": status,
        "received_at": "2026-11-22T00:00:01+00:00",
        "body": cuerpo,
    }


def test_sin_reserva_es_not_run() -> None:
    r = normalizar_slot(case_id="C:1", repetition=0, arm="S1", estado_reserva=None)
    assert r == {"case_id": "C:1", "repetition": 0, "arm": "S1",
                 "outcome": "NOT_RUN", "physical_calls": 0}


def test_reserva_activa_sin_recibo_es_not_run() -> None:
    r = normalizar_slot(case_id="C:1", repetition=0, arm="S1",
                        estado_reserva=_reserva())
    assert r["outcome"] == "NOT_RUN"
    assert r["physical_calls"] == 0


def test_recibo_support_con_un_llamada() -> None:
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA1, receipt=SHA1),
        recibos=[_recibo(request=SHA1, cuerpo={"veredicto": "SUPPORT"})],
    )
    assert r["outcome"] == "SUPPORT"
    assert r["physical_calls"] == 1


def test_recibo_reject_con_un_llamada() -> None:
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA1, receipt=SHA1),
        recibos=[_recibo(request=SHA1, cuerpo={"veredicto": "REJECT"})],
    )
    assert r["outcome"] == "REJECT"
    assert r["physical_calls"] == 1


def test_cerrada_sin_cuerpo_es_error_no_inventa() -> None:
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA1, receipt=SHA1),
        recibos=[_recibo(request=SHA1, cuerpo=None)],
    )
    assert r["outcome"] == "ERROR"
    assert r["physical_calls"] == 1


def test_cuerpo_con_veredicto_invalido_es_error() -> None:
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA1, receipt=SHA1),
        recibos=[_recibo(request=SHA1, cuerpo={"veredicto": "PERTINENTE"})],
    )
    assert r["outcome"] == "ERROR"


def test_intento_tardio_stale_no_cuenta_como_exito_del_vigente() -> None:
    """El caso del handoff: la tardia es STALE, no SUPPORT del intento 2."""
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA2, receipt=SHA2),
        recibos=[
            _recibo(request=SHA1, cuerpo={"veredicto": "SUPPORT"}, status="STALE"),
            _recibo(request=SHA2, cuerpo={"veredicto": "REJECT"}, status="CLOSED"),
        ],
    )
    # El vigente es el del intento 2 (REJECT); la tardia no se cuenta.
    assert r["outcome"] == "REJECT"
    assert r["physical_calls"] == 1


def test_physical_calls_es_uno_por_intento_no_por_veredicto() -> None:
    """Dos recibos (tardio + vigente) siguen siendo 1 llamada productiva."""
    r = normalizar_slot(
        case_id="C:1", repetition=0, arm="S1",
        estado_reserva=_reserva(status="CLOSED", request=SHA2, receipt=SHA2),
        recibos=[
            _recibo(request=SHA1, cuerpo={"veredicto": "SUPPORT"}, status="STALE"),
            _recibo(request=SHA2, cuerpo={"veredicto": "REJECT"}, status="CLOSED"),
        ],
    )
    assert r["physical_calls"] == 1


def test_lote_completo_y_validacion_de_contrato() -> None:
    slots = [("A", 0, "S0"), ("A", 0, "S1"), ("B", 0, "S1")]
    estado = {
        ("A", 0, "S0"): None,
        ("A", 0, "S1"): _reserva(status="CLOSED", request=SHA1, receipt=SHA1),
        ("B", 0, "S1"): _reserva(),
    }
    recibos = {
        ("A", 0, "S1"): [_recibo(request=SHA1, cuerpo={"veredicto": "SUPPORT"})],
    }
    registros = normalizar_lote(slots, estado, recibos)
    assert [r["outcome"] for r in registros] == ["NOT_RUN", "SUPPORT", "NOT_RUN"]
    assert validar_registros(registros) == []


def test_validar_registros_detecta_contratos_rotos() -> None:
    malos = [
        {"case_id": "A", "repetition": 0, "arm": "S1", "outcome": "SUPPORT",
         "physical_calls": 0},  # etiqueta sin llamada
        {"case_id": "B", "repetition": 0, "arm": "S1", "outcome": "NOT_RUN",
         "physical_calls": 1},  # NOT_RUN con llamada
        {"case_id": "C", "repetition": 0, "arm": "S1", "outcome": "INVENTADO",
         "physical_calls": 1},
    ]
    errores = validar_registros(malos)
    assert len(errores) == 3, errores


def test_claves_exactas_del_gate() -> None:
    """Las 5 claves coinciden con lo que exige pilot_gate.summarize."""
    assert set(CAMPOS) == {"case_id", "repetition", "arm", "outcome", "physical_calls"}


@pytest.mark.skipif(not (GATE_DIR / "pilot_gate.py").exists(),
                    reason="gate de referencia no disponible")
def test_acepta_salida_del_gate_real() -> None:
    """El gate real debe aceptar nuestros registros sin excepcion.

    Se invoca ``summarize`` del gate en un subproceso con un plan A
    sintetico que cumple los slots; si el contrato no coincidiera, el gate
    lanzaria ValueError.
    """
    # Plan A completo: 16 slots. Relleno NOT_RUN para probar el contrato.
    sys.path.insert(0, str(GATE_DIR))
    import pilot_gate as gate
    slots = [(s["case_id"], s["repetition"], s["arm"]) for s in gate.schedule("A")]
    registros = [
        {"case_id": c, "repetition": r, "arm": a,
         "outcome": "NOT_RUN", "physical_calls": 0}
        for c, r, a in slots
    ]
    # summarize exige el manifiesto y los slots exactos: debe aceptar el lote.
    resumen = gate.summarize("A", registros)
    assert resumen["physical_calls_reported"] == 0
    assert resumen["expected_slots"] == 16
    assert resumen["reference_status"] == "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD"
    assert resumen["provenance_status"] == "NOT_VALIDATED_BY_THIS_TOOL"
    assert resumen["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
    assert resumen["p0_status"] == "OPEN"


def test_gate_rechaza_slot_desconocido() -> None:
    """Un slot que no esta en el plan A debe ser rechazado por el gate."""
    sys.path.insert(0, str(GATE_DIR))
    try:
        import pilot_gate as gate
        slots = [(s["case_id"], s["repetition"], s["arm"]) for s in gate.schedule("A")]
        registros = [
            {"case_id": c, "repetition": r, "arm": a,
             "outcome": "NOT_RUN", "physical_calls": 0}
            for c, r, a in slots
        ]
        # Cuelo un slot que no existe en el plan.
        registros.append({"case_id": "NO-EXISTE:aligned", "repetition": 99,
                          "arm": "S1", "outcome": "NOT_RUN", "physical_calls": 0})
        with pytest.raises(ValueError):
            gate.summarize("A", registros)
    finally:
        sys.path.remove(str(GATE_DIR))