"""Phase17: protocol worker callbacks are session-bound, one-shot, and deduped.

Qt event loop and provider requests are NOT used. PySide is required to import
the actual actions module; do not claim a PASS when dependency is unavailable.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from criba.ui import actions


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
        self.fn = fn
        self.signals = SimpleNamespace(done=Signal(), fail=Signal())


class Button:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value):
        self.enabled = value


class Text:
    def __init__(self):
        self.value = ""

    def setText(self, value):
        self.value = value


def sheet(run="run-1", candidate="candidate-1"):
    return {
        "run_id": run, "query": "synthetic query",
        "entries": [{"candidate_id": candidate, "estado_interpretacion": "PROPUESTA",
                     "hipotesis": "not validated", "mecanismo": "synthetic"}],
    }


@pytest.fixture
def rig(monkeypatch):
    workers = []
    errors = []
    activities = []
    applied = []
    monkeypatch.setattr(actions, "Worker", FakeWorker)
    monkeypatch.setattr(actions, "_start_worker", lambda _win, worker: workers.append(worker))
    monkeypatch.setattr(actions, "set_chip", lambda *_args: None)
    monkeypatch.setattr(actions, "show_error", lambda *_args: errors.append(_args))
    monkeypatch.setattr(actions, "_activity", lambda *_args: activities.append(_args))
    from criba.interprete import refinamiento
    def apply(entry, report):
        applied.append((entry, report))
        return {**entry, "protocolo_operativo": "test only"}
    monkeypatch.setattr(refinamiento, "aplicar_protocolo", apply)
    return workers, errors, activities, applied


def window(current):
    return SimpleNamespace(
        invent_sheet=current, problem=current["query"],
        candidates=None, right_panel=SimpleNamespace(protocolo=Button()),
        refs={"ideaSummary": Text(), "ideaEstadoChip": Text()},
    )


def test_old_done_does_not_replace_new_sheet(rig):
    workers, errors, _, applied = rig
    initial = sheet("old", "old")
    win = window(initial)
    actions.on_protocolo_operativo(win)
    assert len(workers) == 1 and not win.right_panel.protocolo.enabled
    replacement = sheet("new", "new")
    win.invent_sheet = replacement
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert win.invent_sheet is replacement
    assert replacement["entries"][0]["candidate_id"] == "new"
    assert not applied and not errors
    assert win.right_panel.protocolo.enabled
    assert win._protocolo_intent is None


@pytest.mark.parametrize("change", [
    lambda w: w.invent_sheet.update(run_id="another-run"),
    lambda w: w.invent_sheet.update(query="different objective"),
    lambda w: w.invent_sheet["entries"][0].update(mecanismo="changed while working"),
    lambda w: w.invent_sheet["entries"].reverse(),
    lambda w: setattr(w, "problem", "new problem"),
])
def test_modified_context_does_not_apply_stale_result(rig, change):
    workers, errors, _, applied = rig
    s = sheet()
    s["entries"].append({**s["entries"][0], "candidate_id": "other"})
    win = window(s)
    actions.on_protocolo_operativo(win)
    change(win)
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert not applied and not errors
    assert win._protocolo_intent is None
    assert win.right_panel.protocolo.enabled


def test_old_failure_cannot_interrupt_new_request(rig):
    workers, errors, _, _ = rig
    win = window(sheet("old"))
    actions.on_protocolo_operativo(win)
    win.invent_sheet = sheet("new")
    actions.on_protocolo_operativo(win)
    assert len(workers) == 2
    workers[0].signals.fail.emit("stale failure")
    assert not errors and not win.right_panel.protocolo.enabled
    workers[1].signals.fail.emit("current failure")
    assert len(errors) == 1 and "current failure" in errors[0][-1]
    assert win.right_panel.protocolo.enabled


def test_double_invocation_only_creates_one_worker(rig):
    workers, _, _, _ = rig
    win = window(sheet())
    actions.on_protocolo_operativo(win)
    actions.on_protocolo_operativo(win)
    assert len(workers) == 1
    workers[0].signals.fail.emit("done")


def test_current_success_is_one_shot_and_late_failure_is_ignored(rig):
    workers, errors, _, applied = rig
    win = window(sheet())
    actions.on_protocolo_operativo(win)
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert len(applied) == 1
    assert win.invent_sheet["entries"][0]["protocolo_operativo"] == "test only"
    assert win.right_panel.protocolo.enabled
    previous = win.refs["ideaSummary"].value
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    workers[0].signals.fail.emit("late")
    assert len(applied) == 1 and not errors
    assert win.refs["ideaSummary"].value == previous


def test_old_failure_on_replaced_sheet_is_silent(rig):
    workers, errors, _, _ = rig
    win = window(sheet("old"))
    actions.on_protocolo_operativo(win)
    win.invent_sheet = sheet("new")
    workers[0].signals.fail.emit("old error")
    assert errors == []
    assert win.right_panel.protocolo.enabled



def test_selection_change_in_same_sheet_discards_old_result(rig):
    workers, errors, _, applied = rig
    s = sheet()
    s["entries"].append({
        "candidate_id": "candidate-2",
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "not validated",
        "mecanismo": "different",
    })
    win = window(s)
    win.candidates = SimpleNamespace(interpretation_index=0)
    actions.on_protocolo_operativo(win)
    win.candidates.interpretation_index = 1
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert not applied and not errors
    assert win.candidates.interpretation_index == 1
    assert "protocolo_operativo" not in s["entries"][0]


def test_new_selection_supersedes_old_request_even_with_same_sheet(rig):
    workers, errors, _, applied = rig
    s = sheet()
    s["entries"].append({
        "candidate_id": "candidate-2",
        "estado_interpretacion": "PROPUESTA",
        "hipotesis": "not validated",
        "mecanismo": "different",
    })
    win = window(s)
    win.candidates = SimpleNamespace(interpretation_index=0)
    actions.on_protocolo_operativo(win)
    win.candidates.interpretation_index = 1
    actions.on_protocolo_operativo(win)
    assert len(workers) == 2
    workers[0].signals.fail.emit("old worker")
    assert not errors
    assert not win.right_panel.protocolo.enabled
    # A controlled failure from the currently selected proposal is delivered.
    workers[1].signals.fail.emit("new worker")
    assert len(errors) == 1
    assert win.right_panel.protocolo.enabled
    assert not applied
