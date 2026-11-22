"""F29 Qt contract: explicit source selection; no live HTTP or model requests."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "shadow_ui"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

pytest.importorskip("PySide6")
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication, QMessageBox  # noqa: E402

from criba.interpreter_sources import ModelChoice, SourceCatalog  # noqa: E402
from criba.model_config import load_model_settings, save_model_settings, ModelProfile  # noqa: E402
from criba.ui import actions  # noqa: E402
from shadow_window import ShadowWindow  # noqa: E402


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture()
def win(app, tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.setenv("CRIBA_EXTERNAL_BASE_URL", "http://127.0.0.1:8645/v1")
    monkeypatch.delenv("CRIBA_EXTERNAL_API_KEY", raising=False)
    monkeypatch.delenv("CRIBA_EXTERNAL_PROVIDER", raising=False)
    monkeypatch.delenv("CRIBA_CRITIC_MODEL", raising=False)
    window = ShadowWindow(database=str(tmp_path / "shadow.sqlite3"))
    try:
        yield window
    finally:
        window.close()
        app.processEvents()


def test_default_never_chooses_stale_cloud_model(win):
    selector = win.topcards.interpreter_selector
    assert selector.currentData() is None
    assert selector.currentText() == "Cargar modelo"
    assert "Cargar modelo" in win.header.model_btn.text()
    assert selector.count() == 5


def test_hermes_catalog_requires_user_selection_and_no_free_claim(win, app):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:hermes"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "provider/actual-model"),),
        "Precio y acceso NO verificados.",
    ))
    app.processEvents()
    assert selector.currentData() is None
    choices = [
        (i, selector.itemText(i)) for i in range(selector.count())
        if selector.itemData(i) == ("openai_compatible", "provider/actual-model")
    ]
    assert len(choices) == 1
    index, label = choices[0]
    assert "precio no verificado" in label
    assert "· free" not in label
    selector.setCurrentIndex(index)
    assert "provider/actual-model" in win.header.model_btn.text()


def test_late_catalog_cannot_override_changed_source(win):
    selector = win.topcards.interpreter_selector
    before = selector.count()
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "stale-model"),),
        "not authoritative",
    ))
    assert selector.count() == before


def test_opencode_catalog_does_not_create_executable_interpreter(win):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:opencode"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "opencode", SourceCatalog(
        "opencode", (ModelChoice("opencode", "fast", "provider", True),),
        "catalog only",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("opencode_catalog", "provider/fast")
    )
    selector.setCurrentIndex(index)
    assert "NO EJECUTABLE" in win.topcards.interpreter_status.text()


def test_ollama_selection_activates_explicit_profile_without_token(
    win, app, monkeypatch
):
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:ollama"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "ollama", SourceCatalog(
        "ollama", (ModelChoice("ollama", "qwen3:8b"),), "catalog",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("ollama_catalog", "qwen3:8b")
    )
    selector.setCurrentIndex(index)
    app.processEvents()
    assert selector.currentData() == "local_llama"
    settings = load_model_settings()
    assert settings.enabled
    assert settings.active_profile().backend == "ollama"
    assert settings.active_profile().model == "qwen3:8b"
    assert settings.active_profile().endpoint == "http://127.0.0.1:11434"
    assert "banco pendiente" in selector.currentText()


def test_no_model_preflight_denies_invent_before_provider_or_mutator(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    selector.setCurrentIndex(0)
    win.problem = "fixture"
    messages = []
    monkeypatch.setattr(actions, "show_error", lambda _win, title, message:
                        messages.append((title, message)))
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("must not lock or create work without model"))
    actions.on_inventar(win)
    assert messages and messages[0][0] == "Cargar modelo"


def test_wrong_hermes_base_blocked_before_any_work(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    selector.addItem("Hermes · fixture", ("openai_compatible", "fixture"))
    selector.setCurrentIndex(selector.count() - 1)
    win.problem = "fixture"
    monkeypatch.setenv("CRIBA_EXTERNAL_BASE_URL", "https://external.invalid/v1")
    errors = []
    monkeypatch.setattr(actions, "show_error", lambda _win, title, message:
                        errors.append((title, message)))
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("must not send selected Hermes model elsewhere"))
    actions.on_inventar(win)
    assert errors and errors[0][0] == "Hermes"


def test_ollama_cancel_preserves_disabled_settings(win, app, monkeypatch):
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:ollama"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "ollama", SourceCatalog(
        "ollama", (ModelChoice("ollama", "fixture-cancel:7b"),), "catalog",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("ollama_catalog", "fixture-cancel:7b")
    )
    selector.setCurrentIndex(index)
    app.processEvents()
    settings = load_model_settings()
    assert not settings.enabled
    assert not any(p.model == "fixture-cancel:7b" for p in settings.profiles)
    assert selector.currentData() == ("ollama_catalog", "fixture-cancel:7b")


def test_remote_price_unknown_decline_does_not_launch_worker(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:hermes"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "provider/paid-unknown"),), "unknown",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("openai_compatible", "provider/paid-unknown")
    )
    assert selector.itemData(index, Qt.ItemDataRole.UserRole + 1) == "hermes"
    selector.setCurrentIndex(index)
    win.problem = "fixture"
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.No,
    )
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("declined consent may not start work"))
    actions.on_inventar(win)
    assert selector.isEnabled()


def test_remote_price_unknown_approval_reaches_mutation_boundary(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:hermes"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "provider/paid-unknown"),), "unknown",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("openai_compatible", "provider/paid-unknown")
    )
    selector.setCurrentIndex(index)
    win.problem = "fixture"
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    class ConsentReached(Exception):
        pass
    def before_mutation(_win):
        raise ConsentReached()
    monkeypatch.setattr(actions, "_cancelar_protocolo_pendiente", before_mutation)
    with pytest.raises(ConsentReached):
        actions.on_inventar(win)


def test_hidden_second_critic_model_is_denied_before_cost_consent(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:hermes"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "provider/selected"),), "unknown",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("openai_compatible", "provider/selected")
    )
    selector.setCurrentIndex(index)
    win.problem = "fixture"
    monkeypatch.setenv("CRIBA_CRITIC_MODEL", "poolside/laguna-s-2.1:free")
    messages = []
    monkeypatch.setattr(actions, "show_error", lambda _win, title, message:
                        messages.append((title, message)))
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: pytest.fail("must not request paid consent for hidden critic"),
    )
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("must not run with unselected critic"))
    actions.on_inventar(win)
    assert messages and messages[0][0] == "Hermes · modelo de crítica"


def test_ollama_profile_drift_blocks_before_mutator(win, monkeypatch):
    selector = win.topcards.interpreter_selector
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
    )
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:ollama"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "ollama", SourceCatalog(
        "ollama", (ModelChoice("ollama", "qwen:original"),), "catalog",
    ))
    index = next(i for i in range(selector.count())
                 if selector.itemData(i) == ("ollama_catalog", "qwen:original"))
    selector.setCurrentIndex(index)
    assert selector.itemData(index, Qt.ItemDataRole.UserRole + 2) == (
        "ollama", "qwen:original"
    )
    settings = load_model_settings()
    replacement = ModelProfile(backend="ollama", model="qwen:replacement",
                               endpoint="http://127.0.0.1:11434")
    settings.profiles.append(replacement)
    settings.active_profile_id = replacement.id
    save_model_settings(settings)

    win.problem = "fixture"
    errors = []
    monkeypatch.setattr(actions, "show_error", lambda _win, title, msg:
                        errors.append((title, msg)))
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("changed active profile cannot start work"))
    actions.on_inventar(win)
    assert errors and errors[0][0] == "Ollama · perfil cambiado"


@pytest.mark.parametrize("change", ["model", "problem", "critic", "seed"])
def test_hermes_modal_approval_is_not_reusable_after_change(
    win, monkeypatch, change
):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:hermes"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "hermes", SourceCatalog(
        "hermes", (ModelChoice("hermes", "provider/consented"),), "unknown",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("openai_compatible", "provider/consented")
    )
    selector.setCurrentIndex(index)
    win.problem = "original"
    win.topcards.seed_input.clear()
    errors = []
    monkeypatch.setattr(actions, "show_error", lambda _win, title, msg:
                        errors.append((title, msg)))

    def user_changes_during_modal(*_a, **_kw):
        if change == "model":
            selector.setCurrentIndex(0)
        elif change == "problem":
            win.problem = "modified"
        elif change == "critic":
            monkeypatch.setenv("CRIBA_CRITIC_MODEL", "another/provider")
        else:
            win.topcards.seed_input.setText("invalid")
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", user_changes_during_modal)
    monkeypatch.setattr(actions, "_lock_mutators", lambda _win:
                        pytest.fail("stale consent may never start inference"))
    actions.on_inventar(win)
    assert errors and errors[0][0] == "Hermes · consentimiento caducado"


@pytest.mark.parametrize("mutation", ["selection", "disk"])
def test_ollama_consent_cannot_overwrite_drifted_selection_or_file(
    win, app, monkeypatch, mutation
):
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:ollama"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "ollama", SourceCatalog(
        "ollama", (ModelChoice("ollama", "f30:pending"),), "catalog",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("ollama_catalog", "f30:pending")
    )
    config_path = Path(os.environ["CRIBA_MODEL_CONFIG"])

    def mutate_during_modal(*_args, **_kwargs):
        if mutation == "selection":
            selector.setCurrentIndex(0)
        else:
            config_path.write_text('{"sentinel":"external-edit"}', encoding="utf-8")
        return QMessageBox.StandardButton.Yes

    monkeypatch.setattr(QMessageBox, "question", mutate_during_modal)
    selector.setCurrentIndex(index)
    app.processEvents()
    assert not any(p.model == "f30:pending"
                   for p in load_model_settings().profiles)
    if mutation == "disk":
        assert config_path.read_text(encoding="utf-8") == (
            '{"sentinel":"external-edit"}'
        )
    else:
        assert not config_path.exists()


@pytest.mark.parametrize("corrupt", [
    '{"schema_version":1,"enabled":true,"profiles":[]}',
    '{"schema_version":1,"enabled":true,"active_profile_id":"missing",'
    '"profiles":[{"id":"active"}]}',
    '{"schema_version":1,"enabled":true,"active_profile_id":"same",'
    '"profiles":[{"id":"same"},{"id":"same"}]}',
    '{"schema_version":1,"enabled":true,"active_profile_id":"a",'
    '"profiles":[{"id":"a"}],"enabled":false}',
    '{"schema_version":1,"enabled":true,"active_profile_id":"a",'
    '"profiles":[{"id":"a"}],"x":NaN}',
    '{"schema_version":2,"enabled":true,"active_profile_id":"a",'
    '"profiles":[{"id":"a"}]}',
    "{invalid-json",
])
def test_ollama_activation_never_overwrites_untrusted_old_model_settings(
    win, app, monkeypatch, corrupt
):
    config_path = Path(os.environ["CRIBA_MODEL_CONFIG"])
    config_path.write_text(corrupt, encoding="utf-8")
    selector = win.topcards.interpreter_selector
    block = selector.blockSignals(True)
    selector.setCurrentIndex(selector.findData("source:ollama"))
    selector.blockSignals(block)
    actions._on_source_catalog(win, "ollama", SourceCatalog(
        "ollama", (ModelChoice("ollama", "f30:new"),), "catalog",
    ))
    index = next(
        i for i in range(selector.count())
        if selector.itemData(i) == ("ollama_catalog", "f30:new")
    )
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *_a, **_kw: pytest.fail(
            "corrupt config must be rejected before confirmation"
        ),
    )
    selector.setCurrentIndex(index)
    app.processEvents()
    assert config_path.read_text(encoding="utf-8") == corrupt
    assert selector.currentData() == ("ollama_catalog", "f30:new")
