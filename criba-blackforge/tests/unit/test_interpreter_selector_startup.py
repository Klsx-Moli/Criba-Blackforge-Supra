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
    # La entrada local ya no está en un índice fijo: entre el externo y ella
    # están los modelos gratuitos del proxy. Se localiza por su userData.
    local_index = next(
        i for i in range(selector.count()) if selector.itemData(i) == BACKEND_LOCAL
    )
    # On startup, the local option should say "Cargar modelo", not "Local"
    assert selector.itemText(local_index) == "Cargar modelo"
