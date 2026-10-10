"""Alineación schema(grammar) <-> validar_propuesta (validador).

El schema fija la FORMA; el validador fija el CONTENIDO. Este test exige que
para cada clave obligatoria, quitarla falle en AMBOS; y documenta las
discrepancias esperadas (el schema acepta algo que el validador rechaza).

Solo usa jsonschema como dependencia de test. No cambia umbrales ni contratos.
"""

from __future__ import annotations

import json
import re

import jsonschema
import pytest

from criba.interprete.contrato import (
    schema_critica,
    schema_propuesta,
    validar_critica,
    validar_propuesta,
)

IDEA = {"method1": "Poka-Yoke", "method2": "Retroalimentación", "title": "t"}
EVIDENCIA = [{"title": "Registro de visitas", "abstract": "30 de 100 se repiten."}]

PROPUESTA_VALIDA = {
    "pertinencia": "PERTINENTE",
    "hipotesis": "Revisar registros antes de confirmar reduce segundas visitas.",
    "mecanismo": (
        "La comprobación previa detecta campos ausentes antes de confirmar la cita "
        "y evita retornos por errores."
    ),
    "cadena_causal": ["Comprobar campos detecta ausencias.", "Corregir evita retornos."],
    "aportacion_por_tecnica": ["Detectar ausencias.", "Comunicar campos a corregir."],
    "supuestos": ["Los retornos se deben a datos incompletos."],
    "evidencia_citada": [1],
    "conocimiento_previo": [],
    "incertidumbre": "Se desconoce la fracción de retornos por registro.",
    "novedad": "Antecedentes sin buscar; no se afirma novedad.",
    "prueba_concreta": "Comparar cien citas por grupo.",
    "prueba": {
        "metrica": "porcentaje de retornos",
        "baseline": "cien citas sin comprobación",
        "umbral": "al menos 10 puntos menos",
        "condicion_fracaso": "reducción inferior a 10 puntos",
        "alternativa_explicativa": "Los retornos dependen de disponibilidad.",
        "resultado_favorable_mecanismo": "Retornos bajan al menos 10 puntos.",
        "resultado_favorable_alternativa": "Los retornos no bajan.",
    },
    "comprobacion_restricciones": [],
    "ruta_desbloqueo": "desacoplar_dependencia",
}

CRITICA_VALIDA = {
    "pertinente": True,
    "mecanismo_especifico": True,
    "falsable": True,
    "fiel_evidencia": True,
    "restricciones_respetadas": True,
    "discrimina_alternativas": True,
    "intercambio_tecnicas_generico": False,
    "objeciones": [],
    "incertidumbre": "Límites de esta crítica automática.",
    "respuestas_epistemologicas": {
        f"Q{i}": "Eje no demostrado; revisar antes de afirmar." for i in range(1, 12)
    },
}

REQUIRED_PROPUESTA = [
    "pertinencia",
    "hipotesis",
    "cadena_causal",
    "mecanismo",
    "aportacion_por_tecnica",
    "supuestos",
    "evidencia_citada",
    "conocimiento_previo",
    "incertidumbre",
    "novedad",
    "prueba_concreta",
    "prueba",
    "comprobacion_restricciones",
]


def _valida_schema(schema: dict, instance: dict) -> bool:
    try:
        jsonschema.validate(instance, schema)
        return True
    except jsonschema.ValidationError:
        return False


def test_golden_aceptada_por_schema_y_validador() -> None:
    schema = schema_propuesta(IDEA, EVIDENCIA)
    assert _valida_schema(schema, PROPUESTA_VALIDA), "el schema rechaza una propuesta golden"
    assert validar_propuesta(PROPUESTA_VALIDA, IDEA, EVIDENCIA) == [], (
        "el validador rechaza una propuesta golden"
    )


@pytest.mark.parametrize("clave", REQUIRED_PROPUESTA)
def test_quitar_required_falla_en_ambos(clave: str) -> None:
    schema = schema_propuesta(IDEA, EVIDENCIA)
    sin_clave = {k: v for k, v in PROPUESTA_VALIDA.items() if k != clave}
    assert not _valida_schema(schema, sin_clave), f"el schema aceptó sin {clave}"
    assert validar_propuesta(sin_clave, IDEA, EVIDENCIA), f"el validador aceptó sin {clave}"


def test_score_rechazado_en_ambos() -> None:
    schema = schema_propuesta(IDEA, EVIDENCIA)
    con_score = {**PROPUESTA_VALIDA, "score": 0.9}
    assert not _valida_schema(schema, con_score), "additionalProperties debería rechazar score"
    assert validar_propuesta(con_score, IDEA, EVIDENCIA), "el validador debería rechazar score"


def test_cita_fuera_de_rango_rechazada_en_ambos() -> None:
    schema = schema_propuesta(IDEA, EVIDENCIA)
    fuera = {**PROPUESTA_VALIDA, "evidencia_citada": [5]}
    assert not _valida_schema(schema, fuera), "maximum debería rechazar índice 5"
    assert validar_propuesta(fuera, IDEA, EVIDENCIA), "el validador debería rechazar índice 5"


def test_tres_aportaciones_rechazadas_en_ambos() -> None:
    schema = schema_propuesta(IDEA, EVIDENCIA)
    tres = {**PROPUESTA_VALIDA, "aportacion_por_tecnica": ["a", "b", "c"]}
    assert not _valida_schema(schema, tres), "maxItems=2 debería rechazar tres aportaciones"
    assert validar_propuesta(tres, IDEA, EVIDENCIA), "el validador debería rechazar tres"


def test_estado_viola_lo_acepta_schema_pero_lo_rechaza_validador() -> None:
    """Discrepancia documentada: el schema permite VIOLA; el validador exige CUMPLE."""
    idea = {
        "method1": "Replicación",
        "method2": "Mensajería",
        "bloqueo": {"restricciones_obligatorias": ["No transmitir datos."]},
    }
    schema = schema_propuesta(idea, [])
    con_viola = {
        **PROPUESTA_VALIDA,
        "evidencia_citada": [],
        "comprobacion_restricciones": [
            {"restriccion": "No transmitir datos.", "estado": "VIOLA", "justificacion": "x"}
        ],
    }
    assert _valida_schema(schema, con_viola), "el schema debe permitir el enum VIOLA"
    assert validar_propuesta(con_viola, idea, []), "el validador debe rechazar VIOLA"


def test_mecanismo_repite_tecnica_lo_acepta_schema_pero_lo_rechaza_validador() -> None:
    """Discrepancia documentada: el schema no puede codificar esta regla de contenido."""
    schema = schema_propuesta(IDEA, EVIDENCIA)
    repite = {**PROPUESTA_VALIDA, "mecanismo": "Poka-Yoke reduce los errores de registro."}
    assert _valida_schema(schema, repite), "el schema debe aceptar el texto"
    assert validar_propuesta(repite, IDEA, EVIDENCIA), "el validador debe rechazar la repetición"


def test_critica_booleans_son_type_boolean_no_const() -> None:
    schema = schema_critica()
    for campo in (
        "pertinente",
        "mecanismo_especifico",
        "falsable",
        "fiel_evidencia",
        "restricciones_respetadas",
        "discrimina_alternativas",
        "intercambio_tecnicas_generico",
    ):
        assert schema["properties"][campo] == {"type": "boolean"}, (
            f"{campo} debe ser type boolean, nunca const"
        )


def test_critica_golden_aceptada() -> None:
    schema = schema_critica()
    assert _valida_schema(schema, CRITICA_VALIDA), "el schema de crítica rechaza la golden"
    assert validar_critica(CRITICA_VALIDA) == [], "el validador rechaza la crítica golden"


def test_critica_false_es_aceptada_por_schema() -> None:
    """La grammar no debe forzar la aprobación: false debe pasar el schema."""
    schema = schema_critica()
    rechazo = {**CRITICA_VALIDA, "pertinente": False}
    assert _valida_schema(schema, rechazo), "el schema no debe forzar true"
    assert validar_critica(rechazo), "el validador sí debe rechazar pertinente=False"


def test_schema_no_usa_ref_externos() -> None:
    """$ref internos (a #/$defs) son válidos en llama-server; los externos no.

    04A exigía no usar $ref porque los EXTERNOS rompen llama-server. 04B
    introduce $ref planos INTERNOS, verificados por el canario. Lo que se
    prohíbe sigue siendo el $ref externo (que apunta fuera del documento).
    """
    for schema in (schema_propuesta(IDEA, EVIDENCIA), schema_critica()):
        serializado = json.dumps(schema)
        for ref in re.findall(r'"\$ref":\s*"([^"]+)"', serializado):
            assert ref.startswith("#/"), f"$ref externo no soportado por llama-server: {ref}"
