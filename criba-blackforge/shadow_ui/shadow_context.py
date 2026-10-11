"""ShadowActionContext — adaptador de compatibilidad ShadowWindow ↔ actions.py.

La ShadowWindow nueva (composición CRIBA_UI_FINAL) NO expone el contrato de la
CribaMainWindow antigua que ``criba.ui.actions`` consume. Este módulo CIERRA esa
brecha SIN modificar actions.py ni ningún motor:

    ShadowWindow → ShadowActionContext → actions.py (existente) → servicios

El contexto expone exactamente lo que actions.py/dialogs.py leen o escriben:
  nav (12 claves, protocolo NavButton), refs (28 claves), t (tokens), pool,
  footerSegs, sessionDot/sessionLabel/greetingSub, content_label/content_sub,
  errorBanner/errorBannerText, content_layout, show_blackforge_page y el estado
  compartido (store/packet/problem/saved_ids/sources_updated_at/invent_sheet...).

Cablea widgets REALES de la composición donde existen; donde no hay control
equivalente (stages/connectors/histograma/donut/footer segments) absorbe el
estado en sinks mínimos y registrables — nunca se inventa capacidad nueva.
"""
from __future__ import annotations

import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from criba.ui.i18n import t as _t
from criba.ui.ranking import COL_IDEA, RankingFilterProxy
from PySide6.QtCore import QProcess, QProcessEnvironment, Qt, QThreadPool
from PySide6.QtWidgets import QMessageBox, QPushButton, QVBoxLayout, QWidget


def _blackforge_launch_env() -> QProcessEnvironment:
    """Entorno del hijo BLACKFORGE.

    Hereda el entorno del proceso y añade ``src/`` al PYTHONPATH: el hijo se
    lanza como ``python -m criba.blackforge_gui`` y sin esto moría con
    ModuleNotFoundError (BLACKFORGE no abría desde su botón).
    """
    env = QProcessEnvironment.systemEnvironment()
    src_dir = str(Path(__file__).resolve().parents[1] / "src")
    current = env.value("PYTHONPATH")
    env.insert("PYTHONPATH", f"{src_dir}{os.pathsep}{current}" if current else src_dir)
    return env


def _set_candidate_count(label: Any, value: Any) -> None:
    """Contador de candidatos traducible (B1).

    Guarda el número en la propiedad ``count`` del widget para que el cambio de
    idioma reconstruya el texto sin perder el valor real.
    """
    try:
        count = int(value)
    except (TypeError, ValueError):
        count = 0
    label.setProperty("count", count)
    label.setText(_t("shadow.candidatos").format(n=count))


def _set_score_display(label: Any, value: Any) -> None:
    """§14: la ausencia de score se dice con palabras, no con un guion.

    El contrato canónico escribe "—" cuando no hay evaluación; en la composición
    shadow eso se muestra como "No evaluado" (nunca 0 ni un valor inventado).
    """
    text = str(value or "").strip()
    label.setText(_t("shadow.no_evaluado") if text in ("", "—", "-") else text)

# Cabeceras de columna de la composición CRIBA_UI_FINAL (la tabla del shadow).
# RankingModel.canonical COLUMNS queda intacto; sólo se traduce la cabecera.
# ``SHADOW_COLUMNS`` conserva el texto ES por defecto (contrato previo) y las
# claves i18n permiten el cambio de idioma en caliente.
SHADOW_COLUMNS = ("#", "Idea", "Score interno", "Convergencia",
                  "Impacto estimado", "Estado")
SHADOW_COLUMN_KEYS = ("shadow.col.idx", "shadow.col.idea", "shadow.col.score",
                      "shadow.col.conv", "shadow.col.impact", "shadow.col.estado")


class ShadowRankingProxy(RankingFilterProxy):
    """Proxy canónico de filtrado + cabeceras de la composición shadow.

    Hereda el comportamiento real (set_mode/filterAcceptsRow) de
    criba.ui.ranking.RankingFilterProxy sin modificarlo.
    """

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if (role == Qt.ItemDataRole.DisplayRole
                and orientation == Qt.Orientation.Horizontal
                and 0 <= section < len(SHADOW_COLUMN_KEYS)):
            return _t(SHADOW_COLUMN_KEYS[section])
        return super().headerData(section, orientation, role)


class _SegAdapter:
    """Adapta un bloque REAL del pie al contrato footerSeg (set_value/freshness).

    §27: cuando existe un elemento visual equivalente, el estado se mapea ahí en
    vez de absorberse en un sink invisible.
    """

    def __init__(self, block: Any) -> None:
        self.block = block

    def set_value(self, value: Any) -> None:
        label = getattr(self.block, "_sub_label", None)
        if label is not None:
            label.setText(str(value))

    def set_freshness(self, state: str) -> None:
        from shadow_window import SUCCESS, TEXT_MUTED, TEXT_SUB, WARNING

        colors = {"ok": SUCCESS, "warn": WARNING, "stale": TEXT_MUTED}
        label = getattr(self.block, "_sub_label", None)
        if label is not None:
            label.setStyleSheet(
                f"font-size: 9px; color: {colors.get(state, TEXT_SUB)};"
                " background: transparent;")


class _Sink:
    """Absorbe llamadas de estado sin widget equivalente en la composición.

    Registra cada llamada (auditable en tests). Métodos de retorno numérico
    usados por actions.py (p.ej. donutLegend.count()) reciben None, que es
    falsy y corta los bucles de vaciado de forma segura.
    """

    def __init__(self, name: str = "sink") -> None:
        self.name = name
        self.recorded: list[tuple[str, tuple, dict]] = []

    def __getattr__(self, item: str) -> Callable[..., None]:
        def _absorb(*args: Any, **kwargs: Any) -> None:
            self.recorded.append((item, args, kwargs))
        return _absorb


class _ValueSink:
    """set_value/set_freshness con callback real opcional (p.ej. labels)."""

    def __init__(self, on_value: Callable[[str], None] | None = None) -> None:
        self.value: str | None = None
        self.freshness: str | None = None
        self._on_value = on_value

    def set_value(self, value: str) -> None:
        self.value = str(value)
        if self._on_value is not None:
            self._on_value(self.value)

    def set_freshness(self, level: str) -> None:
        self.freshness = level


class _ScoreSink:
    """Equivalente mínimo del scoreGauge antiguo (sin gauge en la composición)."""

    def __init__(self, on_score: Callable[[float], None] | None = None) -> None:
        self.score: float | None = None
        self.percentile: str | None = None
        self._on_score = on_score

    def show(self) -> None:  # el score de la tarjeta 3 siempre es visible
        pass

    def hide(self) -> None:
        pass

    def set_score(self, value: float, animate: bool = True) -> None:
        del animate
        self.score = float(value)
        if self._on_score is not None:
            self._on_score(self.score)

    def set_percentile(self, text: str) -> None:
        self.percentile = text


class _NavShim:
    """Protocolo NavButton (set_state/set_suggested/setChecked/text) sobre un
    QPushButton real de la composición shadow. El estado se registra y se
    expone como tooltip; NO se restila el botón (presentación preservada)."""

    def __init__(self, button: QPushButton | None, key: str) -> None:
        self.button = button
        self.key = key
        self.state: str = "idle"
        self.state_msg: str | None = None
        self.suggested: bool = False

    # -- protocolo usado por actions.py --
    def setChecked(self, on: bool) -> None:  # noqa: N802 — API Qt
        if self.button is not None:
            self.button.setChecked(on)

    def setEnabled(self, on: bool) -> None:  # noqa: N802
        if self.button is not None:
            self.button.setEnabled(on)

    def isEnabled(self) -> bool:  # noqa: N802
        return bool(self.button is not None and self.button.isEnabled())

    def set_state(self, state: str, msg: str | None = None) -> None:
        self.state = state
        self.state_msg = msg
        if self.button is not None:
            self.button.setToolTip(f"{state}" + (f": {msg}" if msg else ""))

    def set_suggested(self, on: bool) -> None:
        self.suggested = on

    def text(self) -> str:
        return self.button.text() if self.button is not None else self.key


class ShadowActionContext:
    """Fachada compatible con criba.ui.actions para la ShadowWindow."""

    def __init__(self, win: Any, database: Any = None) -> None:
        self.win = win

        # ---- Estado compartido (fuente de verdad; la ventana delega aquí) ----
        from criba.storage import Storage

        self.store = Storage(database)
        self.packet: dict[str, Any] | None = None
        self.problem: str = ""
        self.saved_ids: set[str] = set()
        self.sources_updated_at: datetime | None = None
        self.invent_sheet: dict[str, Any] | None = None
        self.sources_report: dict[str, Any] | None = None
        self._live_workers: list[Any] = []
        self._progress_label: Any = None
        self._bf_process: QProcess | None = None
        self._bf_embedded: QWidget | None = None
        self._bf_window: Any = None
        self._bf_prev_widget: Any = None
        self.selected_candidate_id: str | None = None
        self.interpreter_cancel_requested: bool = False

        # ---- Dependencias Qt / theme ----
        self.pool = QThreadPool.globalInstance()
        from criba.ui.tokens import load_tokens

        self.t = load_tokens()

        self._build_nav()
        self._build_refs()
        self._build_status_sinks()
        self._wire_table_selection()
        # NOTA: apply_initial_state() lo invoca ShadowWindow tras adjuntarse
        # el contexto (necesita la delegación win.nav → ctx ya activa).

    # ------------------------------------------------------------------ nav
    def _build_nav(self) -> None:
        sb = self.win.sidebar.buttons
        tc = self.win.topcards
        real: dict[str, QPushButton] = {
            # 4 críticos: botones reales de las tarjetas superiores
            "navNuevaIdea": tc.btn_nueva,
            "navGenerar": tc.btn_gen,
            "navInventar": tc.btn_inv,
            "navEvaluar": tc.btn_eval,
            # 8 accesos del sidebar
            "navRed": sb["navRed"],
            "navHistorial": sb["navHistorial"],
            "navRetro": sb["navRetro"],
            "navMemoria": sb["navMemoria"],
            "navTecnicas": sb["navTecnicas"],
            "navModelos": sb["navModelos"],
            "navBlackforge": sb["navBlackforge"],
            "navSupra": sb["navSupra"],
        }
        self._nav_buttons = real
        self.nav: dict[str, _NavShim] = {
            key: _NavShim(btn, key) for key, btn in real.items()
        }

    # ----------------------------------------------------------------- refs
    def _build_refs(self) -> None:
        tc = self.win.topcards
        cand = self.win.candidates
        rp = self.win.right_panel

        self.refs: dict[str, Any] = {
            # detalle de idea seleccionada (widgets reales)
            "ideaTitle": cand.detail_title,
            "ideaSummary": cand.detail_desc,
            "ideaEstadoChip": cand.detail_chip,
            # score real de la tarjeta "Evaluación interna"
            "scoreGauge": _ScoreSink(
                on_score=lambda v: tc.score_val.setText(f"{v:.2f}")),
            "mOperadores": _ValueSink(),
            "mIdeas": _ValueSink(
                on_value=lambda v: _set_candidate_count(tc.cand_label, v)),
            "mConvergencia": _ValueSink(),
            "mBestScore": _ValueSink(
                on_value=lambda v: _set_score_display(tc.score_val, v)),
            # workflow stages/connectors: no existen en la composición → sinks
            "stages": {
                k: _Sink(k) for k in (
                    "stageProblema", "stageGenerar", "stageEvaluar",
                    "stageGuardar", "stageEvolucionar")
            },
            "connectors": [_Sink(f"connector{i}") for i in range(4)],
            # tabla de ranking REAL (modelo/proxy canónicos)
            "rankingTable": cand.view,
            "rankingEmpty": _Sink("rankingEmpty"),
            "rankingModel": cand.model,
            "rankingProxy": cand.proxy,
            "rankingTabs": cand.tabs,
            # gráficos no presentes en la composición → sinks
            "scoreHistogram": _Sink("scoreHistogram"),
            "catDonut": _Sink("catDonut"),
            "donutLegend": _Sink("donutLegend"),
            # fuentes
            "actualizarFuentesBtn": tc.btn_act,
            "sourcesProgress": tc.sources_progress,
            "sourcesProfile": tc.sources_profile,
            "staleBand": tc.stale_warn,
            "sourceBars": {},
            # actividad reciente (layout real dentro de la tarjeta)
            "activityList": rp.activity_lay,
            # §19: el estado "sin eventos" es un label REAL (visible), no un sink.
            "activityEmpty": getattr(rp, "activity_empty_label", _Sink("activityEmpty")),
            # campana: la actividad real alimenta las notificaciones
            "notification_sink": self.win.record_notification,
            # botones reales del panel derecho / candidatos
            "supraBtn": rp.supra,
            "historialCompletoBtn": rp.ver_hist,
            "verTodasBtn": cand.ver_todas,
            "irBlackforgeBtn": rp.ir_bf,
            # banner de error S9 (oculto en reposo)
            "errorDismissBtn": self.win.errorDismissBtn,
        }

    # ------------------------------------------------------- status widgets
    def _build_status_sinks(self) -> None:
        cand = self.win.candidates
        self.footerSegs = {
            k: _ValueSink() for k in (
                "fsModelo", "fsSesion", "fsIdeas", "fsConvergencia",
                "fsUltima", "fsFuentes")
        }
        # No hay dot/label/greeting equivalentes en la composición: sinks.
        self.sessionDot = _Sink("sessionDot")
        self.sessionLabel = _Sink("sessionLabel")
        self.greetingSub = _Sink("greetingSub")
        # §26/§27: donde SÍ existe un widget real, el estado se mapea ahí (nada
        # de sinks invisibles para información que el usuario debe ver).
        footer = getattr(self.win, "footer", None)
        if footer is not None:
            session_label = getattr(getattr(footer, "session_block", None),
                                    "_title_label", None)
            if session_label is not None:
                self.sessionLabel = session_label
            session_dot = getattr(getattr(footer, "session_block", None),
                                  "_dot_label", None)
            if session_dot is not None:
                self.sessionDot = session_dot
            if getattr(footer, "sources_block", None) is not None:
                self.footerSegs["fsFuentes"] = _SegAdapter(footer.sources_block)
        # títulos reales del panel "Candidatos y evaluación"
        self.content_label = cand.title
        self.content_sub = cand.sub
        self.errorBanner = self.win.errorBanner
        self.errorBannerText = self.win.errorBannerText
        # layout real donde actions.py inserta el label transitorio de progreso
        self.content_layout = cand.lay

    # ------------------------------------------------ table → detalle real
    def _wire_table_selection(self) -> None:
        view = self.refs["rankingTable"]
        sm = view.selectionModel()
        if sm is not None:
            sm.currentChanged.connect(self._on_current_candidate)

    def _on_current_candidate(self, current: Any, _previous: Any) -> None:
        """proxy index → mapToSource → fila real del RankingModel (UserRole)."""
        if not current.isValid():
            return
        proxy = self.refs["rankingProxy"]
        model = self.refs["rankingModel"]
        source = proxy.mapToSource(current)
        row = model.data(model.index(source.row(), COL_IDEA),
                         Qt.ItemDataRole.UserRole)
        if not isinstance(row, dict):
            return
        self.selected_candidate_id = row.get("id")
        from criba.ui.ranking import RankingModel
        from criba.ui.widgets import set_chip

        cand = self.win.candidates
        cand.set_detail_empty(False)   # §12: hay candidato real seleccionado
        cand.detail_title.setText(str(row.get("titulo", ""))[:120])
        cand.detail_desc.setText(str(row.get("descripcion", ""))[:240])
        estado = str(row.get("estado", "exploracion"))
        set_chip(cand.detail_chip,
                 RankingModel.ESTADO_TEXT.get(estado, estado), estado)

    # ------------------------------------------------------------- estado S1
    def apply_initial_state(self) -> None:
        """Estado inicial equivalente a S1 SIN llamar enter_s1: enter_s1 oculta
        rankingTable y sobrescribe las labels ilustrativas de la maqueta
        (composición CRIBA_UI_FINAL). Aquí sólo se aplica la máquina de estados
        funcional: botones habilitados/deshabilitados + frescor de fuentes."""
        from criba.ui import actions as _actions

        _actions._set_buttons(self.win, {
            "navNuevaIdea": True,
            "navGenerar": False,   # requiere problema base
            "navInventar": False,  # requiere problema base
            "navEvaluar": False,   # requiere packet
            "navRed": True,
            "navHistorial": True,
            "navBlackforge": True,
            "navSupra": True,
        })
        _actions.refresh_sources_freshness(self.win)

    def sync_problem_input(self, value: str) -> None:
        """Efecto lateral real: el problema definido aparece en el input."""
        header = getattr(self.win, "header", None)
        if header is not None and value:
            header.problem_input.setText(str(value))

    # ---------------------------------------------------------- BLACKFORGE
    def show_blackforge_page(
        self, history_packet: dict[str, Any] | None = None
    ) -> None:
        """BLACKFORGE integrado como pestaña en Shadow (premisa: sin aislamiento).

        Embebe ``BlackforgeWindow`` en el área de contenido en lugar de lanzarla
        como proceso hijo que oculta la ventana. Si el embed falla (p.ej. el
        motor no importa), degrada al bridge de proceso hijo SIN romper.
        """
        del history_packet  # compatibilidad con on_historial
        if self._bf_embedded is not None:
            self._toggle_blackforge_embedded()
            return
        try:
            self._show_blackforge_embedded()
        except Exception:  # noqa: BLE001 - degradar, nunca romper la app
            self._show_blackforge_child()

    def _show_blackforge_embedded(self) -> None:
        """Inserta BlackforgeWindow como widget dentro del contenido de Shadow."""
        from criba.ui.blackforge_window import BlackforgeWindow

        container = QWidget(self.win)
        lay = QVBoxLayout(container)
        lay.setContentsMargins(0, 0, 0, 0)
        bf = BlackforgeWindow(self.win.database if hasattr(self.win, "database") else None,
                              query=self.problem or "")
        lay.addWidget(bf)
        # Guardar el contenido previo para poder volver (toggle).
        self._bf_prev_widget = self.content_layout.parentWidget()
        # Vaciar el contenido actual y poner BLACKFORGE.
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
        self.content_layout.addWidget(container)
        self._bf_embedded = container
        self._bf_window = bf

    def _toggle_blackforge_embedded(self) -> None:
        """Vuelve de BLACKFORGE al contenido de CRIBA (toggle del sidebar)."""
        if self._bf_embedded is None:
            return
        self.content_layout.removeWidget(self._bf_embedded)
        self._bf_embedded.deleteLater()
        self._bf_embedded = None
        self._bf_window = None
        # Re-mostrar el contenido de CRIBA que se ocultó.
        for i in range(self.content_layout.count()):
            pass
        if self._bf_prev_widget is not None:
            for child in self._bf_prev_widget.findChildren(QWidget):
                child.show()

    def _show_blackforge_child(self) -> None:
        """Camino original: lanzar BLACKFORGE como proceso hijo (fallback)."""
        if (self._bf_process is not None
                and self._bf_process.state() != QProcess.ProcessState.NotRunning):
            self.win.hide()
            return

        from criba.ui.app_bridge import (
            BlackforgeLaunchError,
            resolve_blackforge_launch,
        )

        try:
            launch = resolve_blackforge_launch()
        except BlackforgeLaunchError as exc:
            QMessageBox.warning(self.win, "CRIBA · BLACKFORGE", str(exc))
            return

        process = QProcess(self.win)
        process.setProgram(launch.program)
        arguments = list(launch.arguments)
        if self.problem:
            arguments.extend(("--query", self.problem[:20_000]))
        process.setArguments(arguments)
        if launch.arguments:
            process.setWorkingDirectory(
                str(Path(__file__).resolve().parents[1]))
            env = _blackforge_launch_env()
            process.setProcessEnvironment(env)
        else:
            process.setWorkingDirectory(str(Path(launch.program).parent))
        process.started.connect(self.win.hide)
        process.finished.connect(self._on_bf_finished)
        process.errorOccurred.connect(self._on_bf_error)
        self._bf_process = process
        process.start()

    def _on_bf_finished(self, exit_code: int, exit_status: Any) -> None:
        del exit_code, exit_status
        process = self._bf_process
        self._bf_process = None
        if process is not None:
            process.deleteLater()
        self.win.show()
        self.win.raise_()
        self.win.activateWindow()

    def _on_bf_error(self, error: Any) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            process = self._bf_process
            detail = process.errorString() if process is not None else str(error)
            self._bf_process = None
            QMessageBox.warning(
                self.win, "CRIBA · BLACKFORGE",
                f"No se pudo iniciar BLACKFORGE:\n{detail}",
            )
            self.win.show()
