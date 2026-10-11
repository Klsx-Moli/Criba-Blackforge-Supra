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
    assert te is not None and te.startswith("critica_no_disponible:")
    assert de == "transport_failure"
    assert result == "ERROR"


def test_abstencion_con_motivo_es_abstener() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:abstencion:Problema sin solución conocida",
        error_kind="domain",
        raw_output='{"pertinencia": "ABSTENER"}',
    )
    te, de, result = _clasificar_error(r)
    assert te is None
    assert de == "validacion:abstencion:Problema sin solución conocida"
    assert result == "REJECTED"


def test_critica_pertinente_schema_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:critica.pertinente",
        error_kind="schema",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te == "schema_invalido:critica.pertinente"
    assert de == "schema_validation_failed"
    assert result == "ERROR"


def test_prueba_sin_umbral_schema_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:prueba.sin_umbral",
        error_kind="schema",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te == "schema_invalido:prueba.sin_umbral"
    assert de == "schema_validation_failed"
    assert result == "ERROR"


def test_abstencion_sin_motivo_schema_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="validacion:abstencion_sin_motivo",
        error_kind="schema",
        raw_output='{"pertinencia": "ABSTENER"}',
    )
    te, de, result = _clasificar_error(r)
    assert te == "schema_invalido:abstencion_sin_motivo"
    assert de == "schema_validation_failed"
    assert result == "ERROR"


def test_critica_no_disponible_timeout_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="critica_no_disponible:timeout",
        raw_output='{"pertinencia": "PERTINENTE"}',
    )
    te, de, result = _clasificar_error(r)
    assert te == "critica_no_disponible:timeout"
    assert de == "transport_failure"
    assert result == "ERROR"


def test_entrada_invalida_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="entrada_invalida:ValueError",
        raw_output="",
    )
    te, de, result = _clasificar_error(r)
    assert te == "entrada_invalida:ValueError"
    assert de == "transport_failure"
    assert result == "ERROR"


def test_proposal_failed_is_error() -> None:
    r = _r(
        estado=ESTADO_PENDIENTE,
        error="proposal_failed:RuntimeError",
        raw_output="",
    )
    te, de, result = _clasificar_error(r)
    assert te == "proposal_failed:RuntimeError"
    assert de == "transport_failure"
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
