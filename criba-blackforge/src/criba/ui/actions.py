"""Máquina de estados visual (STATE_MATRIX_CRIBA.md S1..S10) + acciones.

Todas las mutaciones (generar/evaluar/actualizar) corren en QThreadPool;
la GUI nunca se congela (WIDGET_TREE §3).
"""

from __future__ import annotations

import json
import traceback
from collections.abc import Callable
from datetime import datetime
from threading import Event
from typing import Any

from PySide6.QtCore import QObject, QRunnable, Signal, Slot
from PySide6.QtGui import QColor

from .. import __version__ as ENGINE_VERSION
from ..engine import activate
from .ranking import RankingModel
from .widgets import set_chip

MUTATORS = ("navNuevaIdea", "navGenerar", "navInventar", "navEvaluar", "navRed")


class _Signals(QObject):
    done = Signal(object)
    fail = Signal(str)
    progress = Signal(object)


class Worker(QRunnable):
    def __init__(self, fn: Callable[[], Any]) -> None:
        super().__init__()
        self.fn = fn
        self.signals = _Signals()

    def run(self) -> None:
        # `QThreadPool.globalInstance()` outlives the window that started the
        # work, and so does this QRunnable. Its `_Signals` QObject is owned by
        # Python and dies with the window, so emitting after that raises
        # `RuntimeError: Signal source has been deleted` from inside
        # QRunnable::run — which Qt reports as a Python override failure and
        # takes the surrounding process down. Nobody is listening any more, so
        # the emission is meaningless; dropping it is correct, not a mute.
        try:
            self.signals.done.emit(self.fn())
        except RuntimeError:
            return
        except Exception as exc:  # noqa: BLE001 — S9 muestra el motivo real
            try:
                self.signals.fail.emit(f"{exc}\n{traceback.format_exc(limit=3)}")
            except RuntimeError:
                return


def _now_ts() -> str:
    return datetime.now().strftime("%H:%M")


def _start_worker(win: Any, worker: Worker, operation: str = "") -> None:
    """Retener la referencia del worker hasta que emita: sin esto el GC de
    Python destruye el QObject de señales antes de entregar done/fail
    (pitfall QRunnable.autoDelete + señal encolada entre hilos).

    Background workers (enhance) are not tracked in _live_workers so they
    do not block harnesses or UI waits that only care about the primary
    operation completing.
    """
    if operation != "enhance":
        if not hasattr(win, "_live_workers"):
            win._live_workers = []
        win._live_workers.append(worker)
    loading = None
    cards = getattr(win, "topcards", None)
    mapping = {
        "generate": ("generation_loading", "Generando ideas…"),
        "interpret": ("generation_loading", "Interpretando…"),
        "evaluate": ("evaluation_loading", "Evaluando…"),
        "sources": ("sources_loading", "Actualizando fuentes…"),
    }
    if cards is not None and operation in mapping:
        attr, text = mapping[operation]
        loading = getattr(cards, attr, None)
        if loading is not None:
            loading.begin(worker, text)

    def _release(*_a: Any) -> None:
        if loading is not None:
            loading.finish(worker)
        try:
            win._live_workers.remove(worker)
        except ValueError:
            pass

    worker.signals.done.connect(_release)
    worker.signals.fail.connect(_release)
    worker.setAutoDelete(False)
    win.pool.start(worker)


def _activity(win: Any, kind: str, text: str) -> None:
    from .panels import add_activity

    add_activity(win.t, win.refs, _now_ts(), kind, text)


def _set_buttons(win: Any, enabled: dict[str, bool]) -> None:
    for key, on in enabled.items():
        win.nav[key].setEnabled(on)


def _suggest(win: Any, key: str | None) -> None:
    for k in MUTATORS + ("navHistorial", "navBlackforge"):
        win.nav[k].set_suggested(k == key)


def _lock_mutators(win: Any) -> None:
    for k in MUTATORS:
        win.nav[k].setEnabled(False)


def _session_badge(win: Any, active: bool) -> None:
    color = win.t.success if active else win.t.text_muted
    win.sessionDot.setStyleSheet(f"color:{color}; background:transparent;")
    win.sessionLabel.setText("Sesión activa" if active else "Sin sesión")


# ---------------------------------------------------------------------------
# S1 — SIN SESIÓN
# ---------------------------------------------------------------------------
def enter_s1(win: Any) -> None:
    from ..model_config import active_model_label

    _session_badge(win, False)
    win.greetingSub.setText("Crea una nueva idea para empezar")
    r = win.refs
    r["ideaTitle"].setText("Ninguna idea activa")
    r["ideaSummary"].setText("Pulsa Nueva idea para definir el problema base")
    set_chip(r["ideaEstadoChip"], "Sin sesión", "exploracion")
    r["scoreGauge"].hide()
    r["mOperadores"].set_value("0/16")
    r["mIdeas"].set_value("0")
    r["mConvergencia"].set_value("—")
    r["mBestScore"].set_value("—")
    for stage in r["stages"].values():
        stage.set_state("pending")
    for conn in r["connectors"]:
        conn.set_lit(False)
    r["rankingTable"].hide()
    r["rankingEmpty"].show()
    r["scoreHistogram"].set_bins([])
    r["catDonut"].set_segments([])
    r["catDonut"].set_center("0", "ideas totales")
    win.footerSegs["fsModelo"].set_value(f"CRIBA {ENGINE_VERSION} · {active_model_label()}")
    win.footerSegs["fsSesion"].set_value("—")
    win.footerSegs["fsIdeas"].set_value("0")
    win.footerSegs["fsConvergencia"].set_value("—")
    win.footerSegs["fsUltima"].set_value("—")
    refresh_sources_freshness(win)
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": False,
            "navInventar": False,
            "navEvaluar": False,
            "navRed": True,
            "navHistorial": True,
            "navBlackforge": True,
            "navSupra": True,
        },
    )
    _suggest(win, "navNuevaIdea")


# ---------------------------------------------------------------------------
# S2 — NUEVA IDEA SIN EVALUAR
# ---------------------------------------------------------------------------
def on_nueva_idea(win: Any) -> None:
    from .dialogs import ask_problem

    problem = ask_problem(win)
    win.nav["navNuevaIdea"].setChecked(False)
    if not problem:
        return
    _apply_new_problem(win, problem)


def on_nueva_idea_no_dialog(win: Any, problem: str) -> None:
    """Non-interactive variant: apply a problem without a modal dialog.

    Used by automated GUI regression tests (offscreen). Mirrors the real
    on_nueva_idea path exactly, minus the QDialog.
    """
    win.nav["navNuevaIdea"].setChecked(False)
    if not problem:
        return
    _apply_new_problem(win, problem)


def _clear_journey_outputs(win: Any) -> None:
    candidates = getattr(win, "candidates", None)
    if candidates is None:
        return
    candidates.clear_interpreter_entries()
    for widget in (
        candidates.raw_output,
        candidates.interpretation_output,
        candidates.dossier_output,
        candidates.supra_output,
    ):
        widget.clear()
    candidates.output_tabs.setCurrentWidget(candidates.raw_output)
    candidates.save_idea.setEnabled(False)


def _apply_new_problem(win: Any, problem: str) -> None:
    win.problem = problem
    win.packet = None
    win.invent_sheet = None
    _clear_journey_outputs(win)
    right_panel = getattr(win, "right_panel", None)
    if right_panel is not None:
        right_panel.supra.setEnabled(False)
    r = win.refs
    _session_badge(win, True)
    win.greetingSub.setText("Listo para transformar ideas en impacto")
    r["stages"]["stageProblema"].set_state("done")
    r["connectors"][0].set_lit(True)
    r["stages"]["stageGenerar"].set_state("active")
    for key in ("stageEvaluar", "stageGuardar", "stageEvolucionar"):
        r["stages"][key].set_state("pending")
    for conn in r["connectors"][1:]:
        conn.set_lit(False)
    r["ideaTitle"].setText(problem if len(problem) <= 120 else problem[:117] + "…")
    r["ideaSummary"].setText("Problema base capturado. Genera ideas con los 16 operadores.")
    set_chip(r["ideaEstadoChip"], "Sin evaluar", "exploracion")
    r["scoreGauge"].show()
    r["scoreGauge"].set_score(0.0, animate=False)
    r["scoreGauge"].set_percentile("Pendiente")
    r["mOperadores"].set_value("0/16")
    r["mIdeas"].set_value("0")
    r["mConvergencia"].set_value("—")
    r["mBestScore"].set_value("—")
    _activity(win, "cyan", f"Problema base definido: {problem[:60]}")
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navInventar": True,
            "navEvaluar": False,
            "navRed": False,
            "navHistorial": True,
            "navBlackforge": True,
            "navSupra": True,
        },
    )
    _suggest(win, "navGenerar")


# ---------------------------------------------------------------------------
# S3 — GENERANDO  (activate() genera Y evalúa; la fase visual se divide)
# ---------------------------------------------------------------------------
def _generate_criba_packet(problem: str) -> dict[str, Any]:
    """Return deterministic generation immediately; enhance in background."""
    packet = activate(problem)
    packet.setdefault("semantic_generation", {})
    packet["semantic_generation"]["status"] = "pending"
    return packet


def _enhance_packet_async(packet: dict[str, Any]) -> None:
    """Enhance packet in background; never blocks the deterministic result."""
    try:
        from ..model_runtime import enhance_criba_packet
        enhance_criba_packet(packet)
        packet["semantic_generation"]["status"] = "ok"
    except Exception as exc:
        packet["semantic_generation"]["status"] = "fallback"
        packet["semantic_generation"]["error"] = str(exc)


def on_generar(win: Any) -> None:
    win.nav["navGenerar"].setChecked(False)
    if not win.problem:
        show_error(win, "Generar", "Define primero el problema base (Nueva idea).")
        return
    r = win.refs
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navGenerar"].set_state("running", "Ejecutando operadores...")
    r["stages"]["stageGenerar"].set_state("active", spinning=True)
    _activity(win, "blue", "Generación iniciada (16 operadores)")

    # El indicador de actividad está ligado al worker, no a un spinner global.

    def _generate_and_enhance() -> dict[str, Any]:
        packet = _generate_criba_packet(win.problem)
        # Enhancement runs in background; UI shows deterministic ideas now.
        enhance_worker = Worker(lambda: _enhance_packet_async(packet))
        _start_worker(win, enhance_worker, "enhance")
        return packet

    worker = Worker(_generate_and_enhance)
    worker.signals.done.connect(lambda packet: _on_generated(win, packet))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navGenerar", "stageGenerar", msg)
    )
    _start_worker(win, worker, "generate")


def _on_generated(win: Any, packet: dict[str, Any]) -> None:
    win.packet = packet
    r = win.refs
    ideas = packet["innovation"]["ideas"]
    win.nav["navGenerar"].set_state("done")
    r["stages"]["stageGenerar"].set_state("done")
    r["connectors"][1].set_lit(True)
    r["stages"]["stageEvaluar"].set_state("active")
    # Ocultar spinner de progreso
    if hasattr(win, "_progress_label") and win._progress_label:
        win._progress_label.hide()
    r["mOperadores"].set_value("16/16")
    r["mIdeas"].set_value(str(len(ideas)))
    _activity(
        win,
        "blue",
        f"{len(ideas)} ideas generadas "
        f"({packet['innovation']['real_divergent_count']} divergencia real)",
    )
    semantic = packet.get("semantic_generation", {})
    if semantic.get("status") in {"ok", "partial"}:
        enhanced_count = int(semantic.get("enhanced_count", 0))
        candidate_count = int(semantic.get("candidate_count", len(ideas)))
        suffix = " · respuesta parcial" if semantic.get("status") == "partial" else ""
        _activity(
            win,
            "orange" if semantic.get("status") == "partial" else "cyan",
            f"{enhanced_count}/{candidate_count} ideas prioritarias redactadas por "
            f"{semantic.get('model', 'modelo local')} "
            f"({semantic.get('reasoning', 'balanced')}){suffix}",
        )
        win.footerSegs["fsModelo"].set_value(str(semantic.get("model") or "Modelo local"))
    elif semantic.get("status") == "fallback":
        _activity(win, "orange", f"Modelo no disponible: {semantic.get('error', 'fallback')}")
        win.footerSegs["fsModelo"].set_value("Determinista · fallback LLM")
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navInventar": True,
            "navEvaluar": True,
            "navRed": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )
    _suggest(win, "navEvaluar")


# ---------------------------------------------------------------------------
# S3b — INVENTAR (mismo servicio criba.inventar.invent que la CLI)
# ---------------------------------------------------------------------------
def _run_inventar(
    problem: str,
    *,
    backend: str | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Ejecuta ``invent`` con UNA instancia de intérprete fijada para el run.

    El selector solo afecta a la siguiente ejecución. Cambiar el combo mientras
    una tarea está activa no cambia proveedor/modelo a mitad de candidatos.
    Cancelar es cooperativo: se aplica al terminar la petición HTTP en curso y
    evita nuevas llamadas remotas.
    """
    from ..intelligence.refresh import default_store
    from ..interprete.seleccion import (
        construir_interprete,
        estado_interprete,
        seleccion_por_defecto,
    )
    from ..inventar import _default_proponer, append_ledger, invent

    chosen = backend or seleccion_por_defecto()
    interpreter = construir_interprete(chosen)
    interpreter_state = estado_interprete(interpreter)
    completed = 0

    def _proponer(
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        nonlocal completed
        if cancel_requested is not None and cancel_requested():
            from ..inventar import _pending_proposal

            result = _pending_proposal("cancelado por operador")
        else:
            result = _default_proponer(
                query,
                idea,
                domain,
                evidence=evidence,
                interprete=interpreter,
            )
        completed += 1
        if progress is not None:
            progress(
                {
                    "completed": completed,
                    "candidate": str(idea.get("title") or "")[:100],
                    "status": result.get("estado", "PENDIENTE_INTERPRETACION"),
                }
            )
        return result

    sheet = invent(problem, store=default_store(), proponer=_proponer)
    ledger = append_ledger(sheet)
    sheet["ledger_path"] = str(ledger)
    sheet["interpreter"] = interpreter_state
    sheet["cancel_requested"] = bool(cancel_requested and cancel_requested())
    return sheet


def on_inventar(win: Any) -> None:
    win.nav["navInventar"].setChecked(False)
    if not win.problem:
        show_error(win, "Inventar", "Define primero el problema base (Nueva idea).")
        return
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navInventar"].set_state("running", "Cruce → hipótesis → antecedentes...")
    _activity(win, "blue", "Inventar iniciado (cruce → interpretación → antecedentes)")

    selector = getattr(getattr(win, "topcards", None), "interpreter_selector", None)
    backend = str(selector.currentData() if selector is not None else "openai_compatible")
    win.interpreter_cancel_requested = False
    topcards = getattr(win, "topcards", None)
    if topcards is not None:
        topcards.interpreter_selector.setEnabled(False)
        topcards.cancel_interpretation.setEnabled(True)
        topcards.cancel_interpretation.setText("Cancelar interpretación")
        topcards.cancel_interpretation.show()
        topcards.interpreter_status.setText(
            f"{topcards.interpreter_selector.currentText()} · comprobando disponibilidad…"
        )

    holder: dict[str, Worker] = {}

    def _task() -> dict[str, Any]:
        return _run_inventar(
            win.problem,
            backend=backend,
            progress=lambda payload: holder["worker"].signals.progress.emit(payload),
            cancel_requested=lambda: bool(win.interpreter_cancel_requested),
        )

    worker = Worker(_task)
    holder["worker"] = worker
    worker.signals.progress.connect(lambda payload: _on_invent_progress(win, payload))
    worker.signals.done.connect(lambda sheet: _on_invented(win, sheet))
    worker.signals.fail.connect(lambda msg: _on_invent_failed(win, msg))
    _start_worker(win, worker, "interpret")


def _finish_invent_controls(win: Any) -> None:
    topcards = getattr(win, "topcards", None)
    if topcards is None:
        return
    topcards.interpreter_selector.setEnabled(True)
    topcards.cancel_interpretation.hide()


def _on_invent_progress(win: Any, payload: dict[str, Any]) -> None:
    topcards = getattr(win, "topcards", None)
    if topcards is None:
        return
    topcards.interpreter_status.setText(
        f"Interpretación {payload.get('completed', 0)} · "
        f"{payload.get('status', 'PENDIENTE')} · "
        f"{payload.get('candidate', '')}"
    )


def on_cancel_inventar(win: Any) -> None:
    """Solicita cancelación cooperativa tras la petición HTTP en curso."""
    win.interpreter_cancel_requested = True
    topcards = getattr(win, "topcards", None)
    if topcards is not None:
        topcards.cancel_interpretation.setEnabled(False)
        topcards.cancel_interpretation.setText("Cancelación solicitada…")
        topcards.interpreter_status.setText(
            "Cancelación solicitada; se aplicará al terminar la petición en curso."
        )
    _activity(win, "amber", "Cancelación de interpretación solicitada")


def _on_invent_failed(win: Any, message: str) -> None:
    _finish_invent_controls(win)
    on_operation_error(win, "navInventar", None, message)


def _render_interpreter_outputs(win: Any, sheet: dict[str, Any]) -> None:
    """Carga una propuesta por vez para lectura clara y trazable."""
    candidates = getattr(win, "candidates", None)
    if candidates is None:
        return
    candidates.set_interpreter_entries(list(sheet.get("entries", [])))


def _on_invented(win: Any, sheet: dict[str, Any]) -> None:
    """Muestra la ficha honesta: pendientes como pendientes, sin fabricar."""
    _finish_invent_controls(win)
    win.invent_sheet = sheet
    r = win.refs
    totals = sheet["totals"]
    n_entries = len(sheet["entries"])
    pending = totals["pending_interpretation"]
    valid = sum(
        1
        for entry in sheet["entries"]
        if entry.get("estado_interpretacion") == "PROPUESTA"
        and str(entry.get("mecanismo") or "").strip()
    )
    win.nav["navInventar"].set_state(
        "done",
        f"operación terminada: {valid}/{n_entries} propuestas válidas; SUPRA no ejecutado",
    )
    interpreter_state = sheet.get("interpreter") or {}
    topcards = getattr(win, "topcards", None)
    if topcards is not None:
        connected = bool(interpreter_state.get("conectado"))
        provider = str(interpreter_state.get("provider") or "desconocido")
        model = str(interpreter_state.get("model_requested") or "desconocido")
        reason = str(interpreter_state.get("motivo") or "sin motivo declarado")
        topcards.interpreter_status.setText(
            f"{'Disponible' if connected else 'No disponible'} · "
            f"proveedor {provider} · modelo {model} · {reason} · "
            f"interpretación válida {valid}/{n_entries}"
        )
    _render_interpreter_outputs(win, sheet)
    right_panel = getattr(win, "right_panel", None)
    if right_panel is not None:
        right_panel.supra.setEnabled(valid > 0)

    r["ideaTitle"].setText(f"Inventar · {sheet['query'][:100]}")
    r["ideaSummary"].setText(
        f"Operación terminada · {n_entries} candidatos · {valid} propuestas válidas · "
        f"interpretación pendiente: {pending} · SUPRA no ejecutado · "
        f"UNRESOLVED: {totals['unresolved']} · "
        f"PARTIAL: {totals['partial_prior_art']} · SURVIVED: {totals['survived_search']}"
    )
    if valid == 0:
        set_chip(
            r["ideaEstadoChip"],
            f"0 propuestas válidas · {pending} pendientes",
            "exploracion",
        )
        candidates = getattr(win, "candidates", None)
        if candidates is not None:
            candidates.output_tabs.setCurrentWidget(candidates.interpretation_output)
    else:
        set_chip(
            r["ideaEstadoChip"],
            f"{valid} propuestas válidas · {pending} pendientes",
            "ideacion",
        )
    _activity(
        win,
        "cyan" if valid else "amber",
        f"Inventar terminó: {valid}/{n_entries} propuestas válidas · "
        f"{pending} pendientes · SUPRA no ejecutado",
    )

    lines = [
        f"Problema: {sheet['query']}",
        f"Semilla: {sheet['seed']} · modo: {sheet['mode']}",
        "",
    ]
    for i, entry in enumerate(sheet["entries"], 1):
        lines.append(f"{i}. {entry['title']}")
        if entry["estado_interpretacion"] == "PROPUESTA":
            lines.append(f"   hipótesis: {entry['hipotesis'][:200]}")
            lines.append(f"   mecanismo: {entry['mecanismo'][:200]}")
        else:
            reason = entry.get("interpretacion_error") or "sin modelo disponible"
            lines.append(f"   interpretación PENDIENTE ({reason})")
        lines.append(f"   prior-art: {entry['prior_art']['verdict']}")
        lines.append("")
    lines.append(
        f"Totales — ideas: {totals['ideas']} · pendientes: {pending} · "
        f"UNRESOLVED: {totals['unresolved']} · "
        f"PARTIAL: {totals['partial_prior_art']} · "
        f"SURVIVED: {totals['survived_search']}"
    )
    ledger = sheet.get("ledger_path")
    if ledger:
        lines.append(f"Ledger: {ledger}")
    sheet["ficha_texto"] = "\n".join(lines)
    _activity(win, "cyan", "Ficha de inventar disponible (win.invent_sheet)")
    _restore_buttons_after_op(win)


# ---------------------------------------------------------------------------
# S4 -> S5 — EVALUANDO -> RANKING LISTO
# ---------------------------------------------------------------------------
def on_evaluar(win: Any) -> None:
    win.nav["navEvaluar"].setChecked(False)
    if not win.packet:
        show_error(win, "Evaluar", "Genera ideas antes de evaluar.")
        return
    r = win.refs
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navEvaluar"].set_state("running", "Midiendo convergencia...")
    r["stages"]["stageEvaluar"].set_state("active", spinning=True)
    packet = win.packet
    worker = Worker(lambda: _build_ranking_rows(packet))
    worker.signals.done.connect(lambda rows: _on_evaluated(win, rows))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navEvaluar", "stageEvaluar", msg)
    )
    _start_worker(win, worker, "evaluate")


def _build_ranking_rows(packet: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, idea in enumerate(packet["innovation"]["ideas"], start=1):
        conv = idea.get("convergence", {})
        rows.append(
            {
                "rank": i,
                "id": idea.get("id", ""),
                "titulo": idea.get("title") or idea.get("description", ""),
                "descripcion": idea.get("description", ""),
                "value_score": float(conv.get("value_score", 0.0)),
                "convergencia": float(conv.get("novelty", 0.0)),
                "estado": "candidata" if i <= 3 else ("eval" if i <= 6 else "exploracion"),
            }
        )
    return rows


def _on_evaluated(win: Any, rows: list[dict[str, Any]]) -> None:
    r = win.refs
    packet = win.packet
    win.nav["navEvaluar"].set_state("done")
    r["stages"]["stageEvaluar"].set_state("done")
    r["connectors"][2].set_lit(True)
    r["stages"]["stageGuardar"].set_state("active")
    r["rankingModel"].set_rows(rows)
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.save_idea.setEnabled(bool(rows))
    r["rankingEmpty"].hide()
    r["rankingTable"].show()
    r["rankingTabs"].setCurrentIndex(0)
    if rows:
        best = rows[0]
        r["ideaTitle"].setText(best["titulo"][:120])
        r["ideaSummary"].setText(best["descripcion"][:240])
        set_chip(r["ideaEstadoChip"], "En evaluación", "eval")
        r["scoreGauge"].show()
        r["scoreGauge"].set_score(best["value_score"])
        pct = max(1, round(100 / max(1, len(rows))))
        r["scoreGauge"].set_percentile(f"Alto impacto · Top {pct}% del set")
        r["mBestScore"].set_value(f"{best['value_score']:.2f}")
        r["rankingTable"].selectRow(0)
    conv_global = packet["metrics"].get("divergence", 0)
    r["mConvergencia"].set_value(f"{conv_global}%")
    _update_charts(win, rows)
    win.footerSegs["fsSesion"].set_value(f"CRB-{packet['activation_id'][:8].upper()}")
    win.footerSegs["fsIdeas"].set_value(str(len(rows)))
    win.footerSegs["fsConvergencia"].set_value(f"{conv_global}%")
    win.footerSegs["fsUltima"].set_value(datetime.now().strftime("%d/%m %H:%M"))
    _activity(
        win,
        "blue",
        f"Idea evaluada: {rows[0]['titulo'][:60]} (score {rows[0]['value_score']:.2f})"
        if rows
        else "Evaluación sin ideas",
    )
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": True,
            "navInventar": True,
            "navEvaluar": True,
            "navRed": True,
            "navHistorial": True,
            "navBlackforge": True,
            "navSupra": True,
        },
    )
    _suggest(win, "navRed")


def _update_charts(win: Any, rows: list[dict[str, Any]]) -> None:
    r = win.refs
    t = win.t
    if not rows:
        return
    scores = [row["value_score"] for row in rows]
    lo, hi = min(scores), max(scores)
    span = (hi - lo) or 1.0
    nbins = 6
    bins = []
    for i in range(nbins):
        edge = lo + span * (i + 0.5) / nbins
        count = sum(1 for s in scores if lo + span * i / nbins <= s <= lo + span * (i + 1) / nbins)
        bins.append((edge, count))
    r["scoreHistogram"].set_bins(bins)
    # donut por familia de operador (datos reales del packet)
    from collections import Counter

    fams = Counter(i.get("family", "otros") for i in win.packet["innovation"]["ideas"])
    top = fams.most_common(4)
    rest = sum(fams.values()) - sum(c for _, c in top)
    segs = []
    while r["donutLegend"].count():
        item = r["donutLegend"].takeAt(0)
        if item.widget():
            item.widget().deleteLater()
    from .widgets import LegendRow

    total = sum(fams.values()) or 1
    for idx, (name, count) in enumerate(top, start=1):
        color = QColor(t.chart(idx))
        segs.append((name, float(count), color))
        r["donutLegend"].addWidget(LegendRow(t.chart(idx), name, f"{round(100 * count / total)}%"))
    if rest > 0:
        segs.append(("Otros", float(rest), QColor(t.chart(5))))
        r["donutLegend"].addWidget(LegendRow(t.chart(5), "Otros", f"{round(100 * rest / total)}%"))
    r["catDonut"].set_segments(segs)
    r["catDonut"].set_center(str(len(rows)), "ideas totales")


# ---------------------------------------------------------------------------
# S6 — GUARDADO COMPLETADO
# ---------------------------------------------------------------------------
def on_guardar(win: Any) -> None:
    win.nav["navRed"].setChecked(False)
    if not win.packet:
        show_error(win, "Guardar", "No hay evaluación que guardar.")
        return
    r = win.refs
    try:
        ident = win.store.save(
            win.packet["original_query"],
            win.packet,
            {"gui": True, "screen": "innovacion"},
        )
    except Exception as exc:  # noqa: BLE001
        on_operation_error(win, "navRed", "stageGuardar", str(exc))
        return
    win.saved_ids.add(ident)
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.save_idea.setEnabled(False)
    win.nav["navRed"].set_state("done")
    r["stages"]["stageGuardar"].set_state("done")
    r["connectors"][3].set_lit(True)
    r["stages"]["stageEvolucionar"].set_state("active")
    set_chip(r["ideaEstadoChip"], "Guardada en catálogo", "guardada")
    model: RankingModel = r["rankingModel"]
    model.mark_saved(0)
    title = r["ideaTitle"].text()
    _activity(win, "success", f"Idea guardada en catálogo: {title[:60]}")
    win.nav["navRed"].setEnabled(False)  # OFF† hasta cambiar selección
    _suggest(win, None)


# ---------------------------------------------------------------------------
# S7 — HISTORIAL
# ---------------------------------------------------------------------------
def on_historial(win: Any) -> None:
    win.nav["navHistorial"].setChecked(True)
    from .dialogs import show_history

    try:
        loaded = show_history(win)
    finally:
        win.nav["navHistorial"].setChecked(False)
    if loaded:
        packet = loaded["packet"]
        # Blackforge sessions use a different packet shape (ideas at top level,
        # selected_current.id == 'blackforge'); route them to the BF screen
        # instead of the CRIBA evaluator, which expects innovation.ideas.
        sc = packet.get("selected_current", {})
        if isinstance(sc, dict) and sc.get("id") == "blackforge":
            win.show_blackforge_page(history_packet=packet)
            return
        win.packet = packet
        win.problem = packet.get("original_query", "")
        r = win.refs
        _session_badge(win, True)
        r["stages"]["stageProblema"].set_state("done")
        r["connectors"][0].set_lit(True)
        r["stages"]["stageGenerar"].set_state("done")
        r["connectors"][1].set_lit(True)
        rows = _build_ranking_rows(win.packet)
        r["mOperadores"].set_value("16/16")
        r["mIdeas"].set_value(str(len(rows)))
        _activity(win, "cyan", f"Sesión cargada del historial: {win.problem[:50]}")
        _on_evaluated(win, rows)


# ---------------------------------------------------------------------------
# S8 — FUENTES (actualización REAL: adquisición → deduplicación → informe)
# ---------------------------------------------------------------------------
def _refresh_store() -> Any:
    """Almacén de evidencia del perfil activo (fuera del repo del usuario)."""
    from ..intelligence.refresh import default_store

    store = default_store()
    if store is None:
        raise RuntimeError("No se puede abrir el almacén local de evidencia")
    return store


def _refresh_queries(problem: str) -> list[str]:
    """Consultas de adquisición: el problema activo más términos base."""
    return [problem.strip()] if problem.strip() else ["innovation methods", "prior art search"]


class _SourceRefreshBridge(QObject):
    """All acquisition events reach QWidget consumers on the GUI thread."""

    def __init__(self, win: Any) -> None:
        super().__init__(win if isinstance(win, QObject) else None)
        self.win = win

    @Slot(object)
    def progress(self, event: dict[str, Any]) -> None:
        panel = self.win.refs.get("sourcesProgress")
        if panel is not None:
            panel.update_progress(event)

    @Slot(object)
    def done(self, report: dict[str, Any]) -> None:
        _on_sources_updated(self.win, report)
        self.deleteLater()

    @Slot(str)
    def fail(self, message: str) -> None:
        _finish_sources_controls(self.win)
        panel = self.win.refs.get("sourcesProgress")
        if panel is not None:
            panel.fail(message)
        on_operation_error(self.win, "navRed", None, message)
        self.deleteLater()


def _finish_sources_controls(win: Any) -> None:
    from .i18n import t

    win._source_refresh_running = False
    win.refs["actualizarFuentesBtn"].setEnabled(True)
    win.refs["actualizarFuentesBtn"].setText(t("shadow.actualizar"))
    profile = win.refs.get("sourcesProfile")
    if profile is not None:
        profile.setEnabled(True)


def on_cancel_sources(win: Any) -> None:
    """Set the flag; in-flight HTTP may finish, no new request is issued."""
    event = getattr(win, "_source_cancel_event", None)
    if event is not None:
        event.set()
    panel = win.refs.get("sourcesProgress")
    if panel is not None and panel.running:
        panel.set_cancelling()


def on_actualizar(win: Any) -> None:
    from .i18n import t

    if getattr(win, "_source_refresh_running", False):
        return
    win._source_refresh_running = True
    cancel = Event()
    win._source_cancel_event = cancel
    problem = str(win.problem or "")
    profile_widget = win.refs.get("sourcesProfile")
    profile = str(profile_widget.currentData() or "general") if profile_widget else "general"
    if profile_widget is not None:
        profile_widget.setEnabled(False)
    panel = win.refs.get("sourcesProgress")
    if panel is not None:
        panel.begin()
    win.nav["navRed"].setChecked(False)
    r = win.refs
    _lock_mutators(win)
    win.nav["navRed"].set_state("running", "Adquiriendo fuentes...")
    r["actualizarFuentesBtn"].setEnabled(False)
    r["actualizarFuentesBtn"].setText(t("sources.loading"))
    bridge = _SourceRefreshBridge(win)
    win._source_refresh_bridge = bridge

    def _job() -> dict[str, Any]:
        # Adquisición REAL con deduplicación y cantidades reales (mandato §6).
        from ..intelligence.refresh import refresh_sources

        store = _refresh_store()
        try:
            return refresh_sources(
                _refresh_queries(problem),
                profile=profile,
                store=store,
                on_progress=worker.signals.progress.emit,
                cancel_event=cancel,
            )
        finally:
            store.close()

    worker = Worker(_job)
    worker.signals.progress.connect(bridge.progress)
    worker.signals.done.connect(bridge.done)
    worker.signals.fail.connect(bridge.fail)
    _start_worker(win, worker)


def _on_sources_updated(win: Any, report: dict[str, Any]) -> None:
    """Paint the real report. A cached run never refreshes the freshness stamp."""
    r = win.refs
    win.sources_report = report
    totals = report["totals"]
    status = report.get("state", "error" if totals["errores"] else "success")
    if status == "success" and report.get("network_acquisition", False):
        win.sources_updated_at = datetime.now()
    win.nav["navRed"].set_state("done" if status == "success" else "error")
    panel = r.get("sourcesProgress")
    if panel is not None:
        panel.finish(report)
    _finish_sources_controls(win)
    _activity(
        win,
        "cyan",
        f"Fuentes: {totals['documentos']} docs · {totals['nuevos']} nuevos · "
        f"{totals['duplicados']} duplicados · {totals['errores']} errores",
    )
    if totals["documentos"] == 0 and totals["errores"] > 0:
        _activity(win, "orange", "Ninguna fuente respondió: ver errores en win.sources_report")
    refresh_sources_freshness(win)
    _restore_buttons_after_op(win)


def refresh_sources_freshness(win: Any) -> None:
    from .i18n import t

    seg = win.footerSegs["fsFuentes"]
    r = win.refs
    report = getattr(win, "sources_report", None)
    if report and report.get("state") in {"error", "partial", "cancelled"}:
        key = {
            "error": "sources.error",
            "partial": "sources.partial",
            "cancelled": "sources.cancelled",
        }[report["state"]]
        seg.set_value(t(key))
        seg.set_freshness("warn")
        r["staleBand"].show()
        return
    if report and report.get("state") == "success" and not report.get("network_acquisition"):
        seg.set_value(t("sources.cached"))
        seg.set_freshness("warn")
        r["staleBand"].show()
        return
    if win.sources_updated_at is None:
        seg.set_value("Sin actualizar")
        seg.set_freshness("stale")
        r["staleBand"].show()
        return
    mins = int((datetime.now() - win.sources_updated_at).total_seconds() // 60)
    if mins < 60:
        seg.set_value(f"Hace {mins} min")
        seg.set_freshness("ok")
        r["staleBand"].hide()
    else:
        seg.set_value(f"Hace {mins // 60} h")
        seg.set_freshness("warn")
        r["staleBand"].show()


# ---------------------------------------------------------------------------
# S9 — ERROR DE OPERACIÓN
# ---------------------------------------------------------------------------
def show_error(win: Any, op: str, msg: str) -> None:
    win.errorBannerText.setText(f"Fallo en {op}: {msg.splitlines()[0][:160]}")
    win.errorBanner.show()


def on_operation_error(win: Any, nav_key: str, stage_key: str | None, msg: str) -> None:
    first = msg.splitlines()[0][:60]
    win.nav[nav_key].set_state("error", f"Error: {first}")
    if stage_key:
        win.refs["stages"][stage_key].set_state("error")
    show_error(win, win.nav[nav_key].text() or nav_key, msg)
    _activity(win, "error", f"Fallo en operación: {first}")
    _restore_buttons_after_op(win)


def _restore_buttons_after_op(win: Any) -> None:
    has_problem = bool(win.problem)
    has_packet = win.packet is not None
    _set_buttons(
        win,
        {
            "navNuevaIdea": True,
            "navGenerar": has_problem,
            "navInventar": has_problem,
            "navEvaluar": has_packet,
            "navRed": True,
            "navHistorial": True,
            "navBlackforge": True,
        },
    )


# ---------------------------------------------------------------------------
# S10 — BLACKFORGE (aplicación especializada independiente)
# ---------------------------------------------------------------------------
def on_hibrido(win: Any) -> None:
    """Ejecuta el pipeline híbrido completo: ensemble → cadena → adversarial."""
    from ..hybrid import run_hybrid

    win.nav["navSupra"].setChecked(False)
    if not win.problem:
        show_error(win, "Híbrido", "Define primero el problema base (Nueva idea).")
        return

    # Preparar packet para el pipeline híbrido.
    packet = {
        "original_query": win.problem,
        "mode": win.packet.get("mode", "criba") if win.packet else "criba",
        "central_problem": win.problem,
        "desired_outcome": win.packet.get("desired_outcome", "") if win.packet else "",
        "scope": win.packet.get("scope", "") if win.packet else "",
        "actors": win.packet.get("actors", []) if win.packet else [],
        "constraints": win.packet.get("constraints", []) if win.packet else [],
        "confirmed_facts": win.packet.get("confirmed_facts", []) if win.packet else [],
        "assumptions": win.packet.get("assumptions", []) if win.packet else [],
        "unknowns": win.packet.get("unknowns", []) if win.packet else [],
        "success_criteria": win.packet.get("success_criteria", []) if win.packet else [],
        "protected_assets": win.packet.get("protected_assets", []) if win.packet else [],
        "threat_actors": win.packet.get("threat_actors", []) if win.packet else [],
        "authorization_state": (
            win.packet.get("authorization_state", "pending") if win.packet else "pending"
        ),
        "innovation": win.packet.get("innovation", {}) if win.packet else {},
    }

    r = win.refs
    _lock_mutators(win)
    _suggest(win, None)
    win.nav["navSupra"].set_state("running", "Ejecutando pipeline híbrido...")
    r["stages"]["stageGenerar"].set_state("active", spinning=True)
    _activity(win, "cyan", "Pipeline híbrido iniciado (ensemble → cadena → adversarial)")

    worker = Worker(lambda: run_hybrid(packet, storage=win.store))
    worker.signals.done.connect(lambda result: _on_hibrido_done(win, result))
    worker.signals.fail.connect(
        lambda msg: on_operation_error(win, "navSupra", "stageGenerar", msg)
    )
    _start_worker(win, worker)


def _on_hibrido_done(win: Any, result: Any) -> None:
    """Muestra el resultado del pipeline híbrido en la GUI."""
    from ..hybrid import HybridResult

    if not isinstance(result, HybridResult):
        show_error(win, "Híbrido", "Resultado inesperado del pipeline")
        _restore_buttons_after_op(win)
        return

    r = win.refs
    win.nav["navSupra"].set_state("done")
    r["stages"]["stageGenerar"].set_state("done")
    r["connectors"][1].set_lit(True)
    r["stages"]["stageEvaluar"].set_state("done")
    r["connectors"][2].set_lit(True)
    r["stages"]["stageGuardar"].set_state("active")

    # Mostrar recomendación final.
    recommendation = result.final_recommendation or "Sin recomendación"
    confidence = result.final_confidence

    r["ideaTitle"].setText(recommendation[:120])
    summary = f"Pipeline híbrido completado. Confianza: {confidence}. "
    summary += f"Etapas: {', '.join(result.pipeline_stages_completed)}"
    if result.ensemble:
        summary += f". Acuerdos: {len(result.ensemble.strongest_agreements)}"
        summary += f". Emergentes: {len(result.ensemble.emergent_findings)}"
    r["ideaSummary"].setText(summary[:240])

    from .widgets import set_chip

    chip_kind = "eval" if confidence == "confirmed" else "exploracion"
    set_chip(r["ideaEstadoChip"], f"Híbrido: {confidence}", chip_kind)

    r["scoreGauge"].show()
    confidence_score = 0.8 if confidence == "confirmed" else 0.5
    r["scoreGauge"].set_score(confidence_score)
    r["scoreGauge"].set_percentile("Pipeline híbrido completado")

    # Actualizar métricas.
    stages_completed = len(result.pipeline_stages_completed)
    r["mOperadores"].set_value(f"{stages_completed}/3")
    r["mIdeas"].set_value(str(len(result.ensemble.candidate_solutions) if result.ensemble else 0))
    r["mBestScore"].set_value(confidence)

    _activity(
        win, "cyan", f"Pipeline híbrido completado: {recommendation[:60]} (confianza: {confidence})"
    )
    _restore_buttons_after_op(win)


def on_blackforge(win: Any) -> None:
    """Conmutación a BLACKFORGE (mandato §7): una vista activa y como máximo
    una generación activa. Con trabajo en curso NO se lanza el cambio: la
    ventana nunca se oculta dejando workers vivos (defecto 8)."""
    win.nav["navBlackforge"].setChecked(False)
    live = getattr(win, "_live_workers", [])
    if live:
        show_error(
            win,
            "BLACKFORGE",
            "Hay una generación en curso: espera a que termine o cancélala "
            "antes de cambiar de espacio. Estado: deteniendo generación.",
        )
        _activity(win, "orange", "Cambio a BLACKFORGE retenido: trabajo en curso")
        return
    win.show_blackforge_page()


def on_modelos(win: Any) -> None:
    """Open the shared local-model profile manager."""

    from ..model_config import active_model_label
    from .model_settings_dialog import open_model_settings

    win.nav["navModelos"].setChecked(False)
    if open_model_settings(win):
        win.footerSegs["fsModelo"].set_value(f"CRIBA {ENGINE_VERSION} · {active_model_label()}")
        _refresh_interpreter_selector(win)
        _activity(win, "cyan", f"Modelo activo: {active_model_label()}")


def _refresh_interpreter_selector(win: Any) -> None:
    """Reflect the active local model in the Generación interpreter selector."""
    from ..model_config import active_model_label, load_model_settings

    selector = getattr(win, "interpreter_selector", None)
    if selector is None:
        return
    try:
        settings = load_model_settings()
        if settings.enabled and settings.active_profile() is not None:
            label = active_model_label(settings)
            selector.setItemText(1, label)
            selector.setCurrentIndex(1)
        else:
            selector.setItemText(1, _t("shadow.interpreter.local"))
            selector.setCurrentIndex(0)
    except Exception:
        selector.setCurrentIndex(0)


def _on_interpreter_changed(win: Any, index: int) -> None:
    """Handle interpreter selector change from the Generación tab."""
    if index == 1:
        _activity(win, "cyan", "Intérprete local seleccionado")
    else:
        _activity(win, "cyan", "Intérprete Nous/Hermes seleccionado")


# ---------------------------------------------------------------------------
# ranking helpers
# ---------------------------------------------------------------------------
def on_tab_changed(win: Any, index: int) -> None:
    modes = ["", "top", "eval", "exploracion"]
    win.refs["rankingProxy"].set_mode(modes[index] if index < len(modes) else "")


def on_ver_todas(win: Any) -> None:
    win.refs["rankingTabs"].setCurrentIndex(0)
    win.refs["rankingProxy"].set_mode("")


# ---------------------------------------------------------------------------
# DESARROLLAR CON SUPRA (paridad con `inventar --dossier`)
# ---------------------------------------------------------------------------
def _supra_lookup_read(lookup: Any) -> dict[str, Any]:
    """Serialize the canonical GET response without collapsing state channels."""
    receipt = getattr(getattr(lookup, "posture", None), "criba_dossier_receipt", None)
    reason = "UNKNOWN"
    reason_kind = "UNKNOWN"
    if lookup.stage == "BLOCKED":
        checkpoints = getattr(lookup.posture, "checkpoints", [])
        if isinstance(checkpoints, list):
            for checkpoint in reversed(checkpoints):
                if isinstance(checkpoint, dict) and checkpoint.get("stage") == "BLOCKED":
                    declared = checkpoint.get("evidence_summary")
                    if isinstance(declared, str) and declared.strip():
                        reason = declared
                        if (checkpoint.get("actor") == "system:completion_gate"
                                and "verification must be PASS" in reason):
                            reason_kind = "VERIFICATION_GATE"
                        else:
                            reason_kind = "DECLARED_BLOCK"
                    break
    return {
        "block_reason": reason,
        "block_reason_kind": reason_kind,
        "status": lookup.status,
        "status_scope": lookup.status_scope,
        "completion_status": lookup.completion_status,
        "workflow_status": lookup.workflow_status,
        "verification_status": lookup.verification_status,
        "scientific_status": lookup.scientific_status,
        "secure_sandbox_status": lookup.secure_sandbox_status,
        "criba_planning_receipt_status": lookup.criba_planning_receipt_status,
        "criba_mechanism_execution_status": lookup.criba_mechanism_execution_status,
        "status_source": lookup.status_source,
        "persisted_artifact_status": lookup.persisted_artifact_status,
        "persisted_artifact_error_kind": lookup.persisted_artifact_error_kind,
        "stage": lookup.stage,
        "receipt": receipt.model_dump() if receipt else None,
    }


def _execute_supra_dossiers(
    dossiers: list[dict[str, Any]],
    client: Any | None = None,
) -> dict[str, Any]:
    """Execute prepared dossiers through the single canonical SupraClient."""
    from ..integrations import SupraClient, objective_from_dossier

    owned = client is None
    supra = client or SupraClient()
    try:
        health = supra.health()
        runs: list[dict[str, Any]] = []
        for dossier in dossiers:
            result = supra.run_project(
                objective=objective_from_dossier(dossier),
                domain="criba_blackforge",
                allow_disruptive=True,
                criba_dossier=dossier,
            )
            # GET is mandatory: POST success alone does not prove durable
            # readback, and is not what a reopened Shadow instance consumes.
            lookup = supra.get_project(result.project_id)
            runs.append(
                {
                    "dossier_id": dossier["dossier_id"],
                    "project_id": result.project_id,
                    "status": result.status,
                    "completion_status": result.completion_status,
                    "workflow_status": result.workflow_status,
                    "verification_status": result.verification_status,
                    "secure_sandbox_status": result.secure_sandbox_status,
                    "scientific_status": result.scientific_status,
                    "criba_mechanism_execution_status": (result.criba_mechanism_execution_status),
                    "stage": result.stage,
                    "read": _supra_lookup_read(lookup),
                }
            )
        return {
            "endpoint": supra.config.endpoint,
            "health": health.model_dump(),
            "dossiers": dossiers,
            "runs": runs,
        }
    finally:
        if owned:
            supra.close()


def _on_supra_dossiers_done(win: Any, report: dict[str, Any]) -> None:
    sheet = getattr(win, "invent_sheet", None)
    if sheet is None:
        return
    runs = report.get("runs", [])
    sheet["supra_runs"] = runs
    readbacks = sum(1 for item in runs if isinstance(item.get("read"), dict))
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        dossiers = report.get("dossiers", [])
        if dossiers:
            candidates.dossier_output.setPlainText(
                json.dumps(dossiers, ensure_ascii=False, indent=2)
            )
        candidates.supra_output.setPlainText(
            json.dumps(report, ensure_ascii=False, indent=2, default=str)
        )
        candidates.output_tabs.setCurrentWidget(candidates.supra_output)
    completed = sum(1 for item in runs if item.get("completion_status") == "COMPLETED")
    blocked = sum(1 for item in runs if item.get("completion_status") == "BLOCKED")
    sandbox_blocked = sum(
        1
        for item in runs
        if item.get("completion_status") == "BLOCKED"
        and item.get("secure_sandbox_status") != "ISOLATED_BOUND_PASS"
    )
    criba_not_executed = sum(
        1 for item in runs if item.get("criba_mechanism_execution_status") == "NOT_EXECUTED"
    )
    r = win.refs
    sandbox_note = f" · {sandbox_blocked} sin aislamiento acreditado" if sandbox_blocked else ""
    r["ideaSummary"].setText(
        f"SUPRA workflow: {completed} completado(s) · {blocked} bloqueado(s)"
        f"{sandbox_note} · GET/readback: {readbacks}/{len(runs)} · "
        f"mecanismo CRIBA NO EJECUTADO: {criba_not_executed}/{len(runs)}"
    )
    chip = "SUPRA workflow completado" if runs and blocked == 0 else "SUPRA bloqueado"
    set_chip(r["ideaEstadoChip"], chip, "exploracion")
    _activity(
        win,
        "cyan",
        f"SUPRA workflow real: {completed} completado(s), {blocked} bloqueado(s), "
        f"{sandbox_blocked} sin sandbox aislado; mecanismo CRIBA NOT_EXECUTED "
        f"en {criba_not_executed}/{len(runs)}. Verification, sandbox, completion "
        "y ejecución del mecanismo conservan estados separados.",
    )


def _on_supra_dossiers_failed(win: Any, message: str) -> None:
    r = win.refs
    r["ideaSummary"].setText("Dossier SUPRA conservado localmente · ejecución remota NO CONFIRMADA")
    set_chip(r["ideaEstadoChip"], "SUPRA pendiente", "exploracion")
    _activity(win, "amber", "SUPRA remoto no confirmado; dossier local preservado.")
    show_error(win, "SUPRA", message)


def on_desarrollar_supra(win: Any) -> None:
    """Prepare local dossiers, then execute them asynchronously through SupraClient."""
    sheet = getattr(win, "invent_sheet", None)
    if not sheet or not sheet.get("entries"):
        show_error(win, "SUPRA", "Genera candidatos con Inventar antes de desarrollar.")
        return
    propuestas = [
        entry for entry in sheet["entries"] if entry.get("estado_interpretacion") == "PROPUESTA"
    ]
    if not propuestas:
        show_error(
            win,
            "SUPRA",
            "Sin propuestas interpretadas: los candidatos están PENDIENTES "
            "(se requiere modelo) y no hay mecanismo que desarrollar.",
        )
        return
    from ..supra_dossier import guardar_dossier, preparar_dossier

    dossier_payloads: list[dict[str, Any]] = []
    for entry in propuestas:
        dossier = preparar_dossier(
            entry,
            sheet["query"],
            ficha_bloqueo=sheet.get("ficha_bloqueo"),
        )
        path = guardar_dossier(dossier)
        dossier_payloads.append(dossier)

    sheet["dossiers"] = [item["dossier_id"] for item in dossier_payloads]
    sheet["dossiers_path"] = str(path)
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.dossier_output.setPlainText(
            json.dumps(dossier_payloads, ensure_ascii=False, indent=2)
        )
        candidates.supra_output.clear()
        candidates.output_tabs.setCurrentWidget(candidates.dossier_output)
    r = win.refs
    r["ideaSummary"].setText(
        f"{len(dossier_payloads)} dossier(s) SUPRA preparados · enviando al servicio real…"
    )
    set_chip(r["ideaEstadoChip"], "SUPRA pendiente", "exploracion")
    _activity(
        win,
        "cyan",
        f"Desarrollar con SUPRA: {len(dossier_payloads)} dossier(s) preservados -> {path}",
    )

    worker = Worker(lambda: _execute_supra_dossiers(dossier_payloads))
    worker.signals.done.connect(lambda report: _on_supra_dossiers_done(win, report))
    worker.signals.fail.connect(lambda message: _on_supra_dossiers_failed(win, message))
    _start_worker(win, worker)


def _load_latest_supra(client: Any | None = None) -> dict[str, Any]:
    """Recover the latest persisted SUPRA project through LIST + canonical GET."""
    from ..integrations import SupraClient
    from ..supra_dossier import cargar_dossier

    owned = client is None
    supra = client or SupraClient()
    try:
        health = supra.health()
        listed = supra.list_projects(limit=1)
        if not listed.projects:
            return {
                "empty": True,
                "endpoint": supra.config.endpoint,
                "health": health.model_dump(),
            }
        newest = listed.projects[0]
        project_id = (
            newest.get("project_id")
            if isinstance(newest, dict)
            else getattr(newest, "project_id", "")
        )
        if not isinstance(project_id, str) or not project_id:
            raise ValueError("SUPRA listó un proyecto sin project_id")
        lookup = supra.get_project(project_id)
        read = _supra_lookup_read(lookup)
        # Recency is not identity: an unsent local draft may be newer than the
        # project recovered from SUPRA. Only its remote receipt binds a dossier.
        receipt = read.get("receipt") or {}
        dossier_id = receipt.get("criba_dossier_id")
        exact_id = (
            isinstance(dossier_id, str) and bool(dossier_id) and dossier_id == dossier_id.strip()
        )
        dossier = cargar_dossier(dossier_id) if exact_id else None
        identity_fields = {
            "candidate_id": "criba_candidate_id",
            "claim_id": "claim_id",
            "mechanism_version": "mechanism_version",
            "protocol_version": "protocol_version",
        }
        if dossier is not None and any(
            not dossier.get(local_key) or dossier.get(local_key) != receipt.get(remote_key)
            for local_key, remote_key in identity_fields.items()
        ):
            dossier = None
        return {
            "empty": False,
            "endpoint": supra.config.endpoint,
            "health": health.model_dump(),
            "project_id": project_id,
            "dossier": dossier,
            "read": read,
        }
    finally:
        if owned:
            supra.close()


def _on_supra_restore_done(win: Any, report: dict[str, Any]) -> None:
    if report.get("empty"):
        _activity(win, "blue", "SUPRA disponible · sin proyecto previo que recuperar")
        return
    candidates = getattr(win, "candidates", None)
    dossier = report.get("dossier")
    if candidates is not None:
        if dossier:
            candidates.dossier_output.setPlainText(
                json.dumps(dossier, ensure_ascii=False, indent=2)
            )
        else:
            # Missing/mismatched local evidence must not leave another case's
            # dossier visible beside this recovered project's remote receipt.
            candidates.dossier_output.clear()
        candidates.supra_output.setPlainText(
            json.dumps(report, ensure_ascii=False, indent=2, default=str)
        )
        candidates.output_tabs.setCurrentWidget(candidates.supra_output)
        candidates.show_state_only()
    read = report["read"]
    win.refs["ideaTitle"].setText(f"SUPRA recuperado · {report['project_id']}")
    win.refs["ideaSummary"].setText(
        f"Resultado PREVIO recuperado mediante GET de {_provenance_text(read)} · "
        f"status {read['status']} · stage {read['stage']} · "
        f"copia durable {_artifact_text(read)} · {_planning_status_text(read)}"
    )
    set_chip(
        win.refs["ideaEstadoChip"],
        f"SUPRA previo {read['status']} · GET",
        "exploracion",
    )
    win.nav["navSupra"].set_state("done", "resultado previo recuperado mediante GET")
    _activity(
        win,
        "cyan",
        f"Reapertura: proyecto {report['project_id']} recuperado mediante GET; "
        f"fuente {read['status_source']}, artefacto {read['persisted_artifact_status']}",
    )


def _on_supra_restore_failed(win: Any, message: str) -> None:
    _activity(win, "amber", f"No se pudo recuperar SUPRA al reabrir: {message[:120]}")
    show_error(win, "Recuperación SUPRA", message)


def on_restore_latest_supra(win: Any) -> None:
    """Start non-blocking recovery after launcher connected the real endpoint."""
    worker = Worker(_load_latest_supra)
    worker.signals.done.connect(lambda report: _on_supra_restore_done(win, report))
    worker.signals.fail.connect(lambda message: _on_supra_restore_failed(win, message))
    _start_worker(win, worker)


# ---------------------------------------------------------------------------
# Retro OBSERVED + memoria de outcomes + técnicas del canon (cadena G en UI)
# ---------------------------------------------------------------------------
def on_retro(win: Any) -> None:
    """Registrar un resultado OBSERVED (mismo canal que `criba retro`)."""
    win.nav["navRetro"].setChecked(True)
    from .dialogs import ask_retro

    try:
        data = ask_retro(win)
    finally:
        win.nav["navRetro"].setChecked(False)
    if not data:
        return
    _register_retro_for_test(
        win,
        tecnica=data["tecnica"],
        familia=data["familia"],
        resultado=data["resultado"],
        perfil=data["perfil"],
    )
    _activity(win, "blue", f"Outcome OBSERVED registrado: {data['tecnica']} → {data['resultado']}")
    _suggest(win, None)


def on_memoria(win: Any) -> None:
    """Panel de solo lectura de la memoria de outcomes."""
    win.nav["navMemoria"].setChecked(True)
    from .dialogs import show_outcome_memory

    try:
        show_outcome_memory(win)
    finally:
        win.nav["navMemoria"].setChecked(False)
    _suggest(win, None)


def on_red(win: Any) -> None:
    """Panel de Red de Ideas — grafo de relaciones entre ideas generadas."""
    win.nav["navRed"].setChecked(True)
    try:
        if not win.packet or not win.packet.get("innovation", {}).get("ideas"):
            show_error(win, "Red de Ideas", "Genera primero ideas (pestaña Generar).")
            return
        from ..scoring.network import IdeaNetwork

        ideas = win.packet["innovation"]["ideas"]
        network = IdeaNetwork()
        network.build_from_ideas(ideas)
        summary = network.summary()
        win.content_label.setText("Red de Ideas")
        win.content_sub.setText(
            f"Nodos: {summary['n_ideas']} | Relaciones: {summary['n_relationships']} | "
            f"Familias: {summary['n_families']}"
        )
    finally:
        win.nav["navRed"].setChecked(False)
    _suggest(win, None)


def _supra_health() -> dict[str, Any]:
    from ..integrations import SupraClient

    with SupraClient() as client:
        return {
            "endpoint": client.config.endpoint,
            "health": client.health().model_dump(),
        }


# ---------------------------------------------------------------------------
# M2 · SLICE VERTICAL REAL: CRIBA core -> dossier -> SUPRA real -> GET -> UI
# ---------------------------------------------------------------------------
def _selected_idea(win: Any) -> dict[str, Any] | None:
    """The REAL core idea the user selected, or the top-ranked one.

    Selection is by the stable idea id the ranking table already carries, so the
    dossier always describes the candidate the interface is showing. Falling back
    to the first ranked row is deterministic, not a guess.
    """
    packet = getattr(win, "packet", None)
    if not packet:
        return None
    ideas = (packet.get("innovation") or {}).get("ideas") or []
    if not ideas:
        return None
    selected = getattr(win._ctx, "selected_candidate_id", None) if hasattr(win, "_ctx") else None
    if selected:
        for idea in ideas:
            if str(idea.get("id")) == str(selected):
                return idea
    return ideas[0]


def _prepare_dossier_for_selected_idea(win: Any) -> dict[str, Any]:
    """Export the displayed interpretation; keep core-only compatibility."""
    from ..supra_dossier import preparar_dossier, preparar_dossier_desde_idea

    sheet = getattr(win, "invent_sheet", None)
    if sheet is not None:
        if sheet.get("query") != win.problem:
            raise ValueError("la interpretación pertenece a otro objetivo; vuelve a interpretar")
        entries = sheet.get("entries") or []
        index = win.candidates.interpretation_index
        if type(index) is not int or not 0 <= index < len(entries):
            raise ValueError("no hay una interpretación seleccionada")
        entry = entries[index]
        if entry.get("estado_interpretacion") != "PROPUESTA":
            raise ValueError(
                "la interpretación seleccionada está pendiente; "
                "no se sustituye por ejes"
            )
        for field in ("candidate_id", "hipotesis", "mecanismo", "prueba_concreta"):
            if not isinstance(entry.get(field), str) or not entry[field].strip():
                raise ValueError(f"propuesta interpretada sin {field}")
        protocol = entry.get("prueba")
        if not isinstance(protocol, dict):
            raise ValueError("propuesta interpretada sin prueba declarada")
        for field in (
            "metrica", "baseline", "umbral", "condicion_fracaso",
            "alternativa_explicativa", "resultado_favorable_mecanismo",
            "resultado_favorable_alternativa",
        ):
            if not isinstance(protocol.get(field), str) or not protocol[field].strip():
                raise ValueError(f"prueba interpretada sin {field}; no se rellena")
        return preparar_dossier(entry, sheet["query"], ficha_bloqueo=sheet.get("ficha_bloqueo"))

    idea = _selected_idea(win)
    if idea is None:
        raise ValueError("no hay candidatos del núcleo: pulsa «Generar ideas» antes de SUPRA")
    return preparar_dossier_desde_idea(idea, str(getattr(win, "problem", "") or ""))


def _execute_supra_vertical(
    dossier: dict[str, Any],
    project_id: str,
    client: Any | None = None,
) -> dict[str, Any]:
    """POST the dossier, then GET it back from SUPRA's real read path.

    The GET is not decoration: it is the only proof that the state survived
    persistence, and it is the path a consumer uses after a restart. Its
    channels are reported separately and are never collapsed into success.
    """
    from ..integrations import SupraClient, objective_from_dossier

    owned = client is None
    supra = client or SupraClient()
    try:
        health = supra.health()
        posted = supra.run_project(
            objective=objective_from_dossier(dossier),
            domain="criba_blackforge",
            allow_disruptive=True,
            project_id=project_id,
            criba_dossier=dossier,
        )
        lookup = supra.get_project(project_id)
        return {
            "endpoint": supra.config.endpoint,
            "health": health.model_dump(),
            "project_id": project_id,
            "post": posted.model_dump(),
            "read": _supra_lookup_read(lookup),
        }
    finally:
        if owned:
            supra.close()


def _provenance_text(read: dict[str, Any]) -> str:
    """Say where the served posture came from, in the words a reader sees.

    M3: the previous text said "leído del estado persistido" for every answer,
    including one served from SUPRA's in-process cache. That is the same
    unverified provenance claim K1 fixed on the server, reproduced one layer up
    in the interface, and the interface is what the user actually reads.
    """
    return (
        "el estado persistido"
        if read.get("status_source") == "PERSISTED_STATE"
        else "la caché del proceso SUPRA (copia durable sin verificar)"
    )


def _artifact_text(read: dict[str, Any]) -> str:
    """State the verdict on the durable copy, without softening it."""
    if read.get("persisted_artifact_status") == "UNVERIFIABLE":
        detail = {
            "CORRUPT_JSON": "JSON CORRUPTO",
            "INCOMPATIBLE_SCHEMA": "ESQUEMA INCOMPATIBLE",
            "UNREADABLE": "ARTEFACTO NO LEGIBLE",
        }.get(str(read.get("persisted_artifact_error_kind")))
        return f"NO VERIFICABLE ({detail})" if detail else "NO VERIFICABLE (CAUSA NO INFORMADA)"
    return {
        "VERIFIED_FROM_ARTIFACT": "verificada desde el artefacto",
        "MATCHES_CACHE": "verificada contra la caché",
        "DIVERGES_FROM_CACHE": "DIVERGE de la caché",
        "UNVERIFIABLE": "NO VERIFICABLE",
        "MISSING": "AUSENTE",
    }.get(str(read.get("persisted_artifact_status")), "no declarada")


def _planning_status_text(read: dict[str, Any]) -> str:
    """Expose planning limits; never infer relevance from a schema or a 2xx."""
    receipt = read.get("receipt") or {}
    context = receipt.get("interpretacion") or {}
    provenance = context.get("provenance") or {}
    assessment = provenance.get("planning_assessment") or {}
    origin = assessment.get("content_origin", "UNKNOWN")
    text = f"origen {origin} · pertinencia UNKNOWN · prueba propuesta, no validada"
    if read.get("workflow_status") == "BLOCKED":
        text += (f" · bloqueo {read.get('block_reason_kind', 'UNKNOWN')}: "
                 f"{read.get('block_reason', 'UNKNOWN')}")
    return text


def _on_supra_vertical_done(win: Any, report: dict[str, Any]) -> None:
    """Show the real SUPRA read-back state. BLOCKED stays BLOCKED."""
    win._supra_vertical_running = False
    r = win.refs
    read = report["read"]
    receipt = read.get("receipt") or {}
    r["ideaTitle"].setText(f"SUPRA {report['project_id']}")
    r["ideaSummary"].setText(
        f"SUPRA leído de {_provenance_text(read)} ({read['status_source']}): "
        f"status {read['status']} · stage {read['stage']} · "
        f"workflow {read['workflow_status']} · "
        f"verification {read['verification_status']} · "
        f"scientific {read['scientific_status']} · "
        f"sandbox {read['secure_sandbox_status']} · "
        f"dossier {read['criba_planning_receipt_status']} · "
        f"mecanismo CRIBA {read['criba_mechanism_execution_status']} · "
        f"copia durable {_artifact_text(read)} · {_planning_status_text(read)}"
    )
    if receipt:
        set_chip(
            r["ideaEstadoChip"],
            f"SUPRA {read['status']} ·Receipt preservado",
            "exploracion",
        )
    else:
        set_chip(r["ideaEstadoChip"], f"SUPRA {read['status']} ·Sin receipt", "exploracion")
    # El chip es el indicador de estado del panel. Sin encenderlo, el estado
    # real se escribía en un widget oculto y no llegaba a verse: el arranque
    # llama a set_detail_empty(True), que oculta el chip porque aún no hay
    # candidato. Se llama al método DECLARADO del widget, no a un getattr
    # inventado (un _reveal_state inexistente convertía el bug en un no-op
    # silencioso y la prueba pasaba igual, porque text() lee también lo oculto).
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.supra_output.setPlainText(
            json.dumps(report, ensure_ascii=False, indent=2, default=str)
        )
        candidates.output_tabs.setCurrentWidget(candidates.supra_output)
        candidates.show_state_only()
    _activity(
        win,
        "cyan",
        f"SUPRA real {report['endpoint']}: {read['status']}/{read['stage']} "
        f"(verificación {read['verification_status']}, científico "
        f"{read['scientific_status']}); estado leído de "
        f"{_provenance_text(read)}, copia durable {_artifact_text(read)}",
    )
    win.nav["navSupra"].set_state("done", f"{read['status']}/{read['stage']}")


def _on_supra_vertical_failed(win: Any, message: str) -> None:
    """Failure is shown as failure. No fabricated state on the error path."""
    win._supra_vertical_running = False
    win.nav["navSupra"].set_state("error", "SUPRA no disponible")
    set_chip(win.refs["ideaEstadoChip"], "SUPRA no confirmado", "exploracion")
    # El fallo Tambien tiene que verse: un chip de error escrito sobre un
    # widget oculto seria un fallo silencioso, que es peor que no avisar.
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.show_state_only()
    win.refs["ideaSummary"].setText("Dossier local preservado · ejecución SUPRA NO CONFIRMADA")
    _activity(win, "error", f"SUPRA no confirmado: {message.splitlines()[0][:120]}")
    show_error(win, "SUPRA", message)


def on_supra_vertical(win: Any) -> None:
    """One real vertical slice, pressed from the interface.

    CRIBA core (real) -> dossier (real) -> SupraClient (real) -> SUPRA API
    (real) -> persistence -> GET -> this window. No mock anywhere on the path.
    """
    import uuid

    # A second click while this dispatch is outstanding is the same user
    # attempt, not permission to create another remote project.
    if getattr(win, "_supra_vertical_running", False):
        return
    if not getattr(win, "problem", ""):
        show_error(win, "SUPRA", "Define primero el problema base (Nueva idea).")
        return
    try:
        from ..supra_dossier import guardar_dossier

        dossier = _prepare_dossier_for_selected_idea(win)
        # Persist before any remote effect: failure/reopen must not claim that
        # an in-memory-only dossier was preserved locally.
        guardar_dossier(dossier)
    except Exception as exc:  # noqa: BLE001 — el motivo real se muestra
        show_error(win, "SUPRA", f"No se pudo preparar o preservar el dossier: {exc}")
        return

    # SUPRA persists projects across runs, so the id must be unique per slice.
    project_id = "astram2" + uuid.uuid4().hex[:10]
    candidates = getattr(win, "candidates", None)
    if candidates is not None:
        candidates.dossier_output.setPlainText(json.dumps(dossier, ensure_ascii=False, indent=2))
        candidates.supra_output.clear()
        candidates.output_tabs.setCurrentWidget(candidates.dossier_output)
    r = win.refs
    r["ideaSummary"].setText(
        f"Dossier {dossier['dossier_id']} preparado · enviando a SUPRA real ({project_id})…"
    )
    set_chip(r["ideaEstadoChip"], "SUPRA pendiente", "exploracion")
    _activity(
        win,
        "cyan",
        f"Slice vertical: dossier {dossier['dossier_id']} -> proyecto SUPRA {project_id}",
    )
    win.nav["navSupra"].set_state("running", "Enviando a SUPRA…")

    worker = Worker(lambda: _execute_supra_vertical(dossier, project_id))
    worker.signals.done.connect(lambda report: _on_supra_vertical_done(win, report))
    worker.signals.fail.connect(lambda message: _on_supra_vertical_failed(win, message))
    win._supra_vertical_running = True
    _start_worker(win, worker)


def _on_supra_health(win: Any, report: dict[str, Any]) -> None:
    health = report["health"]
    win.content_label.setText("SUPRA Taskmaster")
    win.content_sub.setText(
        f"{health.get('status', 'unknown')} · {health.get('service', 'SUPRA')} "
        f"{health.get('version', '')} · {report['endpoint']}"
    )
    win.nav["navSupra"].setChecked(False)
    _activity(win, "cyan", f"SUPRA health OK · {report['endpoint']}")
    _suggest(win, None)


def _on_supra_health_failed(win: Any, message: str) -> None:
    win.nav["navSupra"].setChecked(False)
    win.content_label.setText("SUPRA Taskmaster")
    win.content_sub.setText("No disponible / autenticación requerida")
    _activity(win, "amber", "SUPRA health no confirmado.")
    show_error(win, "SUPRA", message)
    _suggest(win, None)


def on_supra(win: Any) -> None:
    """Panel SUPRA backed by the same canonical client used for execution."""
    win.nav["navSupra"].setChecked(True)
    win.content_label.setText("SUPRA Taskmaster")
    win.content_sub.setText("Comprobando servicio real…")
    worker = Worker(_supra_health)
    worker.signals.done.connect(lambda report: _on_supra_health(win, report))
    worker.signals.fail.connect(lambda message: _on_supra_health_failed(win, message))
    _start_worker(win, worker)


def on_tecnicas(win: Any) -> None:
    """Router + ejecución de técnicas del canon (mismos servicios que la CLI)."""
    win.nav["navTecnicas"].setChecked(True)
    from .dialogs import show_tecnicas

    try:
        show_tecnicas(win)
    finally:
        win.nav["navTecnicas"].setChecked(False)
    _suggest(win, None)


def _register_retro_for_test(
    _win: Any,
    *,
    tecnica: str,
    familia: str,
    resultado: str,
    perfil: str,
) -> None:
    """Ruta de trabajo de on_retro separada del diálogo (testeable).

    Misma validación que el CLI: técnica y familia no vacías.
    """
    from ..cli import _normalize_tecnica_id
    from ..intelligence.outcome_store import CHANNEL_OBSERVED, default_store

    if not tecnica.strip() or not familia.strip():
        raise ValueError("técnica y familia son obligatorias")
    canon = ""
    try:
        from ..intelligence.registry import TechniqueRegistry

        canon = TechniqueRegistry().canon_version or ""
    except Exception:  # noqa: BLE001 — sin canon, etiqueta vacía (como CLI)
        canon = ""
    default_store().record(
        profile=perfil,
        family=familia,
        technique_id=_normalize_tecnica_id(tecnica),
        channel=CHANNEL_OBSERVED,
        outcome=resultado,
        canon_version=canon,
    )


def _memory_rows_for_test(_win: Any) -> list[dict[str, Any]]:
    from ..intelligence.outcome_store import default_store

    return default_store().summary()


def _run_technique_for_test(
    _win: Any,
    *,
    technique_id: str,
    problem: str,
    params: dict[str, Any],
) -> dict[str, Any]:
    from ..intelligence.execution import execute_technique
    from ..intelligence.registry import TechniqueRegistry

    return execute_technique(TechniqueRegistry(), technique_id, problem, params=params)
