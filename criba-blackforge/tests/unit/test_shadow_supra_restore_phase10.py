"""F10: Qt signal routing under controlled workers, without live SUPRA.

These tests import the complete actions module only in a Qt-enabled checkout;
a sandbox without PySide6 must report NOT_EXECUTED, not PASS.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from criba.ui import actions
from criba.ui import dossier_workflow_view


class Signal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, data):
        assert self.callback is not None
        self.callback(data)


class FakeWorker:
    def __init__(self, fn):
        self.fn = fn
        self.signals = SimpleNamespace(done=Signal(), fail=Signal())


def window(run_id="run-old", problem="problem"):
    return SimpleNamespace(
        invent_sheet={"run_id": run_id},
        packet={"kind": "synthetic"},
        problem=problem,
    )


@pytest.fixture
def rig(monkeypatch):
    workers = []
    reports = []
    errors = []
    monkeypatch.setattr(actions, "Worker", FakeWorker)
    monkeypatch.setattr(actions, "_start_worker", lambda win, worker: workers.append(worker))
    monkeypatch.setattr(actions, "_activity", lambda *args: None)
    monkeypatch.setattr(actions, "show_error", lambda *args: errors.append(args))
    monkeypatch.setattr(
        dossier_workflow_view, "apply_dossier_report",
        lambda win, report: reports.append((win, report)),
    )
    return workers, reports, errors


def test_restore_callback_from_previous_sheet_is_ignored(rig):
    workers, reports, errors = rig
    win = window()
    actions.on_restore_latest_supra(win)
    win.invent_sheet = {"run_id": "new-run"}
    workers[0].signals.done.emit({"empty": True})
    workers[0].signals.fail.emit("old error")
    assert reports == [] and errors == []


def test_restore_when_no_sheet_cannot_overwrite_new_problem(rig):
    workers, reports, _ = rig
    win = window()
    win.invent_sheet = None
    actions.on_restore_latest_supra(win)
    win.problem = "new problem"
    workers[0].signals.done.emit({"empty": True})
    assert reports == []


def test_restore_with_reused_run_id_but_new_sheet_is_stale(rig):
    workers, reports, _ = rig
    win = window()
    actions.on_restore_latest_supra(win)
    win.invent_sheet = {"run_id": "run-old"}
    workers[0].signals.done.emit({"empty": True})
    assert reports == []


def test_mutated_run_id_in_same_sheet_is_stale(rig):
    workers, reports, _ = rig
    win = window()
    actions.on_restore_latest_supra(win)
    win.invent_sheet["run_id"] = "updated"
    workers[0].signals.done.emit({"empty": True})
    assert reports == []


def test_restore_from_older_request_is_ignored(rig):
    workers, reports, _ = rig
    win = window()
    actions.on_restore_latest_supra(win)
    actions.on_restore_latest_supra(win)
    workers[0].signals.done.emit({"empty": True})
    assert reports == []
    workers[1].signals.done.emit({"empty": True})
    assert len(reports) == 1


def test_duplicate_done_and_late_fail_cannot_reapply(rig):
    workers, reports, errors = rig
    win = window()
    actions.on_restore_latest_supra(win)
    workers[0].signals.done.emit({"empty": True})
    workers[0].signals.done.emit({"empty": True})
    workers[0].signals.fail.emit("late error")
    assert len(reports) == 1 and errors == []
    assert win._supra_restore_token is None


def test_successful_restore_in_original_context_applies_once(rig):
    workers, reports, errors = rig
    win = window()
    actions.on_restore_latest_supra(win)
    workers[0].signals.done.emit({"empty": True})
    assert len(reports) == 1 and reports[0][0] is win
    assert not errors


def test_failed_restore_only_changes_original_context(rig):
    workers, _, errors = rig
    win = window()
    win.right_panel = None
    actions.on_restore_latest_supra(win)
    workers[0].signals.fail.emit("synthetic failure")
    assert len(errors) == 1
    assert win._supra_restore_token is None


def test_new_supra_panel_invalidates_old_restore(rig):
    workers, reports, _ = rig
    win = window()
    actions.on_restore_latest_supra(win)
    win.nav = {"navSupra": SimpleNamespace(setChecked=lambda _: None)}
    win.content_label = SimpleNamespace(setText=lambda _: None)
    win.content_sub = SimpleNamespace(setText=lambda _: None)
    actions.on_supra(win)  # actual runtime wiring, worker body never executed
    assert len(workers) == 2
    workers[0].signals.done.emit({"empty": True})
    assert reports == []
