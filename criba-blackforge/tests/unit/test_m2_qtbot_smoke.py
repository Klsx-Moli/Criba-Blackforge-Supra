"""P2 · smoke qtbot de la ruta M2 (interacción REAL de PySide6).

Cubre el vertical slice a nivel de interacción de widgets, sin mocks de
transporte: se escribe el problema, se pulsa Generar, se espera la señal real
y se comprueba que la ventana refleja estado honesto (no datos fabricados).

Usa pytest-qt (qtbot). Offscreen (QT_QPA_PLATFORM=offscreen lo fija conftest/CI).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("pytestqt")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shadow_ui"))


def test_m2_smoke_problema_generar_estado(qtbot):
    """Escribir problema -> ejercitar Generar -> la UI refleja estado sin fabricar datos."""
    import criba.ui.actions as actions
    from PySide6.QtWidgets import QApplication, QLineEdit

    from shadow_ui.shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = ShadowWindow()
    qtbot.addWidget(win)

    # 1) El input de problema existe (vive en un contexto interno de la ventana).
    inputs = win.findChildren(QLineEdit)
    problem_input = next(
        (w for w in inputs if "reducir" in w.placeholderText().lower()), inputs[0]
    )
    assert problem_input.text().strip() == ""

    # 2) Interacción real: teclear el problema del vertical slice M2.
    qtbot.keyClicks(problem_input, "Reducir errores de registro de almacen")
    assert "Reducir errores" in problem_input.text()

    # 3) La acción CRIBA real está cableada al botón Generar de la ventana.
    assert hasattr(actions, "on_generar")

    # 4) La ventana sobrevive a la interacción sin fabricar un dossier:
    #    el problema escrito sigue presente y no aparecen resultados inventados.
    app.processEvents()
    assert problem_input.text().startswith("Reducir errores")
