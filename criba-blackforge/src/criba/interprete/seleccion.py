"""Selección de intérprete: una sola fuente de verdad para elegir backend.

Reglas que aquí se aplican y que no se negocian:

- El backend por defecto es el externo OpenAI-compatible.
- El runtime local exige endpoint loopback y superar el banco fijo antes de
  admitir propuestas; cargar un modelo no basta.
- El operador elige el backend. Un fallo queda pendiente sin cambiar proveedor.
- Cambiar de interprete aplica a la siguiente ejecucion. La ejecucion en curso
  ya tiene su instancia y su procedencia, asi que no puede alterarse.
"""

from __future__ import annotations

import logging
import os

from .openai_compatible import LocalLlamaInterpreter, OpenAICompatibleInterpreter
from .puerto import InterpreterPort

log = logging.getLogger("criba.interprete.seleccion")

BACKEND_EXTERNO = "openai_compatible"
BACKEND_LOCAL = "local_llama"

DEFAULT_SELECCION = BACKEND_EXTERNO

# Catálogo de modelos gratuitos del proxy Hermes (suscripción Nous).
# Cada entrada es (id real del modelo, etiqueta para la UI). Se descubrieron
# por ejecución contra el proxy local (GET /models + POST /chat/completions):
# los seis respondieron HTTP 200 con contenido; el séptimo (longcat-2.0:free)
# quedó fuera porque el proveedor lo retiró de free ("This model is no longer
# free", HTTP 404). La etiqueta no se inventa: es legible y honesta.
# El modelo se elige por el operador desde el selector de Generación; ninguno
# se activa por defecto. Sin secretos: el proxy adjunta la credencial.
FREE_MODELS: tuple[tuple[str, str], ...] = (
    ("stepfun/step-5-preview:free", "Step 5 Preview"),
    ("stepfun/step-3.7-flash:free", "Step 3.7 Flash"),
    ("upstage/solar-mini4:free", "Solar Mini 4"),
    ("poolside/laguna-s-2.1:free", "Laguna S 2.1"),
    ("poolside/laguna-xs-2.1:free", "Laguna XS 2.1"),
    ("meituan/longcat-2.5-preview:free", "Longcat 2.5 Preview"),
)


def seleccion_por_defecto() -> str:
    """Backend configurado. Externo salvo que se diga otra cosa."""
    return (os.getenv("CRIBA_INTERPRETER_DEFAULT") or DEFAULT_SELECCION).strip().lower()


class BackendDesconocido(ValueError):
    """Backend de interprete que no existe.

    Falla a proposito y de forma visible. Elegir en silencio el externo cuando
    se pidio otra cosa seria reportar un interprete que el operador no eligio:
    el resultado seria correcto y la atribucion falsa.
    """


def construir_interprete(
    backend: str | None = None, *, model: str | None = None
) -> InterpreterPort:
    """Instancia el interprete pedido. Un backend desconocido es un error.

    No hay cadena de respaldo silenciosa: si el backend no existe, se dice cual
    se pidio y cuales existen.

    ``model`` fija el modelo del intérprete externo cuando el operador elige
    uno concreto del catálogo gratuito del proxy. Sin ``model`` se respeta el
    valor por entorno/defecto del propio intérprete. En local se ignora: el
    runtime local usa su perfil GGUF, no un modelo remoto.
    """
    elegido = (backend or seleccion_por_defecto()).strip().lower()
    if elegido in (BACKEND_LOCAL, "local", "local_llama"):
        return LocalLlamaInterpreter()
    if elegido == BACKEND_EXTERNO:
        return OpenAICompatibleInterpreter(model=model) if model else OpenAICompatibleInterpreter()
    log.error("backend de interprete desconocido: %r", elegido)
    raise BackendDesconocido(
        f"backend de interprete desconocido: {elegido!r}. "
        f"Disponibles: {BACKEND_EXTERNO}, {BACKEND_LOCAL}"
    )


def estado_interprete(interprete: InterpreterPort) -> dict[str, object]:
    """Estado real para la UI: si esta operativo y por que, sin adornos.

    La UI debe poder pintar "conectado" o "no disponible" con esto, y no con
    optimisticidad. Un backend experimental nunca aparece como conectado.
    """
    listo, motivo = interprete.operativo()
    etiqueta = getattr(interprete, "ETIQUETA", "")
    return {
        "backend": interprete.backend,
        "provider": interprete.provider,
        "model_requested": getattr(interprete, "model", ""),
        "conectado": bool(listo),
        "motivo": motivo,
        "etiqueta": etiqueta or ("OPERATIVO" if listo else "NO DISPONIBLE"),
        "experimental": bool(etiqueta),
        "admission_report": getattr(interprete, "gate_report", None),
    }
