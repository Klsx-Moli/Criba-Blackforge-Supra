"""Verifica que la clasificación estructurada (error_kind) NO altera
`passed` ni `schema_response_rate` del banco.

Construye resultados sintéticos que reproducen los casos reales observados
(JSON válido con fallo de dominio, JSON válido con fallo de forma, JSON
inválido) y comprueba que la tasa de respuesta-de-esquema solo depende de si
hubo ERROR técnico, no del canal de diagnóstico añadido.
"""

from __future__ import annotations

from criba.interprete.banco import _clasificar_error
from criba.interprete.puerto import ESTADO_PENDIENTE, ESTADO_PROPUESTA, InterpretationResult


def _r(**kw) -> InterpretationResult:
    return InterpretationResult(**kw)


def test_domain_failure_is_rejected_not_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:mecanismo repite nombres de técnicas",
        error_kind="domain",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te is None
    assert de == "validacion:mecanismo repite nombres de técnicas"
    assert result == "REJECTED"


def test_schema_failure_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:sin hipotesis",
        error_kind="schema",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te is not None and te.startswith("schema_invalido:")
    assert de == "schema_validation_failed"
    assert result == "ERROR"


def test_json_invalido_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="json_invalido:JSONDecodeError",
        error_kind="",
        raw_output="not json",
    )
    te, de, result = _clasificar_error(r)
    assert te == "json_invalido:JSONDecodeError"
    assert de == "invalid_json"
    assert result == "ERROR"


def test_nested_json_invalido_in_critica_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="critica_no_disponible:json_invalido:ValueError",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te is not None and te.startswith("json_invalido:")
    assert de == "invalid_json"
    assert result == "ERROR"


def test_pass_has_no_error() -> None:
    from verification.interpreter_cases import critica as critica_sintetica

    r = _r(
        estado=ESTADO_PROPUESTA,
        mecanismo="un mecanismo suficientemente largo y especifico del dominio",
        critica={"evaluation_status": "CRITIQUED", "respuesta": critica_sintetica()},
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert (te, de, result) == (None, None, "PASS")
