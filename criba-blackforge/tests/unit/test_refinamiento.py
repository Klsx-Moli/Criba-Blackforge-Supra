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
    index, entry = _entry_para_desarrollo(win, sheet)
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

def test_parse_rechaza_coercion_de_tipos_y_excesos_del_esquema() -> None:
    """Sentinels: un JSON parseable no debe saltarse REFINEMENT_SCHEMA."""
    casos = [
        ("resumen", 7, "resumen:tipo_invalido"),
        ("resumen", False, "resumen:tipo_invalido"),
        ("resumen", "x" * 801, "resumen:maximo:800"),
        ("riesgos", ["Riesgo real", 42], "riesgos[1]:tipo_invalido"),
        ("riesgos", ["r"] * 11, "riesgos:maximo:10"),
        (
            "definiciones_operativas",
            ["x" * 501, "Definicion dos", "Definicion tres"],
            "definiciones_operativas[0]:maximo:500",
        ),
    ]
    for campo, valor, error_esperado in casos:
        data = _protocolo()
        data[campo] = valor
        protocolo, errores = parse_refinement(json.dumps(data))
        assert protocolo is None, (campo, valor)
        assert error_esperado in errores, (campo, errores)


def test_parse_rechaza_brazos_con_campos_extra_y_tipo_incorrecto() -> None:
    data = _protocolo()
    data["prueba_brazos"][0]["verificado"] = True
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "prueba_brazos[0]:campos_desconocidos:verificado" in errores

    data = _protocolo()
    data["prueba_brazos"][0]["umbral"] = 0.9
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "prueba_brazos[0].umbral:tipo_invalido" in errores

    data = _protocolo()
    data["prueba_brazos"][0]["descripcion"] = "x" * 601
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "prueba_brazos[0].descripcion:maximo:600" in errores

    data = _protocolo()
    data["prueba_brazos"].extend([dict(data["prueba_brazos"][0])] * 2)
    protocolo, errores = parse_refinement(json.dumps(data))
    assert protocolo is None
    assert "prueba_brazos:maximo:4" in errores


def test_parse_admite_lista_a_calibrar_vacia_y_limites_validos() -> None:
    data = _protocolo()
    data["parametros_a_calibrar"] = []
    data["resumen"] = "r" * 800
    protocolo, errores = parse_refinement(json.dumps(data))
    assert errores == []
    assert protocolo is not None
    assert protocolo["parametros_a_calibrar"] == []
