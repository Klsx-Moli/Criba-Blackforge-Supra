"""Paso 7: una abstención correcta NO puede salir como ERROR en el banco.

`estados` (PROPUESTA/ABSTENER/ERROR) alimenta passed/schema_response_rate/
correct_abstention_rate. `result` (PASS/REJECTED/ERROR) es el desglose técnico
por intento. Una abstención correcta debe tener estado=ABSTENER (nunca ERROR),
aunque su result técnico sea REJECTED (no es propuesta).
"""

from __future__ import annotations

from criba.interprete.banco import _clasificar_error, evaluar_banco
from criba.interprete.puerto import ESTADO_PENDIENTE, ESTADO_PROPUESTA, InterpretationResult

from verification.interpreter_cases import critica as critica_sintetica


def _abstencion(motivo: str) -> InterpretationResult:
    return InterpretationResult(
        estado=ESTADO_PENDIENTE,
        pertinencia="ABSTENER",
        error="validacion:abstencion:" + motivo,
        raw_output='{"pertinencia": "ABSTENER"}',
    )


def test_abstencion_correcta_tiene_estado_abstener_no_error() -> None:
    """El banco clasifica el ESTADO de una abstención como ABSTENER."""
    caso = next(c for c in __import__("criba.interprete.banco", fromlist=["CASOS"]).CASOS
                if c["expected"] == "ABSTENER")

    # proponer siempre abstiene con motivo -> todos los intentos ABSTENER
    def proponer(*_args):
        return _abstencion("ajeno al dominio del cruce")

    report = evaluar_banco(proponer, repeticiones=2)
    caso_res = report["cases"][[c["id"] for c in report["cases"]].index(caso["id"])]
    assert caso_res["estados"] == ["ABSTENER", "ABSTENER"], caso_res["estados"]
    assert caso_res["correcto"] is True
    # El caso negativo abstiene => correct_abstention_rate lo cuenta bien.
    assert report["correct_abstention_rate"] == 1.0


def test_abstencion_no_es_error_tecnico() -> None:
    """Una abstención correcta no tiene error técnico (solo derivado)."""
    r = _abstencion("ajeno al dominio")
    te, de, result = _clasificar_error(r)
    assert te is None, "una abstención correcta no debe tener error técnico"
    assert de.startswith("validacion:abstencion:")
    # result técnico REJECTED (no es propuesta) pero NO ERROR:
    assert result == "REJECTED"


def test_abstencion_sin_motivo_es_error() -> None:
    """Abstener SIN motivo es un fallo de forma (schema), sí ERROR."""
    r = InterpretationResult(
        estado=ESTADO_PENDIENTE,
        pertinencia="ABSTENER",
        error="validacion:abstencion_sin_motivo",
        error_kind="schema",
        raw_output='{"pertinencia": "ABSTENER"}',
    )
    te, de, result = _clasificar_error(r)
    assert result == "ERROR"
    assert te.startswith("schema_invalido:")


def test_propuesta_valida_estado_propuesta() -> None:
    """Control: una propuesta válida mantiene estado PROPUESTA / result PASS."""
    r = InterpretationResult(
        estado=ESTADO_PROPUESTA,
        pertinencia="PERTINENTE",
        mecanismo="mecanismo suficientemente largo y específico del dominio",
        critica={"evaluation_status": "CRITIQUED", "respuesta": critica_sintetica()},
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert (te, de, result) == (None, None, "PASS")
