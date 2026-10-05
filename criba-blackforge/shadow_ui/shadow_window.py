"""ShadowWindow — reproducción PySide6 de alta fidelidad de CRIBA_UI_FINAL.

Estructura exacta de la imagen de referencia:
  HORIZONTAL: [SidebarWidget] | [Right content]
  Right content (vertical): HeaderWidget → TopCardsWidget →
    QSplitter(CandidatesWidget | RightPanelWidget) → FooterWidget
"""
from __future__ import annotations

import math
import json
import random
from pathlib import Path
from typing import Any

import criba.ui.actions as actions
from criba.ui.i18n import on_change as _i18n_on_change
from criba.ui.i18n import t as _t
from criba.ui.i18n import toggle as _i18n_toggle
from criba.ui.ranking import RankingModel
from loading_indicator import LoadingIndicator
from PySide6.QtCore import QPoint, QPointF, QRectF, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QTableView,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from shadow_context import (
    ShadowActionContext,
    ShadowRankingProxy,
    _set_candidate_count,
)

# ---- i18n (B1): los textos visibles siguen al idioma activo ----------------
# Cada widget traducible se registra UNA vez; i18n.on_change re-aplica todo en
# caliente (sin reconstruir la ventana). Los objetos C++ ya destruidos (ventanas
# cerradas en tests) se descartan al primer fallo.
_I18N_TEXTS: list[tuple[Any, str]] = []          # setText(clave)
_I18N_PLACEHOLDERS: list[tuple[Any, str]] = []   # setPlaceholderText(clave)
_I18N_GLYPHS: list[tuple[Any, str, str]] = []    # (widget, glifo, clave)
_I18N_CALLBACKS: list[Any] = []                  # textos compuestos (modelo, pie)


def bind_text(widget: Any, key: str) -> Any:
    """Registra ``widget`` para que su texto siga al idioma activo."""
    _I18N_TEXTS.append((widget, key))
    _apply_text(widget, key)
    return widget


def bind_placeholder(widget: Any, key: str) -> Any:
    _I18N_PLACEHOLDERS.append((widget, key))
    widget.setPlaceholderText(_t(key))
    return widget


def bind_glyph(widget: Any, glyph: str, key: str) -> Any:
    """Texto con glifo delante (botones de navegación, idioma)."""
    _I18N_GLYPHS.append((widget, glyph, key))
    widget.setText(f"{glyph}{_t(key)}")
    return widget


def bind_callback(callback: Any) -> Any:
    """Textos compuestos: el widget los reconstruye desde su propio estado."""
    _I18N_CALLBACKS.append(callback)
    return callback


def _apply_text(widget: Any, key: str) -> None:
    texto = _t(key)
    if "{n}" in texto:
        texto = texto.format(n=widget.property("count") or 0)
    widget.setText(texto)


def apply_language() -> None:
    """Re-aplica todos los textos registrados (lo llama i18n.on_change)."""
    for widget, key in list(_I18N_TEXTS):
        try:
            _apply_text(widget, key)
        except RuntimeError:  # objeto C++ destruido: fuera del registro
            _I18N_TEXTS.remove((widget, key))
    for widget, key in list(_I18N_PLACEHOLDERS):
        try:
            widget.setPlaceholderText(_t(key))
        except RuntimeError:
            _I18N_PLACEHOLDERS.remove((widget, key))
    for widget, glyph, key in list(_I18N_GLYPHS):
        try:
            widget.setText(f"{glyph}{_t(key)}")
        except RuntimeError:
            _I18N_GLYPHS.remove((widget, glyph, key))
    for callback in list(_I18N_CALLBACKS):
        try:
            callback()
        except RuntimeError:
            _I18N_CALLBACKS.remove(callback)


_i18n_on_change(apply_language)


# ---- Design tokens ----
BG_APP = "#0A0E14"
BG_SIDEBAR = "#0A0E14"
BG_PANEL = "#0D1520"
BG_CARD = "#0D1920"
BG_INPUT = "#0E1A28"
BG_TABLE_ROW = "#0C141C"
BORDER = "#1A2430"
BORDER_ACTIVE = "#00DDF2"
ACCENT = "#00DDF2"
ACCENT_SOFT = "#0A2A35"
TEXT = "#E0E8F0"
TEXT_SUB = "#7890A8"
TEXT_MUTED = "#506070"
SUCCESS = "#00CC88"
WARNING = "#CC9922"
INFO = "#4488CC"
BADGE_GREEN_BG = "#0A2820"
BADGE_BLUE_BG = "#0A1828"

NAV_ITEMS = [
    ("navRed", "⬡", "shadow.nav.red", "shadow.nav.red.sub"),
    ("navHistorial", "◷", "shadow.nav.historial", ""),
    ("navRetro", "▣", "shadow.nav.retro", ""),
    ("navMemoria", "☰", "shadow.nav.memoria", ""),
    ("navTecnicas", "⚗", "shadow.nav.tecnicas", ""),
    ("navModelos", "◉", "shadow.nav.modelos", ""),
    ("navBlackforge", "△", "shadow.nav.blackforge", ""),
    ("navSupra", "⚛", "shadow.nav.supra", "shadow.nav.supra.sub"),
]


def build_shadow_qss() -> str:
    return f"""
    QMainWindow, QWidget {{
        background-color: {BG_APP}; color: {TEXT};
        font-family: 'Segoe UI', sans-serif; font-size: 12px;
    }}
    QFrame[card="true"] {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0E1A24, stop:1 #0B141C);
        border: 1px solid #143039;
        border-radius: 12px;
    }}
    QLabel {{ background: transparent; color: {TEXT}; }}
    QLabel[h1="true"] {{ font-size: 16px; font-weight: 700; }}
    QLabel[h2="true"] {{ font-size: 13px; font-weight: 600; }}
    QLabel[caption="true"] {{ font-size: 10px; color: {TEXT_SUB}; background: transparent; }}
    QLabel[muted="true"] {{ font-size: 11px; color: {TEXT_MUTED}; background: transparent; }}
    QPushButton {{
        background: {BG_CARD}; border: 1px solid {BORDER};
        border-radius: 6px; padding: 7px 16px; color: {TEXT}; font-size: 12px;
    }}
    QPushButton:hover {{ border-color: {BORDER_ACTIVE}; background: #0E1E2A; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; border-color: {BORDER}; background: {BG_APP}; }}
    QPushButton[accent="true"] {{
        background: {ACCENT_SOFT}; border: 1px solid {BORDER_ACTIVE};
        color: {ACCENT}; font-weight: 600;
    }}
    QPushButton[accent="true"]:hover {{ background: #0E3A48; }}
    QPushButton[ghost="true"] {{
        background: transparent; border: 1px solid {BORDER}; color: {TEXT_SUB};
    }}
    QPushButton[ghost="true"]:hover {{ border-color: {BORDER_ACTIVE}; color: {TEXT}; }}
    QPushButton[success="true"] {{
        background: transparent; border: 1px solid {SUCCESS}; color: {SUCCESS};
    }}
    QPushButton[success="true"]:hover {{ background: #0A2820; }}
    QPushButton[navigation="true"] {{
        background: rgba(11, 29, 39, 218); border: 1px solid #1B5665;
        border-radius: 8px; color: {ACCENT}; font-size: 18px; font-weight: 600;
        padding: 0px;
    }}
    QPushButton[navigation="true"]:hover {{
        background: rgba(14, 58, 72, 235); border-color: {ACCENT};
    }}
    QPushButton[navigation="true"]:disabled {{
        background: rgba(10, 20, 28, 150); color: {TEXT_MUTED};
        border-color: {BORDER};
    }}
    QPushButton[save_action="true"] {{
        background: rgba(8, 42, 33, 185); border: 1px solid {SUCCESS};
        border-radius: 8px; color: {SUCCESS}; font-weight: 600;
    }}
    QPushButton[save_action="true"]:hover {{ background: rgba(10, 58, 43, 225); }}
    QLabel[interpretation_status="true"] {{
        color: {ACCENT}; font-size: 11px; font-weight: 600;
        background: rgba(11, 47, 60, 150); border: 1px solid #1B5665;
        border-radius: 8px; padding: 7px 12px;
    }}
    QPlainTextEdit[interpretation_active="true"] {{
        background: #0B1C25; border: 1px solid #1B5665; color: #D4EAF0;
    }}
    QComboBox {{
        background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 6px;
        padding: 6px 12px; color: {TEXT}; font-size: 12px;
    }}
    QComboBox::drop-down {{ border: none; width: 20px; }}
    QTabWidget::pane {{ border: none; background: transparent; }}
    QTabBar::tab {{
        background: {BG_CARD}; color: {TEXT_SUB}; padding: 7px 18px;
        font-size: 12px; border: 1px solid {BORDER}; border-radius: 6px; margin-right: 6px;
    }}
    QTabBar::tab:selected {{
        color: {ACCENT}; border-color: {BORDER_ACTIVE}; background: {ACCENT_SOFT};
    }}
    QTabBar::tab:hover {{ color: {TEXT}; }}
    QTableWidget, QTableView {{
        background: transparent; border: none; gridline-color: transparent;
        color: {TEXT}; font-size: 12px;
    }}
    QTableWidget::item, QTableView::item {{ padding: 8px 6px; border-bottom: 1px solid {BORDER}; }}
    QTableWidget::item:selected, QTableView::item:selected {{ background: {ACCENT_SOFT}; }}
    QHeaderView::section {{
        background: transparent; color: {TEXT_MUTED}; font-size: 10px;
        font-weight: 500; border: none; border-bottom: 1px solid {BORDER}; padding: 8px 6px;
    }}
    QLineEdit {{
        background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 8px;
        padding: 10px 16px; color: {TEXT}; font-size: 13px;
    }}
    QLineEdit:focus {{ border-color: {BORDER_ACTIVE}; }}
    QPlainTextEdit {{
        background: {BG_INPUT}; border: 1px solid {BORDER}; border-radius: 6px;
        padding: 8px; color: {TEXT_SUB};
        font-family: 'Cascadia Code', 'Consolas', monospace; font-size: 11px;
    }}
    QPlainTextEdit:focus {{ border-color: {BORDER_ACTIVE}; }}
    QScrollArea {{ border: none; background: transparent; }}
    QSplitter::handle {{ background: {BORDER}; width: 1px; }}
    """


def _card(title: str, icon: str = "", i18n: str = "") -> tuple[QFrame, QVBoxLayout]:
    frame = QFrame()
    frame.setProperty("card", True)
    lay = QVBoxLayout(frame)
    lay.setContentsMargins(16, 14, 16, 14)
    lay.setSpacing(10)
    header = QHBoxLayout()
    if icon:
        header.addWidget(_icon_label(icon, 18))
    tl = QLabel(title)
    tl.setProperty("h2", True)
    if i18n:
        bind_text(tl, i18n)
    header.addWidget(tl)
    header.addStretch()
    lay.addLayout(header)
    return frame, lay


def _badge(text: str, color: str, bg: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"font-size: 10px; padding: 3px 10px; border-radius: 10px;"
                      f"color: {color}; background: {bg}; border: 1px solid {color}44;")
    lbl.setFixedHeight(22)
    return lbl


def _paint_landscape(w: int, h: int) -> QPixmap:
    pm = QPixmap(w, h)
    pm.fill(QColor("#050810"))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    grad = QLinearGradient(0, 0, 0, h)
    grad.setColorAt(0, QColor("#050810"))
    grad.setColorAt(0.6, QColor("#0A141E"))
    grad.setColorAt(1, QColor("#0A1E1E"))
    p.fillRect(0, 0, w, h, grad)
    for layer, (color, y_off, alpha) in enumerate([
        ("#0C1A20", 0.50, 0.5), ("#0E2428", 0.65, 0.7),
        ("#0A2A24", 0.78, 0.9), ("#082220", 0.90, 1.0),
    ]):
        c = QColor(color)
        c.setAlphaF(alpha)
        p.setBrush(c)
        p.setPen(Qt.PenStyle.NoPen)
        pts = [(0, h)]
        for i in range(w + 1):
            y = h * y_off + math.sin(i * 0.015 + layer * 2.5) * h * 0.07 \
                + math.sin(i * 0.004 + layer) * h * 0.04
            pts.append((i, y))
        pts.append((w, h))
        p.drawPolygon(QPolygonF([QPointF(x, y) for x, y in pts]))
    random.seed(7)
    p.setPen(QColor(ACCENT))
    for _ in range(30):
        x, y = random.randint(0, w), random.randint(int(h * 0.4), h - 2)
        p.drawPoint(x, y)
    p.end()
    return pm


# ---------------------------------------------------------------------------
# Iconos vectoriales + paisaje real (la referencia usa iconos de contorno)
# ---------------------------------------------------------------------------

ASSETS_DIR = Path(__file__).resolve().parent / "assets"


def _landscape_pixmap(w: int, h: int) -> QPixmap:
    """Paisaje de la referencia: recorte nítido del screenshot, escalado."""
    src = ASSETS_DIR / "sidebar_landscape.png"
    pm = QPixmap(str(src)) if src.is_file() else QPixmap()
    if pm.isNull():
        return _paint_landscape(w, h)
    return pm.scaled(w, h, Qt.AspectRatioMode.IgnoreAspectRatio,
                     Qt.TransformationMode.SmoothTransformation)


def _icon_pixmap(kind: str, size: int = 18, color: str = ACCENT) -> QPixmap:
    """Icono vectorial monocromo dibujado con QPainter (sin emoji)."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color))
    pen.setWidthF(max(1.2, size / 11.0))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = float(size)
    c = s / 2.0

    if kind == "network":
        nodes = [(c, s * 0.20), (s * 0.20, s * 0.80), (s * 0.80, s * 0.80)]
        for a, b in ((0, 1), (0, 2), (1, 2)):
            p.drawLine(QPointF(*nodes[a]), QPointF(*nodes[b]))
        for x, y in nodes:
            p.drawEllipse(QPointF(x, y), s * 0.11, s * 0.11)
    elif kind == "globe":
        p.drawEllipse(QPointF(c, c), s * 0.38, s * 0.38)
        p.drawEllipse(QRectF(c - s * 0.16, c - s * 0.38, s * 0.32, s * 0.76))
        p.drawLine(QPointF(s * 0.12, c), QPointF(s * 0.88, c))
    elif kind == "bell":
        path = QPainterPath()
        path.moveTo(s * 0.24, s * 0.66)
        path.lineTo(s * 0.30, s * 0.34)
        path.cubicTo(s * 0.30, s * 0.12, s * 0.70, s * 0.12, s * 0.70, s * 0.34)
        path.lineTo(s * 0.76, s * 0.66)
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.20, s * 0.66), QPointF(s * 0.80, s * 0.66))
        p.drawLine(QPointF(c, s * 0.74), QPointF(c, s * 0.80))
    elif kind == "shield":
        path = QPainterPath()
        path.moveTo(c, s * 0.12)
        path.lineTo(s * 0.86, s * 0.30)
        path.lineTo(c, s * 0.90)
        path.lineTo(s * 0.14, s * 0.30)
        path.closeSubpath()
        p.drawPath(path)
        p.drawPolyline(QPolygonF([QPointF(s * 0.32, s * 0.46), QPointF(s * 0.45, s * 0.60),
                                  QPointF(s * 0.70, s * 0.34)]))
    elif kind == "ban":
        p.drawEllipse(QPointF(c, c), s * 0.36, s * 0.36)
        p.drawLine(QPointF(s * 0.26, s * 0.74), QPointF(s * 0.74, s * 0.26))
    elif kind == "info":
        p.drawEllipse(QPointF(c, c), s * 0.36, s * 0.36)
        p.drawLine(QPointF(c, s * 0.28), QPointF(c, s * 0.32))
        p.drawLine(QPointF(c, s * 0.44), QPointF(c, s * 0.70))
    elif kind == "doc":
        path = QPainterPath()
        path.moveTo(s * 0.22, s * 0.12)
        path.lineTo(s * 0.60, s * 0.12)
        path.lineTo(s * 0.80, s * 0.32)
        path.lineTo(s * 0.80, s * 0.88)
        path.lineTo(s * 0.22, s * 0.88)
        path.closeSubpath()
        p.drawPath(path)
        p.drawLine(QPointF(s * 0.60, s * 0.12), QPointF(s * 0.60, s * 0.32))
        p.drawLine(QPointF(s * 0.60, s * 0.32), QPointF(s * 0.80, s * 0.32))
        for y in (0.48, 0.60, 0.72):
            p.drawLine(QPointF(s * 0.34, s * y), QPointF(s * 0.68, s * y))
    elif kind == "bolt":
        p.drawPolyline(QPolygonF([QPointF(s * 0.56, s * 0.10), QPointF(s * 0.28, s * 0.54),
                                  QPointF(s * 0.48, s * 0.54), QPointF(s * 0.42, s * 0.90),
                                  QPointF(s * 0.72, s * 0.44), QPointF(s * 0.52, s * 0.44),
                                  QPointF(s * 0.56, s * 0.10)]))
    elif kind == "chart":
        for x, top in ((0.24, 0.52), (0.44, 0.30), (0.64, 0.42)):
            p.drawLine(QPointF(s * x, s * 0.84), QPointF(s * x, s * top))
        p.drawLine(QPointF(s * 0.16, s * 0.86), QPointF(s * 0.84, s * 0.86))
    elif kind == "archive":
        p.drawRect(QRectF(s * 0.16, s * 0.30, s * 0.68, s * 0.56))
        p.drawLine(QPointF(s * 0.12, s * 0.18), QPointF(s * 0.88, s * 0.18))
        p.drawLine(QPointF(s * 0.12, s * 0.18), QPointF(s * 0.16, s * 0.30))
        p.drawLine(QPointF(s * 0.88, s * 0.18), QPointF(s * 0.84, s * 0.30))
        p.drawLine(QPointF(s * 0.42, s * 0.52), QPointF(s * 0.58, s * 0.52))
    elif kind == "clipboard":
        p.drawRect(QRectF(s * 0.22, s * 0.16, s * 0.56, s * 0.72))
        p.drawRect(QRectF(s * 0.38, s * 0.08, s * 0.24, s * 0.14))
        for y in (0.42, 0.56, 0.70):
            p.drawLine(QPointF(s * 0.34, s * y), QPointF(s * 0.66, s * y))
    elif kind == "clock":
        p.drawEllipse(QPointF(c, c), s * 0.38, s * 0.38)
        p.drawLine(QPointF(c, c), QPointF(c, s * 0.30))
        p.drawLine(QPointF(c, c), QPointF(s * 0.68, c))
    elif kind == "mountain":
        p.drawPolyline(QPolygonF([QPointF(s * 0.08, s * 0.80), QPointF(s * 0.36, s * 0.30),
                                  QPointF(s * 0.52, s * 0.60), QPointF(s * 0.66, s * 0.44),
                                  QPointF(s * 0.92, s * 0.80), QPointF(s * 0.08, s * 0.80)]))
        p.drawPolyline(QPolygonF([QPointF(s * 0.44, s * 0.50), QPointF(s * 0.38, s * 0.64),
                                  QPointF(s * 0.50, s * 0.64), QPointF(s * 0.44, s * 0.78)]))
    elif kind == "flask":
        p.drawPolyline(QPolygonF([QPointF(s * 0.40, s * 0.14), QPointF(s * 0.60, s * 0.14),
                                  QPointF(s * 0.60, s * 0.44), QPointF(s * 0.80, s * 0.84),
                                  QPointF(s * 0.20, s * 0.84), QPointF(s * 0.40, s * 0.44),
                                  QPointF(s * 0.40, s * 0.14)]))
        p.drawLine(QPointF(s * 0.32, s * 0.62), QPointF(s * 0.68, s * 0.62))
    else:
        p.drawEllipse(QPointF(c, c), s * 0.30, s * 0.30)
    p.end()
    return pm


def _icon_label(kind: str, size: int = 18, color: str = ACCENT) -> QLabel:
    lbl = QLabel()
    lbl.setPixmap(_icon_pixmap(kind, size, color))
    lbl.setFixedSize(size, size)
    lbl.setStyleSheet("background: transparent;")
    return lbl


def _glow(widget: QWidget, color: str = ACCENT, blur: int = 26) -> None:
    """Halo suave: la referencia tiene glow en los botones principales."""
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, 0)
    c = QColor(color)
    c.setAlpha(150)
    eff.setColor(c)
    widget.setGraphicsEffect(eff)


def _footer_block(kind: str, title: str, sub: str = "",
                  icon_color: str = ACCENT, dot: str = "") -> QWidget:
    """Bloque del pie: icono de contorno + título + subtítulo (o punto de estado).

    Expone las etiquetas reales (box._title_label / box._sub_label) para que el
    pie pueda reflejar estado real en vez de quedarse con el texto de maqueta.
    """
    box = QWidget()
    lay = QHBoxLayout(box)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(8)
    lay.addWidget(_icon_label(kind, 16, icon_color))
    txt = QVBoxLayout()
    txt.setSpacing(0)
    t = QLabel(title)
    t.setStyleSheet(f"font-size: 10px; color: {TEXT}; background: transparent;")
    txt.addWidget(t)
    box._title_label = t
    if sub:
        s = QLabel(sub)
        s.setStyleSheet(f"font-size: 9px; color: {TEXT_SUB}; background: transparent;")
        txt.addWidget(s)
        box._sub_label = s
    elif dot:
        d = QLabel("●")
        d.setStyleSheet(f"font-size: 7px; color: {dot}; background: transparent;")
        txt.addWidget(d)
        box._dot_label = d
    lay.addLayout(txt)
    return box


# ---------------------------------------------------------------------------
# Sidebar — 8 accesos + logo + paisaje + tarjeta BLACKFORGE
# ---------------------------------------------------------------------------

class _ClickableCard(QFrame):
    """Tarjeta clicable real (override C++ virtual, no lambda de instancia:
    PySide6 no despacha eventos a atributos Python del objeto)."""

    def __init__(self, on_click, parent=None) -> None:
        super().__init__(parent)
        self._on_click = on_click

    def mousePressEvent(self, event) -> None:  # noqa: N802 — API Qt
        if event.button() == Qt.MouseButton.LeftButton and self._on_click:
            self._on_click()
        super().mousePressEvent(event)


class SidebarWidget(QWidget):
    def __init__(self, win: ShadowWindow) -> None:
        super().__init__()
        self.win = win
        self.setFixedWidth(264)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        # Logo
        logo_row = QHBoxLayout()
        logo_row.setContentsMargins(14, 16, 14, 4)
        hex_l = QLabel("⟨C⟩")
        hex_l.setStyleSheet(
            f"color: {ACCENT}; font-size: 26px; font-weight: 800; "
            "background: transparent;"
        )
        logo_row.addWidget(hex_l)
        name_box = QVBoxLayout()
        name_l = QLabel("CRIBA")
        name_l.setStyleSheet(
            f"font-size: 18px; font-weight: 800; color: {TEXT}; "
            "letter-spacing: 3px; background: transparent;"
        )
        name_box.addWidget(name_l)
        sub_l = QLabel("DESCUBRIR PARA DECIDIR")
        sub_l.setStyleSheet(
            f"font-size: 6px; color: {TEXT_MUTED}; letter-spacing: 2px; "
            "background: transparent;"
        )
        bind_text(sub_l, "shadow.brand_sub")
        name_box.addWidget(sub_l)
        logo_row.addLayout(name_box)
        lay.addLayout(logo_row)

        # Nav (8 botones)
        self.buttons: dict[str, QPushButton] = {}
        for i, (key, glyph, key_label, _key_sub) in enumerate(NAV_ITEMS):
            btn = QPushButton(f"{glyph}  {_t(key_label)}")
            bind_glyph(btn, f"{glyph}  ", key_label)
            # el glyph cian se estiliza via QSS
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(42)
            if i == 0:
                btn.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding: 0 18px;"
                    f"border-left: 3px solid {ACCENT}; background: {ACCENT_SOFT};"
                    f"color: {ACCENT}; font-weight: 600; font-size: 12px; "
                    "border-radius: 0; }"
                )
            else:
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding: 0 18px;"
                    "border: none; border-left: 3px solid transparent;"
                    f"color: {TEXT_SUB}; font-size: 12px; border-radius: 0; "
                    "background: transparent; }"
                    f"QPushButton:hover {{ color: {TEXT}; background: {ACCENT_SOFT}; }}"
                )
            btn.clicked.connect(lambda checked, k=key: self.win._nav(k))
            lay.addWidget(btn)
            self.buttons[key] = btn

        lay.addStretch()

        # Paisaje real (recorte de la referencia) + tarjeta BLACKFORGE encima,
        # abajo: composición exacta de la referencia.
        bottom = QWidget()
        bottom.setFixedHeight(381)
        bottom_lay = QGridLayout(bottom)
        bottom_lay.setContentsMargins(0, 0, 0, 0)
        bottom_lay.setSpacing(0)
        landscape = QLabel()
        landscape.setPixmap(_landscape_pixmap(264, 381))
        landscape.setScaledContents(True)
        bottom_lay.addWidget(landscape, 0, 0)

        # Tarjeta BLACKFORGE
        # Target 25: tarjeta BLACKFORGE clicable → bridge real (on_blackforge)
        bf = _ClickableCard(lambda: actions.on_blackforge(self.win))
        bf.setStyleSheet("background: rgba(13, 21, 32, 236);"
                         f" border: 1px solid {BORDER}; border-radius: 8px; margin: 10px;")
        bf_lay = QHBoxLayout(bf)
        bf_lay.setContentsMargins(10, 8, 10, 8)
        bf_lay.setSpacing(4)
        bf_lay.addWidget(_icon_label("mountain", 18))
        bf_info = QVBoxLayout()
        bf_info.setSpacing(1)
        bf_name = QLabel("BLACKFORGE")
        bf_name.setStyleSheet(
            f"font-size: 9px; font-weight: 700; color: {TEXT}; "
            "background: transparent;"
        )
        bf_info.addWidget(bf_name)
        bf_sub = QLabel("Espacio especializado")
        bf_sub.setStyleSheet(f"font-size: 7px; color: {TEXT_SUB}; background: transparent;")
        bind_text(bf_sub, "shadow.bf_card.sub")
        bf_info.addWidget(bf_sub)
        bf_lay.addLayout(bf_info, stretch=1)
        bf_arrow = QLabel("→")
        bf_arrow.setFixedWidth(12)
        bf_arrow.setStyleSheet(f"color: {ACCENT}; background: transparent;")
        bf_lay.addWidget(bf_arrow)
        bf.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bf_card = bf
        bottom_lay.addWidget(bf, 0, 0, Qt.AlignmentFlag.AlignBottom
                             | Qt.AlignmentFlag.AlignHCenter)
        lay.addWidget(bottom)


# ---------------------------------------------------------------------------
# Header — input problema + modelo + ES + notificaciones
# ---------------------------------------------------------------------------

class HeaderWidget(QWidget):
    def __init__(self, win: ShadowWindow) -> None:
        super().__init__()
        self.win = win
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 6)
        lay.setSpacing(10)

        # Input problema
        prob_box = QVBoxLayout()
        prob_label = QLabel("Problema actual")
        prob_label.setProperty("caption", True)
        bind_text(prob_label, "shadow.problema")
        self.prob_label = prob_label
        prob_box.addWidget(prob_label)
        self.problem_input = QLineEdit()
        self.problem_input.setPlaceholderText(
            "Reducir el impacto de las baterías sin aumentar el coste ni "
            "comprometer el suministro."
        )
        bind_placeholder(self.problem_input, "shadow.problema.placeholder")
        self.problem_input.setFixedHeight(42)
        # §16: el input es un BORRADOR explícito; no crea estado científico por sí
        # solo. Enter lo aplica por la vía CANÓNICA (la misma que "Nueva idea"),
        # así lo que el usuario ve y lo que consumen las acciones coinciden.
        self.problem_input.returnPressed.connect(self._apply_problem_draft)
        self.problem_input.editingFinished.connect(self._sync_draft_state)
        self.problem_input.textChanged.connect(self._sync_draft_state)
        prob_box.addWidget(self.problem_input)
        lay.addLayout(prob_box, stretch=1)

        model_btn = QPushButton("  Modelo local · …")
        model_btn.setIcon(QIcon(_icon_pixmap("network", 16)))
        model_btn.setProperty("ghost", True)
        model_btn.setFixedHeight(36)
        model_btn.clicked.connect(self._open_modelos)
        self.model_btn = model_btn
        self.refresh_model_label()
        bind_callback(self.refresh_model_label)
        lay.addWidget(model_btn)

        es_btn = QPushButton("  ES")
        es_btn.setIcon(QIcon(_icon_pixmap("globe", 16)))
        es_btn.setProperty("ghost", True)
        es_btn.setFixedHeight(36)
        es_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        es_btn.setToolTip("Cambiar idioma ES/EN")
        es_btn.clicked.connect(_i18n_toggle)
        bind_glyph(es_btn, "  ", "lang.btn")
        self.es_btn = es_btn
        lay.addWidget(es_btn)

        notif_btn = QPushButton()
        notif_btn.setIcon(QIcon(_icon_pixmap("bell", 16)))
        notif_btn.setProperty("ghost", True)
        notif_btn.setFixedSize(36, 36)
        notif_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        notif_btn.clicked.connect(self._show_notifications)
        self.notif_btn = notif_btn
        self._notif_menu: QMenu | None = None
        self.refresh_notifications()
        lay.addWidget(notif_btn)

    def _apply_problem_draft(self) -> None:
        """§16: Enter aplica el borrador por la vía canónica de CRIBA."""
        text = self.problem_input.text().strip()
        if text:
            actions.on_nueva_idea_no_dialog(self.win, text)

    def _sync_draft_state(self) -> None:
        """§16: mientras el borrador no se aplique, se dice claramente."""
        current = ""
        try:
            current = str(getattr(self.win, "problem", "") or "").strip()
        except Exception:
            current = ""
        draft = self.problem_input.text().strip()
        self.problem_input.setToolTip(_t("shadow.problema.borrador")
                                      if draft and draft != current else "")

    # ------------------------------------------------- modelo local (real)
    def refresh_model_label(self) -> None:
        """Etiqueta REAL del modelo activo, no el texto fijo de la maqueta.

        La composición mostraba "Modelo local · Desactivado" hardcodeado aunque
        hubiera perfil activo. Aquí se lee la misma fuente que el footer clásico
        (model_config.active_model_label) y el botón queda clicable hacia el
        gestor compartido de modelos (actions.on_modelos).
        """
        label = _t("shadow.desactivado")
        try:
            from criba.model_config import active_model_label, load_model_settings

            settings = load_model_settings()
            if settings.enabled and settings.active_profile() is not None:
                label = active_model_label(settings)
        except Exception:
            label = _t("shadow.desactivado")
        self.model_btn.setText(f"  {_t('shadow.modelo')} · {label}")
        if label == _t("shadow.desactivado"):
            self.model_btn.setToolTip(_t("shadow.modelo.tip_off"))
        else:
            self.model_btn.setToolTip(
                f"Modelo activo: {label} — clic para gestionar perfiles (Modelos IA)")

    def _open_modelos(self) -> None:
        """Clic en la cabecera → gestor de modelos compartido y refresco real."""
        actions.on_modelos(self.win)
        refresh = getattr(self.win, "refresh_model_state", None)
        if callable(refresh):
            refresh()
        else:
            self.refresh_model_label()

    # ------------------------------------------------- campana (real)
    def refresh_notifications(self) -> None:
        """Tooltip/indicador de la campana con el estado real de la sesión."""
        unseen = int(getattr(self.win, "unseen_notifications", 0) or 0)
        total = len(getattr(self.win, "notifications", []) or [])
        if unseen:
            self.notif_btn.setToolTip(
                f"Notificaciones — {unseen} sin leer (últimas: {total})")
            self.notif_btn.setStyleSheet(
                f"QPushButton {{ border: 1px solid {ACCENT}; border-radius: 6px; }}")
        else:
            self.notif_btn.setToolTip(f"Notificaciones ({total})")
            self.notif_btn.setStyleSheet("")

    def _show_notifications(self) -> None:
        """Popup real (no bloqueante) con la actividad reciente de la sesión."""
        if self._notif_menu is not None:
            self._notif_menu.close()   # un solo popup vivo (sin fugas)
        entries = list(getattr(self.win, "notifications", []) or [])
        menu = QMenu(self)
        if entries:
            for ts, _kind, text in reversed(entries[-12:]):
                act = menu.addAction(f"{ts}   {text}")
                act.setEnabled(False)
        else:
            empty = menu.addAction("Sin notificaciones todavía")
            empty.setEnabled(False)
        # Abrir la campana marca como leídas (indicador real, no decorativo).
        self.win.unseen_notifications = 0
        self.refresh_notifications()
        self._notif_menu = menu
        menu.popup(self.notif_btn.mapToGlobal(QPoint(0, self.notif_btn.height())))


# ---------------------------------------------------------------------------
# Top cards — 4 tarjetas
# ---------------------------------------------------------------------------

class TopCardsWidget(QWidget):
    def __init__(self, win: ShadowWindow) -> None:
        super().__init__()
        self.win = win
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # 1. Problema actual
        f1, l1 = _card("Problema actual", "doc", i18n="shadow.problema")
        grid = QGridLayout()
        sesion_lbl = QLabel("Sesión:")
        bind_text(sesion_lbl, "shadow.sesion")
        grid.addWidget(sesion_lbl, 0, 0)
        self.session_state = QLabel("")
        self.session_state.setWordWrap(True)
        grid.addWidget(self.session_state, 0, 1)
        objetivo_lbl = QLabel("Objetivo:")
        bind_text(objetivo_lbl, "shadow.objetivo")
        grid.addWidget(objetivo_lbl, 1, 0)
        self.objective_state = QLabel("")
        self.objective_state.setWordWrap(True)
        grid.addWidget(self.objective_state, 1, 1)
        grid.setColumnStretch(1, 1)
        l1.addLayout(grid)
        btn_nueva = QPushButton("＋ Nueva idea")
        btn_nueva.setProperty("accent", True)
        bind_text(btn_nueva, "shadow.nueva_idea")
        self.btn_nueva = btn_nueva
        btn_nueva.clicked.connect(lambda: actions.on_nueva_idea(win))
        l1.addWidget(btn_nueva)
        lay.addWidget(f1, stretch=1)

        # 2. Generación
        f2, l2 = _card("Generación", "bolt", i18n="shadow.card.generacion")
        motor_lbl = QLabel("⚙ Motor determinista")
        bind_text(motor_lbl, "shadow.motor")
        l2.addWidget(motor_lbl)
        selector_row = QHBoxLayout()
        selector_label = QLabel("Intérprete:")
        selector_label.setProperty("caption", True)
        selector_row.addWidget(selector_label)
        self.interpreter_selector = QComboBox()
        self.interpreter_selector.addItem(
            "Nous/Hermes OAuth · Space Bunny", "openai_compatible"
        )
        self.interpreter_selector.addItem(
            _t("shadow.interpreter.local"), "local_llama"
        )
        selector_row.addWidget(self.interpreter_selector, stretch=1)
        l2.addLayout(selector_row)
        self.interpreter_status = QLabel(
            _t("shadow.interpreter.status")
        )
        self.interpreter_status.setWordWrap(True)
        self.interpreter_status.setProperty("caption", True)
        l2.addWidget(self.interpreter_status)
        self.generation_loading = LoadingIndicator("flujo_energia", QSize(210, 54))
        l2.addWidget(self.generation_loading)
        self.cancel_interpretation = QPushButton("Cancelar interpretación")
        self.cancel_interpretation.setProperty("ghost", True)
        self.cancel_interpretation.clicked.connect(lambda: actions.on_cancel_inventar(win))
        self.cancel_interpretation.hide()
        l2.addWidget(self.cancel_interpretation)
        self.cand_label = QLabel("⬡ 0 candidatos")
        # El contador lo actualiza shadow_context; la propiedad permite
        # reconstruir el texto en el idioma activo sin perder el número.
        self.cand_label.setProperty("count", 0)
        bind_text(self.cand_label, "shadow.candidatos")
        l2.addWidget(self.cand_label)
        btn_row = QHBoxLayout()
        btn_gen = QPushButton("✦ Generar ideas")
        bind_text(btn_gen, "shadow.generar")
        btn_gen.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                    stop:0 #0A3830, stop:1 #0A2A35);
                border: 1px solid {SUCCESS}; border-radius: 6px;
                color: {SUCCESS}; font-weight: 700; font-size: 13px;
                padding: 9px 18px;
            }}
            QPushButton:hover {{ background: #0A4838; border-color: {ACCENT}; }}
            QPushButton:disabled {{ background: #0A1A18; border-color: #1E3A30; color: #3A6A58; }}
        """)
        self.btn_gen = btn_gen
        btn_gen.clicked.connect(lambda: actions.on_generar(win))
        _glow(btn_gen, SUCCESS, 26)
        btn_row.addWidget(btn_gen, stretch=1)
        btn_inv = QPushButton("⚗ Inventar")
        bind_text(btn_inv, "shadow.inventar")
        self.btn_inv = btn_inv
        btn_inv.clicked.connect(lambda: actions.on_inventar(win))
        btn_row.addWidget(btn_inv, stretch=1)
        l2.addLayout(btn_row)
        lay.addWidget(f2, stretch=1)

        # 3. Evaluación interna
        f3, l3 = _card("Evaluación interna", "chart", i18n="shadow.card.evaluacion")
        score_row = QHBoxLayout()
        score_label = QLabel("Mejor score")
        score_label.setProperty("caption", True)
        bind_text(score_label, "shadow.mejor_score")
        score_row.addWidget(score_label)
        score_val = QLabel("")
        score_val.setStyleSheet(
            f"font-size: 28px; font-weight: 800; color: {ACCENT}; "
            "background: transparent;"
        )
        self.score_val = score_val
        self.set_score_unknown()
        score_row.addWidget(score_val)
        score_row.addStretch()
        l3.addLayout(score_row)
        note = QLabel("No equivale a evidencia.")
        note.setProperty("muted", True)
        bind_text(note, "shadow.no_evidencia")
        l3.addWidget(note)
        btn_eval = QPushButton("📊 Evaluar ideas")
        bind_text(btn_eval, "shadow.evaluar")
        self.btn_eval = btn_eval
        btn_eval.clicked.connect(lambda: actions.on_evaluar(win))
        l3.addWidget(btn_eval)
        self.evaluation_loading = LoadingIndicator("neon_hud", QSize(32, 32))
        l3.addWidget(self.evaluation_loading)
        lay.addWidget(f3, stretch=1)

        # 4. Fuentes
        f4, l4 = _card("Fuentes", "archive", i18n="shadow.card.fuentes")
        warn = QLabel("⚠ Sin actualizar")
        warn.setStyleSheet(f"color: {WARNING}; font-size: 12px; background: transparent;")
        bind_text(warn, "shadow.sin_actualizar")
        self.stale_warn = warn
        l4.addWidget(warn)
        btn_act = QPushButton("↻ Actualizar fuentes")
        bind_text(btn_act, "shadow.actualizar")
        self.btn_act = btn_act
        btn_act.clicked.connect(lambda: actions.on_actualizar(win))
        l4.addWidget(btn_act)
        self.sources_loading = LoadingIndicator("neon_hud", QSize(32, 32))
        l4.addWidget(self.sources_loading)
        lay.addWidget(f4, stretch=1)

    # ------------------------------------------- estado real (runtime truth)
    def set_score_unknown(self) -> None:
        """§14: sin evaluación real no hay score (nunca 0 ni valor de maqueta)."""
        self.score_val.setText(_t("shadow.no_evaluado"))

    def refresh_runtime_state(self, problem: str, packet: Any = None) -> None:
        """§12/§16: la tarjeta refleja el estado REAL de la sesión."""
        has_problem = bool(str(problem or "").strip())
        self.session_state.setText(
            _t("shadow.sesion.activa") if has_problem else _t("shadow.sesion.sin_iniciar"))
        self.objective_state.setText(
            str(problem).strip()[:60] if has_problem else _t("shadow.objetivo.no_definido"))
        if packet is None:
            # Sesión nueva o sin generar: contador y score vuelven al estado honesto.
            _set_candidate_count(self.cand_label, 0)
            self.set_score_unknown()


# ---------------------------------------------------------------------------
# Candidates — tabla + detalle
# ---------------------------------------------------------------------------
# MISSION RUNTIME_TRUTH_UI (§13): la tabla arranca VACÍA. Las filas ilustrativas
# de la maqueta se eliminaron: alimentaban el runtime con datos que aparentaban
# ser resultados reales. Referencia histórica: commit 200a34f.


class CandidatesWidget(QWidget):
    def __init__(self, win: ShadowWindow) -> None:
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        self.lay = lay
        title = QLabel("Candidatos y evaluación")
        title.setProperty("h2", True)
        title.setWordWrap(True)
        bind_text(title, "shadow.candidatos_titulo")
        sub = QLabel("Propuestas para el problema actual")
        sub.setProperty("caption", True)
        sub.setWordWrap(True)
        bind_text(sub, "shadow.candidatos_sub")
        self.title = title
        self.sub = sub
        lay.addWidget(title)
        lay.addWidget(sub)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        for key in ("shadow.tab.ranking", "shadow.tab.top", "shadow.tab.eval",
                    "shadow.tab.exploracion"):
            tabs.addTab(QWidget(), _t(key))
        # Las pestañas no exponen setText por clave: se re-etiquetan al cambiar
        # de idioma (QTabWidget.setTabText).
        def _retitle_tabs() -> None:
            for i, key in enumerate(("shadow.tab.ranking", "shadow.tab.top",
                                     "shadow.tab.eval", "shadow.tab.exploracion")):
                if i < tabs.count():
                    tabs.setTabText(i, _t(key))

        _I18N_CALLBACKS.append(_retitle_tabs)
        tabs.currentChanged.connect(lambda i: actions.on_tab_changed(win, i))
        self.tabs = tabs
        lay.addWidget(tabs)

        # Tabla REAL: RankingModel canónico + proxy shadow (cabeceras de la
        # composición) + QTableView. Selección → mapToSource → candidate ID.
        self.model = RankingModel()
        # §13: la tabla arranca vacía; sólo datos reales tras generar/evaluar.
        self.model.set_rows([])
        self.proxy = ShadowRankingProxy()
        self.proxy.setSourceModel(self.model)
        table = QTableView()
        table.setModel(self.proxy)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setHighlightSections(False)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.view = table
        lay.addWidget(table)

        # Detalle seleccionado
        detail = QFrame()
        detail.setProperty("card", True)
        d_lay = QVBoxLayout(detail)
        d_lay.setContentsMargins(14, 10, 14, 10)
        d_header = QHBoxLayout()
        icon = _icon_label("doc", 18)
        d_header.addWidget(icon)
        d_info = QVBoxLayout()
        sel_label = QLabel("Idea seleccionada")
        sel_label.setStyleSheet(
            f"color: {SUCCESS}; font-size: 10px; font-weight: 600; "
            "background: transparent;"
        )
        bind_text(sel_label, "shadow.idea_sel")
        self.detail_caption = sel_label
        d_info.addWidget(sel_label)
        d_title = QLabel("")
        d_title.setProperty("h2", True)
        d_title.setWordWrap(True)
        self.detail_title = d_title
        d_info.addWidget(d_title)
        d_header.addLayout(d_info, stretch=1)
        self.detail_chip = _badge("● En evaluación", SUCCESS, BADGE_GREEN_BG)
        self.detail_chip.setWordWrap(True)
        d_header.addWidget(self.detail_chip)
        chip_ev = _badge("⚠ Evidencia pendiente", WARNING, "#282008")
        chip_ev.setWordWrap(True)
        self.detail_chip_ev = chip_ev
        d_header.addWidget(chip_ev)
        d_lay.addLayout(d_header)
        d_desc = QLabel("")
        d_desc.setWordWrap(True)
        d_desc.setProperty("sub", True)
        self.detail_desc = d_desc
        # Ficha técnica en monoespaciada (la referencia usa Cascadia Code).
        # Va por QSS: el QSS global pisa cualquier setFont() del widget.
        mono_qss = ("font-family: 'Cascadia Code', 'Consolas', 'Courier New', monospace;"
                    " background: transparent;")
        d_title.setStyleSheet(mono_qss)
        d_desc.setStyleSheet(mono_qss + f" color: {TEXT_SUB};")
        d_lay.addWidget(d_desc)

        # Resultados completos y copiables. La navegación muestra UNA
        # interpretación por vez: juntar todas las propuestas en un blob JSON
        # hacía que parecieran repetidas y ocultaba la lectura importante.
        self.output_tabs = QTabWidget()
        self.output_tabs.setDocumentMode(True)
        self.raw_output = QPlainTextEdit()
        self.raw_output.setReadOnly(True)
        self.raw_output.setPlaceholderText("Sin salida bruta todavía")
        self.interpretation_output = QPlainTextEdit()
        self.interpretation_output.setReadOnly(True)
        self.interpretation_output.setProperty("interpretation_active", True)
        self.interpretation_output.setPlaceholderText("Sin interpretación todavía")
        self.dossier_output = QPlainTextEdit()
        self.dossier_output.setReadOnly(True)
        self.dossier_output.setPlaceholderText("Sin dossier todavía")
        self.supra_output = QPlainTextEdit()
        self.supra_output.setReadOnly(True)
        self.supra_output.setPlaceholderText("Sin estado SUPRA recuperado todavía")
        for label, widget in (
            ("Salida bruta", self.raw_output),
            ("Interpretación", self.interpretation_output),
            ("Dossier", self.dossier_output),
            ("SUPRA / GET", self.supra_output),
        ):
            widget.setMinimumHeight(150)
            self.output_tabs.addTab(widget, label)

        # Controles de lectura: las flechas son cuadrados translúcidos y el
        # guardado permanece a la vista antes de la zona de texto desplazable.
        self.interpretation_entries: list[dict[str, Any]] = []
        self.interpretation_index = 0
        d_btn = QHBoxLayout()
        d_btn.setSpacing(8)
        previous = QPushButton("←")
        previous.setObjectName("interpreterPreviousButton")
        previous.setProperty("navigation", True)
        previous.setFixedSize(34, 34)
        previous.setToolTip("Interpretación anterior")
        previous.setEnabled(False)
        previous.clicked.connect(lambda: self.show_interpreter_entry(self.interpretation_index - 1))
        self.interpreter_previous = previous
        d_btn.addWidget(previous)
        position = QLabel(_t("shadow.interpretacion.vacia"))
        position.setObjectName("interpreterPositionLabel")
        position.setProperty("interpretation_status", True)
        position.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.interpreter_position = position
        d_btn.addWidget(position)
        following = QPushButton("→")
        following.setObjectName("interpreterNextButton")
        following.setProperty("navigation", True)
        following.setFixedSize(34, 34)
        following.setToolTip("Interpretación siguiente")
        following.setEnabled(False)
        following.clicked.connect(
            lambda: self.show_interpreter_entry(self.interpretation_index + 1)
        )
        self.interpreter_next = following
        d_btn.addWidget(following)
        d_btn.addStretch()
        save_idea = QPushButton()
        save_idea.setObjectName("saveIdeaButton")
        save_idea.setProperty("save_action", True)
        save_idea.setEnabled(False)
        bind_glyph(save_idea, "💾 ", "shadow.guardar_idea")
        self.save_idea = save_idea
        save_idea.clicked.connect(lambda: actions.on_guardar(win))
        d_btn.addWidget(save_idea)
        d_lay.addLayout(d_btn)
        d_lay.addWidget(self.output_tabs)
        footer_actions = QHBoxLayout()
        footer_actions.addStretch()
        ver_todas = QPushButton("Ver todas las ideas  →")
        ver_todas.setProperty("accent", True)
        bind_text(ver_todas, "shadow.ver_todas")
        self.ver_todas = ver_todas
        ver_todas.clicked.connect(lambda: actions.on_ver_todas(win))
        footer_actions.addWidget(ver_todas)
        d_lay.addLayout(footer_actions)
        lay.addWidget(detail)
        lay.addStretch()

        # §12: arranque honesto — sin candidato seleccionado.
        self.set_detail_empty(True)

    def set_detail_empty(self, empty: bool) -> None:
        """Detalle sin candidato: texto honesto y sin chips que affirmen estado.

        §9: el componente se conserva; sólo cambia el valor (nunca se borra).
        """
        self.detail_empty = bool(empty)
        self.detail_caption.setVisible(not empty)
        self.detail_chip.setVisible(not empty)
        self.detail_chip_ev.setVisible(not empty)
        if empty:
            self.detail_title.setText(_t("shadow.detail.vacio"))
            self.detail_desc.setText(_t("shadow.detail.vacio.desc"))

    def set_interpreter_entries(self, entries: list[dict[str, Any]]) -> None:
        """Carga las propuestas del run y enfoca la primera interpretación.

        La vista no concatena propuestas: cada avance conserva el bruto y la
        interpretación del MISMO candidato, para que el usuario no confunda
        campos idénticos de ejecuciones distintas con resultados repetidos.
        """
        self.interpretation_entries = list(entries)
        self.interpretation_index = 0
        if not self.interpretation_entries:
            self.clear_interpreter_entries()
            return
        self.show_interpreter_entry(0, focus_interpretation=True)

    def clear_interpreter_entries(self) -> None:
        """Borra la identidad de la interpretación al cambiar de run."""
        self.interpretation_entries = []
        self.interpretation_index = 0
        self.interpreter_position.setText(_t("shadow.interpretacion.vacia"))
        self.interpreter_previous.setEnabled(False)
        self.interpreter_next.setEnabled(False)

    @staticmethod
    def _display_list(value: Any) -> str:
        if isinstance(value, (list, tuple)):
            items = [str(item).strip() for item in value if str(item).strip()]
            return "\n".join(f"• {item}" for item in items) or "No declarado"
        text = str(value or "").strip()
        return text or "No declarado"

    def _format_interpretation(self, entry: dict[str, Any], index: int) -> str:
        title = str(entry.get("title") or f"candidato {index}").strip()
        state = str(entry.get("estado_interpretacion") or "PENDIENTE_INTERPRETACION")
        error = str(entry.get("interpretacion_error") or "").strip()
        sections = [
            f"INTERPRETACIÓN · Propuesta {index} de {len(self.interpretation_entries)}",
            title,
            f"ESTADO\n{state}",
        ]
        if state == "PROPUESTA":
            sections.extend((
                f"HIPÓTESIS\n{self._display_list(entry.get('hipotesis'))}",
                f"MECANISMO PROPUESTO\n{self._display_list(entry.get('mecanismo'))}",
                (
                    "APORTACIÓN DE LA TÉCNICA\n"
                    f"{self._display_list(entry.get('aportacion_por_tecnica'))}"
                ),
                f"SUPUESTOS A COMPROBAR\n{self._display_list(entry.get('supuestos'))}",
                f"PRUEBA CONCRETA\n{self._display_list(entry.get('prueba_concreta'))}",
                f"{_t('shadow.interpreter.uncertainty')}\n"
                f"{entry.get('incertidumbre') or ''}\n{entry.get('novedad') or ''}",
                f"{_t('shadow.interpreter.test')}\n"
                + json.dumps(entry.get("prueba") or {}, ensure_ascii=False, indent=2),
            ))
        else:
            sections.append(f"MOTIVO\n{error or 'sin motivo declarado'}")
            route = str(entry.get("ruta_desbloqueo") or "").strip()
            if route:
                sections.append(f"RUTA DE DESBLOQUEO\n{route}")
        critica = entry.get("critica")
        if isinstance(critica, dict) and critica:
            sections.append(_t("shadow.interpreter.critica") + "\n"
                            + json.dumps(critica, ensure_ascii=False, indent=2))
        provenance = entry.get("interpretacion_provenance")
        if not isinstance(provenance, dict):
            provenance = {}
        provider = str(provenance.get("provider") or "").strip()
        model = str(
            provenance.get("model_reported")
            or provenance.get("model_requested")
            or ""
        ).strip()
        request_id = str(provenance.get("request_id") or "").strip()
        finish_reason = str(entry.get("interpretacion_finish_reason") or "").strip()
        usage = entry.get("interpretacion_usage")
        trace = [part for part in (
            f"Proveedor: {provider}" if provider else "",
            f"Modelo: {model}" if model else "",
            f"Request: {request_id}" if request_id else "",
            f"Finalización: {finish_reason}" if finish_reason else "",
            f"Uso: {usage}" if usage else "",
        ) if part]
        if trace:
            sections.append("TRAZABILIDAD\n" + "\n".join(trace))
        return "\n\n".join(sections)

    def show_interpreter_entry(self, index: int, *, focus_interpretation: bool = False) -> None:
        """Renderiza bruto y parseado de una única propuesta del run actual."""
        if not self.interpretation_entries:
            self.clear_interpreter_entries()
            return
        self.interpretation_index = max(0, min(index, len(self.interpretation_entries) - 1))
        entry = self.interpretation_entries[self.interpretation_index]
        position = self.interpretation_index + 1
        total = len(self.interpretation_entries)
        title = str(entry.get("title") or f"candidato {position}").strip()
        raw = str(entry.get("interpretacion_raw_output") or "").strip()
        error = str(entry.get("interpretacion_error") or "").strip()
        raw_body = raw or f"[SIN CONTENIDO] {error or 'sin motivo declarado'}"
        self.raw_output.setPlainText(
            f"SALIDA BRUTA · Propuesta {position} de {total}\n{title}\n\n{raw_body}"
        )
        self.interpretation_output.setPlainText(self._format_interpretation(entry, position))
        self.interpreter_position.setText(f"Interpretación {position} de {total}")
        self.interpreter_previous.setEnabled(position > 1)
        self.interpreter_next.setEnabled(position < total)
        if focus_interpretation:
            self.output_tabs.setCurrentWidget(self.interpretation_output)

    def show_state_only(self) -> None:
        """Muestra SOLO el chip de estado, sin fingir una idea seleccionada.

        El resultado de SUPRA no es un candidato: no hay «idea seleccionada»
        que anunciar. El chip sí es el indicador de estado del panel, así que
        se enciende; la cabecera de «idea seleccionada» se mantiene oculta
        porque sería una afirmación falsa sobre lo que el panel describe.
        """
        self.detail_empty = False
        self.detail_caption.setVisible(False)
        self.detail_chip.setVisible(True)


# ---------------------------------------------------------------------------
# Right panel — Fuentes + SUPRA + Actividad + BLACKFORGE
# ---------------------------------------------------------------------------

class RightPanelWidget(QWidget):
    def __init__(self, win: ShadowWindow) -> None:
        super().__init__()
        self.win = win
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(10)

        # Fuentes y evidencia
        f1, l1 = _card(
            "Fuentes y evidencia", "clipboard", i18n="shadow.card.fuentes_evidencia"
        )
        for key_label, key_value in [
            ("shadow.refs", "0"),
            ("shadow.pruebas", "shadow.no_ejecutadas"),
            ("shadow.resultados", "shadow.no_disponible"),
        ]:
            row = QHBoxLayout()
            lbl = QLabel(_t(key_label))
            lbl.setProperty("caption", True)
            lbl.setWordWrap(True)
            bind_text(lbl, key_label)
            row.addWidget(lbl)
            val = QLabel(key_value)
            val.setProperty("muted", True)
            val.setWordWrap(True)
            if key_value.startswith("shadow."):
                bind_text(val, key_value)
            row.addWidget(val)
            row.addStretch()
            l1.addLayout(row)
        banner = QHBoxLayout()
        # §20: aquí NO se inventa un error de fuente. Los errores reales van al
        # banner real de operación (ShadowWindow.errorBanner, vía show_error).
        warn = QLabel("")
        warn.setWordWrap(True)
        warn.setStyleSheet(f"color: {WARNING}; font-size: 11px; background: transparent;")
        warn.hide()
        banner.addWidget(warn, stretch=1)
        cerrar = QPushButton("Cerrar")
        cerrar.setFixedHeight(22)
        bind_text(cerrar, "shadow.cerrar")
        cerrar.setStyleSheet(
            f"font-size: 10px; padding: 2px 10px; background: {BG_CARD}; "
            f"border: 1px solid {BORDER}; border-radius: 4px; color: {TEXT_SUB};"
        )
        cerrar.hide()
        banner.addWidget(cerrar)
        l1.addLayout(banner)
        cerrar.clicked.connect(lambda: (warn.hide(), cerrar.hide()))
        supra = QPushButton("⚛ Desarrollar con SUPRA")
        supra.setProperty("success", True)
        supra.setFixedHeight(36)
        bind_text(supra, "shadow.supra_btn")
        self.supra = supra
        supra.setEnabled(False)
        supra.clicked.connect(lambda: actions.on_desarrollar_supra(win))
        l1.addWidget(supra)
        note = QLabel("Prepara dossiers de la sesión. Ejecución pendiente.")
        note.setWordWrap(True)
        note.setProperty("caption", True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bind_text(note, "shadow.supra_nota")
        l1.addWidget(note)
        # M2 · slice vertical REAL: núcleo determinista -> dossier -> SUPRA real
        # -> persistencia -> GET -> esta ventana. Botón propio para que la
        # ruta real no compita con la preparación de dossiers de sesión.
        supra_e2e = QPushButton("▶ Ejecutar en SUPRA (real)")
        supra_e2e.setProperty("accent", True)
        supra_e2e.setFixedHeight(36)
        bind_text(supra_e2e, "shadow.supra_e2e_btn")
        self.supra_e2e = supra_e2e
        supra_e2e.clicked.connect(lambda: actions.on_supra_vertical(win))
        l1.addWidget(supra_e2e)
        note_e2e = QLabel("Núcleo → dossier → SUPRA → estado persistido.")
        note_e2e.setWordWrap(True)
        note_e2e.setProperty("caption", True)
        note_e2e.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bind_text(note_e2e, "shadow.supra_e2e_nota")
        l1.addWidget(note_e2e)
        lay.addWidget(f1)

        # Actividad reciente
        f2, l2 = _card("Actividad reciente", "clock", i18n="shadow.card.actividad")
        # §19: sin eventos ficticios. Sólo eventos REALES (actions._activity →
        # panels.add_activity → este layout); el estado vacío es explícito.
        self.activity_empty_label = QLabel(_t("shadow.actividad.vacia"))
        self.activity_empty_label.setProperty("caption", True)
        self.activity_empty_label.setWordWrap(True)
        l2.addWidget(self.activity_empty_label)
        # Layout real para entradas de actividad (actions._activity). Vacío
        # en reposo → presentación inicial idéntica a la referencia.
        self.activity_lay = QVBoxLayout()
        self.activity_lay.setContentsMargins(0, 0, 0, 0)
        self.activity_lay.setSpacing(4)
        l2.addLayout(self.activity_lay)
        ver_hist = QPushButton("Ver historial completo")
        ver_hist.setProperty("ghost", True)
        bind_text(ver_hist, "shadow.ver_historial")
        self.ver_hist = ver_hist
        ver_hist.clicked.connect(lambda: actions.on_historial(win))
        l2.addWidget(ver_hist)
        lay.addWidget(f2)

        # BLACKFORGE
        f3, l3 = _card("BLACKFORGE", "mountain")
        bf_desc = QLabel("Aplicación independiente")
        bf_desc.setProperty("caption", True)
        bind_text(bf_desc, "shadow.bf_indep")
        l3.addWidget(bf_desc)
        ir_bf = QPushButton("Ir a Blackforge  →")
        ir_bf.setProperty("accent", True)
        bind_text(ir_bf, "shadow.ir_bf")
        self.ir_bf = ir_bf
        ir_bf.clicked.connect(lambda: actions.on_blackforge(win))
        l3.addWidget(ir_bf)
        lay.addWidget(f3)
        lay.addStretch()


# ---------------------------------------------------------------------------
# Footer
# ---------------------------------------------------------------------------

class FooterWidget(QWidget):
    def __init__(self, win: ShadowWindow | None = None) -> None:
        super().__init__()
        self.win = win
        self.setFixedHeight(40)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(16, 4, 16, 4)
        lay.setSpacing(20)
        sesion_block = _footer_block("shield", _t("shadow.footer.sin_sesion"),
                                     icon_color=SUCCESS, dot=SUCCESS)
        # §26: el pie refleja el estado REAL (sin sesión al arrancar; activa
        # cuando existe problema). Una sola fuente: win.problem.
        self.session_block = sesion_block
        bind_callback(self.refresh_session_state)
        lay.addWidget(sesion_block)
        self.model_block = _footer_block("ban", "Modelo desactivado",
                                         "Sin generación de IA", icon_color=TEXT_SUB)
        lay.addWidget(self.model_block)
        # §26/§20: el tercer bloque deja de afirmar "Maqueta · Datos ilustrativos"
        # (la UI ya no es una maqueta) y muestra el estado REAL de las fuentes
        # (lo escribe actions.refresh_sources_freshness vía footerSegs["fsFuentes"]).
        self.sources_block = _footer_block("info", _t("shadow.card.fuentes"),
                                           _t("shadow.sin_actualizar.plain"),
                                           icon_color=WARNING)
        lay.addWidget(self.sources_block)
        lay.addStretch()
        lema = QLabel("CIENCIA  //  RIGOR  //  IMPACTO REAL")
        lema.setStyleSheet(
            f"font-size: 9px; color: {TEXT_MUTED}; letter-spacing: 2px; "
            "background: transparent;"
        )
        bind_text(lema, "shadow.lema")
        lay.addWidget(lema)
        self.refresh_model_state()
        # El pie del modelo se reconstruye desde el estado real (no desde una
        # clave fija): va como callback para que corra tras los textos.
        bind_callback(self.refresh_model_state)

    def refresh_session_state(self) -> None:
        """§26: estado REAL de la sesión en el pie (fuente única: win.problem)."""
        problem = ""
        try:
            problem = str(getattr(self.win, "problem", "") or "")
        except Exception:  # ventana en construcción / contexto no listo
            problem = ""
        active = bool(problem.strip())
        label = getattr(self.session_block, "_title_label", None)
        if label is not None:
            label.setText(_t("shadow.footer.sesion") if active
                          else _t("shadow.footer.sin_sesion"))

    def refresh_model_state(self) -> None:
        """Pie real: refleja el perfil activo (la maqueta decía 'desactivado' fijo)."""
        label, sub = _t("shadow.footer.modelo_off"), _t("shadow.footer.modelo_off.sub")
        try:
            from criba.model_config import active_model_label, load_model_settings

            settings = load_model_settings()
            if settings.enabled and settings.active_profile() is not None:
                label = active_model_label(settings)
                sub = _t("shadow.footer.gen_local")
        except Exception:
            pass
        title = getattr(self.model_block, "_title_label", None)
        detail = getattr(self.model_block, "_sub_label", None)
        if title is not None:
            title.setText(label)
        if detail is not None:
            detail.setText(sub)


# ---------------------------------------------------------------------------
# ShadowWindow
# ---------------------------------------------------------------------------

class ShadowWindow(QMainWindow):
    """Reproducción de CRIBA_UI_FINAL con bindings reales."""

    def __init__(self, database: Any = None) -> None:
        super().__init__()
        self.setWindowTitle(_t("shadow.title"))
        bind_callback(lambda: self.setWindowTitle(_t("shadow.title")))
        self.setMinimumSize(1360, 768)
        self.resize(1680, 1050)
        self.setStyleSheet(build_shadow_qss())

        # Campana de notificaciones: estado REAL de la sesión (la actividad de
        # actions._activity alimenta esta lista vía refs["notification_sink"]).
        self.notifications: list[tuple[str, str, str]] = []
        self.unseen_notifications = 0

        # Estructura: [Sidebar] | [Header + TopCards + Splitter(Candidates|Right) + Footer]
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_splitter.setContentsMargins(0, 0, 0, 0)
        main_splitter.setHandleWidth(0)

        self.sidebar = SidebarWidget(self)
        main_splitter.addWidget(self.sidebar)

        right_side = QWidget()
        right_lay = QVBoxLayout(right_side)
        right_lay.setContentsMargins(8, 0, 8, 0)
        right_lay.setSpacing(6)

        # Banner de error S9 (actions.show_error). OCULTO en reposo: la
        # composición en reposo es idéntica a la referencia.
        self.errorBanner = QFrame()
        self.errorBanner.setStyleSheet(
            "QFrame { background: #1A0E10; border: 1px solid #CC4444;"
            " border-radius: 8px; }")
        eb = QHBoxLayout(self.errorBanner)
        eb.setContentsMargins(12, 6, 12, 6)
        eb_icon = QLabel("⚠")
        eb_icon.setStyleSheet("color: #FF8888; background: transparent;")
        eb.addWidget(eb_icon)
        self.errorBannerText = QLabel()
        self.errorBannerText.setWordWrap(True)
        self.errorBannerText.setStyleSheet("color: #FF8888; background: transparent;")
        eb.addWidget(self.errorBannerText, 1)
        self.errorDismissBtn = QPushButton("Cerrar")
        self.errorDismissBtn.setFixedHeight(22)
        self.errorDismissBtn.setStyleSheet(
            f"font-size: 10px; padding: 2px 10px; background: {BG_CARD};"
            f" border: 1px solid {BORDER}; border-radius: 4px; color: {TEXT_SUB};")
        self.errorDismissBtn.clicked.connect(lambda: self.errorBanner.hide())
        eb.addWidget(self.errorDismissBtn)
        self.errorBanner.hide()
        right_lay.addWidget(self.errorBanner)

        self.header = HeaderWidget(self)
        right_lay.addWidget(self.header)
        self.topcards = TopCardsWidget(self)
        right_lay.addWidget(self.topcards)

        content_splitter = QSplitter(Qt.Orientation.Horizontal)
        center_scroll = QScrollArea()
        center_scroll.setWidgetResizable(True)
        self.candidates = CandidatesWidget(self)
        center_scroll.setWidget(self.candidates)
        content_splitter.addWidget(center_scroll)
        right_scroll = QScrollArea()
        right_scroll.setWidgetResizable(True)
        self.right_panel = RightPanelWidget(self)
        right_scroll.setWidget(self.right_panel)
        content_splitter.addWidget(right_scroll)
        content_splitter.setSizes([880, 500])
        # Proporción de la referencia: centro ancho, panel derecho acotado
        # (si no, el panel derecho se queda con el espacio y el centro desborda).
        content_splitter.setStretchFactor(0, 1)
        content_splitter.setStretchFactor(1, 0)
        right_scroll.setMaximumWidth(520)
        right_lay.addWidget(content_splitter, stretch=1)

        self.footer = FooterWidget(self)
        right_lay.addWidget(self.footer)
        main_splitter.addWidget(right_side)
        main_splitter.setSizes([200, 1160])
        self.setCentralWidget(main_splitter)

        # Adaptador de compatibilidad (capa permitida):
        #   ShadowWindow → ShadowActionContext → actions.py → servicios.
        # El estado compartido vive en el contexto; la ventana delega.
        self._ctx = ShadowActionContext(self, database)
        self._ctx.apply_initial_state()
        # §12: arranque limpio y honesto (0 candidatos, sin score, sin sesión).
        self.refresh_runtime_state()

    # ------------------------------------------------------------------
    # Notificaciones (campana): actividad real de la sesión
    # ------------------------------------------------------------------
    def record_notification(self, timestamp: str, kind: str, text: str) -> None:
        """Registra una notificación real (la llama panels.add_activity)."""
        self.notifications.append((timestamp, kind, text))
        del self.notifications[:-50]          # tope de historial
        self.unseen_notifications += 1
        header = self.__dict__.get("header")
        if header is not None:
            header.refresh_notifications()

    # ------------------------------------------------------------------
    # Estado real del modelo (cabecera + pie)
    # ------------------------------------------------------------------
    def refresh_model_state(self) -> None:
        """Refresca cabecera y pie con el perfil real (una sola fuente)."""
        self.header.refresh_model_label()
        self.footer.refresh_model_state()

    # ------------------------------------------------------------------
    # Runtime truth (§12/§15/§16/§39): una sola fuente de estado
    # ------------------------------------------------------------------
    def refresh_runtime_state(self) -> None:
        """Sincroniza los widgets que antes mostraban datos de maqueta.

        Fuente única: el estado compartido del contexto (problem / packet).
        Un problema nuevo reinicia la vista de sesión (candidatos, score,
        detalle) sin tocar el historial persistente.
        """
        ctx = self.__dict__.get("_ctx")
        if ctx is None:
            return
        problem = str(getattr(ctx, "problem", "") or "")
        packet = getattr(ctx, "packet", None)
        top = self.__dict__.get("topcards")
        if top is not None:
            top.refresh_runtime_state(problem, packet)
        cand = self.__dict__.get("candidates")
        if cand is not None and packet is None:
            # §15/§39: problema nuevo ⇒ la sesión no arrastra candidatos,
            # selección ni score del problema anterior.
            cand.model.set_rows([])
            cand.set_detail_empty(True)
            view = getattr(cand, "view", None)
            if view is not None and view.selectionModel() is not None:
                view.clearSelection()
                view.selectionModel().clearCurrentIndex()
        foot = self.__dict__.get("footer")
        if foot is not None:
            foot.refresh_session_state()

    # ------------------------------------------------------------------
    # Delegación de estado/contrato al ShadowActionContext
    # ------------------------------------------------------------------
    _SHADOW_STATE = frozenset({
        "store", "packet", "problem", "saved_ids", "sources_updated_at",
        "invent_sheet", "sources_report", "_live_workers", "_progress_label",
        "interpreter_cancel_requested",
    })

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ShadowWindow._SHADOW_STATE:
            ctx = self.__dict__.get("_ctx")
            if ctx is None:
                raise AttributeError(
                    f"{name}: ShadowActionContext aún no inicializado")
            object.__setattr__(ctx, name, value)
            if name == "problem" and value:
                ctx.sync_problem_input(value)
            if name in ("problem", "packet", "invent_sheet"):
                self.refresh_runtime_state()
            return
        super().__setattr__(name, value)

    def __getattr__(self, name: str) -> Any:
        # Sólo se invoca cuando la búsqueda normal falla: nav/refs/t/pool/
        # footerSegs/errorBanner/show_blackforge_page/... viven en el adapter.
        if name == "_ctx":
            raise AttributeError(name)
        ctx = self.__dict__.get("_ctx")
        if ctx is None:
            raise AttributeError(name)
        return getattr(ctx, name)

    def _nav(self, key: str) -> None:
        callback_map = {
            "navRed": actions.on_red,
            "navHistorial": actions.on_historial,
            "navRetro": actions.on_retro,
            "navMemoria": actions.on_memoria,
            "navTecnicas": actions.on_tecnicas,
            "navModelos": actions.on_modelos,
            "navBlackforge": actions.on_blackforge,
            "navSupra": actions.on_supra,
        }
        fn = callback_map.get(key)
        if fn:
            fn(self)
        else:
            print(f"[shadow] No hay callback para {key}")
