"""Regresion del puerto de interpretacion y del borde que rompia el journey.

El borde demostrado: sin un interprete alcanzable, ``_default_proponer``
devolvia PENDIENTE_INTERPRETACION para todas las entradas, ``on_desarrollar_supra``
encontraba cero PROPUESTAS y abortaba antes de construir el dossier. Desde ahi
no habia POST a SUPRA, ni persistencia, ni GET. Medido el 2026-10-03.

Lo que fijan estos tests, uno por borde:

- sin interprete alcanzable -> 0 PROPUESTA y el motivo real se conserva
- PROPUESTA sin mecanismo -> degrada a PENDIENTE con motivo (no se rellena)
- JSON invalido -> PENDIENTE con el tipo de error, sin campos inventados
- HTTP 429 / 401 -> PENDIENTE con su codigo, sin volcar la respuesta
- timeout -> PENDIENTE, y el timeout es configurable
- procedencia completa en exito y en fallo, y sin ninguna clave
- el modelo distinto al solicitado se registra como reportado, no como pedido
- los dos backends pasan por el mismo esquema y el mismo `to_campos`
- el backend local NO se declara operativo
- no hay fallback automatico: solo si el operador lo activa
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from verification.interpreter_cases import critica, propuesta
from criba.interprete import openai_compatible as oc
from criba.interprete import puerto as P
from criba.interprete.seleccion import (
    construir_interprete,
    estado_interprete,
    seleccion_por_defecto,
)

IDEA = {"title": "cruce A+B", "method1": "contradiccion", "method2": "separacion"}

PROPUESTA_JSON = propuesta()


class _Respuesta:
    """Respuesta falsa con la misma forma que usa la libreria."""

    def __init__(self, status_code: int, cuerpo: Any = None, texto: str = "") -> None:
        self.status_code = status_code
        self._cuerpo = cuerpo if cuerpo is not None else {}
        self.text = texto or json.dumps(self._cuerpo)

    def json(self) -> Any:
        return self._cuerpo

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("http", request=None, response=None)


def _patch_post(monkeypatch, respuesta: _Respuesta) -> list[dict[str, Any]]:
    """Captura lo que se envia, para poder afirmar sobre el payload."""
    enviados: list[dict[str, Any]] = []

    class _Cliente:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> _Cliente:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def post(self, url: str, json: Any = None, headers: Any = None) -> _Respuesta:
            enviados.append({"url": url, "json": json, "headers": headers or {}})
            if len(enviados) > 1:
                return _Respuesta(200, {"model": "critico-reportado", "choices": [
                    {"finish_reason": "stop", "message": {"content": __import__("json").dumps(critica())}}
                ]})
            return respuesta

    monkeypatch.setattr(oc.httpx, "Client", _Cliente)
    return enviados


def _ok(clave: str = "mecanismo_que_falta") -> _Respuesta:
    cuerpo = {
        "model": "otro-modelo-reportado",
        "choices": [{"message": {"content": json.dumps(PROPUESTA_JSON)}}],
    }
    del clave
    return _Respuesta(200, cuerpo)


def _interprete(**kwargs: Any) -> oc.OpenAICompatibleInterpreter:
    base = {"base_url": "http://127.0.0.1:9/v1", "model": "m", "api_key": "secreto-de-prueba"}
    base.update(kwargs)
    return oc.OpenAICompatibleInterpreter(**base)


# ----------------------------------------------------------------_exito
def test_propuesta_valida_lleva_procedencia_completa(monkeypatch):
    cuerpo = {
        "model": "otro-modelo-reportado",
        "usage": {
            "completion_tokens": 321,
            "completion_tokens_details": {"reasoning_tokens": 123},
        },
        "choices": [
            {
                "finish_reason": "stop",
                "message": {"content": json.dumps(PROPUESTA_JSON)},
            }
        ],
    }
    enviados = _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA, {"title": "d"}, [])
    assert resultado.es_propuesta
    assert resultado.raw_output == json.dumps(PROPUESTA_JSON)
    assert resultado.finish_reason == "stop"
    assert resultado.completion_tokens == 321
    assert resultado.reasoning_tokens == 123
    assert "tools" not in enviados[0]["json"]
    assert enviados[0]["json"]["response_format"] == {"type": "json_object"}
    prov = resultado.provenance
    assert prov is not None
    assert prov.interpreter_backend == "openai_compatible"
    assert prov.model_requested == "m"
    # El modelo REPORTADO puede diferir del pedido: se guardan los dos, no uno.
    assert prov.model_reported == "otro-modelo-reportado"
    assert prov.prompt_version and prov.schema_version and prov.request_id
    assert prov.duration_ms >= 0
    assert prov.raw_output_sha256 and len(prov.raw_output_sha256) == 64
    assert prov.timestamp.endswith("Z")
    assert prov.fallback_used is False


def test_la_credencial_no_aparece_en_la_procedencia_nunca():
    prov = P.Provenance(
        interpreter_backend="x",
        provider="p",
        model_requested="m",
        model_reported="m",
        endpoint="http://127.0.0.1:8642/v1",
        timestamp="t",
        duration_ms=1,
        prompt_version="v",
        schema_version="s",
        request_id="r",
        fallback_used=False,
        raw_output_sha256="h",
    )
    volcado = json.dumps(prov.sin_secretos())
    assert "secreto-de-prueba" not in volcado
    assert "Bearer" not in volcado


def test_endpoint_con_credenciales_embebidas_queda_redactado():
    prov = P.Provenance(
        interpreter_backend="x",
        provider="p",
        model_requested="m",
        model_reported="m",
        endpoint="http://usuario:clave-secreta@host/v1?api_key=abc",
        timestamp="t",
        duration_ms=1,
        prompt_version="v",
        schema_version="s",
        request_id="r",
        fallback_used=False,
        raw_output_sha256="h",
    )
    limpio = prov.sin_secretos()
    assert limpio["endpoint"] == "[REDACTADO]"
    assert "clave-secreta" not in json.dumps(limpio)


def test_sin_secretos_de_url():
    assert P.sin_secretos("http://u:p@host:8642/v1/") == "http://host:8642/v1"
    assert P.sin_secretos("http://host/v1?x=1") == "http://host/v1"


# ----------------------------------------------------------------_fallos
def test_json_invalido_no_inventa_campos_y_conserva_salida_bruta(monkeypatch):
    raw = "esto no es json, es prosa"
    cuerpo = {
        "model": "m-reportado",
        "choices": [{"finish_reason": "stop", "message": {"content": raw}}],
    }
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    assert not resultado.es_propuesta
    campos = resultado.to_campos()
    assert campos["estado"] == P.ESTADO_PENDIENTE
    assert campos["mecanismo"] == ""
    assert campos["error"] == "json_invalido:JSONDecodeError"
    assert resultado.raw_output == raw
    assert resultado.finish_reason == "stop"
    # Y la procedencia existe tambien en el fallo: sin causa no es diagnosticable.
    assert resultado.provenance is not None


@pytest.mark.parametrize("cuerpo", [{}, {"choices": []}])
def test_choices_ausente_o_vacio_es_error_especifico(monkeypatch, cuerpo):
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "respuesta_sin_choices"
    assert resultado.raw_output == ""


def test_choice_de_tipo_inesperado_es_error_especifico(monkeypatch):
    _patch_post(monkeypatch, _Respuesta(200, {"choices": ["no-es-objeto"]}))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "choice_tipo_inesperado:str"


def test_content_de_tipo_inesperado_no_se_convierte_a_texto(monkeypatch):
    cuerpo = {"choices": [{"finish_reason": "stop", "message": {"content": ["x"]}}]}
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "contenido_tipo_inesperado:list"
    assert resultado.raw_output == ""


def test_tool_calls_sin_contenido_no_se_presenta_como_interpretacion(monkeypatch):
    cuerpo = {
        "choices": [
            {
                "finish_reason": "tool_calls",
                "message": {"content": None, "tool_calls": [{"id": "call-1"}]},
            }
        ]
    }
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "tool_calls_sin_contenido"
    assert resultado.raw_output == ""


def test_http_500_conserva_codigo_sin_volcar_cuerpo(monkeypatch):
    _patch_post(monkeypatch, _Respuesta(500, texto="detalle-interno-sensible"))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "http_error_500"
    assert "detalle-interno-sensible" not in resultado.to_campos()["error"]


def test_propuesta_sin_mecanismo_degrada_con_motivo(monkeypatch):
    sin_mecanismo = {**PROPUESTA_JSON, "mecanismo": "   "}
    cuerpo = {"choices": [{"message": {"content": json.dumps(sin_mecanismo)}}]}
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    # El backend degrada el PROPUESTA sin mecanismo antes de devolverlo, asi que
    # lo que sale ya es PENDIENTE con su motivo. No se rellena el hueco.
    assert resultado.estado == P.ESTADO_PENDIENTE
    assert "sin mecanismo" in resultado.motivo_real()
    assert resultado.to_campos()["estado"] == P.ESTADO_PENDIENTE
    assert resultado.to_campos()["mecanismo"] == ""


def test_429_no_inventa_y_conserva_el_codigo(monkeypatch):
    _patch_post(monkeypatch, _Respuesta(429))
    resultado = _interprete().proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "plan_agotado_429"


@pytest.mark.parametrize("codigo", [401, 403])
def test_401_403_no_vuelca_el_cuerpo_de_respuesta(monkeypatch, codigo):
    _patch_post(monkeypatch, _Respuesta(codigo, texto="token=secreto-en-cuerpo"))
    resultado = _interprete().proponer("q", IDEA)
    campos = resultado.to_campos()
    assert f"HTTP {codigo}" in campos["error"]
    assert "secreto-en-cuerpo" not in campos["error"]


def test_modelo_sin_contenido_por_presupuesto_de_tokens(monkeypatch):
    """El caso real del 2026-10-03: content=null y todo el gasto en razonamiento.

    Un modelo de razonamiento con 2048 tokens consumio 1988 pensando y no
    emitio nada. Antes esto reventaba con TypeError al medir len(None), y antes
    aun con JSONDecodeError. Ahora se dice exactamente lo que paso.
    """
    cuerpo = {
        "model": "m-reportado",
        "usage": {
            "completion_tokens": 2048,
            "completion_tokens_details": {"reasoning_tokens": 1988},
        },
        "choices": [{"finish_reason": "length", "message": {"content": None}}],
    }
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    campos = resultado.to_campos()
    assert campos["estado"] == P.ESTADO_PENDIENTE
    assert campos["error"].startswith("sin_contenido")
    assert "length" in campos["error"]
    assert "1988" in campos["error"], "el gasto de razonamiento es la causa"
    assert "TypeError" not in campos["error"]
    assert campos["mecanismo"] == ""


def test_el_presupuesto_de_tokens_supera_a_un_modelo_razonador():
    """2048 se demostro insuficientes; el adaptador antiguo pedia 4096."""
    assert oc.MAX_TOKENS >= 4096


def test_el_presupuesto_de_tokens_es_configurable(monkeypatch):
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "8192")
    enviados = _patch_post(monkeypatch, _ok())
    _interprete().proponer("q", IDEA)
    assert enviados[0]["json"]["max_tokens"] == 8192


def test_timeout_es_configurable_y_produce_pendiente(monkeypatch):
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
    resultado = _interprete(timeout_s=0.5).proponer("q", IDEA)
    assert resultado.to_campos()["error"] == "timeout"


def test_salida_truncada_se_atribuye_y_no_se_confunde_con_json_invalido(monkeypatch):
    """finish_reason=length NO es JSON invalido: es la respuesta cortada.

    Medido el 2026-10-03: el modelo devolvio 1434 caracteres cortados a mitad
    de cadena y el error que se reportaba era "JSONDecodeError", que no dice
    nada sobre la causa. Con finish_reason se distingue y se dice la verdad.
    """
    cuerpo = {
        "model": "m-reportado",
        "choices": [
            {"finish_reason": "length", "message": {"content": '{"hipotesis": "cortada a medi'}}
        ],
    }
    _patch_post(monkeypatch, _Respuesta(200, cuerpo))
    resultado = _interprete().proponer("q", IDEA)
    campos = resultado.to_campos()
    assert campos["estado"] == P.ESTADO_PENDIENTE
    assert campos["error"].startswith("salida_truncada")
    assert "length" in campos["error"]
    assert "JSONDecodeError" not in campos["error"], "no debe disfrazarse de JSON invalido"
    assert resultado.provenance is not None
    assert resultado.provenance.model_reported == "m-reportado"


def test_el_timeout_por_defecto_supera_los_30s_del_adaptador_anterior():
    """30 s se demostraron insuficientes: una propuesta real dio timed out."""
    assert oc.TIMEOUT_POR_DEFECTO >= 60.0


# ----------------------------------------------------------------_contrato
def test_ambos_backends_comparten_esquema_y_to_campos(monkeypatch):
    _patch_post(monkeypatch, _Respuesta(503))
    for interprete in (
        oc.OpenAICompatibleInterpreter(base_url="http://x/v1"),
        oc.LocalLlamaInterpreter(),
    ):
        assert isinstance(interprete.backend, str) and interprete.backend
        resultado = interprete.proponer("q", IDEA, {"title": "d"}, [])
        campos = resultado.to_campos()
        assert set(campos) == set(P.CAMPOS_PROPUESTA)
        assert resultado.provenance is not None
        assert resultado.provenance.interpreter_backend == interprete.backend


def test_local_llama_no_se_declara_operativo(monkeypatch):
    """Genera ideas, pero la interpretacion no lo esta: se dice, no se disimula."""
    monkeypatch.setattr(
        oc.OpenAICompatibleInterpreter, "operativo", lambda self: (False, "runtime ausente (prueba)")
    )
    local = oc.LocalLlamaInterpreter()
    listo, motivo = local.operativo()
    assert listo is False
    assert "interpretación operativa" in motivo
    assert len(motivo) > 40, "el motivo debe explicar, no solo negar"
    estado = estado_interprete(local)
    assert estado["conectado"] is False
    assert estado["experimental"] is True
    resultado = local.proponer("q", IDEA)
    assert resultado.to_campos()["estado"] == P.ESTADO_PENDIENTE
    assert resultado.to_campos()["mecanismo"] == ""


# ----------------------------------------------------------------_seleccion
def test_el_defecto_es_el_externo(monkeypatch):
    monkeypatch.delenv("CRIBA_INTERPRETER_DEFAULT", raising=False)
    assert seleccion_por_defecto() == "openai_compatible"
    assert construir_interprete().backend == "openai_compatible"


def test_local_se_puede_elegir_expresamente(monkeypatch):
    monkeypatch.setenv("CRIBA_INTERPRETER_DEFAULT", "local")
    assert construir_interprete().backend == "local_llama"


def test_backend_desconocido_falla_visible_no_elige_por_silencio(monkeypatch):
    """Pedir un backend que no existe es un error, no un permiso para usar otro.

    Elegir el externo en silencio produciria una respuesta correcta atribuida a
    un interprete que el operador no eligio. Falla, y el mensaje dice que se
    pidio y que hay.
    """
    from criba.interprete.seleccion import BackendDesconocido

    monkeypatch.setenv("CRIBA_INTERPRETER_DEFAULT", "no-existe")
    with pytest.raises(BackendDesconocido) as excinfo:
        construir_interprete()
    mensaje = str(excinfo.value)
    assert "no-existe" in mensaje
    assert "openai_compatible" in mensaje and "local_llama" in mensaje


def test_el_motivo_de_backend_desconocido_llega_a_la_propuesta(monkeypatch):
    """El mensaje accionable tiene que llegar a la ficha, no solo al log."""
    monkeypatch.setenv("CRIBA_INTERPRETER_DEFAULT", "no-existe")
    from criba.inventar import _default_proponer

    campos = _default_proponer("q", {"title": "t", "method1": "A", "method2": "B"}, None)
    assert campos["estado"] == "PENDIENTE_INTERPRETACION"
    assert "no-existe" in campos["error"]
    assert "ValueError" not in campos["error"], "el tipo de excepcion no es accionable"


def test_no_hay_fallback_automatico_por_defecto():
    """Solo cae a local si el operador lo activa. Nunca por defecto."""
    assert oc.OpenAICompatibleInterpreter().fallback_local is False
    assert oc.OpenAICompatibleInterpreter(fallback_local=True).fallback_local is True


def test_operativo_comprueba_de_verdad_y_no_por_configuracion(monkeypatch):
    """Tener URL y modelo no significa estar listo: hay que responder."""

    class _ClienteModels:
        def __init__(self, *a: Any, **k: Any) -> None:
            pass

        def __enter__(self) -> _ClienteModels:
            return self

        def __exit__(self, *a: Any) -> None:
            return None

        def get(self, url: str, headers: Any = None) -> _Respuesta:
            return _Respuesta(200, {"data": [{"id": "otro"}]})

    monkeypatch.setattr(oc.httpx, "Client", _ClienteModels)
    listo, motivo = oc.OpenAICompatibleInterpreter(
        base_url="http://127.0.0.1:8642/v1", model="no-en-catalogo"
    ).operativo()
    assert listo is False
    assert "catalogo" in motivo


def test_json_envuelto_en_vallas_se_acepta():
    """El modelo envuelve en ```json con frecuencia; no es JSON invalido."""
    envuelto = "```json\n" + json.dumps(PROPUESTA_JSON) + "\n```"
    assert oc._extraer_json(envuelto)["mecanismo"] == PROPUESTA_JSON["mecanismo"]
    con_ruido = "Aqui va:\n" + json.dumps(PROPUESTA_JSON) + "\nfin"
    assert oc._extraer_json(con_ruido)["mecanismo"] == PROPUESTA_JSON["mecanismo"]


def test_prompt_conserva_los_campos_del_contrato():
    prompt = oc.construir_prompt("q", IDEA, {"title": "d"}, [{"title": "t", "abstract": "a"}])
    for campo in (
        "hipotesis",
        "mecanismo",
        "aportacion_por_tecnica",
        "supuestos",
        "prueba_concreta",
    ):
        assert campo in prompt
    assert "EVIDENCIA LOCAL PERTINENTE" in prompt
