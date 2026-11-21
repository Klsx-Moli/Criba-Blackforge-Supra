"""Saving a model profile must select it automatically."""
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


def test_save_selects_current_profile(qapp, tmp_path, monkeypatch) -> None:
    from criba.model_config import ModelProfile, save_model_settings
    from criba.ui.model_settings_dialog import ModelSettingsDialog

    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    dialog = ModelSettingsDialog()
    # Add a second profile and select it
    dialog._add_profile()
    new_id = dialog._current_profile_id
    assert new_id != ""
    dialog._save()
    # After save, the active profile must be the one we just saved
    saved = save_model_settings.__wrapped__ if hasattr(save_model_settings, "__wrapped__") else None
    from criba.model_config import load_model_settings
    settings = load_model_settings()
    assert settings.active_profile_id == new_id
