from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from criba.model_config import load_model_settings
from criba.ui.model_settings_dialog import ModelSettingsDialog
from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QPushButton, QScrollArea


@pytest.fixture(scope="module")
def qt_app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_model_dialog_switches_runtime_defaults_and_persists(
    tmp_path, monkeypatch, qt_app: QApplication
) -> None:
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    dialog = ModelSettingsDialog()
    try:
        dialog.show()
        qt_app.processEvents()
        assert dialog.endpoint_edit.text() == "http://127.0.0.1:8080"

        dialog.backend_combo.setCurrentIndex(dialog.backend_combo.findData("ollama"))
        assert dialog.endpoint_edit.text() == "http://127.0.0.1:11434"
        assert not dialog.gguf_row.isEnabled()
        assert not dialog.server_row.isEnabled()

        dialog.name_edit.setText("Ollama para CRIBA")
        dialog.model_edit.setText("qwen3:4b")
        dialog.use_model.setChecked(True)
        dialog._save()
    finally:
        dialog.close()

    loaded = load_model_settings(target)
    profile = loaded.active_profile()
    assert loaded.enabled
    assert profile is not None
    assert profile.name == "Ollama para CRIBA"
    assert profile.backend == "ollama"
    assert profile.endpoint == "http://127.0.0.1:11434"
    assert profile.model == "qwen3:4b"


@pytest.mark.parametrize(
    "width,height,font_size", [(1088, 574, 10), (800, 560, 12), (1024, 640, 14)]
)
def test_model_dialog_keeps_save_reachable_on_small_scaled_screens(
    tmp_path, monkeypatch, qt_app: QApplication, width: int, height: int, font_size: int
) -> None:
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    available = QRect(0, 0, width, height)
    monkeypatch.setattr(
        ModelSettingsDialog,
        "screen",
        lambda self: SimpleNamespace(availableGeometry=lambda: available),
    )
    dialog = ModelSettingsDialog()
    font = QFont(dialog.font())
    font.setPointSize(font_size)
    dialog.setFont(font)
    try:
        dialog.show()
        qt_app.processEvents()
        assert dialog.frameGeometry().height() <= height, "Dialog extends below the usable screen"
        assert dialog.frameGeometry().width() <= width, "Dialog extends beyond the usable screen"
        save = dialog.findChild(QPushButton, "primaryModelButton")
        assert save is not None and save.isVisibleTo(dialog)
        assert dialog.rect().contains(QRect(save.mapTo(dialog, QPoint(0, 0)), save.size()))
        scroll = dialog.findChild(QScrollArea)
        assert scroll is not None, "Settings must scroll instead of forcing a taller window"
        center_in_content = dialog.temperature_spin.mapTo(
            scroll.widget(), dialog.temperature_spin.rect().center()
        )
        scroll.ensureVisible(center_in_content.x(), center_in_content.y(), 10, 10)
        qt_app.processEvents()
        center = dialog.temperature_spin.mapTo(
            scroll.viewport(), dialog.temperature_spin.rect().center()
        )
        assert scroll.viewport().rect().contains(center), "Temperature must remain reachable"
        assert not scroll.isAncestorOf(save), "Saving must not require scrolling to the bottom"
        dialog.temperature_spin.setValue(0.25)
        save.click()
        assert dialog.result() == dialog.DialogCode.Accepted
        assert load_model_settings(target).active_profile().temperature == 0.25
    finally:
        dialog.close()
