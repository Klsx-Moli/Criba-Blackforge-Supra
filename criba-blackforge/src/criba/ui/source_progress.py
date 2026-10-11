"""Live acquisition status and a crisp, DPI-independent neon HUD."""

from __future__ import annotations

import weakref
from typing import Any

from PySide6.QtCore import QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .i18n import on_change, t

# The mark is drawn as vectors relative to this reference edge, so growing the
# widget costs no bitmap memory and keeps every stroke crisp at any DPI.
HUD_REFERENCE = 48
HUD_MIN = 48
HUD_MAX = 132

SOURCE_NAMES = {
    "crossref": "Crossref",
    "github": "GitHub",
    "wikipedia": "Wikipedia",
    "google_patents": "Google Patents",
    "cisa_kev": "CISA KEV",
    "mitre_attack": "MITRE ATT&CK",
    "arxiv": "arXiv",
    "openalex": "OpenAlex",
    "epo": "EPO",
    "clinicaltrials": "ClinicalTrials",
    "nsf_awards": "NSF",
}


class NeonHUD(QWidget):
    """Native vector animation inspired by the supplied circular cyan mark.

    Rendering at the actual device resolution avoids a sprite sheet's resampling
    and memory cost. The timer runs only while the widget is visible and active.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sourcesHud")
        # Preferred = the whole available edge; the layout may still shrink it to
        # HUD_MIN, but it must never be pinned to a fixed square.
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(HUD_MIN, HUD_MIN)
        self.setMaximumSize(HUD_MAX, HUD_MAX)
        self.setAccessibleName(t("sources.loading"))
        self.angle = 0
        self.active = False
        self.reduced_motion = False
        self.timer = QTimer(self)
        self.timer.setInterval(50)
        self.timer.timeout.connect(self._advance)

    def set_active(self, active: bool) -> None:
        self.active = active
        if active and self.isVisible() and not self.reduced_motion:
            self.timer.start()
        else:
            self.timer.stop()
        self.update()

    def _advance(self) -> None:
        self.angle = (self.angle + 6) % 360
        self.update()

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        self.set_active(self.active)

    def hideEvent(self, event: Any) -> None:
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        # Normalise to the reference edge so the mark scales with the widget
        # instead of being clipped or leaving dead space around it.
        scale = min(self.width(), self.height()) / HUD_REFERENCE
        painter.scale(scale, scale)
        cyan = QColor("#00D7E9")
        painter.setPen(QPen(QColor(0, 215, 233, 38), 1))
        painter.drawEllipse(QRectF(-21, -21, 42, 42))
        for radius, width, offset, span in ((18, 3.2, 0, 240), (12, 1.1, 170, 225)):
            painter.setPen(
                QPen(cyan, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            )
            painter.drawArc(
                QRectF(-radius, -radius, radius * 2, radius * 2),
                (self.angle + offset) * 16,
                span * 16,
            )
        painter.save()
        painter.rotate(-self.angle)
        painter.setPen(QPen(QColor("#91F7FF"), 1))
        for position in (-1, 1):
            painter.drawLine(-2, position * 20, 2, position * 20)
        painter.restore()
        painter.setPen(QPen(cyan, 1))
        painter.setBrush(QColor(0, 215, 233, 32))
        painter.drawEllipse(QRectF(-5, -5, 10, 10))
        painter.setBrush(cyan)
        painter.drawEllipse(QRectF(-1.5, -1.5, 3, 3))
        painter.end()


class SourceProgress(QWidget):
    """Bounded card with actual per-source states, counts and cancellation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("sourcesProgress")
        self.rows: dict[str, tuple[QLabel, QLabel]] = {}
        self.states: dict[str, str] = {}
        self.running = False
        self._last_events: dict[str, dict[str, Any]] = {}
        self._last_counter: tuple[int, int] | None = None
        self._report: dict[str, Any] | None = None
        self._message_key = "sources.waiting"
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        header = QHBoxLayout()
        header.setSpacing(8)
        self.hud = NeonHUD(self)
        header.addWidget(self.hud, 3)
        header_text = QVBoxLayout()
        header_text.setSpacing(2)
        self.label = QLabel(t("sources.waiting"))
        self.label.setWordWrap(True)
        self.label.setMinimumWidth(0)
        self.label.setTextFormat(Qt.TextFormat.PlainText)
        self.current_query = QLabel("")
        self.current_query.setTextFormat(Qt.TextFormat.PlainText)
        self.current_query.setWordWrap(True)
        self.current_query.setStyleSheet("color: #00D7E9;")
        self.current_query.setVisible(False)
        header_text.addWidget(self.label)
        header_text.addWidget(self.current_query)
        header.addLayout(header_text, 2)
        layout.addLayout(header)
        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setMinimumHeight(54)
        # No ceiling: the per-source list uses the physical space it is given.
        self.scroll_area.setMaximumHeight(16777215)
        self.body = QWidget()
        self.grid = QGridLayout(self.body)
        self.grid.setContentsMargins(0, 0, 4, 0)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(4)
        self.grid.setColumnStretch(0, 1)
        self.scroll_area.setWidget(self.body)
        layout.addWidget(self.scroll_area)
        self.counter = QLabel()
        self.counter.setProperty("caption", True)
        self.counter.setWordWrap(True)
        self.counter.setTextFormat(Qt.TextFormat.PlainText)
        layout.addWidget(self.counter)
        self.cancel = QPushButton(t("sources.cancel"))
        self.cancel.setProperty("ghost", True)
        layout.addWidget(self.cancel)
        self.hide()
        reference = weakref.ref(self)

        def translate() -> None:
            widget = reference()
            if widget is not None:
                widget._translate()

        on_change(translate)

    def _translate(self) -> None:
        self.label.setText(t(self._message_key))
        self.hud.setAccessibleName(t("sources.loading"))
        self.cancel.setText(t("sources.cancel"))
        for source_id, (_, status) in self.rows.items():
            if source_id not in self._last_events:
                status.setText(t("sources.queued"))
        for event in list(self._last_events.values()):
            self.update_progress(event)
        if self._report is not None:
            self._set_summary(self._report)
        elif self._last_counter is not None:
            done, total = self._last_counter
            self.counter.setText(t("sources.queries").format(done=done, total=total))

    def set_cancelling(self) -> None:
        self._message_key = "sources.cancelling"
        self.label.setText(t(self._message_key))
        self.cancel.setEnabled(False)

    def begin(self) -> None:
        for pair in self.rows.values():
            for label in pair:
                self.grid.removeWidget(label)
                label.deleteLater()
        self.rows.clear()
        self.states.clear()
        self._last_events.clear()
        self._last_counter = None
        self._report = None
        self._message_key = "sources.loading"
        self.running = True
        self.label.setText(t(self._message_key))
        self.current_query.clear()
        self.current_query.setVisible(False)
        self.counter.clear()
        self.cancel.setText(t("sources.cancel"))
        self.cancel.setEnabled(True)
        self.cancel.show()
        self.show()
        self.hud.set_active(True)

    def _row(self, source_id: str) -> tuple[QLabel, QLabel]:
        if source_id not in self.rows:
            name = QLabel(SOURCE_NAMES.get(source_id, source_id))
            name.setTextFormat(Qt.TextFormat.PlainText)
            name.setWordWrap(True)
            status = QLabel(t("sources.queued"))
            status.setTextFormat(Qt.TextFormat.PlainText)
            status.setWordWrap(True)
            index = len(self.rows)
            self.grid.addWidget(name, index, 0)
            self.grid.addWidget(status, index, 1)
            self.rows[source_id] = (name, status)
        return self.rows[source_id]

    def update_progress(self, event: dict[str, Any]) -> None:
        source_id = str(event.get("source_id", ""))
        phase = event.get("phase", "")
        if phase == "started":
            for planned in event.get("source_ids", []):
                self._row(str(planned))
        if source_id:
            self._last_events[source_id] = event
            _, status = self._row(source_id)
            state = str(event.get("state", "running"))
            self.states[source_id] = state
            summary = event.get("summary", {})
            docs = int(summary.get("documents", event.get("documents", 0)))
            errors = int(summary.get("errores", 0))
            if phase == "source_completed":
                key = (
                    "sources.partial"
                    if state == "partial"
                    else "sources.error"
                    if errors
                    else "sources.done"
                )
                if state == "cancelled":
                    key = "sources.cancelled"
                cached = int(summary.get("cached_queries", 0))
                detail = (
                    t("sources.cached") if cached and not summary.get("network_queries") else t(key)
                )
                status.setText(detail + f" · {docs} docs")
                status.setStyleSheet("color: #FFB45A;" if errors else "color: #77DDBA;")
            else:
                completed_for_source = event.get("source_completed_queries", 0)
                total_for_source = event.get("source_total_queries", 0)
                text = t("sources.querying")
                if total_for_source:
                    text += f" {completed_for_source}/{total_for_source} · {docs} docs"
                status.setText(text)
                status.setStyleSheet("color: #00D7E9;")
            if phase == "query_started":
                # Which source is running right now, and on what: the user asked
                # to SEE the source being updated, not infer it from a counter.
                query = str(event.get("query") or "")
                if source_id and query:
                    self.current_query.setText(
                        t("sources.current_query").format(
                            source=SOURCE_NAMES.get(source_id, source_id), query=query
                        )
                    )
                    self.current_query.setVisible(True)
            elif phase in {"query_completed", "source_completed", "completed"}:
                self.current_query.setVisible(False)
            error_messages = summary.get("errors", [])
            if error_messages:
                status.setToolTip("\n".join(str(e) for e in error_messages[:3]))
        completed = event.get("completed_queries")
        total = event.get("total_queries")
        if isinstance(completed, int) and isinstance(total, int):
            self._last_counter = (completed, total)
            self.counter.setText(t("sources.queries").format(done=completed, total=total))

    def finish(self, report: dict[str, Any]) -> None:
        self.running = False
        self.hud.set_active(False)
        self.cancel.hide()
        self.current_query.setVisible(False)
        self._report = report
        for summary in report.get("per_source", []):
            self.update_progress(
                {
                    "phase": "source_completed",
                    "source_id": summary["source_id"],
                    "state": summary.get("state", "done"),
                    "summary": summary,
                }
            )
        self._set_summary(report)

    def _set_summary(self, report: dict[str, Any]) -> None:
        totals = report.get("totals", {})
        self.counter.setText(
            t("sources.summary").format(
                docs=totals.get("documentos", 0),
                new=totals.get("nuevos", 0),
                changed=totals.get("modificados", 0),
                errors=totals.get("errores", 0),
            )
        )
        status = report.get("state", "success")
        key = {
            "cancelled": "sources.cancelled",
            "error": "sources.error",
            "partial": "sources.partial",
        }.get(status, "sources.done")
        if status == "success" and not report.get("network_acquisition", False):
            key = "sources.cached"
        self._message_key = key
        self.label.setText(t(key))

    def fail(self, message: str) -> None:
        self.running = False
        self.hud.set_active(False)
        self.cancel.hide()
        self.current_query.setVisible(False)
        self._message_key = "sources.error"
        self.label.setText(t("sources.error"))
        self.counter.setText(message.splitlines()[0][:180])
