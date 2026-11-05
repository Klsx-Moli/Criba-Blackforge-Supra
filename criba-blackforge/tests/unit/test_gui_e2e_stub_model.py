"""GUI -> shared service -> loopback OpenAI-compatible transport -> render."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")
pytest.importorskip("pytestqt")

from criba import inventar as inventar_mod
from criba.ui import actions
from PySide6.QtCore import QEventLoop, QThreadPool, QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "shadow_ui"))

from shadow_window import ShadowWindow  # noqa: E402

from tests.support.openai_stub import StubOpenAIServer  # noqa: E402


@pytest.fixture(scope="module")
def qapp() -> Any:
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def _drain_pool(qapp):
    pool = QThreadPool.globalInstance()
    pool.clear()
    pool.waitForDone(3000)
    qapp.processEvents()
    yield
    pool.clear()
    pool.waitForDone(3000)
    qapp.processEvents()


def _wait_for(qapp, predicate, timeout_ms: int = 15000):
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: loop.quit() if predicate() else None)
    timer.start(25)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    timer.stop()
    return predicate()


def _configure(monkeypatch, tmp_path, server: StubOpenAIServer) -> None:
    monkeypatch.setenv("CRIBA_EXTERNAL_BASE_URL", server.base_url)
    monkeypatch.setenv("CRIBA_EXTERNAL_MODEL", "stub/valid-model")
    monkeypatch.setenv("CRIBA_EXTERNAL_TIMEOUT_S", "5")
    monkeypatch.setenv("CRIBA_EXTERNAL_MAX_TOKENS", "2048")
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "no-local-model.json"))
    monkeypatch.setattr(
        "criba.intelligence.refresh.default_store",
        lambda: None,
    )
    monkeypatch.setattr(
        inventar_mod,
        "append_ledger",
        lambda _sheet, ledger_dir=None: tmp_path / "ledger.jsonl",
    )
    real_invent = inventar_mod.invent

    def limited_invent(problem: str, **kwargs):
        kwargs["top"] = 1
        kwargs["batch_size"] = 2
        return real_invent(problem, **kwargs)

    monkeypatch.setattr(inventar_mod, "invent", limited_invent)


def _window(tmp_path, name: str) -> ShadowWindow:
    win = ShadowWindow(database=str(tmp_path / f"{name}.sqlite3"))
    win.show()
    return win


def test_gui_e2e_inventar_protocolo_y_render_por_transporte_real(
    qapp, tmp_path, monkeypatch
) -> None:
    progress_events: list[dict] = []
    original_progress = actions._on_invent_progress

    def record_progress(win, payload):
        progress_events.append(dict(payload))
        original_progress(win, payload)

    monkeypatch.setattr(actions, "_on_invent_progress", record_progress)

    with StubOpenAIServer() as server:
        _configure(monkeypatch, tmp_path, server)
        win = _window(tmp_path, "e2e")
        try:
            actions.on_nueva_idea_no_dialog(
                win,
                "Reducir errores de registros de almacén sin aumentar tiempos de inspección.",
            )
            win.topcards.btn_gen.click()
            assert _wait_for(qapp, lambda: win.invent_sheet is not None), (
                "la GUI no recibió el lote del servicio"
            )
            sheet = win.invent_sheet
            assert sheet is not None
            entry = sheet["entries"][0]
            assert entry["estado_interpretacion"] == "PROPUESTA"
            assert entry["mecanismo"]
            assert "El pestillo" in win.candidates.interpretation_output.toPlainText()
            assert progress_events
            assert win.topcards.cancel_interpretation.isHidden()

            assert win.right_panel.protocolo.isEnabled()
            win.right_panel.protocolo.click()
            assert _wait_for(
                qapp,
                lambda: bool(
                    (win.invent_sheet or {}).get("entries", [{}])[0].get("protocolo_operativo")
                ),
            ), "la GUI no recibió el protocolo operativo"
            rendered = win.candidates.interpretation_output.toPlainText()
            for marker in (
                "MECANISMO CONCRETO",
                "Componentes:",
                "Secuencia operativa:",
                "Punto físico:",
                "Modo de efecto declarado: MITIGA",
                "Prueba del mecanismo:",
                "(NO VALIDADO)",
            ):
                assert marker in rendered
        finally:
            win.close()
            qapp.processEvents()


def test_gui_e2e_429_muestra_pendiente_sin_crash(qapp, tmp_path, monkeypatch) -> None:
    with StubOpenAIServer(mode="429") as server:
        _configure(monkeypatch, tmp_path, server)
        monkeypatch.setenv("CRIBA_ACCEPTANCE_NO_RETRIES", "1")
        win = _window(tmp_path, "e2e-429")
        try:
            actions.on_nueva_idea_no_dialog(win, "Problema sintético para 429.")
            win.topcards.btn_gen.click()
            assert _wait_for(qapp, lambda: win.invent_sheet is not None)
            entry = win.invent_sheet["entries"][0]
            assert entry["estado_interpretacion"] == "PENDIENTE_INTERPRETACION"
            assert entry["interpretacion_error_kind"] == "rate_limit"
            assert "plan_agotado_429" in entry["interpretacion_error"]
            assert "PENDIENTE DE INTERPRETACIÓN" in (
                win.candidates.interpretation_output.toPlainText()
            )
            assert win.topcards.cancel_interpretation.isHidden()
        finally:
            win.close()
            qapp.processEvents()


def test_gui_e2e_cancelar_muestra_estado_y_no_rompe_la_ventana(qapp, tmp_path, monkeypatch) -> None:
    with StubOpenAIServer(delay_s=0.4) as server:
        _configure(monkeypatch, tmp_path, server)
        win = _window(tmp_path, "e2e-cancel")
        try:
            actions.on_nueva_idea_no_dialog(win, "Problema sintético para cancelar.")
            win.topcards.btn_gen.click()
            assert _wait_for(qapp, lambda: win.topcards.cancel_interpretation.isVisible())
            win.topcards.cancel_interpretation.click()
            assert win.interpreter_cancel_requested is True
            assert "Cancelación solicitada" in win.topcards.cancel_interpretation.text()
            status = win.topcards.interpreter_status.text()
            assert "Cancelación solicitada" in status
            assert "Tiempo:" in status
            assert _wait_for(qapp, lambda: win.invent_sheet is not None, 20000)
            assert win.topcards.cancel_interpretation.isHidden()
            assert win.isVisible()
        finally:
            win.close()
            qapp.processEvents()
