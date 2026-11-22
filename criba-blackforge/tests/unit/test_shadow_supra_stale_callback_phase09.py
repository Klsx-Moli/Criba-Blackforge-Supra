"""F09: stale SUPRA worker signals must never contaminate another Shadow run.

All workers, dossier writes and UI widgets are doubles. No SUPRA client,
network, filesystem write, model call or Qt event loop is started.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from criba.ui import actions
from criba import supra_dossier


class Text:
    def __init__(self):
        self.text = ""

    def setText(self, value):
        self.text = value


class Signal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback

    def emit(self, value):
        assert self.callback is not None
        self.callback(value)


class FakeWorker:
    def __init__(self, fn):
        # Intentionally do not run fn: execution and external POST forbidden.
        self.fn = fn
        self.signals = SimpleNamespace(done=Signal(), fail=Signal())


@pytest.fixture
def harness(monkeypatch):
    workers = []
    errors = []
    monkeypatch.setattr(actions, "Worker", FakeWorker)
    monkeypatch.setattr(actions, "_start_worker", lambda win, worker: workers.append(worker))
    monkeypatch.setattr(actions, "set_chip", lambda *args: None)
    monkeypatch.setattr(actions, "_activity", lambda *args: None)
    monkeypatch.setattr(actions, "show_error", lambda *args: errors.append(args))
    monkeypatch.setattr(
        supra_dossier, "preparar_dossier",
        lambda entry, query, ficha_bloqueo=None: {
            "dossier_id": "dossier-" + entry["candidate_id"],
            "candidate_id": entry["candidate_id"],
        },
    )
    monkeypatch.setattr(
        supra_dossier, "guardar_dossier",
        lambda dossier: Path("/synthetic/no-dossier-written.jsonl"),
    )
    return workers, errors


def sheet(run_id, candidate_id):
    return {
        "query": "Synthetic problem " + run_id,
        "run_id": run_id,
        "entries": [{
            "candidate_id": candidate_id,
            "estado_interpretacion": "PROPUESTA",
            "hipotesis": "synthetic",
            "mecanismo": "synthetic model fixture only",
        }],
    }


def window(s):
    return SimpleNamespace(
        invent_sheet=s,
        candidates=None,
        refs={"ideaSummary": Text(), "ideaEstadoChip": Text()},
    )


def reply(candidate_id):
    return {
        "dossiers": [{"dossier_id": "dossier-" + candidate_id}],
        "runs": [{
            "dossier_id": "dossier-" + candidate_id,
            "completion_status": "COMPLETED",
            "secure_sandbox_status": "NOT_VERIFIED",
            "criba_mechanism_execution_status": "NOT_EXECUTED",
            "read": {"project_id": "synthetic-" + candidate_id},
        }],
    }


def test_old_completion_cannot_write_new_run(harness):
    workers, errors = harness
    old, new = sheet("old", "old"), sheet("new", "new")
    win = window(old)
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1
    win.invent_sheet = new
    actions.on_desarrollar_supra(win)
    summary = win.refs["ideaSummary"].text
    assert len(workers) == 2

    workers[0].signals.done.emit(reply("old"))
    assert "supra_runs" not in old and "supra_runs" not in new
    assert win.refs["ideaSummary"].text == summary

    workers[1].signals.done.emit(reply("new"))
    assert new["supra_runs"] == reply("new")["runs"]
    assert "supra_runs" not in old
    assert win._supra_submission_token is None
    assert errors == []


def test_old_failure_does_not_overwrite_new_submission_same_sheet(harness):
    workers, errors = harness
    current = sheet("same", "candidate")
    win = window(current)
    actions.on_desarrollar_supra(win)
    actions.on_desarrollar_supra(win)
    assert len(workers) == 2
    before = win.refs["ideaSummary"].text
    workers[0].signals.fail.emit("old synthetic timeout")
    assert win.refs["ideaSummary"].text == before
    assert errors == []
    workers[1].signals.fail.emit("new synthetic timeout")
    assert "NO CONFIRMADA" in win.refs["ideaSummary"].text
    assert len(errors) == 1
    assert win._supra_submission_token is None


def test_duplicate_done_or_late_failure_does_not_undo_first_terminal_signal(harness):
    workers, errors = harness
    win = window(sheet("run", "one"))
    actions.on_desarrollar_supra(win)
    workers[0].signals.done.emit(reply("one"))
    before = win.refs["ideaSummary"].text
    committed = list(win.invent_sheet["supra_runs"])
    workers[0].signals.done.emit(reply("wrong"))
    workers[0].signals.fail.emit("late error")
    assert win.refs["ideaSummary"].text == before
    assert win.invent_sheet["supra_runs"] == committed
    assert errors == []


def test_modified_run_id_in_same_sheet_blocks_old_callback(harness):
    workers, errors = harness
    s = sheet("old-run", "one")
    win = window(s)
    actions.on_desarrollar_supra(win)
    s["run_id"] = "new-run"
    before = win.refs["ideaSummary"].text
    workers[0].signals.done.emit(reply("one"))
    assert "supra_runs" not in s
    assert win.refs["ideaSummary"].text == before
    assert errors == []


def test_completion_without_current_sheet_never_updates_widget(harness):
    workers, errors = harness
    win = window(sheet("gone", "one"))
    actions.on_desarrollar_supra(win)
    win.invent_sheet = None
    before = win.refs["ideaSummary"].text
    workers[0].signals.done.emit(reply("one"))
    workers[0].signals.fail.emit("late")
    assert win.refs["ideaSummary"].text == before
    assert errors == []

def test_reused_run_id_with_new_sheet_is_not_the_same_submission(harness):
    workers, errors = harness
    original = sheet("same-run-id", "old")
    win = window(original)
    actions.on_desarrollar_supra(win)
    replacement = sheet("same-run-id", "new")
    win.invent_sheet = replacement
    summary = win.refs["ideaSummary"].text
    workers[0].signals.done.emit(reply("old"))
    assert "supra_runs" not in replacement and "supra_runs" not in original
    assert win.refs["ideaSummary"].text == summary
    assert errors == []
