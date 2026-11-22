"""F23: one explicit first remote send after archived NOT_ATTEMPTED.

Qt Worker is intercepted before execution; real dossier JSONL, journal and
reservation are not mocked. No live network or paid provider calls.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.ui import actions
from test_dossier_batch_phase15_integration import ENDPOINT, dossiers
from test_shadow_supra_archived_get_phase22 import old_sheet
from test_shadow_supra_stale_callback_phase09 import harness, window


def _prepared(tmp_path):
    originals = dossiers()
    key = journal.guardar_lote_dossiers(originals, tmp_path)["batch_id"]
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key]["remote"] == "NOT_ATTEMPTED"
    return key, originals


def test_declining_first_send_never_mutates_journal_or_starts_worker(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    calls = []
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch",
        lambda w, b: calls.append(b["batch_id"]) or False,
    )
    before = (tmp_path / journal.JOURNAL).read_bytes()
    actions.on_desarrollar_supra(win)
    assert calls == [key]
    assert workers == [] and errors == []
    assert (tmp_path / journal.JOURNAL).read_bytes() == before
    assert "dossier_batch_id" not in win.invent_sheet


def test_accepted_first_send_fsyncs_unknown_before_worker_launch(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, originals = _prepared(tmp_path)
    win = window(old_sheet())
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", lambda *_args: True,
    )
    invoked = []

    def fake_submit(payloads, *, batch_id=None, expected_endpoint=None):
        invoked.append((payloads, batch_id, expected_endpoint))
        assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key]["remote"] == "UNKNOWN"
        return {"status": "UNKNOWN"}

    monkeypatch.setattr(actions, "_execute_supra_dossiers", fake_submit)
    actions.on_desarrollar_supra(win)
    assert errors == [] and len(workers) == 1
    assert invoked == []  # No remote call before start/confirmation/fsync
    assert win.invent_sheet["dossier_batch_id"] == key
    assert win.invent_sheet["dossiers"] == [d["dossier_id"] for d in originals]
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    assert [e["event"] for e in journal._events(tmp_path / journal.JOURNAL)].count(
        "REMOTE_UNKNOWN"
    ) == 1
    workers[0].fn()
    assert invoked == [(originals, key, ENDPOINT)]


def test_two_clicks_after_confirmation_never_queue_second_post(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    asked = []
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch",
        lambda *_args: asked.append(True) or True,
    )
    actions.on_desarrollar_supra(win)
    actions.on_desarrollar_supra(win)
    assert asked == [True]
    assert len(workers) == 1 and len(errors) == 1
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key]["remote"] == "UNKNOWN"


def test_after_first_send_fails_next_action_is_only_get_not_post(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", lambda *_args: True,
    )
    actions.on_desarrollar_supra(win)
    workers[0].signals.fail.emit("timed out after remote reservation")
    assert win._supra_submission_token is None
    monkeypatch.setattr(
        actions, "_execute_supra_dossiers",
        lambda *_args, **_kw: pytest.fail("second POST forbidden"),
    )
    actions.on_desarrollar_supra(win)
    assert len(workers) == 2
    assert errors and "timed out" in errors[0][2]
    assert key == win.invent_sheet["dossier_batch_id"]


def test_current_visible_problem_mismatch_rejected_before_consent(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    _prepared(tmp_path)
    win = window(old_sheet())
    win.problem = "different problem on current screen"
    calls = []
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch",
        lambda *_args: calls.append(True) or True,
    )
    actions.on_desarrollar_supra(win)
    assert calls == [] and workers == []
    assert len(errors) == 1 and "problema visible" in errors[0][2]


def test_dossier_altered_while_confirmation_is_open_fails_closed(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    journal_file = tmp_path / journal.JOURNAL
    before = journal_file.read_bytes()

    def alter_then_approve(_win, _prior):
        path = tmp_path / "dossiers.jsonl"
        path.write_text(
            path.read_text(encoding="utf-8").replace(
                "mechanism-1", "forged-mechanism",
            ), encoding="utf-8",
        )
        return True

    monkeypatch.setattr(actions, "_confirm_first_prepared_dispatch", alter_then_approve)
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "original local dossier history changed" in errors[0][2]
    assert journal_file.read_bytes() == before
    assert journal._state(journal._events(journal_file))[key]["remote"] == "NOT_ATTEMPTED"


def test_parallel_reservation_during_consent_prevents_second_dispatch(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())

    def another_process_reserved(_win, _prior):
        assert journal.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)
        return True

    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", another_process_reserved,
    )
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "already reserved" in errors[0][2]
    assert len(journal._events(tmp_path / journal.JOURNAL)) == 3


def test_bad_endpoint_does_not_write_unknown_or_start_worker(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", lambda *_args: True,
    )
    monkeypatch.setenv("SUPRA_ENDPOINT", "http://host/private")
    before = (tmp_path / journal.JOURNAL).read_bytes()
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "endpoint" in errors[0][2]
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_incomplete_prepared_does_not_ask_consent_or_post(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    original = dossiers()
    key = journal._batch_id("phase15-run", "Synthetic recovery problem")
    sd._append_historial(
        tmp_path / journal.JOURNAL,
        journal._event(
            "PREPARED", key, run_id="phase15-run",
            problema="Synthetic recovery problem",
            fingerprint=journal._fingerprint(original), dossiers=original,
        ),
    )
    win = window(old_sheet())
    calls = []
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch",
        lambda *_args: calls.append(True) or True,
    )
    actions.on_desarrollar_supra(win)
    assert calls == [] and workers == []
    assert len(errors) == 1 and "incompleto" in errors[0][2]


@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def test_real_shadow_zero_proposal_prepared_shows_first_dispatch_consent(
    qapp, tmp_path, monkeypatch,
):
    from criba.ui.main_window import CribaMainWindow

    _prepared(tmp_path)
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    sheet = {
        "query": "Synthetic recovery problem",
        "run_id": "phase15-run",
        "seed": 42, "mode": "stratified", "entries": [],
        "totals": {
            "ideas": 0, "pending_interpretation": 0,
            "unresolved": 0, "partial_prior_art": 0,
            "survived_search": 0,
        },
    }
    win = CribaMainWindow(database=tmp_path / "f23-shadow.sqlite")
    try:
        win.problem = "Synthetic recovery problem"
        actions._on_invented(win, sheet)
        assert win.right_panel.supra.isEnabled()
        assert not win.right_panel.protocolo.isEnabled()
        assert "primer envío SUPRA requiere confirmación" in win.refs["ideaSummary"].text()
    finally:
        win.close()



def test_late_dialog_acceptance_after_window_switched_sheet_has_no_effect(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    before = (tmp_path / journal.JOURNAL).read_bytes()

    def switch_session_then_approve(win, _batch):
        win.invent_sheet = {
            "run_id": "other-run", "query": "Other problem", "entries": [],
        }
        return True

    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", switch_session_then_approve,
    )
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "sesión cambió" in errors[0][2]
    assert (tmp_path / journal.JOURNAL).read_bytes() == before
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key]["remote"] == "NOT_ATTEMPTED"


@pytest.mark.parametrize("mutation", ["run_id", "query", "problem"])
def test_in_place_mutation_during_consent_prevents_first_remote_reservation(
    harness, monkeypatch, tmp_path, mutation,
):
    workers, errors = harness
    _prepared(tmp_path)
    win = window(old_sheet())
    journal_file = tmp_path / journal.JOURNAL
    before = journal_file.read_bytes()

    def change_context(win, _batch):
        if mutation == "problem":
            win.problem = "unrelated visible problem"
        else:
            win.invent_sheet[mutation] = "unrelated value"
        return True

    monkeypatch.setattr(actions, "_confirm_first_prepared_dispatch", change_context)
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "sesión cambió" in errors[0][2]
    assert journal_file.read_bytes() == before
