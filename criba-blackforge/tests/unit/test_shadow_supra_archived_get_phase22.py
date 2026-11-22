"""F22: production Shadow route picks original journal GET after SQLite restart.

Requires PySide6 to import actions; HTTP is simulated, real JSONL is not.
No POST, LIST-latest or model execution.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from criba.ui import actions
from test_dossier_batch_phase15_integration import OnlyGet, dossiers, prepared
from test_shadow_supra_stale_callback_phase09 import harness, window


def old_sheet(*, entries=None):
    return {
        "run_id": "phase15-run",
        "query": "Synthetic recovery problem",
        "entries": [] if entries is None else entries,
    }


def test_saved_before_post_reopens_without_batch_hint_and_runs_get_only(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, originals = prepared(tmp_path)
    win = window(old_sheet())
    calls = []

    def get_only(batch_id, run_id, problem):
        calls.append((batch_id, run_id, problem))
        return reconciliar_lote_por_get(
            batch_id, OnlyGet(originals), tmp_path,
            expected_run_id=run_id, expected_problem=problem,
        )

    monkeypatch.setattr(actions, "_reconciliar_lote_supra_get", get_only)
    monkeypatch.setattr(
        actions, "_execute_supra_dossiers",
        lambda *a, **kw: pytest.fail("never resubmit an uncertain POST"),
    )
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1 and errors == []
    assert win.invent_sheet["dossier_batch_id"] == key
    assert win.invent_sheet["dossiers"] == [d["dossier_id"] for d in originals]
    result = workers[0].fn()
    assert calls == [(key, "phase15-run", "Synthetic recovery problem")]
    workers[0].signals.done.emit(result)
    assert win.invent_sheet["dossier_recovery_view_state"] == "FRESH_JOURNALED"
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "remote"
    ] == "READBACK_OBSERVED"


def test_old_archived_sheet_with_modified_entries_never_reconstructs_dossier(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, originals = prepared(tmp_path)
    win = window(old_sheet(entries=[{"candidate_id": "altered", "estado_interpretacion": "UNKNOWN"}]))
    monkeypatch.setattr(
        sd, "preparar_dossier",
        lambda *a, **kw: pytest.fail("reconstruction forbidden"),
    )
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1 and errors == []
    assert win.invent_sheet["dossier_batch_id"] == key
    assert win.invent_sheet["dossiers"] == [d["dossier_id"] for d in originals]


def test_wrong_problem_in_reopened_sheet_is_blocked_before_get(harness, tmp_path):
    workers, errors = harness
    prepared(tmp_path)
    win = window(old_sheet())
    win.invent_sheet["query"] = "other problem"
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "conflicts" in errors[0][2]
    assert "dossier_batch_id" not in win.invent_sheet


def test_current_visible_problem_mismatch_blocks_old_receipt(harness, tmp_path):
    workers, errors = harness
    prepared(tmp_path)
    win = window(old_sheet())
    win.problem = "different visible problem"
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "problema visible" in errors[0][2]


def test_locally_prepared_without_remote_reservation_never_post(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    journal.guardar_lote_dossiers(dossiers(), tmp_path)
    win = window(old_sheet())
    monkeypatch.setattr(
        actions, "_execute_supra_dossiers",
        lambda *a, **kw: pytest.fail("unreserved archive must not post"),
    )
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "PREPARED" in errors[0][2]


def test_local_intent_not_committed_cannot_start_any_worker(harness, tmp_path):
    workers, errors = harness
    source = dossiers()
    key = journal._batch_id("phase15-run", "Synthetic recovery problem")
    sd._append_historial(
        tmp_path / journal.JOURNAL,
        journal._event(
            "PREPARED", key, run_id="phase15-run",
            problema="Synthetic recovery problem",
            fingerprint=journal._fingerprint(source),
            dossiers=source,
        ),
    )
    win = window(old_sheet())
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "incompleto" in errors[0][2]


def test_forged_batch_hint_does_not_fall_through_to_post(harness, tmp_path):
    workers, errors = harness
    prepared(tmp_path)
    win = window(old_sheet())
    win.invent_sheet["dossier_batch_id"] = "batch-not-original"
    win.invent_sheet["dossier_remote_state"] = "UNKNOWN"
    actions.on_desarrollar_supra(win)
    assert workers == []
    assert len(errors) == 1 and "conflicts" in errors[0][2]


def test_corrupt_journal_blocks_get_and_post(harness, tmp_path):
    workers, errors = harness
    prepared(tmp_path)
    with (tmp_path / journal.JOURNAL).open("ab") as stream:
        stream.write(b'{"batch_id":')
    actions.on_desarrollar_supra(window(old_sheet()))
    assert workers == []
    assert len(errors) == 1 and "no verificable" in errors[0][2]


def test_repeat_click_while_original_get_inflight_is_deduplicated(harness, tmp_path):
    workers, errors = harness
    prepared(tmp_path)
    win = window(old_sheet())
    actions.on_desarrollar_supra(win)
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1 and errors == []



@pytest.fixture
def qapp():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def _zero_proposal_sheet():
    return {
        "query": "Synthetic recovery problem",
        "run_id": "phase15-run",
        "seed": 42,
        "mode": "stratified",
        "entries": [],
        "totals": {
            "ideas": 0, "pending_interpretation": 0,
            "unresolved": 0, "partial_prior_art": 0,
            "survived_search": 0,
        },
    }


def test_real_shadow_button_enabled_for_journal_recovery_without_proposals(
    qapp, monkeypatch, tmp_path,
):
    from criba.ui.main_window import CribaMainWindow

    key, _ = prepared(tmp_path)
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    win = CribaMainWindow(database=tmp_path / "shadow.sqlite")
    try:
        win.problem = "Synthetic recovery problem"
        actions._on_invented(win, _zero_proposal_sheet())
        assert win.right_panel.supra.isEnabled()
        assert not win.right_panel.protocolo.isEnabled()
        assert "GET-only" in win.refs["ideaSummary"].text()
        assert "NO EJECUTADO" not in win.refs["ideaEstadoChip"].text()
        assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
            "remote"
        ] == "UNKNOWN"
    finally:
        win.close()


def test_real_shadow_button_disabled_for_new_sheet_without_any_proposals(
    qapp, monkeypatch, tmp_path,
):
    from criba.ui.main_window import CribaMainWindow

    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    win = CribaMainWindow(database=tmp_path / "shadow.sqlite")
    try:
        win.problem = "Synthetic recovery problem"
        actions._on_invented(win, _zero_proposal_sheet())
        assert not win.right_panel.supra.isEnabled()
        assert not win.right_panel.protocolo.isEnabled()
    finally:
        win.close()


def test_real_shadow_button_disabled_on_corrupt_original_journal(
    qapp, monkeypatch, tmp_path,
):
    from criba.ui.main_window import CribaMainWindow

    prepared(tmp_path)
    with (tmp_path / journal.JOURNAL).open("ab") as output:
        output.write(b'{"event":')
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    win = CribaMainWindow(database=tmp_path / "shadow.sqlite")
    try:
        win.problem = "Synthetic recovery problem"
        actions._on_invented(win, _zero_proposal_sheet())
        assert not win.right_panel.supra.isEnabled()
        assert not win.right_panel.protocolo.isEnabled()
    finally:
        win.close()
