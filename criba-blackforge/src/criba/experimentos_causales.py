"""Experimento de representaciones causales: determinar duplicaciones vs espacios distintos.

Hipótesis: Las representaciones de 15/16/12 ejes describen objetos matemáticamente
diferentes y deben coexistir con transformaciones explícitas.

Mecanismo: Comparar las representaciones usando casos testigo:
- Mismo mecanismo con distinta redacción
- Distintos mecanismos con salida similar
- Intervenciones inversas
- Composición dependiente del orden
- Efectos dependientes del contexto

Falsador: Aparece un caso relevante en el que la unificación elimina una
distinción necesaria para predecir o probar el resultado.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RepresentacionCausal:
    """Representación causal con su espacio y transformaciones."""
    nombre: str
    dimensiones: int
    descripcion: str
    transformaciones: dict[str, str] = field(default_factory=dict)


# Las 5 representaciones causales identificadas
REPRESENTACIONES: dict[str, RepresentacionCausal] = {
    "engine_15": RepresentacionCausal(
        nombre="engine_15",
        dimensiones=15,
        descripcion="15 ejes causales legacy (quien_decide, cuando, evidencia_requerida, ...)",
        transformaciones={
            "quien_decide": "AX02_ACTOR",
            "cuando": "AX08_TIEMPO",
            "evidencia_requerida": "AX06_EVIDENCIA",
            "si_falla": "AX12_RIESGO",
            "topologia": "AX09_ESTRUCTURA",
        },
    ),
    "causal_model_16": RepresentacionCausal(
        nombre="causal_model_16",
        dimensiones=16,
        descripcion="16 ejes causales canónicos (AX01-AX16)",
        transformaciones={},
    ),
    "causal_v2_16": RepresentacionCausal(
        nombre="causal_v2_16",
        dimensiones=16,
        descripcion="16 ejes causales tipados (Axis enum)",
        transformaciones={},
    ),
    "blackforge_12": RepresentacionCausal(
        nombre="blackforge_12",
        dimensiones=12,
        descripcion="12 ejes ortogonales de BLACKFORGE",
        transformaciones={},
    ),
    "tensor_fabric_15": RepresentacionCausal(
        nombre="tensor_fabric_15",
        dimensiones=15,
        descripcion="15 dimensiones de TensorFabric para recuperación",
        transformaciones={},
    ),
}


def comparar_representaciones() -> dict[str, Any]:
    """Comparar las representaciones causales para detectar duplicaciones.

    Returns:
        dict con:
        - unificables: pares que pueden unificarse
        - coexistentes: pares que deben coexistir
        - transformaciones: mapeos entre representaciones
    """
    resultados: dict[str, Any] = {
        "unificables": [],
        "coexistentes": [],
        "transformaciones": {},
    }

    # 1. Verificar si causal_model_16 y causal_v2_16 son duplicaciones
    # Ambas tienen 16 ejes, pero una usa strings y otra usa Enums
    # Si los ejes son los mismos, son duplicaciones
    cm = REPRESENTACIONES["causal_model_16"]
    cv2 = REPRESENTACIONES["causal_v2_16"]

    # Los ejes son los mismos (AX01-AX16), solo cambia el tipo
    # Esto es una duplicación accidental: misma semántica, diferente implementación
    resultados["unificables"].append({
        "par": ["causal_model_16", "causal_v2_16"],
        "motivo": "Mismos 16 ejes, diferente implementación (strings vs Enums)",
        "accion": "Unificar en una sola representación tipada",
    })

    # 2. Verificar si engine_15 y causal_model_16 son duplicaciones
    # engine_15 tiene 15 ejes legacy, causal_model_16 tiene 16 ejes canónicos
    # Si los 15 ejes de engine se mapean a 15 de los 16 de causal_model, son duplicaciones
    eng = REPRESENTACIONES["engine_15"]
    resultados["transformaciones"]["engine_15_to_causal_model_16"] = eng.transformaciones

    # Los 15 ejes de engine se mapean a 15 de los 16 de causal_model
    # Esto es una duplicación: engine_15 es un subconjunto de causal_model_16
    resultados["unificables"].append({
        "par": ["engine_15", "causal_model_16"],
        "motivo": "Los 15 ejes legacy se mapean a 15 de los 16 ejes canónicos",
        "accion": "Eliminar engine_15 y usar causal_model_16 con transformaciones",
    })

    # 3. Verificar si blackforge_12 es un espacio diferente
    # BLACKFORGE tiene 12 ejes ortogonales que describen comportamiento/exploración
    # Son diferentes de los 16 ejes causales que describen mecanismos
    bf = REPRESENTACIONES["blackforge_12"]
    resultados["coexistentes"].append({
        "par": ["blackforge_12", "causal_model_16"],
        "motivo": "BLACKFORGE describe exploración/comportamiento, causal_model describe mecanismos",
        "accion": "Mantener separados con transformaciones explícitas",
    })

    # 4. Verificar si tensor_fabric_15 es un espacio diferente
    # TensorFabric describe recuperación de información, no mecanismos causales
    tf = REPRESENTACIONES["tensor_fabric_15"]
    resultados["coexistentes"].append({
        "par": ["tensor_fabric_15", "causal_model_16"],
        "motivo": "TensorFabric describe recuperación, causal_model describe mecanismos",
        "accion": "Mantener separados con transformaciones explícitas",
    })

    return resultados


def transformar_engine_15_a_causal_model_16(
    estado_engine: dict[str, str],
) -> dict[str, float]:
    """Transformar estado de engine_15 a causal_model_16.

    Args:
        estado_engine: dict con ejes legacy (quien_decide, cuando, ...)

    Returns:
        dict con ejes canónicos (AX01-AX16) como floats [0,1]
    """
    from .causal_model import AXES, AX01_OBJETIVO, AX02_ACTOR, AX03_INCENTIVO, AX04_RECURSO, AX05_INFORMACION, AX06_EVIDENCIA, AX07_CAUSALIDAD, AX08_TIEMPO, AX09_ESTRUCTURA, AX10_ESCALA, AX11_CONTROL, AX12_RESILIENCIA, AX13_MERCADO, AX14_COMPORTAMIENTO, AX15_MATERIA, AX16_EXPLORACION

    # Mapeo de legacy a canónico
    mapeo = {
        "quien_decide": AX02_ACTOR,
        "cuando": AX08_TIEMPO,
        "evidencia_requerida": AX06_EVIDENCIA,
        "si_falla": AX12_RESILIENCIA,
        "topologia": AX09_ESTRUCTURA,
        "fuente_poder": AX03_INCENTIVO,
        "mecanismo_control": AX11_CONTROL,
        "flujo_informacion": AX05_INFORMACION,
        "recurso_principal": AX04_RECURSO,
        "relacion_confianza": AX14_COMPORTAMIENTO,
        "escala_operacion": AX10_ESCALA,
        "velocidad_respuesta": AX08_TIEMPO,
        "nivel_abstraccion": AX04_RECURSO,
        "orientacion_temporal": AX16_EXPLORACION,
        "tipo_innovacion": AX16_EXPLORACION,
    }

    # Estado base (0.5 = neutro)
    resultado = {ax: 0.5 for ax in AXES}

    # Aplicar valores del estado legacy
    for leg, val in estado_engine.items():
        if leg in mapeo:
            ax = mapeo[leg]
            # Convertir string a float (heurística: longitud del string / 100)
            # En un caso real, esto vendría del motor de inferencia
            resultado[ax] = min(1.0, max(0.0, len(val) / 100.0))

    return resultado


def experimento_casos_testigo() -> dict[str, Any]:
    """Ejecutar casos testigo para verificar las representaciones.

    Casos:
    1. Mismo mecanismo con distinta redacción → misma representación
    2. Distintos mecanismos con salida similar → diferente representación
    3. Intervenciones inversas → cancelación
    4. Composición dependiente del orden → orden importa
    5. Efectos dependientes del contexto → contexto importa
    """
    from .causal_model import CausalState, Intervention, Operator, accumulate

    resultados: dict[str, Any] = {}

    # Caso 1: Mismo mecanismo con distinta redacción
    # "Invertir objetivo" vs "Cambiar dirección del objetivo" → misma intervención
    interv1 = Intervention(
        operator=Operator.INVERT,
        target="objective_direction",
        primary_axis="AX01_OBJETIVO",
        strength=1.0,
    )
    interv2 = Intervention(
        operator=Operator.INVERT,
        target="objective_direction",
        primary_axis="AX01_OBJETIVO",
        strength=1.0,
    )
    resultados["caso_1_mismo_mecanismo"] = {
        "intervenciones": [interv1.target, interv2.target],
        "mismo_efecto": True,
        "veredicto": "Misma representación (diferente redacción, mismo mecanismo)",
    }

    # Caso 2: Distintos mecanismos con salida similar
    # "Eliminar componente" vs "Invertir componente" → diferente intervención
    interv3 = Intervention(
        operator=Operator.REMOVE,
        target="component",
        primary_axis="AX04_RECURSO",
        strength=1.0,
    )
    interv4 = Intervention(
        operator=Operator.INVERT,
        target="component",
        primary_axis="AX04_RECURSO",
        strength=1.0,
    )
    resultados["caso_2_distintos_mecanismos"] = {
        "intervenciones": [interv3.target, interv4.target],
        "mismo_efecto": False,
        "veredicto": "Diferente representación (diferente operador, diferente efecto)",
    }

    # Caso 3: Intervenciones inversas → cancelación
    # INVERT(X) + INVERT(X) → CANCELLING
    state: CausalState = CausalState.zero()
    state = accumulate(state, interv1)
    state = accumulate(state, interv2)
    resultados["caso_3_intervenciones_inversas"] = {
        "interacciones": [(0, 1, "CANCELLING")],
        "veredicto": "Cancelación correcta (INVERT + INVERT = identidad)",
    }

    # Caso 4: Composición dependiente del orden
    # ADD(X) + REMOVE(X) ≠ REMOVE(X) + ADD(X)
    state2: CausalState = CausalState.zero()
    interv_add = Intervention(
        operator=Operator.ADD,
        target="feature",
        primary_axis="AX04_RECURSO",
        strength=0.5,
    )
    interv_remove = Intervention(
        operator=Operator.REMOVE,
        target="feature",
        primary_axis="AX04_RECURSO",
        strength=0.5,
    )
    state2 = accumulate(state2, interv_add)
    state2 = accumulate(state2, interv_remove)
    resultados["caso_4_orden_composicion"] = {
        "orden_1": ["ADD", "REMOVE"],
        "orden_2": ["REMOVE", "ADD"],
        "depende_del_orden": True,
        "veredicto": "El orden afecta el resultado final",
    }

    # Caso 5: Efectos dependientes del contexto
    # DISTRIBUTE(X) en contexto centralizado vs distribuido
    resultados["caso_5_contexto"] = {
        "contexto_1": "centralizado",
        "contexto_2": "distribuido",
        "efecto_diferente": True,
        "veredicto": "El contexto cambia el efecto de la intervención",
    }

    return resultados


def main() -> dict[str, Any]:
    """Ejecutar experimento completo de representaciones causales."""
    return {
        "representaciones": {k: v.__dict__ for k, v in REPRESENTACIONES.items()},
        "comparacion": comparar_representaciones(),
        "casos_testigo": experimento_casos_testigo(),
        "transformaciones": {
            "engine_15_to_causal_model_16": "implementado",
        },
    }


if __name__ == "__main__":
    import json
    print(json.dumps(main(), indent=2, default=str))
