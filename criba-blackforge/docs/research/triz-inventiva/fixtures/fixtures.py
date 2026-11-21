"""Fixtures deterministas para la campaña TRIZ+Koestler (IMP-03/IMP-04 aislados).

EVIDENCIA: datos sintéticos etiquetados. NO son muestras científicas ni lecturas
de libros. Sirven para ejercitar el validador y la cadena de intérprete en
aislamiento, sin servicios, red ni modelos.
"""
from __future__ import annotations

# Ficha AC-06 VALIDA: transferencia inventiva con fuente, mecanismo, ruptura y prueba discriminante.
FICHA_VALIDA = {
    "ficha_id": "FIX-AC06-01",
    "source_id": "SRC03",
    "work_id": "Gadd-TRIZ-for-Engineers-2011",
    "claim_id": "FIX-CLAIM-01",
    "operator_id": "OP-TRIZ-02",
    "candidate_id": None,
    "content": {
        "problema": "Reducir coste de revision sin perder restricciones obligatorias.",
        "restricciones": ["revisar 100% de salidas criticas", "sin datos falsos"],
        "funcion": "detectar defectos antes de liberar",
        "contradiccion": "mas revision aumenta cobertura y coste",
        "operacion": "revision barata continua + revision profunda solo ante disparador justificable",
        "recursos": ["logs ya persistidos", "metadatos de revision previa"],
        "mecanismo": "un disparador basado en riesgo concentra la revision profunda donde el coste de fallo es mayor",
        "precondiciones": ["el disparador debe ser observable", "los logs deben conservar lineage"],
        "supuestos": ["los logs previos son fiables"],
        "contraejemplo": "omitir revision obligatoria para aparentar menor coste",
    },
    "cross_domain": {
        "origen": "control de presion en sistema hidraulico",
        "destino": "control de revision en pipeline de software",
        "puente": "umbral que dispara accion correctora",
        "correspondencias": [
            {"origen": "sensor presion", "destino": "detector de riesgo", "soporte": "aportado"},
            {"origen": "valvula al limite", "destino": "revision profunda", "soporte": "inferido"},
        ],
        "relacion_transferida": "separar exigencias por condicion (OP-TRIZ-02)",
    },
    "limits": {
        "precondiciones": ["logs con lineage"],
        "supuestos": ["fiableidad de logs"],
        "contraejemplo": "omitir revision obligatoria",
        "ruptura": "si el disparador no es observable, la separacion cambia el requisito obligatorio",
        "abstencion": "si disponibilidad de logs es UNKNOWN, no afirmar factibilidad",
    },
    "discrimination": {
        "rival": "la mejora proviene de mas documentacion, no de la transferencia",
        "observable": "omisiones de revision obligatoria y coste total",
        "prediccion_mecanismo": "omisiones cercanas a cero con coste menor que politica de referencia",
        "prediccion_rival": "omisiones sin cambio de coste",
        "regla": "si omisiones>0 o coste mayor, no atribuir al mecanismo",
        "fallo": "omisiones>0 bajo disparador",
    },
    "provenance": {
        "localizador": "https://onlinelibrary.wiley.com/doi/book/10.1002/9780470684320",
        "version": "2011",
        "acceso_real": "PUBLISHER_DESCRIPTION_AND_CONTENTS",
        "derechos": "NOT_VERIFIED: enlazar y parafrasear; no redistribuir el original",
        "lineage": "adaptacion original del paquete, no cita literal",
        "seleccion": "manual por relevancia con SRC03",
    },
    "states": {
        "workflow": "PREPARED",
        "execution": "NOT_EXECUTED",
        "scientific_validation": "NOT_VALIDATED_FOR_CRIBA",
    },
}

# Ficha AC-06 INVALIDA: ruptura = 0 (UNKNOWN != 0) y predicciones iguales (no discrimina).
FICHA_INVALIDA_NO_RIVAL = {
    "ficha_id": "FIX-AC06-BAD1",
    "source_id": "SRC03",
    "content": {
        "operacion": "revisar todo",
        "mecanismo": "revisar todo detecta todo",
    },
    "limits": {
        "ruptura": 0,
    },
    "discrimination": {
        "rival": "la mejora proviene de mas documentacion, no de la transferencia",
        "prediccion_mecanismo": "omisiones cercanas a cero",
        "prediccion_rival": "omisiones cercanas a cero",  # iguales: no discrimina
    },
}

# Ficha AC-06 INVALIDA: content sin operacion/mecanismo y source_id UNKNOWN.
FICHA_INVALIDA_MISSING = {
    "ficha_id": "FIX-AC06-BAD2",
    "source_id": "UNKNOWN",
    "content": {},
    "discrimination": {
        "rival": "rival presente",
        "prediccion_mecanismo": "x",
        "prediccion_rival": "y",
    },
}

# Operador de laboratorio (adaptacion original, no cita). Ejemplo utilizable.
OPERADOR_VALIDO = {
    "operator_id": "OP-TRIZ-02",
    "title": "Separar exigencias por condicion",
    "origin": "ORIGINAL_ADAPTATION_IN_THIS_PACKAGE_NOT_AUTHOR_QUOTATION",
    "source_ids": ["SRC03"],
    "required_inputs": ["contradiccion", "restricciones"],
    "transformation": "Identificar si exigencias opuestas pueden satisfacerse en tiempos, partes o condiciones distintos sin violar restricciones.",
    "output_requirements": "condiciones, regla de separacion y mecanismo",
    "abstention_or_limit": "Abstenerse si la separacion cambia el requisito obligatorio o no hay condicion comprobable.",
    "own_example_not_observed": "Revision barata siempre y revision profunda solo ante disparador justificable.",
    "counterexample": "Omitir revision obligatoria para aparentar menor coste.",
    "discriminating_test_proposal": "Contrastar omisiones y coste frente a politica de referencia.",
    "execution_status": "NOT_EXECUTED",
    "validation_status": "NOT_VALIDATED",
    "production_binding": "NOT_WIRED",
    "rights": "Redaccion original; no reproduccion de tablas o capitulos.",
}

# Operador INVALIDO: execution_status no es NOT_EXECUTED (debe ser rechazado).
OPERADOR_INVALIDO = dict(OPERADOR_VALIDO)
OPERADOR_INVALIDO["execution_status"] = "EXECUTED"

# Entrada de intérprete realista (IMP-03): construida sobre el contrato existente.
# Usa campos compatibles con interprete/contrato.py: PROBLEMA, DOMINIO, CRUCE,
# EVIDENCIA LOCAL PERTINENTE, BLOQUEO IDENTIFICADO.
INTERPRETER_INPUT_VALIDO = {
    "PROBLEMA": "Reducir coste de revision sin perder restricciones obligatorias.",
    "DOMINIO": {
        "eje": "methodology",
        "sector": "calidad",
    },
    "CRUCE": {
        "operator_id": "OP-TRIZ-02",
        "operator_title": "Separar exigencias por condicion",
        "origen": "control de presion hidraulica",
        "destino": "pipeline de revision de software",
        "correspondencias": [
            {"origen": "sensor presion", "destino": "detector de riesgo", "soporte": "aportado"},
            {"origen": "valvula al limite", "destino": "revision profunda", "soporte": "inferido"},
        ],
        "relacion_transferida": "separar exigencias por condicion",
        "mecanismo": "un disparador basado en riesgo concentra la revision profunda donde el coste de fallo es mayor",
        "supuestos": ["logs previos fiables"],
        "ruptura": "si el disparador no es observable, la separacion cambia el requisito obligatorio",
    },
    "BLOQUEO IDENTIFICADO": {
        "restricciones_obligatorias": [
            "revisar 100% de salidas criticas",
            "no generar datos falsos",
        ]
    },
    "EVIDENCIA LOCAL PERTINENTE": [
        {
            "source_id": "SRC03",
            "reading_level": "PUBLISHER_DESCRIPTION_AND_CONTENTS",
            "retrieved_at": "2026-10-28",
            "acceso_real": "PUBLISHER_DESCRIPTION_AND_CONTENTS",
            "resumen": "TRIZ para ingenieros: contradicciones, recursos, funcion, idealidad, ARIZ.",
        }
    ],
    "CONTENCION_DECLARADA": "DESCONOCIDA",
}
