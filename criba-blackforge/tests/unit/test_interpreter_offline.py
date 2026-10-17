from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from unittest.mock import patch, MagicMock

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from criba.interprete.openai_compatible import OpenAICompatibleInterpreter


@dataclass(frozen=True)
class FakeHTTPResponse:
    status_code: int = 200
    payload: dict[str, Any] | None = None
    exception: Exception | None = None

    def json(self) -> dict[str, Any]:
        if self.payload is None:
            raise AssertionError("json() called on an error response")
        return self.payload

    @property
    def text(self) -> str:
        return json.dumps(self.payload) if self.payload else ""


class FakeTransport:
    """Reemplaza solo el borde HTTP; el intérprete y su parser siguen siendo reales."""

    def __init__(self, response: FakeHTTPResponse) -> None:
        self.response = response
        self.requests: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        timeout: float,
    ) -> FakeHTTPResponse:
        self.requests.append(
            {
                "url": url,
                "headers": {
                    key: value
                    for key, value in headers.items()
                    if key.lower() != "authorization"
                },
                "json": json,
                "timeout": timeout,
            }
        )
        if self.response.exception is not None:
            raise self.response.exception
        return self.response


def _proposal_json() -> str:
    """Fixture sintética conforme al contrato; no es evidencia observada."""
    return json.dumps(
        {
            "pertinencia": "PERTINENTE",
            "motivo_abstencion": "",
            "hipotesis": (
                "Instalar grifos con sensor reduce el consumo por uso intermitente."
            ),
            "mecanismo": (
                "El sensor corta el flujo cuando no hay manos bajo el grifo, "
                "reduciendo el consumo innecesario."
            ),
            "aportacion_por_tecnica": [
                "Sensores de movimiento",
                "Reductores de caudal",
            ],
            "supuestos": [
                "Los empleados dejan abiertos los grifos",
                "Los sensores detectan presencia",
            ],
            "prueba_concreta": (
                "Medir consumo antes y después de instalar sensores."
            ),
            "ruta_desbloqueo": (
                "Instalar sensores en dos baños y medir durante 30 días."
            ),
            "cadena_causal": [
                "Instalar sensores",
                "Reducir consumo innecesario",
            ],
            "evidencia_citada": [],
            "conocimiento_previo": [
                "Fixture sintética: los sensores pueden reducir el uso intermitente."
            ],
            "incertidumbre": (
                "No se conoce el ahorro exacto en esta oficina."
            ),
            "novedad": "Aplicación de sensores en baños de oficina.",
            "prueba": {
                "metrica": "Consumo diario de agua",
                "baseline": "Consumo actual sin sensores",
                "umbral": "Reducción del 20%",
                "condicion_fracaso": "No se reduce el consumo",
                "alternativa_explicativa": "Los empleados no usan los baños",
                "resultado_favorable_mecanismo": "El sensor reduce el consumo",
                "resultado_favorable_alternativa": (
                    "Los empleados usan otros baños"
                ),
            },
            "comprobacion_restricciones": [],
            "critica": {},
        },
        ensure_ascii=False,
    )


class MockTransportClient:
    """Reemplaza httpx.Client con un cliente simulado que usa FakeTransport."""
    def __init__(self, transport_ref, *args, **kwargs):
        self.transport_ref = transport_ref
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass
    def post(self, url, **kwargs):
        headers = kwargs.get("headers", {})
        json_data = kwargs.get("json", {})
        timeout = kwargs.get("timeout", 30.0)
        return self.transport_ref.post(url, headers=headers, json=json_data, timeout=timeout)

def _make_interpreter(
    monkeypatch: pytest.MonkeyPatch,
    response: FakeHTTPResponse,
) -> tuple[OpenAICompatibleInterpreter, FakeTransport]:
    transport = FakeTransport(response)

    def make_client(*args, **kwargs):
        return MockTransportClient(transport, *args, **kwargs)

    monkeypatch.setattr(
        "criba.interprete.openai_compatible.httpx.Client",
        make_client,
    )
    interpreter = OpenAICompatibleInterpreter(
        base_url="http://127.0.0.1:8645/v1",
        model="meituan/longcat-2.5-preview:free",
        reasoning_effort="low",
    )
    return interpreter, transport


def _inputs() -> tuple[str, dict[str, str], dict[str, str], list[dict[str, str]]]:
    return (
        "Reducir consumo de agua en una oficina",
        {
            "title": "Instalar grifos con sensores de movimiento",
            "method1": "Sensores de movimiento",
            "method2": "Reductores de caudal",
        },
        {"title": "Oficina con 20 empleados", "domain": "office"},
        [
            {
                "title": "Fixture sintética: sensor reduce uso intermitente",
                "index": 1,
            }
        ],
    )


def test_valid_content_becomes_proposal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A. Respuesta final válida -> propuesta válida."""
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {
                        "content": _proposal_json(),
                        "reasoning": "Razonamiento interno no utilizable como content.",
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"completion_tokens": 42},
        }
    )
    interpreter, transport = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PROPUESTA"
    assert result.hipotesis
    assert result.mecanismo
    assert result.provenance.request_id
    assert result.finish_reason == "stop"
    assert transport.requests[0]["json"]["reasoning_effort"] == "low"
    assert "authorization" not in {
        key.lower() for key in transport.requests[0]["headers"]
    }


def test_reasoning_without_content_is_not_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """F. Reasoning sin content no puede sustituir a content."""
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {
                        "content": "",
                        "reasoning": "Parece una idea razonable, pero no hay respuesta final.",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado != "PROPUESTA"
    assert not result.hipotesis
    assert not result.mecanismo
    assert result.finish_reason == "stop"
    assert result.error_kind in {
        None,
        "invalid_response",
        "empty_content",
        "abstention",
    }


def test_empty_content_with_length_is_truncated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """C. content vacío + finish_reason=length -> truncamiento."""
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {"content": "", "reasoning": ""},
                    "finish_reason": "length",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PENDIENTE_INTERPRETACION"
    assert "truncada" in result.error or "length" in result.error
    assert result.finish_reason == "length"


def test_empty_content_without_explanation_is_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D. content vacío sin explicación -> respuesta inválida."""
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {"content": "", "reasoning": ""},
                    "finish_reason": "stop",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PENDIENTE_INTERPRETACION"
    assert "sin_contenido" in result.error


def test_invalid_json_preserves_parse_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """E. JSON inválido -> causa de parseo preservada."""
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {
                        "content": "{pertinencia: PERTINENTE, hipotesis: incompleto",
                        "reasoning": "",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PENDIENTE_INTERPRETACION"
    assert "json_invalido" in result.error


def test_abstention_is_not_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """B. Abstención contractual -> ABSTAINED con causa."""
    abstention = json.dumps(
        {
            "pertinencia": "NO_PERTINENTE",
            "motivo_abstencion": (
                "La entrada no contiene suficiente información para proponer."
            ),
            "hipotesis": "",
            "mecanismo": "",
            "evidencia_citada": [],
        },
        ensure_ascii=False,
    )
    response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {"content": abstention, "reasoning": ""},
                    "finish_reason": "stop",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PROPUESTA"
    assert result.pertinencia == "ABSTENER"
    assert result.error == ""
    assert result.finish_reason == "stop"


def test_http_429_is_rate_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """H. HTTP 429 -> rate limit, sin fallback ni retry."""
    response = FakeHTTPResponse(
        status_code=429,
        payload={"error": {"message": "rate limited"}},
    )
    interpreter, transport = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PENDIENTE_INTERPRETACION"
    assert "429" in result.error or "rate" in result.error.lower()
    assert len(transport.requests) == 1


def test_read_timeout_is_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """I. ReadTimeout -> timeout explícito, sin fallback ni retry."""
    response = FakeHTTPResponse(
        exception=httpx.ReadTimeout("read timed out")
    )
    interpreter, transport = _make_interpreter(monkeypatch, response)
    problem, idea, context, evidence = _inputs()

    result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado == "PENDIENTE_INTERPRETACION"
    assert "timeout" in result.error.lower()
    assert len(transport.requests) == 1


def test_valid_proposal_with_failed_critique_is_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """G. Propuesta válida + crítica fallida -> estado contractual explícito."""
    proposal_response = FakeHTTPResponse(
        payload={
            "choices": [
                {
                    "message": {
                        "content": _proposal_json(),
                        "reasoning": "",
                    },
                    "finish_reason": "stop",
                }
            ],
        }
    )
    interpreter, _ = _make_interpreter(monkeypatch, proposal_response)
    problem, idea, context, evidence = _inputs()

    with patch.object(
        interpreter,
        "criticar",
        side_effect=httpx.ReadTimeout("critique transport failed"),
    ):
        result = interpreter.proponer(problem, idea, context, evidence)

    assert result.estado in {
        "PENDIENTE_INTERPRETACION",
        "PROPUESTA_SIN_CRITICA",
        "CRITICA_FALLIDA",
    }
    assert "timeout" in result.error.lower() or result.hipotesis or result.raw_output
    assert result.hipotesis or result.raw_output
