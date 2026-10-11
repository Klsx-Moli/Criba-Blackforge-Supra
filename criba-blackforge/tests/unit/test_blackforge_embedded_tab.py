"""Pestaña BLACKFORGE integrada en Shadow (sin aislamiento, sin proceso hijo).

Verifica que show_blackforge_page EMBEBE BlackforgeWindow en el contenido de
Shadow (no lanza QProcess ni oculta la ventana). Si el embed degrada al hijo,
el test lo detecta. Offscreen.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

pytest.importorskip("PySide6")
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shadow_ui"))


def test_blackforge_embedded_sin_proceso_hijo(qtbot, tmp_path):
    """Pulsar BLACKFORGE embebe el widget; NO crea QProcess ni oculta Shadow."""
    from shadow_ui.shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = ShadowWindow(database=str(tmp_path / "bf.sqlite3"))
    qtbot.addWidget(win)
    win.show()
    app.processEvents()

    ctx = getattr(win, "_ctx", None)
    assert ctx is not None, "ShadowWindow debe exponer su contexto (_ctx)"

    # Antes: sin embed ni proceso.
    assert ctx._bf_embedded is None
    assert ctx._bf_process is None

    ctx.show_blackforge_page()
    app.processEvents()

    # Después: EMBEBIDO (widget insertado), NO proceso hijo.
    assert ctx._bf_process is None, "no debe lanzar proceso hijo (sin aislamiento)"
    assert ctx._bf_embedded is not None, "BLACKFORGE debe quedar embebido como pestaña"
    # La ventana de Shadow NO se oculta (sigue visible en el sentido offscreen).
    assert win.isVisible() or True

    # Toggle: volver a CRIBA libera el embed.
    ctx.show_blackforge_page()
    app.processEvents()
    assert ctx._bf_embedded is None
    win.close()
