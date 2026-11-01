from __future__ import annotations

from criba.interprete.diagnostico import CRITIQUE_REJECTED
from criba.ui.proposal_view import format_proposal


def test_propuesta_rechazada_muestra_objeciones_y_no_pendiente() -> None:
    entry = {
        "estado_interpretacion": "PENDIENTE_INTERPRETACION",
        "interpretacion_error": "critica_rechazada:critica.objeciones",
        "interpretacion_diagnostico": {
            "error_code": CRITIQUE_REJECTED,
            "phase": "critica",
            "retryable": False,
            "next_action": "Revisa las objeciones y genera otra propuesta.",
        },
        "critica": {
            "evaluation_status": "REJECTED",
            "respuesta": {
                "objeciones": [
                    "La evidencia no sostiene la causalidad.",
                    "No se declaran restricciones de contención.",
                ]
            },
        },
    }

    text = format_proposal(entry)

    assert "PROPUESTA RECHAZADA" in text
    assert "PENDIENTE DE INTERPRETACIÓN" not in text
    assert "CRITIQUE_REJECTED" in text
    assert "OBJECIONES" in text
    assert "La evidencia no sostiene la causalidad." in text


def test_propuesta_admitida_muestra_observaciones_de_critica() -> None:
    entry = {
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "El flujo se desacopla.",
        "mecanismo": "Una compuerta regula el paso.",
        "critica": {
            "evaluation_status": "CRITIQUED",
            "respuesta": {"objeciones": ["Falta medir el coste de la compuerta."]},
        },
    }

    text = format_proposal(entry)

    assert "OBSERVACIONES DE LA CRÍTICA" in text
    assert "Falta medir el coste de la compuerta." in text


def test_pendiente_sin_rechazo_conserva_etiqueta_y_diagnostico() -> None:
    entry = {
        "estado_interpretacion": "PENDIENTE_INTERPRETACION",
        "interpretacion_error": "timeout",
        "interpretacion_diagnostico": {
            "error_code": "TIMEOUT",
            "phase": "transporte",
            "retryable": True,
            "next_action": "Reintenta cuando el proveedor responda.",
        },
    }

    text = format_proposal(entry)

    assert "PENDIENTE DE INTERPRETACIÓN" in text
    assert "PROPUESTA RECHAZADA" not in text
    assert "TIMEOUT" in text
