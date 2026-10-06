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
    from shadow_window import ShadowWindow

    win = ShadowWindow()
    selector = win.topcards.interpreter_selector
    # On startup, the local option should say "Cargar modelo", not "Local"
    assert selector.itemText(1) == "Cargar modelo"
