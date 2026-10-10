"""Background wording must never mutate the published deterministic snapshot."""
import threading
import time
from pathlib import Path

from criba.engine import activate
from criba.ui import actions
from PySide6.QtWidgets import QApplication


def test_pending_enhancement_does_not_mutate_published_packet(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "snapshot.sqlite")
    started, release = threading.Event(), threading.Event()
    def enhance(packet):
        packet["innovation"]["ideas"][0]["title"] = "UNPUBLISHED"
        started.set()
        assert release.wait(5)
    monkeypatch.setattr(actions, "_generate_criba_packet", lambda problem: activate(problem))
    monkeypatch.setattr(actions, "_enhance_packet_async", enhance)
    try:
        actions.on_nueva_idea_no_dialog(win, "Water")
        actions.on_generar(win)
        limit = time.monotonic() + 4
        while not started.is_set() and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(.005)
        assert started.is_set()
        assert win.packet["innovation"]["ideas"][0]["title"] != "UNPUBLISHED"
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()


def test_applied_enhancement_updates_packet_and_ranking_consistently(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "coherent-ranking.sqlite")
    started, release = threading.Event(), threading.Event()

    def enhance(packet):
        packet["innovation"]["ideas"][0]["title"] = "Enhanced coherent title"
        packet["semantic_generation"] = {"status": "ok", "model": "test-model"}
        started.set()
        assert release.wait(5)

    monkeypatch.setattr(actions, "_generate_criba_packet", lambda problem: activate(problem))
    monkeypatch.setattr(actions, "_enhance_packet_async", enhance)
    try:
        actions.on_nueva_idea_no_dialog(win, "Water")
        actions.on_generar(win)
        limit = time.monotonic() + 5
        while (win.packet is None or not started.is_set()) and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        assert win.packet is not None and started.is_set()
        old_ids = [idea["id"] for idea in win.packet["innovation"]["ideas"]]
        assert win.packet["innovation"]["ideas"][0]["title"] != "Enhanced coherent title"

        actions.on_evaluar(win)
        limit = time.monotonic() + 5
        while not win.refs["rankingModel"].rowCount() and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        model = win.refs["rankingModel"]
        assert model.rowCount() == len(win.packet["innovation"]["ideas"])
        assert model.index(0, 1).data() != "Enhanced coherent title"

        release.set()
        win.pool.waitForDone(6000)
        limit = time.monotonic() + 3
        while win._background_workers and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        app.processEvents()
        ideas = win.packet["innovation"]["ideas"]
        assert ideas[0]["title"] == "Enhanced coherent title"
        assert [idea["id"] for idea in ideas] == old_ids
        assert [model.index(row, 1).data() for row in range(model.rowCount())] == [
            idea["title"] for idea in ideas
        ]
        assert win.packet["semantic_generation"]["status"] == "ok"
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()
