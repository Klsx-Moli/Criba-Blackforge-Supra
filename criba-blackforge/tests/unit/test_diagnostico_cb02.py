"""Tests del diagnóstico estructurado (CB-02).

Cada caso del megaprompt produce un código, una fase, un motivo, un
``retryable`` y una siguiente acción. Sin secretos en la salida.

Invariantes que se comprueban explícitamente:

- ``ABSTENER`` correcto no es ``ERROR``.
- ``REJECTED`` (dominio) no implica avería del proveedor.
- Un 503 no es "modelo suspendido": es HTTP_ERROR con http_status=503.
- Banco aprobado no implica servicio disponible.
- No hay fallback silencioso: cada código mapea a una acción.
"""
from __future__ import annotations

import pytest
from criba.interprete.diagnostico import (
    AUTH_REJECTED,
    BANK_CANCELLED,
    BANK_MODE_MISMATCH,
    BANK_NOT_PASSED,
    CANCELLED,
    CORRECT_ABSTENTION,
    CRITIQUE_INVALID,
    CRITIQUE_UNAVAILABLE,
    DOMAIN_CONTRACT_FAILED,
    DOMAIN_REJECTION,
    HTTP_ERROR,
    INVALID_CONFIGURATION,
    INVALID_JSON,
    RATE_LIMITED,
    SCHEMA_VALIDATION_FAILED,
    TIMEOUT,
    TRANSPORT_UNAVAILABLE,
    TRUNCATED_RESPONSE,
    classify,
)


class _Prov:
    """Procedencia mínima sin_secretos()."""

    def __init__(self, **kw: object) -> None:
        self._d = {
            "model_requested": "criba-local",
            "model_reported": "",
            "request_id": "abc123",
            "raw_output_sha256": "deadbeef",
            "generation_parameters": {"constrained_decoding": "json_schema"},
            "endpoint": "http://127.0.0.1:8080/v1",
        }
        self._d.update(kw)

    def sin_secretos(self) -> dict[str, object]:
        return self._d


class _Result:
    """Resultado mínimo del puerto para alimentar classify()."""

    def __init__(self, **kw: object) -> None:
        self.estado = ""
        self.error = ""
        self.error_kind = ""
        self.provenance = None
        self.finish_reason = ""
        self.completion_tokens = None
        self.reasoning_tokens = None
        for k, v in kw.items():
            setattr(self, k, v)


# --------------------------------------------------------------------------
# Fixtures: un caso por código canónico del megaprompt.
# --------------------------------------------------------------------------


@pytest.fixture
def transporte_caido() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="transporte_http:ConnectError",
        provenance=_Prov(),
    )


@pytest.fixture
def http_503() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="http_error_503",
        provenance=_Prov(),
    )


@pytest.fixture
def auth_401() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="credenciales rechazadas: HTTP 401",
        provenance=_Prov(),
    )


@pytest.fixture
def rate_429() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="plan_agotado_429",
        provenance=_Prov(),
    )


@pytest.fixture
def timeout() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="timeout",
        provenance=_Prov(),
    )


@pytest.fixture
def config_invalida() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="configuracion_invalida:max_tokens",
        provenance=_Prov(),
    )


@pytest.fixture
def json_invalido() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="json_invalido:JSONDecodeError",
        provenance=_Prov(),
    )


@pytest.fixture
def schema_invalido() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="validacion:sin hipotesis",
        error_kind="schema",
        provenance=_Prov(),
    )


@pytest.fixture
def dominio_invalido() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="validacion:mecanismo repite nombres de técnicas",
        error_kind="domain",
        provenance=_Prov(),
    )


@pytest.fixture
def truncado() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="salida_truncada:finish_reason=length tokens=8192",
        provenance=_Prov(),
    )


@pytest.fixture
def critica_json_invalido() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="critica_no_disponible:json_invalido:ValueError",
        provenance=_Prov(),
    )


@pytest.fixture
def critica_transporte() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="critica_no_disponible:timeout",
        provenance=_Prov(),
    )


@pytest.fixture
def abstencion_correcta() -> _Result:
    """Abstención por regla de dominio: no es error."""
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="validacion:abstencion:el problema no se relaciona con el cruce",
        provenance=_Prov(),
    )


@pytest.fixture
def propuesta_valida() -> _Result:
    """Sin error y con estado: abstención/propuesta correcta."""
    return _Result(estado="PROPUESTA", provenance=_Prov())


@pytest.fixture
def cancelado() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="cancelado por el usuario",
        provenance=_Prov(),
    )


@pytest.fixture
def banco_no_superado() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error=(
            "interpretación operativa pendiente: falta superar el banco local; "
            "el endpoint no responde /models: HTTP 503"
        ),
        provenance=_Prov(),
    )


@pytest.fixture
def banco_cancelado() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error="banco local cancelado; intérprete no admitido",
        provenance=_Prov(),
    )


@pytest.fixture
def banco_modo() -> _Result:
    return _Result(
        estado="PENDIENTE_INTERPRETACION",
        error=(
            "banco local evaluado en otro modo de decodificación "
            "('json_schema' != ''); reevaluar"
        ),
        provenance=_Prov(),
    )


# --------------------------------------------------------------------------
# Tests: un código por caso.
# --------------------------------------------------------------------------


def test_transporte_caido(transporte_caido: _Result) -> None:
    d = classify(transporte_caido)
    assert d.error_code == TRANSPORT_UNAVAILABLE
    assert d.phase == "transporte"
    assert d.retryable is True
    assert d.next_action


def test_http_503_no_es_modelo_suspendido(http_503: _Result) -> None:
    """Un 503 es un fallo transitorio del proveedor, no 'modelo suspendido'."""
    d = classify(http_503)
    assert d.error_code == HTTP_ERROR
    assert d.http_status == 503
    assert d.retryable is True
    assert "5xx" in d.next_action or "servicio" in d.next_action


def test_auth_rechazada(auth_401: _Result) -> None:
    d = classify(auth_401)
    assert d.error_code == AUTH_REJECTED
    assert d.retryable is False


def test_rate_limited(rate_429: _Result) -> None:
    d = classify(rate_429)
    assert d.error_code == RATE_LIMITED
    assert d.retryable is True


def test_timeout(timeout: _Result) -> None:
    d = classify(timeout)
    assert d.error_code == TIMEOUT
    assert d.phase == "transporte"


def test_config_invalida(config_invalida: _Result) -> None:
    d = classify(config_invalida)
    assert d.error_code == INVALID_CONFIGURATION
    assert d.phase == "configuracion"
    assert d.retryable is False


def test_json_invalido(json_invalido: _Result) -> None:
    d = classify(json_invalido)
    assert d.error_code == INVALID_JSON
    assert d.phase == "parseo"


def test_schema_invalido_no_es_fallo_proveedor(schema_invalido: _Result) -> None:
    d = classify(schema_invalido)
    assert d.error_code == SCHEMA_VALIDATION_FAILED
    assert d.phase == "validacion"
    assert d.retryable is False


def test_dominio_invalido(dominio_invalido: _Result) -> None:
    d = classify(dominio_invalido)
    assert d.error_code == DOMAIN_CONTRACT_FAILED
    assert d.phase == "validacion"


def test_truncado(truncado: _Result) -> None:
    d = classify(truncado)
    assert d.error_code == TRUNCATED_RESPONSE
    assert d.finish_reason == ""  # no se rellena desde aquí


def test_critica_json_invalido(critica_json_invalido: _Result) -> None:
    d = classify(critica_json_invalido)
    assert d.error_code == CRITIQUE_INVALID
    assert d.phase == "critica"


def test_critica_transporte(critica_transporte: _Result) -> None:
    d = classify(critica_transporte)
    assert d.error_code == CRITIQUE_UNAVAILABLE
    assert d.phase == "critica"
    assert d.retryable is True


def test_abstencion_correcta_no_es_error(abstencion_correcta: _Result) -> None:
    """ABSTENER correcto: DOMAIN_REJECTION, retryable=False, no es avería."""
    d = classify(abstencion_correcta)
    assert d.error_code == DOMAIN_REJECTION
    assert d.phase == "dominio"
    assert d.retryable is False


def test_propuesta_valida(propuesta_valida: _Result) -> None:
    d = classify(propuesta_valida)
    assert d.error_code == CORRECT_ABSTENTION
    assert d.retryable is False


def test_cancelado(cancelado: _Result) -> None:
    d = classify(cancelado)
    assert d.error_code == CANCELLED
    assert d.phase == "cancelacion"
    assert d.retryable is False


def test_banco_no_superado(banco_no_superado: _Result) -> None:
    d = classify(banco_no_superado)
    assert d.error_code == BANK_NOT_PASSED
    assert d.phase == "banco"
    assert d.retryable is False


def test_banco_cancelado(banco_cancelado: _Result) -> None:
    d = classify(banco_cancelado)
    assert d.error_code == BANK_CANCELLED


def test_banco_modo_mismatch(banco_modo: _Result) -> None:
    d = classify(banco_modo)
    assert d.error_code == BANK_MODE_MISMATCH


# --------------------------------------------------------------------------
# Invariantes transversales.
# --------------------------------------------------------------------------


def test_nunca_secretos_en_diagnostico(http_503: _Result) -> None:
    """La procedencia saneada no debe contener credenciales."""
    prov = http_503.provenance
    assert isinstance(prov, _Prov)
    d = classify(http_503)
    prov_str = str(d.provenance)
    for marcador in ("Bearer", "key=", "token=", "sk-"):
        assert marcador not in prov_str


def test_todos_los_codigos_tienen_next_action(
    transporte_caido: _Result,
    http_503: _Result,
    auth_401: _Result,
    rate_429: _Result,
    timeout: _Result,
    config_invalida: _Result,
    json_invalido: _Result,
    schema_invalido: _Result,
    dominio_invalido: _Result,
    truncado: _Result,
    critica_json_invalido: _Result,
    critica_transporte: _Result,
    abstencion_correcta: _Result,
    propuesta_valida: _Result,
    cancelado: _Result,
    banco_no_superado: _Result,
    banco_cancelado: _Result,
    banco_modo: _Result,
) -> None:
    """Sin fallback silencioso: cada código produce una acción explícita."""
    for r in (
        transporte_caido,
        http_503,
        auth_401,
        rate_429,
        timeout,
        config_invalida,
        json_invalido,
        schema_invalido,
        dominio_invalido,
        truncado,
        critica_json_invalido,
        critica_transporte,
        abstencion_correcta,
        propuesta_valida,
        cancelado,
        banco_no_superado,
        banco_cancelado,
        banco_modo,
    ):
        d = classify(r)
        assert d.next_action, f"{d.error_code} sin next_action"


def test_as_dict_seriable(http_503: _Result) -> None:
    d = classify(http_503)
    import json

    json.dumps(d.as_dict())  # no debe lanzar
