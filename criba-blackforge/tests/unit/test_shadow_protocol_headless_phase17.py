"""Phase17: execute actual protocol callback functions without importing Qt.

Extract the four functions from the checked-out production actions.py via
Python AST. This tests the real function bodies in a headless namespace but
does NOT test signal delivery or QWidget lifecycle in PySide6.
"""
from __future__ import annotations

import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest


class Signal:
    def __init__(self) -> None:
        self.callback = None

    def connect(self, fn) -> None:
        self.callback = fn

    def emit(self, result: Any) -> None:
        assert self.callback is not None
        self.callback(result)


class Worker:
    def __init__(self, fn) -> None:
        self.fn = fn
        self.signals = SimpleNamespace(done=Signal(), fail=Signal())


class Button:
    def __init__(self) -> None:
        self.enabled = True

    def setEnabled(self, value: bool) -> None:
        self.enabled = value


def _sheet(run: str = "run", item: str = "a") -> dict:
    return {
        "run_id": run,
        "query": "Synthetic",
        "interpreter": {"backend": "openai_compatible", "model_requested": "x"},
        "entries": [{"candidate_id": item, "estado_interpretacion": "PROPUESTA",
                     "mecanismo": "synthetic", "hipotesis": "NO VALIDADA"}],
    }


def _window(s: dict, *, selected: int = 0) -> SimpleNamespace:
    return SimpleNamespace(
        invent_sheet=s, problem=s["query"],
        right_panel=SimpleNamespace(protocolo=Button()),
        candidates=SimpleNamespace(interpretation_index=selected),
    )


@pytest.fixture
def harness():
    source = Path(__file__).resolve().parents[2] / "src/criba/ui/actions.py"
    original_tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    required = {
        "_entry_para_desarrollo",
        "_protocolo_intent_actual",
        "_finalizar_protocolo_worker",
        "on_protocolo_operativo",
    }
    selected = [
        n for n in original_tree.body
        if isinstance(n, ast.FunctionDef) and n.name in required
    ]
    assert {n.name for n in selected} == required
    workers = []
    applies = []
    fails = []
    errors = []
    namespace = {
        "Any": Any,
        "deepcopy": deepcopy,
        "Worker": Worker,
        "_start_worker": lambda _win, w: workers.append(w),
        "_activity": lambda *_args: None,
        "show_error": lambda *_args: errors.append(_args),
        "_on_protocolo_done": lambda win, s, i, result: (
            applies.append((s, i, result)),
            win.right_panel.protocolo.setEnabled(True),
        ),
        "_on_protocolo_failed": lambda win, message: (
            fails.append(message),
            win.right_panel.protocolo.setEnabled(True),
        ),
    }
    isolated = ast.Module(body=selected, type_ignores=[])
    ast.fix_missing_locations(isolated)
    exec(compile(isolated, str(source), "exec"), namespace)
    return namespace["on_protocolo_operativo"], workers, applies, fails, errors


def test_same_request_is_deduped_and_terminal_signal_is_one_shot(harness):
    start, workers, applies, fails, _ = harness
    s = _sheet()
    w = _window(s)
    start(w)
    start(w)
    assert len(workers) == 1
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    workers[0].signals.fail.emit("late")
    assert len(applies) == 1 and fails == []
    assert applies[0][0] is s and applies[0][1] == 0
    assert w.right_panel.protocolo.enabled


def test_new_sheet_cannot_be_overwritten_by_old_result(harness):
    start, workers, applies, fails, _ = harness
    old = _sheet("old")
    w = _window(old)
    start(w)
    current = _sheet("new")
    w.invent_sheet = current
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert w.invent_sheet is current
    assert applies == [] and fails == []
    assert w.right_panel.protocolo.enabled


def test_equal_content_new_entry_supersedes_old_worker(harness):
    start, workers, applies, fails, _ = harness
    s = _sheet()
    w = _window(s)
    start(w)
    s["entries"][0] = dict(s["entries"][0])
    start(w)
    assert len(workers) == 2
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert not applies and not w.right_panel.protocolo.enabled
    workers[1].signals.done.emit({"estado": "PROTOCOLO"})
    assert len(applies) == 1 and fails == []


def test_model_change_invalidates_old_callback(harness):
    start, workers, applies, fails, _ = harness
    s = _sheet()
    w = _window(s)
    start(w)
    s["interpreter"]["model_requested"] = "new-model"
    start(w)
    assert len(workers) == 2
    workers[0].signals.fail.emit("former model")
    assert not w.right_panel.protocolo.enabled and fails == []
    workers[1].signals.fail.emit("current model")
    assert fails == ["current model"] and not applies


def test_switching_selected_candidate_blocks_old_result(harness):
    start, workers, applies, fails, _ = harness
    s = _sheet()
    s["entries"].append({**s["entries"][0], "candidate_id": "b"})
    w = _window(s)
    start(w)
    w.candidates.interpretation_index = 1
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert not applies and not fails
    assert w.candidates.interpretation_index == 1


@pytest.mark.parametrize("mutation", [
    lambda w: w.invent_sheet.update(run_id="other"),
    lambda w: w.invent_sheet["entries"][0].update(mecanismo="new mechanism"),
    lambda w: w.invent_sheet.update(query="different query"),
    lambda w: setattr(w, "problem", "different window problem"),
])
def test_context_mutation_rejects_inflight_result(harness, mutation):
    start, workers, applies, fails, _ = harness
    w = _window(_sheet())
    start(w)
    mutation(w)
    workers[0].signals.done.emit({"estado": "PROTOCOLO"})
    assert not applies and not fails
