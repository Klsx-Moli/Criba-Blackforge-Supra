"""Interpreter selector shows 'Cargar modelo' on startup when no local model."""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src"))
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "shadow_ui"))

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_interpreter_selector_shows_cargar_modelo_on_startup(qapp) -> None:
    from criba.interprete.seleccion import BACKEND_LOCAL
    from shadow_window import ShadowWindow

    win = ShadowWindow()
    selector = win.topcards.interpreter_selector
    # No una cuota gratuita caducada ni un modelo remoto por defecto.
    assert selector.currentIndex() == 0
    assert selector.currentData() is None
    assert selector.itemText(0) == "Cargar modelo"
    assert [selector.itemData(i) for i in range(1, 4)] == [
        "source:hermes", "source:opencode", "source:ollama"
    ]
    local_index = next(
        i for i in range(selector.count()) if selector.itemData(i) == BACKEND_LOCAL
    )
    assert "GGUF" in selector.itemText(local_index)
