"""A real Qt worker must not publish into a different session."""
import threading
import time
from pathlib import Path

import pytest
from criba.engine import activate
from criba.ui import actions
from PySide6.QtWidgets import QApplication


@pytest.mark.parametrize("transition", ["new", "history", "close"])
def test_generation_result_after_new_session_is_discarded(tmp_path, monkeypatch, transition):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow
    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "session.sqlite")
    started, release = threading.Event(), threading.Event()
    packet = activate("A")
    def generate(problem):
        started.set()
        assert release.wait(5)
        return packet
    monkeypatch.setattr(actions, "_generate_criba_packet", generate)
    monkeypatch.setattr(actions, "_enhance_packet_async", lambda packet: None)
    try:
        actions.on_nueva_idea_no_dialog(win, "A")
        actions.on_generar(win)
        assert started.wait(3)
        if transition == "new":
            actions.on_nueva_idea_no_dialog(win, "B")
        elif transition == "history":
            from criba.ui import dialogs
            monkeypatch.setattr(dialogs, "show_history", lambda _win: {"packet": activate("B")})
            actions.on_historial(win)
        else:
            win.close()
        expected_packet = win.packet
        expected_problem = win.problem
        release.set()
        limit = time.monotonic() + 5
        while win._live_workers and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        app.processEvents()
        assert not win._live_workers
        assert win.problem == expected_problem
        assert win.packet is expected_packet
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()





def test_evaluation_callback_is_discarded_after_history_loads_new_packet(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "evaluation-history.sqlite")
    started, release = threading.Event(), threading.Event()
    old_packet = activate("Old objective")
    new_packet = activate("New objective")
    real_build = actions._build_ranking_rows
    applied = []

    def delayed_build(packet):
        if packet is old_packet:
            started.set()
            assert release.wait(5)
        return real_build(packet)

    def record_evaluation(window, rows):
        applied.append(
            {
                "problem": window.problem,
                "titles": [row["titulo"] for row in rows],
                "gui_thread": threading.get_ident() == threading.main_thread().ident,
            }
        )

    monkeypatch.setattr(actions, "_build_ranking_rows", delayed_build)
    monkeypatch.setattr(actions, "_on_evaluated", record_evaluation)
    monkeypatch.setattr("criba.ui.dialogs.show_history", lambda _win: {"packet": new_packet})
    try:
        actions._invalidate_generation(win)
        win.problem = old_packet["original_query"]
        win.packet = old_packet
        actions.on_evaluar(win)
        assert started.wait(3)
        actions.on_historial(win)
        expected_new_titles = [idea["title"] for idea in new_packet["innovation"]["ideas"]]
        assert applied == [
            {
                "problem": new_packet["original_query"],
                "titles": expected_new_titles,
                "gui_thread": True,
            }
        ]
        release.set()
        limit = time.monotonic() + 5
        while win._live_workers and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        app.processEvents()
        assert not win._live_workers
        assert len(applied) == 1
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()


def test_opening_history_invalidates_inflight_generation_even_when_cancelled(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "history-cancel.sqlite")
    started, release = threading.Event(), threading.Event()
    packet = activate("A")

    def generate(problem):
        started.set()
        assert release.wait(5)
        return packet

    def open_and_cancel(_win):
        release.set()
        limit = time.monotonic() + 5
        while win._live_workers and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        app.processEvents()
        return None

    monkeypatch.setattr(actions, "_generate_criba_packet", generate)
    monkeypatch.setattr(actions, "_enhance_packet_async", lambda _packet: None)
    monkeypatch.setattr("criba.ui.dialogs.show_history", open_and_cancel)
    try:
        actions.on_nueva_idea_no_dialog(win, "A")
        actions.on_generar(win)
        assert started.wait(3)
        actions.on_historial(win)
        assert win.packet is None
        assert win.problem == "A"
        assert not win._live_workers
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()





def test_inventar_result_is_discarded_after_project_changes(tmp_path, monkeypatch):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "models.json"))
    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication([])
    app.setQuitOnLastWindowClosed(False)
    win = ShadowWindow(database=tmp_path / "inventar-session.sqlite")
    started, release = threading.Event(), threading.Event()
    returned = []

    def invent(problem, **_kwargs):
        returned.append(problem)
        started.set()
        assert release.wait(5)
        return {"query": problem}

    applied = []
    monkeypatch.setattr(actions, "_run_inventar", invent)
    monkeypatch.setattr(actions, "_on_invented", lambda _win, sheet: applied.append(sheet))
    try:
        actions.on_nueva_idea_no_dialog(win, "Project A")
        actions.on_inventar(win)
        assert started.wait(3)
        actions.on_nueva_idea_no_dialog(win, "Project B")
        release.set()
        limit = time.monotonic() + 5
        while win._live_workers and time.monotonic() < limit:
            app.processEvents()
            threading.Event().wait(0.005)
        app.processEvents()
        assert returned == ["Project A"]
        assert applied == []
        assert win.problem == "Project B"
        assert not win._live_workers
    finally:
        release.set()
        win.pool.waitForDone(6000)
        app.processEvents()
        win.close()




