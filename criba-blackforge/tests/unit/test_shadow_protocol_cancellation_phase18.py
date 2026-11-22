"""Phase18: cooperative pre-provider cancellation of real Shadow functions.

Extract production function bodies from actions.py to avoid requiring PySide6.
Only worker/signal and interpreter-provider boundaries are fake. This tests
actual callback/task source but not real Qt lifecycle or HTTP cancellation.
"""
from __future__ import annotations

import ast
import sys
from copy import deepcopy
from pathlib import Path
from threading import Event
from types import ModuleType, SimpleNamespace
from typing import Any

import pytest


class Signal:
    def __init__(self):
        self.fn = None

    def connect(self, callback):
        self.fn = callback

    def emit(self, value):
        assert self.fn is not None
        self.fn(value)


class Worker:
    def __init__(self, fn):
        self.fn = fn
        self.signals = SimpleNamespace(done=Signal(), fail=Signal())


class Button:
    def __init__(self):
        self.enabled = True

    def setEnabled(self, value):
        self.enabled = value


def sheet():
    return {
        "run_id": "initial", "query": "synthetic target",
        "interpreter": {"backend": "openai_compatible", "model_requested": "model-old"},
        "entries": [{"candidate_id": "one", "estado_interpretacion": "PROPUESTA",
                     "mecanismo": "original", "hipotesis": "unverified"}],
    }


@pytest.fixture
def harness(monkeypatch):
    path = Path(__file__).resolve().parents[2] / "src/criba/ui/actions.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names = {
        "_entry_para_desarrollo", "_cancelar_protocolo_pendiente",
        "_protocolo_intent_actual", "_finalizar_protocolo_worker",
        "on_protocolo_operativo",
    }
    selected = [node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    assert {node.name for node in selected} == names
    workers, constructed, dispatched, applied, failures = [], [], [], [], []
    hooks = SimpleNamespace(construct=None, refine=None)

    def construct(backend, **kwargs):
        constructed.append((backend, kwargs))
        if hooks.construct is not None:
            hooks.construct()
        return "interpreter-stub"

    def refine(interpreter, query, entry):
        dispatched.append((interpreter, query, deepcopy(entry)))
        if hooks.refine is not None:
            hooks.refine()
        return {"estado": "PROTOCOLO"}

    fake_selection = ModuleType("criba.interprete.seleccion")
    fake_selection.construir_interprete = construct
    fake_refinement = ModuleType("criba.interprete.refinamiento")
    fake_refinement.refinar_propuesta = refine
    monkeypatch.setitem(sys.modules, "criba.interprete.seleccion", fake_selection)
    monkeypatch.setitem(sys.modules, "criba.interprete.refinamiento", fake_refinement)

    namespace = {
        "__name__": "criba.ui.actions", "__package__": "criba.ui",
        "Any": Any, "deepcopy": deepcopy, "Event": Event, "Worker": Worker,
        "_start_worker": lambda win, worker: workers.append(worker),
        "_activity": lambda *args: None, "show_error": lambda *args: failures.append(args),
        "_on_protocolo_done": lambda win, s, i, result: (
            applied.append((s, i, result)), win.right_panel.protocolo.setEnabled(True)),
        "_on_protocolo_failed": lambda win, message: (
            failures.append(message), win.right_panel.protocolo.setEnabled(True)),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                 str(path), "exec"), namespace)

    def window():
        s = sheet()
        return SimpleNamespace(
            invent_sheet=s, problem=s["query"],
            candidates=SimpleNamespace(interpretation_index=0),
            right_panel=SimpleNamespace(protocolo=Button()),
        )

    return SimpleNamespace(start=namespace["on_protocolo_operativo"],
                           cancel=namespace["_cancelar_protocolo_pendiente"],
                           workers=workers, constructed=constructed,
                           dispatched=dispatched, applied=applied, failures=failures,
                           hooks=hooks, window=window, source=tree)


def test_duplicate_request_does_not_cancel_its_own_event(harness):
    w = harness.window()
    harness.start(w)
    first = w._protocolo_intent
    harness.start(w)
    assert len(harness.workers) == 1
    assert first is w._protocolo_intent
    assert first["cancel"].is_set() is False


def test_superseded_before_queued_worker_runs_skips_construction(harness):
    w = harness.window()
    harness.start(w)
    old = harness.workers[0]
    w.invent_sheet["entries"][0]["mecanismo"] = "updated"
    harness.start(w)
    assert len(harness.workers) == 2
    result = old.fn()
    assert result["error"] == "REFINEMENT_SUPERSEDED"
    assert harness.constructed == [] and harness.dispatched == []
    old.signals.done.emit(result)
    assert harness.applied == []
    assert not w.right_panel.protocolo.enabled


def test_cancel_during_interpreter_construction_skips_provider(harness):
    w = harness.window()
    harness.start(w)
    first = harness.workers[0]
    harness.hooks.construct = lambda: harness.cancel(w)
    result = first.fn()
    assert result["error"] == "REFINEMENT_SUPERSEDED"
    assert len(harness.constructed) == 1 and harness.dispatched == []


def test_context_change_without_new_call_can_explicitly_invalidate(harness):
    w = harness.window()
    harness.start(w)
    first = harness.workers[0]
    w.invent_sheet = sheet()
    assert harness.cancel(w)
    assert w._protocolo_intent is None
    result = first.fn()
    assert result["error"] == "REFINEMENT_SUPERSEDED"
    assert not harness.constructed
    first.signals.done.emit(result)
    assert not harness.applied


def test_task_uses_original_entry_snapshot_not_mutated_live_entry(harness):
    w = harness.window()
    harness.start(w)
    first = harness.workers[0]
    w.invent_sheet["entries"][0]["mecanismo"] = "changed after click"
    result = first.fn()
    assert result["estado"] == "PROTOCOLO"
    assert harness.dispatched[0][2]["mecanismo"] == "original"
    first.signals.done.emit(result)
    assert not harness.applied


def test_task_uses_original_model_snapshot_not_mutated_configuration(harness):
    w = harness.window()
    harness.start(w)
    first = harness.workers[0]
    w.invent_sheet["interpreter"]["model_requested"] = "different-model"
    result = first.fn()
    assert result["estado"] == "PROTOCOLO"
    assert harness.constructed[0] == (
        "openai_compatible", {"model": "model-old"}
    )
    first.signals.done.emit(result)
    assert not harness.applied


def test_provider_already_started_is_not_claimed_cancelled(harness):
    w = harness.window()
    harness.start(w)
    first = harness.workers[0]
    harness.hooks.refine = lambda: harness.cancel(w)
    result = first.fn()
    assert result["estado"] == "PROTOCOLO"
    # We cannot interrupt a provider already inside completar_json.
    assert len(harness.dispatched) == 1
    first.signals.done.emit(result)
    assert not harness.applied


def test_cancelling_twice_is_idempotent(harness):
    w = harness.window()
    harness.start(w)
    assert harness.cancel(w) is True
    assert harness.cancel(w) is False
    assert harness.workers[0].fn()["error"] == "REFINEMENT_SUPERSEDED"


def test_navigation_entrypoints_invalidate_pending_protocol(harness):
    functions = {
        node.name: node for node in harness.source.body
        if isinstance(node, ast.FunctionDef)
    }
    for name in ("_apply_new_problem", "_on_invented", "on_inventar", "on_historial"):
        assert name in functions
        invocations = [
            node for node in ast.walk(functions[name])
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
            and node.func.id == "_cancelar_protocolo_pendiente"
        ]
        assert invocations, name
