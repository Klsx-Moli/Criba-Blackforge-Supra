"""Tests for the model settings dialog breathing gradient feedback."""
from __future__ import annotations

import os
import sys

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src"))

pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication  # noqa: E402


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


def test_dialog_has_breathing_methods(qapp) -> None:
    from criba.ui.model_settings_dialog import ModelSettingsDialog

    dialog = ModelSettingsDialog()
    assert hasattr(dialog, "_start_breathing")
    assert hasattr(dialog, "_stop_breathing")
    assert hasattr(dialog, "_tick_breath")


def test_breathing_changes_button_text(qapp) -> None:
    from criba.ui.model_settings_dialog import ModelSettingsDialog

    dialog = ModelSettingsDialog()
    original = dialog.test_button.text()
    dialog._start_breathing()
    assert dialog.test_button.text() == "Cargando…"
    dialog._stop_breathing()
    assert dialog.test_button.text() == original


def test_breathing_sets_stylesheet(qapp) -> None:
    from criba.ui.model_settings_dialog import ModelSettingsDialog

    dialog = ModelSettingsDialog()
    dialog._start_breathing()
    dialog._tick_breath()
    style = dialog.test_button.styleSheet()
    assert "background" in style
    dialog._stop_breathing()
    assert dialog.test_button.styleSheet() == ""


def test_breathing_timer_lifecycle(qapp) -> None:
    from criba.ui.model_settings_dialog import ModelSettingsDialog

    dialog = ModelSettingsDialog()
    dialog._start_breathing()
    assert dialog._breath_timer is not None
    dialog._stop_breathing()
    assert dialog._breath_timer is None
