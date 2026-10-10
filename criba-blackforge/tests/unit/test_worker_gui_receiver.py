"""Worker callbacks must execute in their explicit GUI receiver context."""
import threading
import time

from criba.ui import actions
from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication


def test_worker_callback_runs_in_gui_thread(monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    delivered = []
    worker = actions.Worker(lambda: 42)
    receiver = actions._WorkerCallback(
        lambda value: delivered.append((value, QThread.currentThread()))
    )
    worker.signals.done.connect(receiver.done)
    thread = threading.Thread(target=worker.run)
    thread.start()
    thread.join(3)
    limit = time.monotonic() + 3
    while not delivered and time.monotonic() < limit:
        app.processEvents()
    assert delivered == [(42, app.thread())]
    assert receiver.thread() == app.thread()


def test_destroyed_gui_receiver_drops_late_worker_callback(monkeypatch):
    import shiboken6
    from PySide6.QtCore import QCoreApplication, QEvent

    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance() or QApplication([])
    delivered = []
    worker = actions.Worker(lambda: 42)
    actions._connect_gui(worker, worker.signals.done, delivered.append)
    receiver = worker._gui_receivers[0]
    receiver.deleteLater()
    QCoreApplication.sendPostedEvents(receiver, QEvent.Type.DeferredDelete)
    assert not shiboken6.isValid(receiver)

    errors = []

    def run_worker():
        try:
            worker.run()
        except BaseException as exc:  # assertion captures thread escape, including RuntimeError
            errors.append(exc)

    thread = threading.Thread(target=run_worker)
    thread.start()
    thread.join(3)
    app.processEvents()
    assert not thread.is_alive()
    assert errors == []
    assert delivered == []
