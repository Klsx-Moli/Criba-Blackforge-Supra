"""CB-S04: red, puertos y servicios locales — límites y fallos no corruptos.

Complementa test_api_boundaries (FastAPI rechaza no-loopback) y
test_interprete_puerto (401/403/429/timeout). Aquí se verifican los casos de
disponibilidad del megaprompt contra OpenAICompatibleInterpreter real:

- 503/500 NO se interpretan como "modelo suspendido": son fallos del proveedor
- conexión cortada (ConnectError) → fallo de transporte clasificado
- respuesta lenta controlada por timeout configurable
- URL con credenciales embebidas rechazada antes de conectar
- un fallo de red no fabrica propuesta: siempre PENDIENTE con código

Invariante: local sólo loopback; fallo de red no corrompe; 503 != suspendido;
sin reintento automático.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import httpx
import pytest

# Reutiliza los helpers de transporte del test de puerto (misma superficie).
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "unit"))
from criba.interprete import openai_compatible as oc  # noqa: E402
from test_interprete_puerto import _interprete, _patch_post, _Respuesta  # noqa: E402


def _idea() -> dict[str, Any]:
    return {
        "title": "Confirmar sin revisar",
        "method1": "Confirmación automática",
        "method2": "Recordatorios",
        "bloqueo": {"title": "salud"},
    }


# --------------------------------------------------------------------------
# 503 / 500 NO es "modelo suspendido"
# --------------------------------------------------------------------------


@pytest.mark.parametrize("codigo", [500, 502, 503])
def test_5xx_es_fallo_de_proveedor_no_suspendido(monkeypatch, codigo: int) -> None:
    """Un 5xx se clasifica como http_error, nunca como 'modelo suspendido'."""
    _patch_post(monkeypatch, _Respuesta(codigo, texto="service unavailable"))
    resultado = _interprete().proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    error = campos["error"]
    assert error.startswith("http_error_")
    assert "suspendid" not in error.casefold()
    # No fabrica propuesta.
    assert campos["hipotesis"] == ""


def test_503_no_promueve_abstencion(monkeypatch) -> None:
    """Un 503 no se convierte en una abstención del dominio: es indisponibilidad."""
    _patch_post(monkeypatch, _Respuesta(503, texto="unavailable"))
    resultado = _interprete().proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    # El estado es pendiente por fallo, no ABSTENER.
    assert "abstencion" not in campos["error"].casefold()
    assert campos["hipotesis"] == ""


# --------------------------------------------------------------------------
# Conexión cortada → fallo de transporte clasificado
# --------------------------------------------------------------------------


def test_conexion_cortada_es_transporte(monkeypatch) -> None:
    """Un ConnectError se clasifica como fallo de transporte, sin romper el run."""
    class _ClienteCorte:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> _ClienteCorte:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def post(self, *a: Any, **k: Any) -> Any:
            raise httpx.ConnectError("conexion cortada")

    monkeypatch.setattr(oc.httpx, "Client", _ClienteCorte)
    resultado = _interprete().proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert "transporte" in campos["error"].casefold() or "ConnectError" in campos["error"]
    assert campos["hipotesis"] == ""


def test_error_http_generico_es_transporte(monkeypatch) -> None:
    """Cualquier httpx.HTTPError se clasifica como fallo de transporte."""
    class _ClienteError:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> _ClienteError:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def post(self, *a: Any, **k: Any) -> Any:
            raise httpx.ReadError("lectura cortada")

    monkeypatch.setattr(oc.httpx, "Client", _ClienteError)
    resultado = _interprete().proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert "transporte" in campos["error"].casefold()
    assert campos["hipotesis"] == ""


# --------------------------------------------------------------------------
# Timeout configurable → pendiente, sin colgar
# --------------------------------------------------------------------------


def test_timeout_produce_pendiente(monkeypatch) -> None:
    """Un timeout se clasifica como 'timeout', no como propuesta vacía."""
    class _ClienteTimeout:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> _ClienteTimeout:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def post(self, *a: Any, **k: Any) -> Any:
            raise httpx.TimeoutException("se agoto")

    monkeypatch.setattr(oc.httpx, "Client", _ClienteTimeout)
    resultado = _interprete(timeout_s=0.01).proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert campos["error"] == "timeout"
    assert campos["hipotesis"] == ""


def test_timeout_invalido_es_configuracion(monkeypatch) -> None:
    """Un timeout fuera de rango se rechaza como configuración inválida."""
    import os

    monkeypatch.setenv("CRIBA_EXTERNAL_TIMEOUT_S", "-5")
    resultado = _interprete(timeout_s=-5).proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert "configuracion_invalida" in campos["error"]
    assert os.getenv("CRIBA_EXTERNAL_TIMEOUT_S") == "-5"


# --------------------------------------------------------------------------
# URL con credenciales embebidas rechazada
# --------------------------------------------------------------------------


class _SinRed:
    """Sustituto de httpx.Client que falla el test si alguien intenta conectar."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise AssertionError("se intentó abrir una conexión HTTP: debió rechazarse antes")


@pytest.mark.parametrize(
    "url",
    [
        "http://user:pass@127.0.0.1:8645/v1",  # credenciales embebidas
        "http://:solo-pass@127.0.0.1:8645/v1",  # solo contraseña
        "http://api.ejemplo-remoto.com/v1",  # http en claro hacia host remoto
        "ftp://127.0.0.1/v1",  # esquema no permitido
        "http:///v1",  # sin host
    ],
)
def test_endpoint_inseguro_se_rechaza_sin_abrir_conexion(monkeypatch, url: str) -> None:
    """operativo() y proponer() rechazan el endpoint ANTES de conectar y sin Bearer."""
    monkeypatch.setattr(oc.httpx, "Client", _SinRed)
    interp = _interprete(base_url=url)

    listo, motivo = interp.operativo()
    assert listo is False
    assert "rechazado antes de conectar" in motivo
    assert "secreto-de-prueba" not in motivo and "pass" not in motivo.replace("rechazado", "")

    resultado = interp.proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert campos["error"].startswith("configuracion_invalida:endpoint:")
    assert campos["hipotesis"] == ""
    assert resultado.model_requests == 0


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8645/v1",
        "http://localhost:8080/v1",
        "http://[::1]:8080/v1",
        "https://api.ejemplo-remoto.com/v1",
    ],
)
def test_endpoint_aceptable_no_se_rechaza_por_validacion(url: str) -> None:
    assert oc.endpoint_problem(url) is None


def test_url_con_credenciales_rechazada() -> None:
    """Un endpoint con usuario:password@ se rechaza como no operable (sin conectar)."""

    interp = _interprete(base_url="http://user:pass@127.0.0.1:8645/v1")
    listo, motivo = interp.operativo()
    assert listo is False
    # Antes se aceptaba la palabra "endpoint" suelta, que también aparece en
    # "el modelo no está en el catálogo del endpoint": el test pasaba tras
    # CONECTAR. Ahora exige el rechazo explícito previo a cualquier conexión.
    assert "credenciales embebidas" in motivo


def test_endpoint_no_loopback_rechazado() -> None:
    """Un endpoint remoto (no loopback) se rechaza como no operable para el local."""
    interp = _interprete(base_url="https://api.ejemplo-remoto.com/v1")
    listo, _motivo = interp.operativo()
    assert listo is False


# --------------------------------------------------------------------------
# Un fallo de red nunca fabrica propuesta
# --------------------------------------------------------------------------


def test_fallo_red_nunca_fabrica(monkeypatch) -> None:
    """Ante cualquier fallo de red, el resultado es PENDIENTE sin hipótesis inventada."""
    _patch_post(monkeypatch, _Respuesta(500, texto="boom"))
    resultado = _interprete().proponer("problema", _idea(), None)
    campos = resultado.to_campos()
    assert campos["hipotesis"] == ""
    assert campos["mecanismo"] == ""
    # El error declara la causa, no un éxito vacío.
    assert campos["error"]
