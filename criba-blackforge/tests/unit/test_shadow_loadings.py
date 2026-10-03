"""Loading state and frame regression tests; no network or artificial success."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))

import pytest
from criba.ui.actions import Worker, _start_worker
from loading_indicator import LoadingIndicator
from PySide6.QtCore import QSize
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication


@pytest.mark.parametrize("resource", ["flujo_energia", "neon_hud"])
def test_frames_lifecycle_and_concurrency(resource):
    app = QApplication.instance() or QApplication([])
    w = LoadingIndicator(resource, QSize(210, 54))
    assert len(w.frames) == 60
    assert set(w.durations) == {40.0}
    assert w.frames[0].hasAlphaChannel()
    assert not w.timer.isActive()
    w.begin("first", "Generando ideas…")
    app.processEvents()
    assert w.timer.isActive()
    QTest.qWait(130)
    assert w.index > 0
    w.begin("second", "Interpretando…")
    w.finish("first")
    assert w.isVisible() and w.timer.isActive()
    w.index = 59
    w._advance()
    assert w.index == 0
    w.hide()
    assert not w.timer.isActive()
    w.show()
    assert w.timer.isActive()
    w.finish("second")
    assert w.isHidden() and not w.timer.isActive()
    w.close()


@pytest.mark.parametrize("signal", ["done", "fail"])
def test_worker_terminal_signals_stop_only_own_loading(signal):
    app = QApplication.instance() or QApplication([])
    loading = LoadingIndicator("flujo_energia", QSize(210, 54))
    win = SimpleNamespace(topcards=SimpleNamespace(generation_loading=loading),
                          pool=SimpleNamespace(start=lambda worker: None), _live_workers=[])
    first, second = Worker(lambda: None), Worker(lambda: None)
    _start_worker(win, first, "generate")
    _start_worker(win, second, "interpret")
    getattr(first.signals, signal).emit("test")
    app.processEvents()
    assert len(loading.operations) == 1
    second.signals.done.emit({"cancelled": True})
    app.processEvents()
    assert not loading.operations
    assert loading.isHidden() and not loading.timer.isActive()
    loading.close()
