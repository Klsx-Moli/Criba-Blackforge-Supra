"""Work failures must not be mistaken for a deleted Qt signal source."""
from criba.ui.actions import Worker
from PySide6.QtWidgets import QApplication


def test_runtime_error_from_work_is_delivered_as_failure(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    assert app is not None
    failures = []
    def fail():
        raise RuntimeError("work-runtime-error")
    worker = Worker(fail)
    worker.signals.fail.connect(failures.append)
    worker.run()
    assert len(failures) == 1
    assert "work-runtime-error" in failures[0]


def test_runtime_error_is_reported_and_releases_registered_worker(monkeypatch):
    import time
    from types import SimpleNamespace

    from criba.ui.actions import _connect_gui, _start_worker
    from PySide6.QtCore import QThreadPool

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    failures = []
    pool = QThreadPool()
    win = SimpleNamespace(pool=pool, _live_workers=[])

    def fail():
        raise RuntimeError("registered-worker-failure")

    worker = Worker(fail)
    _connect_gui(worker, worker.signals.fail, failures.append, failure=True)
    _start_worker(win, worker, "generate")
    assert pool.waitForDone(3000)
    limit = time.monotonic() + 3
    while (win._live_workers or not failures) and time.monotonic() < limit:
        app.processEvents()
        time.sleep(0.005)
    app.processEvents()
    assert len(failures) == 1
    assert "registered-worker-failure" in failures[0]
    assert win._live_workers == []
