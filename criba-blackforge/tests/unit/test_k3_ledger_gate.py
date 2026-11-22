"""Tests del puente ledger K3 -> pilot_gate (punto 3 del encargo).

Sin proveedor y sin red. Se comprueba que el adaptador:
  - produce EXACTAMENTE las 5 claves que exige el gate;
  - nunca inventa un veredicto: sin recibo cerrado -> NOT_RUN o ERROR;
  - cuenta llamadas fisicas por recibo, no por veredicto;
  - respeta el caso exigido: el intento tardio (STALE) no se cuenta como
    exito del intento vigente.
"""

from __future__ import annotations

import runpy
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
GATE_DIR = Path(__file__).resolve().parents[3] / "docs/research/semantic-correspondence/g0-draft"


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


@pytest.fixture
def gate():
    """Load the vendored gate without global import-path or module-cache changes."""
    return runpy.run_path(str(GATE_DIR / "pilot_gate.py"))


@pytest.mark.parametrize("phase,expected", [("A", 16), ("B", 36), ("C", 108)])
def test_acepta_salida_del_gate_real(gate, phase, expected) -> None:
    """Feed actual normalizer output to the gate from a fresh checkout."""
    slots = [(s["case_id"], s["repetition"], s["arm"]) for s in gate["schedule"](phase)]
    registros = normalizar_lote(slots, {})
    assert len(registros) == expected
    assert validar_registros(registros) == []
    assert all(r["outcome"] == "NOT_RUN" and r["physical_calls"] == 0 for r in registros)
    resumen = gate["summarize"](phase, registros)
    assert resumen["status"] == "INCOMPLETE"
    assert resumen["physical_calls_reported"] == 0
    assert resumen["expected_slots"] == expected
    assert resumen["reference_status"] == "PROVISIONAL_AUTHOR_REVIEW_NOT_GOLD"
    assert resumen["provenance_status"] == "NOT_VALIDATED_BY_THIS_TOOL"
    assert resumen["authorization"] == "NOT_GRANTED_BY_THIS_TOOL"
    assert resumen["p0_status"] == "OPEN"


def test_gate_rechaza_slot_desconocido(gate) -> None:
    """An unknown slot emitted by the normalizer must fail the gate."""
    slots = [(s["case_id"], s["repetition"], s["arm"]) for s in gate["schedule"]("A")]
    slots.append(("NO-EXISTE:aligned", 99, "S1"))
    with pytest.raises(ValueError, match="unexpected or duplicate slot"):
        gate["summarize"]("A", normalizar_lote(slots, {}))


def test_gate_recibe_lexico_normalizado_sin_promocion_cientifica(gate) -> None:
    """Synthetic receipt exercises the adapter, not a real model or physical call."""
    slots = [(s["case_id"], s["repetition"], s["arm"]) for s in gate["schedule"]("A")]
    slot = slots[0]
    registros = normalizar_lote(
        slots,
        {slot: _reserva(status="CLOSED", request=SHA1, receipt="b" * 64)},
        {slot: [_recibo(request=SHA1, cuerpo={"veredicto": "REJECT"})]},
    )
    assert registros[0]["outcome"] == "REJECT"
    resumen = gate["summarize"]("A", registros)
    assert resumen["physical_calls_reported"] == 1
    assert resumen["status"] == "INCOMPLETE"
    assert resumen["provenance_status"] == "NOT_VALIDATED_BY_THIS_TOOL"
    assert resumen["p0_status"] == "OPEN"
