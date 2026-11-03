"""Refinamiento operativo de una propuesta creativa.

El motor genera propuestas y el intérprete las desarrolla. Una propuesta
creativa puede ser novedosa y, aun así, no ser accionable: no define estados,
tolerancias, regla de decisión, guardarraíl de tiempo ni cómo aislar el efecto
atención. Este módulo pide una segunda pasada al mismo intérprete para producir
un protocolo operativo explícito y falsable.

Reglas de honestidad:

- El refinamiento NO valida nada. El estado de evidencia del entry no cambia y
  el protocolo se guarda como propuesta, no como resultado.
- Los parámetros que el modelo no pueda derivar de datos observados deben
  declararse en ``parametros_a_calibrar``. No se acepta precisión inventada.
- Si la salida no cumple el contrato, el resultado es PENDIENTE con el motivo
  real. Nunca se rellena una sección ausente para que el esquema pase.
"""

from __future__ import annotations

import json
from typing import Any

PROMPT_VERSION_REFINAMIENTO = "refinar-operativo-v1"

_SYSTEM_REFINAMIENTO = (
    "Eres un ingeniero de operaciones. Recibes una propuesta creativa y su "
    "crítica. Produces un protocolo operativo explícito, medible y falsable. "
    "No afirmas que la propuesta funciona: describes cómo probarla. No inventas "
    "datos observados; los parámetros sin evidencia se declaran a calibrar. "
    "Respondes solo con el JSON del esquema."
)

_CAMPOS_TEXTO = (
    "resumen",
    "criterio_dominancia",
    "asignacion_presupuesto",
    "metrica_principal",
    "metrica_secundaria",
    "regla_exito",
    "banda_intermedia",
    "condicion_fracaso",
    "guardarrail_tiempo",
    "tamano_muestra",
    "limitaciones",
)

_LISTAS_MINIMAS = {
    "definiciones_operativas": 3,
    "riesgos": 2,
    "condiciones_parada": 2,
    "parametros_a_calibrar": 0,
    "prueba_brazos": 3,
}

REFINEMENT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "resumen",
        "definiciones_operativas",
        "criterio_dominancia",
        "asignacion_presupuesto",
        "metrica_principal",
        "metrica_secundaria",
        "regla_exito",
        "banda_intermedia",
        "condicion_fracaso",
        "guardarrail_tiempo",
        "prueba_brazos",
        "tamano_muestra",
        "riesgos",
        "condiciones_parada",
        "parametros_a_calibrar",
        "limitaciones",
    ],
    "properties": {
        "resumen": {"type": "string", "minLength": 1, "maxLength": 800},
        "definiciones_operativas": {
            "type": "array",
            "minItems": 3,
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "criterio_dominancia": {"type": "string", "minLength": 1, "maxLength": 900},
        "asignacion_presupuesto": {"type": "string", "minLength": 1, "maxLength": 900},
        "metrica_principal": {"type": "string", "minLength": 1, "maxLength": 400},
        "metrica_secundaria": {"type": "string", "minLength": 1, "maxLength": 400},
        "regla_exito": {"type": "string", "minLength": 1, "maxLength": 600},
        "banda_intermedia": {"type": "string", "minLength": 1, "maxLength": 900},
        "condicion_fracaso": {"type": "string", "minLength": 1, "maxLength": 600},
        "guardarrail_tiempo": {"type": "string", "minLength": 1, "maxLength": 900},
        "prueba_brazos": {
            "type": "array",
            "minItems": 3,
            "maxItems": 4,
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["brazo", "descripcion", "metrica", "umbral"],
                "properties": {
                    "brazo": {"type": "string", "minLength": 1, "maxLength": 120},
                    "descripcion": {"type": "string", "minLength": 1, "maxLength": 600},
                    "metrica": {"type": "string", "minLength": 1, "maxLength": 300},
                    "umbral": {"type": "string", "minLength": 1, "maxLength": 300},
                },
            },
        },
        "tamano_muestra": {"type": "string", "minLength": 1, "maxLength": 600},
        "riesgos": {
            "type": "array",
            "minItems": 2,
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "condiciones_parada": {
            "type": "array",
            "minItems": 2,
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 500},
        },
        "parametros_a_calibrar": {
            "type": "array",
            "minItems": 0,
            "maxItems": 10,
            "items": {"type": "string", "minLength": 1, "maxLength": 400},
        },
        "limitaciones": {"type": "string", "minLength": 1, "maxLength": 900},
    },
}


def _texto(valor: Any) -> str:
    return str(valor or "").strip()


def _lineas(valor: Any) -> list[str]:
    if isinstance(valor, str):
        valor = [valor]
    if not isinstance(valor, (list, tuple)):
        return []
    return [linea for linea in (_texto(item) for item in valor) if linea]


def build_refinement_prompt(query: str, entry: dict[str, Any]) -> str:
    """Prompt determinista a partir de la propuesta y su crítica.

    El orden de los campos es fijo para que el hash del prompt sea reproducible.
    """
    hipotesis = _texto(entry.get("hipotesis"))
    mecanismo = _texto(entry.get("mecanismo"))
    if not hipotesis or not mecanismo:
        raise ValueError("propuesta_sin_hipotesis_o_mecanismo")

    prueba = entry.get("prueba_discriminante") or entry.get("prueba") or {}
    if isinstance(prueba, dict):
        prueba_txt = json.dumps(prueba, ensure_ascii=False, sort_keys=True)
    else:
        prueba_txt = _texto(prueba)

    critica = entry.get("critica") if isinstance(entry.get("critica"), dict) else {}
    respuesta = critica.get("respuesta") if isinstance(critica.get("respuesta"), dict) else {}
    objeciones = _lineas(respuesta.get("objeciones"))
    criterios = respuesta.get("respuestas_epistemologicas")
    criterios_txt = (
        json.dumps(criterios, ensure_ascii=False, sort_keys=True)
        if isinstance(criterios, dict)
        else ""
    )
    incertidumbre = _texto(entry.get("incertidumbre"))

    return (
        "PROBLEMA\n"
        f"{_texto(query)}\n\n"
        "PROPUESTA CREATIVA (no validada)\n"
        f"Hipotesis: {hipotesis}\n"
        f"Mecanismo: {mecanismo}\n"
        f"Prueba declarada: {prueba_txt}\n"
        f"Incertidumbre: {incertidumbre}\n\n"
        "CRITICA RECIBIDA\n"
        f"Objeciones: {json.dumps(objeciones, ensure_ascii=False)}\n"
        f"Criterios operativos: {criterios_txt}\n\n"
        "TAREA\n"
        "Convierte la propuesta en un protocolo operativo ejecutable. Exige:\n"
        "1. Definiciones operativas con tolerancias numericas: que cuenta como "
        "contradiccion menor y mayor, y que se retiene, descarta o pone en cuarentena.\n"
        "2. Dominancia por estados: criterio calculado con frecuencias observadas "
        "(por ejemplo, Pareto 80/20), no con probabilidades inventadas, y como se "
        "asigna el presupuesto de inspeccion.\n"
        "3. Metrica principal y secundaria, regla de exito, regla explicita para "
        "la banda intermedia y condicion de fracaso.\n"
        "4. Guardarrail de tiempo con umbral de activacion y recorte concreto.\n"
        "5. Prueba de al menos tres brazos que aísle el efecto atencion: baseline, "
        "solo priorizacion y priorizacion mas retencion.\n"
        "6. Tamano de muestra y analisis previsto, aunque sea aproximado.\n"
        "7. Riesgos y condiciones de parada inmediata.\n"
        "8. Todo parametro que no puedas derivar del enunciado o de datos "
        "observados debe aparecer en parametros_a_calibrar. No inventes datos "
        "historicos ni presentes el protocolo como validado.\n"
        "Devuelve solo el JSON del esquema.\n\n"
        "ESQUEMA EXACTO (claves planas, sin anidar; no añadas ni renombres claves)\n"
        '{"resumen": "texto", '
        '"definiciones_operativas": ["texto", "texto", "texto"], '
        '"criterio_dominancia": "texto", '
        '"asignacion_presupuesto": "texto", '
        '"metrica_principal": "texto", '
        '"metrica_secundaria": "texto", '
        '"regla_exito": "texto", '
        '"banda_intermedia": "texto", '
        '"condicion_fracaso": "texto", '
        '"guardarrail_tiempo": "texto", '
        '"prueba_brazos": [{"brazo": "texto", "descripcion": "texto", '
        '"metrica": "texto", "umbral": "texto"}, '
        '{"brazo": "texto", "descripcion": "texto", "metrica": "texto", "umbral": "texto"}, '
        '{"brazo": "texto", "descripcion": "texto", "metrica": "texto", "umbral": "texto"}], '
        '"tamano_muestra": "texto", '
        '"riesgos": ["texto", "texto"], '
        '"condiciones_parada": ["texto", "texto"], '
        '"parametros_a_calibrar": ["texto"], '
        '"limitaciones": "texto"}'
    )


def parse_refinement(raw: str) -> tuple[dict[str, Any] | None, list[str]]:
    """Extrae y valida el protocolo. Devuelve (protocolo, errores).

    Acepta JSON envuelto en vallas de markdown, pero no rellena campos.
    """
    texto = _texto(raw)
    if not texto:
        return None, ["respuesta_vacia"]
    if texto.startswith("```"):
        texto = texto.strip("`")
        if texto.lower().startswith("json"):
            texto = texto[4:]
        texto = texto.strip()
    inicio = texto.find("{")
    fin = texto.rfind("}")
    if inicio < 0 or fin <= inicio:
        return None, ["json_no_encontrado"]
    try:
        data = json.loads(texto[inicio : fin + 1])
    except json.JSONDecodeError as exc:
        return None, [f"json_invalido:{exc.msg}"]
    return validar_protocolo(data)


def validar_protocolo(data: Any) -> tuple[dict[str, Any] | None, list[str]]:
    """Valida el contrato del protocolo sin completar huecos."""
    if not isinstance(data, dict):
        return None, ["protocolo_no_es_objeto"]
    errores: list[str] = []
    protocolo: dict[str, Any] = {}

    desconocidas = sorted(set(data) - set(REFINEMENT_SCHEMA["properties"]))
    if desconocidas:
        errores.append("campos_desconocidos:" + ",".join(desconocidas))

    for campo in _CAMPOS_TEXTO:
        valor = _texto(data.get(campo))
        if not valor:
            errores.append(f"falta:{campo}")
        protocolo[campo] = valor

    for campo, minimo in _LISTAS_MINIMAS.items():
        valor = data.get(campo)
        if campo == "prueba_brazos":
            brazos: list[dict[str, str]] = []
            if not isinstance(valor, list):
                errores.append(f"falta:{campo}")
            else:
                for indice, brazo in enumerate(valor):
                    if not isinstance(brazo, dict):
                        errores.append(f"{campo}[{indice}]:no_es_objeto")
                        continue
                    limpio = {
                        clave: _texto(brazo.get(clave))
                        for clave in ("brazo", "descripcion", "metrica", "umbral")
                    }
                    faltan = [clave for clave, texto in limpio.items() if not texto]
                    if faltan:
                        errores.append(f"{campo}[{indice}]:falta:" + ",".join(faltan))
                        continue
                    brazos.append(limpio)
                if len(brazos) < minimo:
                    errores.append(f"{campo}:minimo:{minimo}")
                etiquetas = {brazo["brazo"].lower() for brazo in brazos}
                if len(etiquetas) < len(brazos):
                    errores.append(f"{campo}:brazos_duplicados")
            protocolo[campo] = brazos
            continue

        lista = _lineas(valor)
        if not isinstance(valor, list):
            errores.append(f"falta:{campo}")
        elif len(lista) < minimo:
            errores.append(f"{campo}:minimo:{minimo}")
        protocolo[campo] = lista

    if errores:
        return None, errores
    protocolo["prompt_version"] = PROMPT_VERSION_REFINAMIENTO
    return protocolo, []


def refinar_propuesta(
    interprete: Any, query: str, entry: dict[str, Any]
) -> dict[str, Any]:
    """Ejecuta el refinamiento con el intérprete real.

    Devuelve un informe serializable. Nunca lanza por un fallo del modelo y
    nunca promueve el estado de evidencia.

    La decodificación restringida es opt-in, igual que en ``proponer``: algunos
    endpoints aceptan ``json_schema`` y otros lo ignoran o se atascan. Por
    defecto se pide ``json_object`` y el contrato se valida aquí.
    """
    try:
        prompt = build_refinement_prompt(query, entry)
    except ValueError as exc:
        return {"estado": "PENDIENTE", "error": str(exc), "protocolo": None}

    import os

    restringido = os.getenv("CRIBA_CONSTRAINED_DECODING", "").strip().lower() in (
        "json_schema",
        "1",
        "true",
    )
    try:
        max_tokens = int(os.getenv("CRIBA_REFINEMENT_MAX_TOKENS", "8192"))
    except ValueError:
        max_tokens = 8192

    transporte = interprete.completar_json(
        prompt,
        schema=REFINEMENT_SCHEMA if restringido else None,
        schema_name="protocolo_operativo",
        max_tokens=max_tokens,
        temperature=0.2,
    )
    provenance = (
        transporte.provenance.sin_secretos() if transporte.provenance else {}
    )
    if str(getattr(transporte, "estado", "")) == "PENDIENTE_INTERPRETACION":
        return {
            "estado": "PENDIENTE",
            "error": str(getattr(transporte, "error", "") or "refinamiento_pendiente"),
            "provenance": provenance,
            "protocolo": None,
        }

    protocolo, errores = parse_refinement(str(getattr(transporte, "raw_output", "")))
    if errores:
        return {
            "estado": "PENDIENTE",
            "error": "validacion:" + "; ".join(errores),
            "provenance": provenance,
            "protocolo": None,
        }
    return {
        "estado": "PROTOCOLO",
        "error": "",
        "provenance": provenance,
        "protocolo": protocolo,
    }


def aplicar_protocolo(entry: dict[str, Any], informe: dict[str, Any]) -> dict[str, Any]:
    """Adjunta el protocolo a una copia del entry sin tocar el estado de evidencia."""
    item = dict(entry)
    item["protocolo_operativo"] = informe.get("protocolo")
    item["protocolo_estado"] = str(informe.get("estado") or "PENDIENTE")
    item["protocolo_error"] = str(informe.get("error") or "")
    item["protocolo_provenance"] = informe.get("provenance") or {}
    return item
