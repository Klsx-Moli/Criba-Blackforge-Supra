"""Respuestas sintéticas SOLO para ejercitar transportes y validadores en tests."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from criba.interprete.puerto import InterpretationResult


def propuesta() -> dict[str, Any]:
    return deepcopy(
        {
            "pertinencia": "PERTINENTE",
            "motivo_abstencion": "",
            "hipotesis": "Revisar registros antes de confirmar reduce segundas visitas.",
            "mecanismo": "La comprobación previa detecta campos ausentes antes de confirmar "
            "la cita, permite corregir el registro y evita retornos por errores.",
            "cadena_causal": [
                "Comprobar campos detecta ausencias.",
                "Corregir ausencias evita retornos por datos incompletos.",
            ],
            "aportacion_por_tecnica": [
                "Detectar ausencias antes de confirmar.",
                "Comunicar al usuario los campos que debe corregir.",
            ],
            "supuestos": ["Los retornos se deben a datos incompletos."],
            "evidencia_citada": [],
            "conocimiento_previo": [],
            "incertidumbre": "Se desconoce qué fracción de retornos se debe al registro.",
            "novedad": "Antecedentes sin buscar; no se afirma novedad.",
            "prueba_concreta": "Comparar cien citas por grupo y contar retornos por registro.",
            "prueba": {
                "metrica": "porcentaje de citas con retorno por registro",
                "baseline": "cien citas confirmadas sin comprobación previa",
                "umbral": "al menos 10 puntos porcentuales menos de retornos",
                "condicion_fracaso": "reducción inferior a 10 puntos porcentuales",
                "alternativa_explicativa": "Los retornos dependen de disponibilidad de citas.",
                "resultado_favorable_mecanismo": (
                    "Retornos bajan al menos 10 puntos manteniendo citas."
                ),
                "resultado_favorable_alternativa": (
                    "Los retornos no bajan al mantener disponibilidad de citas."
                ),
            },
            "comprobacion_restricciones": [],
            "ruta_desbloqueo": "desacoplar_dependencia",
        }
    )


def critica() -> dict[str, Any]:
    return {
        "pertinente": True,
        "mecanismo_especifico": True,
        "falsable": True,
        "fiel_evidencia": True,
        "restricciones_respetadas": True,
        "discrimina_alternativas": True,
        "intercambio_tecnicas_generico": False,
        "objeciones": [],
        "incertidumbre": "Esta crítica automática no es validación experimental.",
        "respuestas_epistemologicas": {
            f"Q{i}": "Eje no demostrado experimentalmente; revisar registros y alternativas "
            "antes de atribuir causalidad o afirmar novedad."
            for i in range(1, 12)
        },
    }


def resultado(**overrides: Any) -> InterpretationResult:
    """Puerto sintético con contrato completo, sin afirmar un modelo real."""
    campos = propuesta()
    campos.pop("motivo_abstencion")
    campos.update(
        estado="PROPUESTA",
        critica={
            "evaluation_status": "CRITIQUED",
            "respuesta": critica(),
            "independent_validation": False,
        },
    )
    campos.update(overrides)
    return InterpretationResult(**campos)
