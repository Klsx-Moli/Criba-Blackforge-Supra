"""Serialize background enhancement, retaining only the latest queued request."""
from types import SimpleNamespace

from criba.ui import actions
from PySide6.QtWidgets import QApplication


def test_only_latest_enhancement_is_queued(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    started = []
    win = SimpleNamespace(pool=SimpleNamespace(start=started.append))
    workers = [actions.Worker(lambda: None) for _ in range(3)]
    for worker in workers:
        actions._start_worker(win, worker, "enhance")
    assert started == workers[:1]
    assert win._enhancement_pending is workers[2]
    assert win._background_workers == workers[:1]
    workers[0].signals.done.emit(None)
    app.processEvents()
    assert started == [workers[0], workers[2]]
    workers[2].signals.done.emit(None)
    app.processEvents()
    assert win._background_workers == []
