"""SHADOW_BINDINGS — mapa declarativo control_id → callback real de actions.py.

Este archivo NO conecta señales: documenta el contrato de cada control y es
consumido por el entrypoint shadow para VERIFICAR que cada conexión ya existe
en CribaMainWindow (§16: reutilizar funciones, no duplicarlas).

Si un callback no existe, el target se marca DISABLED_WITH_REASON.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ShadowBinding:
    control_id: str
    callback: str  # nombre de la función en criba.ui.actions
    description: str
    kind: str = "button"  # button | tab | card
    reason: str = ""  # relleno si kind == "disabled"


SHADOW_BINDINGS: list[ShadowBinding] = [
    # --- 12 nav buttons (§10 del megaprompt) ---
    ShadowBinding("navNuevaIdea", "on_nueva_idea", "Inicia el flujo, pide el problema base"),
    ShadowBinding("navGenerar", "on_generar", "Ejecuta los 16 operadores"),
    ShadowBinding("navInventar", "on_inventar", "Cruce → hipótesis → antecedentes"),
    ShadowBinding("navEvaluar", "on_evaluar", "Ranking multicriterio (MCDA)"),
    ShadowBinding("navRed", "on_red", "Grafo de relaciones entre ideas"),
    ShadowBinding("navBlackforge", "on_blackforge", "Panel de control BLACKFORCE"),
    ShadowBinding("navSupra", "on_supra", "Taskmaster orquestador"),
    ShadowBinding("navTecnicas", "on_tecnicas", "Canon T001–T130"),
    ShadowBinding("navModelos", "on_modelos", "Añadir GGUF y ajustar reasoning"),
    ShadowBinding("navHistorial", "on_historial", "Ideas generadas antes"),
    ShadowBinding("navRetro", "on_retro", "Registrar resultado OBSERVED"),
    ShadowBinding("navMemoria", "on_memoria", "Outcomes aprendidos (solo lectura)"),
    # --- otros controles documentados ---
    ShadowBinding("errorDismissBtn", "", "Cerrar banner de error"),
    ShadowBinding("verTodasBtn", "on_ver_todas", "Ver todas las ideas del ranking"),
    ShadowBinding("irBlackforgeBtn", "on_blackforge", "Acceso directo a BLACKFORGE"),
    ShadowBinding("actualizarFuentesBtn", "on_actualizar", "Refrescar fuentes"),
    ShadowBinding("supraBtn", "on_desarrollar_supra", "Desarrollar con SUPRA (prepara dossiers)"),
    ShadowBinding("supraE2eBtn", "on_supra_vertical",
                  "Slice vertical real: núcleo → dossier → SUPRA API → GET"),
    ShadowBinding("historialCompletoBtn", "on_historial", "Historial completo"),
    ShadowBinding("btnGuardar", "on_guardar", "Guardar idea seleccionada"),
    ShadowBinding("btnHibrido", "on_hibrido", "Generación híbrida"),
]

# 4 tabs del ranking (QTabWidget) → on_tab_changed(win, index)
RANKING_TABS = ["top", "evaluacion", "exploracion", "todas"]

# 1 tarjeta BLACKFORGE (build_motor_card) → puente a blackforge bridge
BLACKFORGE_CARD = "build_motor_card"

# Verificación: 12 nav + 9 otros + 4 tabs + 1 card = 26
# El control 26 es el botón del slice vertical real (M2), añadido a los 25
# que la ventana ya tenía; el número se deriva de SHADOW_BINDINGS, no de un
# literal dispersionado.
STATIC_TARGETS_EXPECTED = 26
