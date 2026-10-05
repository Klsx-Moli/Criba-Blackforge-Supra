"""i18n mínimo — ES (default) / EN. Sin dependencias externas."""
from __future__ import annotations

from collections.abc import Callable

_STRINGS: dict[str, dict[str, str]] = {
    "es": {
        # nav
        "nav.nueva_idea":   "Nueva idea",
        "nav.nueva_idea.sub": "Inicia el flujo, pide el problema base",
        "nav.generar":      "Generar",
        "nav.generar.sub":  "Ejecuta los 16 operadores",
        "nav.evaluar":      "Evaluar",
        "nav.evaluar.sub":  "Ranking por value_score",
        "nav.guardar":      "Guardar",
        "nav.guardar.sub":  "Persiste la idea en el catálogo",
        "nav.actualizar":   "Actualizar fuentes",
        "nav.actualizar.sub": "Tendencias, tecnología, diseño",
        "nav.historial":    "Historial",
        "nav.historial.sub": "Ideas generadas antes",
        "nav.blackforge":   "Blackforge",
        "nav.blackforge.sub": "Panel de control BLACKFORGE",
        # topbar
        "greeting.title":   "Hola, Innovador",
        "greeting.sub":     "Listo para transformar ideas en impacto",
        "mode.innovacion":  "MODO: INNOVACIÓN",
        "lang.btn":         "EN",
        # CRIBA main
        "motor.title":      "MOTOR DE INNOVACIÓN",
        "idea.activa":      "IDEA ACTIVA",
        "ranking.title":    "RANKING DE IDEAS",
        # BLACKFORGE
        "bf.ejecutar":      "▶  EJECUTAR GENERACIÓN",
        "bf.ejecutando":    "⟳  EJECUTANDO...",
        "bf.volver":        "← VOLVER A CRIBA",
        "bf.ver_contexto":  "VER CONTEXTO",
        "bf.estado":        "ESTADO DE BLACKFORGE",
        "bf.estado.desc":   ("Sistema listo para generar ideas de innovación en "
                             "ciberseguridad estructuradas y verificables: red team, "
                             "explotación, defensa, ingeniería social e IA & ML."),
        "bf.operativa":     "● OPERATIVA",
        "bf.modos":         "MODOS DE TRABAJO",
        "bf.ideas":         "IDEAS GENERADAS (TOP 5)",
        "bf.modelos":       "INTEGRACIÓN DE MODELOS",
        "bf.verificacion":  "VERIFICACIÓN Y TRAZABILIDAD",
        "bf.modo.optimizado":      "Modo optimizado",
        "bf.modo.optimizado.desc": "Equilibra novedad y eficacia.",
        "bf.modo.asociativa":      "Lotería asociativa",
        "bf.modo.asociativa.desc": "Combina familias y mecanismos.",
        "bf.modo.pura":            "Lotería pura",
        "bf.modo.pura.desc":       "Explora combinaciones aleatorias.",
        # tabla ideas
        "col.titulo":       "Título de la Idea",
        "col.mecanismo":    "Mecanismo Principal",
        "col.riesgo":       "Riesgo",
        "col.novedad":      "Novedad",
        "col.prioridad":    "Prioridad",
        # KPIs
        "kpi.cobertura":    "COBERTURA DE FAMILIAS",
        "kpi.cubierto":     "Cubierto",
        "kpi.integridad":   "INTEGRIDAD DEL PROCESO",
        "kpi.excelente":    "Excelente",
        "kpi.verificador":  "ESTADO DEL VERIFICADOR",
        "kpi.activo":       "● VERIFICADOR ACTIVO",
        "kpi.todo_ok":      "Todo en orden",
        # riesgo / novedad / prioridad
        "risk.low":         "Bajo",
        "risk.medium":      "Medio",
        "risk.high":        "Alto",
        "risk.critical":    "Crítico",
        "nov.alta":         "Alta",
        "nov.muy_alta":     "Muy alta",
        "nov.media":        "Media",
        "pri.critica":      "Crítica",
        "pri.alta":         "Alta",
        "pri.media":        "Media",
        # Shadow UI (M1). Textos copiados del historico, no inventados.
        "shadow.actividad.vacia": "Sin eventos en esta sesión",
        "shadow.actualizar": "↻ Actualizar fuentes",
        "shadow.bf_card.sub": "Espacio especializado",
        "shadow.bf_indep": "Aplicación independiente",
        "shadow.brand_sub": "DESCUBRIR PARA DECIDIR",
        "shadow.candidatos": "⬡ {n} candidatos",
        "shadow.candidatos_sub": "Propuestas para el problema actual",
        "shadow.candidatos_titulo": "Candidatos y evaluación",
        "shadow.card.actividad": "Actividad reciente",
        "shadow.card.evaluacion": "Evaluación interna",
        "shadow.card.fuentes": "Fuentes",
        "shadow.card.fuentes_evidencia": "Fuentes y evidencia",
        "shadow.card.generacion": "Generación",
        "shadow.cerrar": "Cerrar",
        "shadow.col.conv": "Convergencia",
        "shadow.col.estado": "Estado",
        "shadow.col.idea": "Idea",
        "shadow.col.idx": "#",
        "shadow.col.impact": "Impacto estimado",
        "shadow.col.score": "Score interno",
        "shadow.desactivado": "Desactivado",
        "shadow.detail.vacio": "Sin candidato seleccionado",
        "shadow.detail.vacio.desc": (
            "Genera ideas y selecciona un candidato para ver aquí su detalle real."
        ),
        "shadow.evaluar": "📊 Evaluar ideas",
        "shadow.footer.gen_local": "Generación con modelo local",
        "shadow.footer.modelo_off": "Modelo desactivado",
        "shadow.footer.modelo_off.sub": "Sin generación de IA",
        "shadow.footer.sesion": "Sesión activa",
        "shadow.footer.sin_sesion": "Sin sesión",
        "shadow.generar": "✦ Generar ideas",
        "shadow.guardar_idea": "Guardar",
        "shadow.interpretacion.activa": "Interpretación activa",
        "shadow.interpretacion.vacia": "Sin interpretaciones",
        "shadow.idea_sel": "Idea seleccionada",
        "shadow.inventar": "⚗ Inventar",
        "shadow.ir_bf": "Ir a Blackforge  →",
        "shadow.lema": "CIENCIA  //  RIGOR  //  IMPACTO REAL",
        "shadow.mejor_score": "Mejor score",
        "shadow.modelo": "Modelo local",
        "shadow.interpreter.local": "Local · experimental, requiere superar el banco",
        "shadow.interpreter.status": "Se comprobará al ejecutar; el local requiere superar el banco",
        "shadow.interpreter.critica": "Crítica automática · no es validación científica",
        "shadow.interpreter.uncertainty": "Incertidumbre y antecedentes",
        "shadow.interpreter.test": "Prueba discriminante propuesta · no ejecutada",
        "shadow.modelo.tip_off": (
            "Sin modelo local activo — clic para añadir o activar uno (Modelos IA)"
        ),
        "shadow.motor": "⚙ Motor determinista",
        "shadow.nav.blackforge": "Blackforge",
        "shadow.nav.historial": "Historial",
        "shadow.nav.memoria": "Memoria de resultados",
        "shadow.nav.modelos": "Modelos IA",
        "shadow.nav.red": "Red de ideas",
        "shadow.nav.red.sub": "Pendiente",
        "shadow.nav.retro": "Registrar resultado",
        "shadow.nav.supra": "SUPRA",
        "shadow.nav.supra.sub": "Pendiente",
        "shadow.nav.tecnicas": "Técnicas",
        "shadow.no_disponible": "no disponibles",
        "shadow.no_ejecutadas": "No ejecutadas",
        "shadow.no_evaluado": "No evaluado",
        "shadow.no_evidencia": "No equivale a evidencia.",
        "shadow.nueva_idea": "＋ Nueva idea",
        "shadow.objetivo": "Objetivo:",
        "shadow.objetivo.no_definido": "No definido",
        "shadow.problema": "Problema actual",
        "shadow.problema.borrador": (
            "Borrador sin aplicar — pulsa Enter (o «Nueva idea») para definirlo"
        ),
        "shadow.problema.placeholder": (
            "Reducir el impacto de las baterías sin aumentar el coste ni "
            "comprometer el suministro."
        ),
        "shadow.pruebas": "Pruebas ejecutadas:",
        "shadow.refs": "Referencias enlazadas:",
        "shadow.resultados": "Resultados observados:",
        "shadow.sesion": "Sesión:",
        "shadow.sesion.activa": "Definida",
        "shadow.sesion.sin_iniciar": "Sin iniciar",
        "shadow.sin_actualizar": "⚠ Sin actualizar",
        "shadow.sin_actualizar.plain": "Sin actualizar",
        "shadow.supra_btn": "⚛ Desarrollar con SUPRA",
        "shadow.supra_nota": "Prepara dossiers de la sesión. Ejecución pendiente.",
        "shadow.supra_e2e_btn": "▶ Ejecutar en SUPRA (real)",
        "shadow.supra_e2e_nota": "Núcleo → dossier → SUPRA → estado persistido.",
        "shadow.tab.eval": "En evaluación",
        "shadow.tab.exploracion": "Exploración",
        "shadow.tab.ranking": "Ranking de Ideas",
        "shadow.tab.top": "Top ideas",
        "shadow.title": "CRIBA — Shadow UI (UIEDITION)",
        "shadow.ver_historial": "Ver historial completo",
        "shadow.ver_todas": "Ver todas las ideas  →",
    },
    "en": {
        # nav
        "nav.nueva_idea":   "New idea",
        "nav.nueva_idea.sub": "Start flow, enter base problem",
        "nav.generar":      "Generate",
        "nav.generar.sub":  "Run the 16 operators",
        "nav.evaluar":      "Evaluate",
        "nav.evaluar.sub":  "Rank by value_score",
        "nav.guardar":      "Save",
        "nav.guardar.sub":  "Persist idea to catalog",
        "nav.actualizar":   "Update innovations",
        "nav.actualizar.sub": "Trends, technology, design",
        "nav.historial":    "History",
        "nav.historial.sub": "Previously generated ideas",
        "nav.blackforge":   "Blackforge",
        "nav.blackforge.sub": "BLACKFORGE control panel",
        # topbar
        "greeting.title":   "Hello, Innovator",
        "greeting.sub":     "Ready to transform ideas into impact",
        "mode.innovacion":  "MODE: INNOVATION",
        "lang.btn":         "ES",
        # CRIBA main
        "motor.title":      "INNOVATION ENGINE",
        "idea.activa":      "ACTIVE IDEA",
        "ranking.title":    "IDEA RANKING",
        # BLACKFORGE
        "bf.ejecutar":      "▶  RUN GENERATION",
        "bf.ejecutando":    "⟳  RUNNING...",
        "bf.volver":        "← BACK TO CRIBA",
        "bf.ver_contexto":  "VIEW CONTEXT",
        "bf.estado":        "BLACKFORGE STATUS",
        "bf.estado.desc":   ("System ready to generate structured, verifiable "
                             "cybersecurity innovation ideas: red team, exploitation, "
                             "defense, social engineering & AI/ML."),
        "bf.operativa":     "● OPERATIONAL",
        "bf.modos":         "WORK MODES",
        "bf.ideas":         "GENERATED IDEAS (TOP 5)",
        "bf.modelos":       "MODEL INTEGRATION",
        "bf.verificacion":  "VERIFICATION & TRACEABILITY",
        "bf.modo.optimizado":      "Optimized mode",
        "bf.modo.optimizado.desc": "Balances novelty and effectiveness.",
        "bf.modo.asociativa":      "Associative lottery",
        "bf.modo.asociativa.desc": "Combines families and mechanisms.",
        "bf.modo.pura":            "Pure lottery",
        "bf.modo.pura.desc":       "Explores random combinations.",
        # tabla ideas
        "col.titulo":       "Idea Title",
        "col.mecanismo":    "Main Mechanism",
        "col.riesgo":       "Risk",
        "col.novedad":      "Novelty",
        "col.prioridad":    "Priority",
        # KPIs
        "kpi.cobertura":    "FAMILY COVERAGE",
        "kpi.cubierto":     "Covered",
        "kpi.integridad":   "PROCESS INTEGRITY",
        "kpi.excelente":    "Excellent",
        "kpi.verificador":  "VERIFIER STATUS",
        "kpi.activo":       "● VERIFIER ACTIVE",
        "kpi.todo_ok":      "All clear",
        # riesgo / novedad / prioridad
        "risk.low":         "Low",
        "risk.medium":      "Medium",
        "risk.high":        "High",
        "risk.critical":    "Critical",
        "nov.alta":         "High",
        "nov.muy_alta":     "Very high",
        "nov.media":        "Medium",
        "pri.critica":      "Critical",
        "pri.alta":         "High",
        "pri.media":        "Medium",
        # Shadow UI (M1). Textos copiados del historico, no inventados.
        "shadow.actividad.vacia": "No events in this session",
        "shadow.actualizar": "↻ Update sources",
        "shadow.bf_card.sub": "Specialized workspace",
        "shadow.bf_indep": "Standalone application",
        "shadow.brand_sub": "DISCOVER TO DECIDE",
        "shadow.candidatos": "⬡ {n} candidates",
        "shadow.candidatos_sub": "Proposals for the current problem",
        "shadow.candidatos_titulo": "Candidates and evaluation",
        "shadow.card.actividad": "Recent activity",
        "shadow.card.evaluacion": "Internal evaluation",
        "shadow.card.fuentes": "Sources",
        "shadow.card.fuentes_evidencia": "Sources and evidence",
        "shadow.card.generacion": "Generation",
        "shadow.cerrar": "Close",
        "shadow.col.conv": "Convergence",
        "shadow.col.estado": "State",
        "shadow.col.idea": "Idea",
        "shadow.col.idx": "#",
        "shadow.col.impact": "Estimated impact",
        "shadow.col.score": "Internal score",
        "shadow.desactivado": "Disabled",
        "shadow.detail.vacio": "No candidate selected",
        "shadow.detail.vacio.desc": (
            "Generate ideas and select a candidate to see its real detail here."
        ),
        "shadow.evaluar": "📊 Evaluate ideas",
        "shadow.footer.gen_local": "Generation with local model",
        "shadow.footer.modelo_off": "Model disabled",
        "shadow.footer.modelo_off.sub": "No AI generation",
        "shadow.footer.sesion": "Active session",
        "shadow.footer.sin_sesion": "No session",
        "shadow.generar": "✦ Generate ideas",
        "shadow.guardar_idea": "Save",
        "shadow.interpretacion.activa": "Active interpretation",
        "shadow.interpretacion.vacia": "No interpretations",
        "shadow.idea_sel": "Selected idea",
        "shadow.inventar": "⚗ Invent",
        "shadow.ir_bf": "Go to Blackforge  →",
        "shadow.lema": "SCIENCE  //  RIGOR  //  REAL IMPACT",
        "shadow.mejor_score": "Best score",
        "shadow.modelo": "Local model",
        "shadow.interpreter.local": "Local · experimental, requires admission benchmark",
        "shadow.interpreter.status": "Checked when running; local requires admission benchmark",
        "shadow.interpreter.critica": "Automatic critique · not scientific validation",
        "shadow.interpreter.uncertainty": "Uncertainty and prior art",
        "shadow.interpreter.test": "Proposed discriminant test · not executed",
        "shadow.modelo.tip_off": "No local model active — click to add or enable one (AI models)",
        "shadow.motor": "⚙ Deterministic engine",
        "shadow.nav.blackforge": "Blackforge",
        "shadow.nav.historial": "History",
        "shadow.nav.memoria": "Outcome memory",
        "shadow.nav.modelos": "AI models",
        "shadow.nav.red": "Idea network",
        "shadow.nav.red.sub": "Pending",
        "shadow.nav.retro": "Record outcome",
        "shadow.nav.supra": "SUPRA",
        "shadow.nav.supra.sub": "Pending",
        "shadow.nav.tecnicas": "Techniques",
        "shadow.no_disponible": "not available",
        "shadow.no_ejecutadas": "Not run",
        "shadow.no_evaluado": "Not evaluated",
        "shadow.no_evidencia": "Not equivalent to evidence.",
        "shadow.nueva_idea": "＋ New idea",
        "shadow.objetivo": "Goal:",
        "shadow.objetivo.no_definido": "Not defined",
        "shadow.problema": "Current problem",
        "shadow.problema.borrador": "Draft not applied — press Enter (or “New idea”) to define it",
        "shadow.problema.placeholder": (
            "Cut the impact of batteries without raising cost or risking supply."
        ),
        "shadow.pruebas": "Tests run:",
        "shadow.refs": "Linked references:",
        "shadow.resultados": "Observed outcomes:",
        "shadow.sesion": "Session:",
        "shadow.sesion.activa": "Defined",
        "shadow.sesion.sin_iniciar": "Not started",
        "shadow.sin_actualizar": "⚠ Not updated",
        "shadow.sin_actualizar.plain": "Not updated",
        "shadow.supra_btn": "⚛ Develop with SUPRA",
        "shadow.supra_nota": "Prepares session dossiers. Execution pending.",
        "shadow.supra_e2e_btn": "▶ Run in SUPRA (real)",
        "shadow.supra_e2e_nota": "Core → dossier → SUPRA → persisted state.",
        "shadow.tab.eval": "Under evaluation",
        "shadow.tab.exploracion": "Exploration",
        "shadow.tab.ranking": "Idea ranking",
        "shadow.tab.top": "Top ideas",
        "shadow.title": "CRIBA — Shadow UI (UIEDITION)",
        "shadow.ver_historial": "See full history",
        "shadow.ver_todas": "See all ideas  →",
    },
}

_current: str = "es"
_listeners: list[Callable[[], None]] = []


def t(key: str) -> str:
    """Devuelve el string en el idioma activo; fallback a ES, luego a la clave."""
    return (_STRINGS[_current].get(key)
            or _STRINGS["es"].get(key)
            or key)


def lang() -> str:
    return _current


def set_lang(code: str) -> None:
    global _current
    _current = code if code in _STRINGS else "es"
    for cb in _listeners:
        try:
            cb()
        except Exception:
            pass


def toggle() -> None:
    set_lang("en" if _current == "es" else "es")


def on_change(cb: Callable[[], None]) -> None:
    """Registra callback invocado en cada cambio de idioma."""
    _listeners.append(cb)
