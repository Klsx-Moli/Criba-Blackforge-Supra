"""F35: shared GGUF/Ollama dialog cannot overwrite edits made after open.

Qt is offscreen; no external inference and no user configuration is touched.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from criba.model_config import (  # noqa: E402
    ModelProfile, default_model_settings, save_model_settings,
)
from criba.ui.model_settings_dialog import (  # noqa: E402
    ModelSettingsDialog, _read_shared_settings_snapshot,
)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def test_two_open_model_dialogs_cannot_silently_lose_first_save(
    app, tmp_path, monkeypatch,
):
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    # Both editors start from the same absent file, and have distinct
    # in-memory random default profile IDs. The second must not overwrite.
    first = ModelSettingsDialog()
    second = ModelSettingsDialog()
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda _dialog, title, message: warnings.append((title, message)),
    )
    try:
        first.name_edit.setText("first saved")
        first._save()
        assert first.result() == first.DialogCode.Accepted
        saved = target.read_bytes()

        second.name_edit.setText("second stale")
        second._save()
        assert target.read_bytes() == saved
        assert second.result() != second.DialogCode.Accepted
        assert warnings and "cambios externos" in warnings[-1][0]
    finally:
        first.close()
        second.close()
        app.processEvents()


@pytest.mark.parametrize("corrupt", [
    b"{broken",
    b'{"future_version":2,"enabled":true,"profiles":[]}',
    b"x" * 1_048_577,
])
def test_model_dialog_never_overwrites_untrusted_existing_config(
    app, tmp_path, monkeypatch, corrupt,
):
    target = tmp_path / "models.json"
    target.write_bytes(corrupt)
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    dialog = ModelSettingsDialog()
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda _d, title, msg: warnings.append((title, msg)),
    )
    try:
        dialog._save()
        assert dialog.result() != dialog.DialogCode.Accepted
        assert warnings and "cambios externos" in warnings[-1][0]
        assert target.read_bytes() == corrupt
    finally:
        dialog.close()
        app.processEvents()


def test_model_dialog_detects_existing_config_changed_during_edit(
    app, tmp_path, monkeypatch,
):
    target = tmp_path / "models.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    settings = default_model_settings()
    save_model_settings(settings, target)
    dialog = ModelSettingsDialog()
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda _d, title, msg: warnings.append((title, msg)),
    )
    try:
        other = default_model_settings()
        other.profiles = [ModelProfile(name="other editor", model="other")]
        other.active_profile_id = other.profiles[0].id
        other.enabled = True
        save_model_settings(other, target)
        external_bytes = target.read_bytes()

        dialog.name_edit.setText("stale editor")
        dialog._save()
        assert target.read_bytes() == external_bytes
        assert dialog.result() != dialog.DialogCode.Accepted
        assert warnings
    finally:
        dialog.close()
        app.processEvents()


def test_model_dialog_detects_config_path_changed_while_open(
    app, tmp_path, monkeypatch,
):
    original = tmp_path / "original.json"
    replacement = tmp_path / "replacement.json"
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(original))
    dialog = ModelSettingsDialog()
    warnings = []
    monkeypatch.setattr(
        QMessageBox, "warning",
        lambda _d, title, msg: warnings.append((title, msg)),
    )
    try:
        monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(replacement))
        dialog._save()
        assert not original.exists()
        assert not replacement.exists()
        assert dialog.result() != dialog.DialogCode.Accepted
        assert warnings
    finally:
        dialog.close()
        app.processEvents()


def test_model_dialog_snapshot_rejects_oversized_file(tmp_path, monkeypatch):
    target = tmp_path / "models.json"
    target.write_bytes(b"x" * 1_048_577)
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(target))
    observed_path, _data, writable = _read_shared_settings_snapshot()
    assert observed_path == target
    assert writable is False
