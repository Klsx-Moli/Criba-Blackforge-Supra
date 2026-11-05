from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from criba.interprete.refinamiento import (
    REFINEMENT_SCHEMA,
    aplicar_protocolo,
    build_refinement_prompt,
    parse_refinement,
    refinar_propuesta,
)
from criba.ui.actions import _entry_para_desarrollo
from criba.ui.proposal_view import format_proposal


def _protocolo() -> dict:
    return {
        "resumen": "Retener inconsistencias menores y priorizar por estados.",
        "fuente_error": "La transcripcion manual y la correccion posterior introducen y ocultan errores.",
        "punto_intervencion": "En el marcado del registro durante la operacion de almacen.",
        "por_que_reduce": "Reduce la fuente porque evita que la contradiccion se pierda antes de revisarla.",
        "mecanismo_concreto": (
            "Un sensor de doble contacto se coloca en la base de cada estanteria "
            "del almacen y bloquea fisicamente la salida del palet cuando el "
            "registro marcado como contradictorio no ha sido revisado por un "
            "segundo operario en los diez minutos siguientes."
        ),
        "punto_fisico": "En el pasillo de salida, junto a la puerta cortafuegos del almacen central.",
        "modo_efecto": "ELIMINA",
        "prueba_mecanismo": (
            "Retirar el sensor durante cinco turnos y medir si el tiempo de "
            "bloqueo por revision pendiente cae a cero."
        ),
        "componentes": [
            "Sensor de doble contacto en la base de la estanteria - detiene la salida del palet - contacto seco con la plataforma",
            "Balanza de puerta con testigo - registra la retencion pendiente - consulta interna cada treinta segundos",
        ],
        "secuencia_operativa": [
            "Registro marcado como contradictorio -> el sensor retiene el palet en la salida -> un segundo operario revisa y libera",
            "Revision no realizada en diez minutos -> la balanza avisa al supervisor -> reasignacion manual del palet",
        ],
        "definiciones_operativas": [
            "Contradiccion menor: diferencia <2% entre registrado y contado.",
            "Contradiccion mayor: diferencia >=2% o dato critico ausente.",
            "Retencion: el registro se marca y sigue en analisis.",
        ],
        "criterio_dominancia": "Pareto 80/20 sobre errores observados por estado.",
        "asignacion_presupuesto": "Tiempo proporcional a la contribucion de cada estado.",
        "metrica_principal": "Errores por 100 operaciones.",
        "metrica_secundaria": "Variacion porcentual del tiempo de inspeccion.",
        "regla_exito": "Reduccion >=15% y tiempo dentro de +-5%.",
        "banda_intermedia": "Entre 5% y 15% se extiende la prueba dos semanas.",
        "condicion_fracaso": "Reduccion <5% o tiempo +10%.",
        "guardarrail_tiempo": "Si el tiempo sube 3%, se recorta inspeccion de baja dominancia.",
        "prueba_brazos": [
            {
                "brazo": "A baseline",
                "descripcion": "Inspeccion aleatoria sin priorizacion.",
                "metrica": "Errores/100 operaciones",
                "umbral": "Referencia",
            },
            {
                "brazo": "B solo lente",
                "descripcion": "Priorizacion por dominancia sin retencion.",
                "metrica": "Errores/100 operaciones",
                "umbral": "Reduccion >=10%",
            },
            {
                "brazo": "C lente + retencion",
                "descripcion": "Priorizacion y retencion paraconsistente.",
                "metrica": "Errores/100 operaciones",
                "umbral": "Reduccion >=15% y +5 puntos sobre B",
            },
        ],
        "tamano_muestra": "200 operaciones por brazo como minimo.",
        "riesgos": ["Saturacion de registros retenidos.", "Errores introducidos a proposito."],
        "condiciones_parada": [
            "Tiempo de inspeccion +10%.",
            "Reduccion <5% tras dos semanas.",
        ],
        "parametros_a_calibrar": ["Tolerancia exacta de la banda gris con historico real."],
        "limitaciones": "Protocolo propuesto; ningun dato ha sido medido todavia.",
    }


def _entry() -> dict:
    return {
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "La retencion paraconsistente reduce errores.",
        "mecanismo": "Se retienen contradicciones menores y se prioriza por estados.",
        "prueba_discriminante": {"metrica": "errores/100 op", "umbral": "15%"},
        "incertidumbre": "No hay piloto ejecutado.",
        "critica": {
            "respuesta": {
                "objeciones": ["No define banda intermedia."],
                "respuestas_epistemologicas": {"Q8": "Prueba de tres brazos."},
            }
        },
        "evidence_mode": "creative",
        "evidence_status": "NO VALIDADO",
    }


class _InterpreteFalso:
    def __init__(self, raw: str, estado: str = "PROPUESTA") -> None:
        self.raw = raw
        self.estado = estado
        self.prompts: list[str] = []
        self.llamadas: list[dict] = []

    def completar_json(self, prompt: str, **kwargs) -> SimpleNamespace:
        self.prompts.append(prompt)
        self.llamadas.append(kwargs)
        return SimpleNamespace(
            estado=self.estado,
            error="" if self.estado == "PROPUESTA" else "external_model_timeout",
            raw_output=self.raw,
            provenance=SimpleNamespace(
                sin_secretos=lambda: {"model_requested": "stepfun/step-3.7-flash:free"}
            ),
        )


def test_prompt_incluye_propuesta_critica_y_exige_calibracion() -> None:
    prompt = build_refinement_prompt("Problema sintetico", _entry())
    assert "Problema sintetico" in prompt
    assert "La retencion paraconsistente reduce errores." in prompt
    assert "No define banda intermedia." in prompt
    assert "parametros_a_calibrar" in prompt
    assert "No inventes datos" in prompt


def test_prompt_incluye_el_cruce_seleccionado() -> None:
    """El refinamiento debe recibir los registros del cruce.

    Sin esta seccion el modelo desarrolla la propuesta sin el material
    operativo del cruce, que es justo lo que distingue a la app de una
    llamada directa al modelo base.
    """
    entry = _entry()
    entry["cross_operational_records"] = [
        {"id": "ruptura_marco_0555", "title": "Logica paraconsistente",
         "description": "tolera contradicciones."},
        {"id": "lentes_1_1700_1112", "title": "Lente de dominancia por estados",
         "description": "comparar opciones escenario por escenario."},
    ]
    prompt = build_refinement_prompt("Problema sintetico", entry)
    assert "CRUCE Y REGISTROS OPERATIVOS SELECCIONADOS" in prompt
    assert "Logica paraconsistente" in prompt
    assert "Lente de dominancia por estados" in prompt
    assert "No disponibles" not in prompt


def test_prompt_declara_cruce_ausente_cuando_no_veniene() -> None:
    prompt = build_refinement_prompt("Problema sintetico", _entry())
    assert "CRUCE Y REGISTROS OPERATIVOS SELECCIONADOS" in prompt
    assert "No disponibles" in prompt


def test_prompt_exige_mecanismo_concreto_y_no_acepta_verbos_de_gestion() -> None:
    prompt = build_refinement_prompt("Problema sintetico", _entry())
    assert "MECANISMO CONCRETO" in prompt
    assert "mecanismo_concreto" in prompt
    assert "modo_efecto" in prompt
    assert "ELIMINA|MITIGA|DETECTA" in prompt
    assert "bucle causal" in prompt
    assert "punto donde ocurre la operacion" in prompt
    assert "procedimiento de gestion" in prompt
    assert "No describas como mecanismo" in prompt


def test_prompt_rechaza_entry_sin_mecanismo() -> None:
    with pytest.raises(ValueError):
        build_refinement_prompt("p", {"hipotesis": "h"})


def test_parse_acepta_json_valido_y_anade_version() -> None:
    protocolo, errores = parse_refinement(json.dumps(_protocolo()))
    assert errores == []
    assert protocolo is not None
    assert protocolo["prompt_version"]
    assert len(protocolo["prueba_brazos"]) == 3


def test_parse_acepta_valla_markdown() -> None:
    raw = "```json\n" + json.dumps(_protocolo()) + "\n```"
    protocolo, errores = parse_refinement(raw)
    assert errores == []
    assert protocolo is not None


def test_parse_no_rellena_secciones_ausentes() -> None:
    data = _protocolo()
    del data["banda_intermedia"]
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "falta:banda_intermedia" in errores


def test_parse_exige_tres_brazos_distintos() -> None:
    data = _protocolo()
    data["prueba_brazos"] = data["prueba_brazos"][:2]
    _, errores = parse_refinement(json.dumps(data))
    assert "prueba_brazos:minimo:3" in errores

    data = _protocolo()
    data["prueba_brazos"][2]["brazo"] = data["prueba_brazos"][0]["brazo"]
    _, errores = parse_refinement(json.dumps(data))
    assert "prueba_brazos:brazos_duplicados" in errores


def test_parse_rechaza_campos_desconocidos() -> None:
    data = _protocolo()
    data["validado"] = "si"
    _, errores = parse_refinement(json.dumps(data))
    assert "campos_desconocidos:validado" in errores


def test_refinar_propuesta_usa_el_esquema_y_no_valida(monkeypatch) -> None:
    monkeypatch.setenv("CRIBA_CONSTRAINED_DECODING", "json_schema")
    interprete = _InterpreteFalso(json.dumps(_protocolo()))
    informe = refinar_propuesta(interprete, "Problema sintetico", _entry())

    assert informe["estado"] == "PROTOCOLO"
    assert informe["protocolo"] is not None
    assert interprete.llamadas[0]["schema"] is REFINEMENT_SCHEMA
    assert interprete.llamadas[0]["schema_name"] == "protocolo_operativo"

    actualizado = aplicar_protocolo(_entry(), informe)
    assert actualizado["protocolo_estado"] == "PROTOCOLO"
    assert actualizado["evidence_status"] == "NO VALIDADO"
    assert actualizado["evidence_mode"] == "creative"


def test_refinar_propuesta_pide_presupuesto_de_tiempo_amplio(monkeypatch) -> None:
    """El refinamiento pide un JSON grande: 120 s por defecto lo corta.

    Verificado en GUI real: con el timeout por defecto del interprete el
    refinamiento terminaba en "timeout" en vez de devolver el protocolo.
    """
    monkeypatch.delenv("CRIBA_REFINEMENT_TIMEOUT_S", raising=False)
    interprete = _InterpreteFalso(json.dumps(_protocolo()))
    refinar_propuesta(interprete, "Problema sintetico", _entry())
    assert interprete.llamadas[0]["timeout_s"] == 300.0

    monkeypatch.setenv("CRIBA_REFINEMENT_TIMEOUT_S", "600")
    interprete = _InterpreteFalso(json.dumps(_protocolo()))
    refinar_propuesta(interprete, "Problema sintetico", _entry())
    assert interprete.llamadas[0]["timeout_s"] == 600.0


def test_refinar_propuesta_por_defecto_no_fuerza_json_schema(monkeypatch) -> None:
    monkeypatch.delenv("CRIBA_CONSTRAINED_DECODING", raising=False)
    interprete = _InterpreteFalso(json.dumps(_protocolo()))
    refinar_propuesta(interprete, "Problema sintetico", _entry())
    assert interprete.llamadas[0]["schema"] is None


def test_refinar_propuesta_propaga_el_fallo_sin_inventar_protocolo() -> None:
    interprete = _InterpreteFalso("", estado="PENDIENTE_INTERPRETACION")
    informe = refinar_propuesta(interprete, "Problema sintetico", _entry())
    assert informe["estado"] == "PENDIENTE"
    assert informe["protocolo"] is None
    assert "timeout" in informe["error"]


def test_refinar_propuesta_no_acepta_salida_incompleta() -> None:
    data = _protocolo()
    data["prueba_brazos"] = []
    interprete = _InterpreteFalso(json.dumps(data))
    informe = refinar_propuesta(interprete, "Problema sintetico", _entry())
    assert informe["estado"] == "PENDIENTE"
    assert informe["protocolo"] is None
    assert "prueba_brazos" in informe["error"]


def test_format_proposal_renderiza_protocolo_sin_promocionar_estado() -> None:
    entry = dict(_entry())
    entry["protocolo_operativo"] = _protocolo()
    entry["protocolo_estado"] = "PROTOCOLO"
    text = format_proposal(entry)
    assert "PROTOCOLO OPERATIVO · PROTOCOLO (NO VALIDADO)" in text
    assert "Regla de éxito" in text
    assert "Prueba de brazos" in text
    assert "Parámetros a calibrar" in text
    assert "MODO CREATIVO · NO VALIDADO" in text


def test_entry_para_desarrollo_prefiere_la_visible_y_salta_pendientes() -> None:
    pendiente = {"estado_interpretacion": "PENDIENTE_INTERPRETACION"}
    valida = {"estado_interpretacion": "PROPUESTA", "mecanismo": "m"}
    win = SimpleNamespace(
        candidates=SimpleNamespace(interpretation_index=0),
    )
    sheet = {"entries": [pendiente, valida]}
    resultado = _entry_para_desarrollo(win, sheet)
    assert resultado is not None
    index, entry = resultado
    assert index == 1 and entry is valida

    win.candidates.interpretation_index = 0
    sheet = {"entries": [pendiente]}
    assert _entry_para_desarrollo(win, sheet) is None


def test_on_protocolo_done_adjunta_sin_promocionar(monkeypatch) -> None:
    from criba.ui import actions

    monkeypatch.setattr(actions, "set_chip", lambda *a, **k: None)
    monkeypatch.setattr(actions, "_activity", lambda *a, **k: None)
    entry = _entry()
    sheet = {"query": "Problema sintetico", "entries": [entry]}
    vistos: list[int] = []
    win = SimpleNamespace(
        invent_sheet=sheet,
        refs={
            "ideaSummary": SimpleNamespace(setText=lambda _t: None),
            "ideaEstadoChip": object(),
        },
        right_panel=SimpleNamespace(protocolo=SimpleNamespace(setEnabled=lambda _v: None)),
        candidates=SimpleNamespace(
            interpretation_entries=[entry],
            show_interpreter_entry=lambda i: vistos.append(i),
        ),
    )
    informe = {"estado": "PROTOCOLO", "protocolo": _protocolo(), "provenance": {}}

    actions._on_protocolo_done(win, sheet, 0, informe)

    actualizado = sheet["entries"][0]
    assert actualizado["protocolo_operativo"] == _protocolo()
    assert actualizado["evidence_status"] == "NO VALIDADO"
    assert win.candidates.interpretation_entries[0] is actualizado
    assert vistos == [0]


def test_on_protocolo_done_pendiente_no_muta_la_propuesta(monkeypatch) -> None:
    from criba.ui import actions

    errores: list[str] = []
    monkeypatch.setattr(actions, "show_error", lambda _w, _t, msg: errores.append(msg))
    monkeypatch.setattr(actions, "_activity", lambda *a, **k: None)
    sheet = {"query": "Problema sintetico", "entries": [_entry()]}
    win = SimpleNamespace(
        invent_sheet=sheet,
        refs={"ideaSummary": object(), "ideaEstadoChip": object()},
        right_panel=SimpleNamespace(protocolo=SimpleNamespace(setEnabled=lambda _v: None)),
        candidates=None,
    )

    actions._on_protocolo_done(win, sheet, 0, {"estado": "PENDIENTE", "error": "timeout"})

    assert "protocolo_operativo" not in sheet["entries"][0]
    assert errores and "timeout" in errores[0]


def test_parse_exige_diagnostico_causal() -> None:
    data = _protocolo()
    del data["fuente_error"]
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "falta:fuente_error" in errores


def test_parse_rechaza_diagnostico_causal_generico() -> None:
    data = _protocolo()
    data["fuente_error"] = "errores"
    _, errores = parse_refinement(json.dumps(data))
    assert "fuente_error:pocas_palabras" in errores

    data = _protocolo()
    data["por_que_reduce"] = data["punto_intervencion"]
    _, errores = parse_refinement(json.dumps(data))
    assert "diagnostico_causal_repetido" in errores


def test_format_proposal_muestra_fuente_y_punto_de_intervencion() -> None:
    entry = dict(_entry())
    entry["protocolo_operativo"] = _protocolo()
    entry["protocolo_estado"] = "PROTOCOLO"
    text = format_proposal(entry)
    assert "Fuente del error: La transcripcion manual" in text
    assert "Punto de intervención:" in text
    assert "Por qué reduce:" in text


def test_parse_exige_mecanismo_concreto() -> None:
    for campo in ("mecanismo_concreto", "punto_fisico", "prueba_mecanismo"):
        data = _protocolo()
        del data[campo]
        protocolo, errores = parse_refinement(json.dumps(data))
        assert protocolo is None
        assert f"falta:{campo}" in errores


def test_parse_exige_componentes_y_secuencia_operativa() -> None:
    data = _protocolo()
    data["componentes"] = data["componentes"][:1]
    _, errores = parse_refinement(json.dumps(data))
    assert "componentes:minimo:2" in errores

    data = _protocolo()
    data["secuencia_operativa"] = data["secuencia_operativa"][:1]
    _, errores = parse_refinement(json.dumps(data))
    assert "secuencia_operativa:minimo:2" in errores


def test_parse_rechaza_modo_efecto_invalido() -> None:
    data = _protocolo()
    data["modo_efecto"] = "TRANSFORMA"
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "modo_efecto:invalido" in errores


def test_parse_rechaza_mecanismo_concreto_generico() -> None:
    data = _protocolo()
    data["mecanismo_concreto"] = "priorizar mejor"
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "mecanismo_concreto:pocas_palabras" in errores

    data = _protocolo()
    data["punto_fisico"] = "aqui"
    _, errores = parse_refinement(json.dumps(data))
    assert "punto_fisico:pocas_palabras" in errores


def test_parse_rechaza_mecanismo_concreto_repetido() -> None:
    data = _protocolo()
    data["mecanismo_concreto"] = data["punto_fisico"]
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "mecanismo_concreto_repetido" in errores


def test_parse_rechaza_mecanismo_generico_aunque_sea_largo() -> None:
    """Cobertura falsa: el minimo de palabras no basta para ser concreto."""
    data = _protocolo()
    data["mecanismo_concreto"] = (
        "Se priorizan y verifican las mejoras del proceso mediante un analisis "
        "continuo que monitoriza el equipo y gestiona el seguimiento de cada "
        "revision para optimizar la gestion y asegurar la mejora aplicada."
    )
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "mecanismo_concreto:generico" in errores


def test_parse_acepta_mecanismo_concreto_con_artefacto() -> None:
    """Un verbo de gestion no invalida un mecanismo con artefacto nombrado."""
    data = _protocolo()
    data["mecanismo_concreto"] = (
        "Un sensor de doble contacto prioriza el palet: lo retiene en la "
        "salida hasta que un segundo operario revise el registro marcado como "
        "contradictorio dentro del plazo de diez minutos."
    )
    protocolo, errores = parse_refinement(json.dumps(data))
    assert errores == []
    assert protocolo is not None


def test_parse_no_rechaza_mecanismo_por_verbo_de_gestion_aislado() -> None:
    data = _protocolo()
    data["mecanismo_concreto"] = (
        "Una valvula de retencion instala un resorte que mantiene el flujo "
        "cerrado mientras el sensor comprueba la temperatura del deposito de "
        "reactivo durante toda la maniobra de purga del circuito."
    )
    protocolo, errores = parse_refinement(json.dumps(data))
    assert errores == []
    assert protocolo is not None


# --- Casos reales de la campana (T1/T2), usados como regresion ---

# Salida real de la app en T1 (multitarea_T1_informe.json): un equipo que
# recopila, valida e identifica supuestos. Cumple el esquema antiguo y no
# cumple el objetivo: no hay artefacto que actue en la operacion.
_MECANISMO_T1_REAL = (
    "Procedimiento operativo de rediseno de flujos de registro e inspeccion "
    "ejecutado por un equipo transversal (operarios de almacen, responsables "
    "de inspeccion, analista de procesos) que consiste en: 1) recopilacion de "
    "todos los supuestos declarados por el equipo de almacen sobre el proceso "
    "de registro, causas de errores y cobertura de inspeccion; 2) validacion de "
    "cada supuesto por contraste con los registros de errores de los ultimos 6 "
    "meses; 3) identificacion de los pares de tipos de registros que concentran "
    "la mayor parte de los errores de interaccion; 4) eliminacion de los pasos "
    "de inspeccion declarados redundantes."
)


def test_parse_rechaza_procedimiento_de_analisis_sin_actuador() -> None:
    """Regresion T1: un equipo que analiza no es un mecanismo accionable."""
    data = _protocolo()
    data["mecanismo_concreto"] = _MECANISMO_T1_REAL
    data["modo_efecto"] = "MITIGA"
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "mecanismo_concreto:sin_actuador" in errores


def test_parse_rechaza_eliminar_solo_con_lectura() -> None:
    """Regresion T2: un sensor que mide detecta, no elimina la fuente."""
    data = _protocolo()
    data["mecanismo_concreto"] = (
        "Procedimiento operativo de ajuste de parametros de componentes: el "
        "equipo de mantenimiento y operacion de la linea, apoyado por sensores "
        "de medicion de consumo energetico por componente, ajusta los parametros "
        "de operacion (presion, velocidad de motores) de los componentes "
        "identificados como generadores de perdidas, previo al inicio de cada "
        "turno de produccion."
    )
    data["modo_efecto"] = "ELIMINA"
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "modo_efecto:incoherente_con_mecanismo" in errores


def test_parse_acepta_mecanismo_con_actuador_que_bloquea() -> None:
    """Un actuador que retiene SI elimina: no debe ser rechazado."""
    data = _protocolo()
    data["mecanismo_concreto"] = (
        "Un sensor de doble contacto en la salida retiene fisicamente el palet "
        "cuando el registro marcado como contradictorio no ha sido revisado por "
        "un segundo operario en los diez minutos siguientes, y bloquea la "
        "salida hasta que ese segundo operario complete la revision."
    )
    data["modo_efecto"] = "ELIMINA"
    protocolo, errores = parse_refinement(json.dumps(data))
    assert errores == []
    assert protocolo is not None


def test_parse_detecta_forma_nominal_no_verbos() -> None:
    """El modelo escribe sustantivos: la deteccion no puede depender del verbo."""
    from criba.interprete.refinamiento import _es_analisis_sin_actuador

    assert _es_analisis_sin_actuador(
        "Recopilacion, validacion e identificacion de supuestos por un equipo, "
        "seguido de documentacion de los pasos a eliminar."
    )
    assert not _es_analisis_sin_actuador(
        "Un sensor de doble contacto retiene el palet en la salida del almacen "
        "hasta la revision del segundo operario, con contacto seco en la "
        "plataforma y aviso al supervisor."
    )


def test_format_proposal_renderiza_mecanismo_concreto_sin_promocionar() -> None:
    entry = dict(_entry())
    entry["protocolo_operativo"] = _protocolo()
    entry["protocolo_estado"] = "PROTOCOLO"
    text = format_proposal(entry)
    assert "MECANISMO CONCRETO" in text
    assert "Mecanismo: Un sensor de doble contacto" in text
    assert "Componentes:" in text
    assert "Secuencia operativa:" in text
    assert "Punto físico: En el pasillo de salida" in text
    assert "Modo de efecto declarado: ELIMINA" in text
    assert "Prueba del mecanismo:" in text
    assert "NO VALIDADO" in text


def test_format_proposal_no_inventa_bloque_mecanismo_si_el_protocolo_no_lo_trae() -> None:
    entry = dict(_entry())
    protocolo = _protocolo()
    for campo in (
        "mecanismo_concreto",
        "punto_fisico",
        "modo_efecto",
        "prueba_mecanismo",
        "componentes",
        "secuencia_operativa",
    ):
        del protocolo[campo]
    entry["protocolo_operativo"] = protocolo
    entry["protocolo_estado"] = "PROTOCOLO"
    text = format_proposal(entry)
    assert "MECANISMO CONCRETO" not in text
    assert "PROTOCOLO OPERATIVO" in text
