"""Phase 12: Shadow vertical callbacks must not cross session or project.

Imports the *real* Qt actions module in a complete checkout. Worker/network
execution is not needed: only deterministic guards and state changes are tested.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6")

from criba.ui import actions


def _ctx():
    sheet = {
        "run_id": "run-a",
        "query": "water",
        "entries": [
            {"candidate_id": "candidate-a", "mecanismo": "divert first flow"},
            {"candidate_id": "candidate-b", "mecanismo": "different"},
        ],
    }
    packet = {"innovation": {"ideas": []}}
    win = SimpleNamespace(
        invent_sheet=sheet, packet=packet, problem="water",
        candidates=SimpleNamespace(interpretation_index=0),
        _supra_vertical_running=True,
    )
    token = object()
    win._supra_vertical_token = token
    context = {
        "token": token,
        "project_id": "project-a",
        "sheet": sheet,
        "packet": packet,
        "problem": "water",
        "run_id": "run-a",
        "selected_index": 0,
        "candidate_snapshot": deepcopy(sheet["entries"][0]),
    }
    return win, context


def test_current_signal_consumed_once():
    win, context = _ctx()
    assert actions._supra_vertical_consume_if_current(win, context)
    assert win._supra_vertical_token is None
    assert not win._supra_vertical_running
    assert not actions._supra_vertical_consume_if_current(win, context)


@pytest.mark.parametrize("change", [
    "sheet", "run", "candidate", "index", "packet", "problem", "token",
])
def test_stale_signal_cannot_change_newer_run(change):
    win, context = _ctx()
    if change == "sheet":
        win.invent_sheet = deepcopy(win.invent_sheet)  # same run, new object
    elif change == "run":
        win.invent_sheet["run_id"] = "other"
    elif change == "candidate":
        win.invent_sheet["entries"][0]["mecanismo"] = "changed"
    elif change == "index":
        win.candidates.interpretation_index = 1
    elif change == "packet":
        win.packet = deepcopy(win.packet)
    elif change == "problem":
        win.problem = "other"
    else:
        new_token = object()
        win._supra_vertical_token = new_token
    assert not actions._supra_vertical_consume_if_current(win, context)
    if change == "token":
        assert win._supra_vertical_running
        assert win._supra_vertical_token is new_token


def test_same_run_id_not_proof_of_same_sheet():
    win, context = _ctx()
    win.invent_sheet = {"run_id": "run-a", "entries": context["sheet"]["entries"]}
    assert not actions._supra_vertical_context_current(win, context)


def test_invalid_index_and_missing_entries_cannot_pass():
    win, context = _ctx()
    win.candidates.interpretation_index = True
    assert not actions._supra_vertical_context_current(win, context)
    win.candidates.interpretation_index = 0
    win.invent_sheet["entries"] = []
    assert not actions._supra_vertical_context_current(win, context)


def test_wrong_project_response_uses_error_path_not_success(monkeypatch):
    win, context = _ctx()
    failures = []
    monkeypatch.setattr(
        actions, "_on_supra_vertical_failed",
        lambda *args, **kwargs: failures.append((args, kwargs)),
    )
    actions._on_supra_vertical_done(
        win, {"project_id": "other-project"}, context=context
    )
    assert len(failures) == 1
    assert failures[0][1]["context"] is context

def test_identical_contents_different_selected_index_still_stale():
    win, context = _ctx()
    win.invent_sheet["entries"][1] = deepcopy(win.invent_sheet["entries"][0])
    win.candidates.interpretation_index = 1
    assert not actions._supra_vertical_context_current(win, context)
