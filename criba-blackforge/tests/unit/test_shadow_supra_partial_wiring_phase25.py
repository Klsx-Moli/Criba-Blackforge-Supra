"""F25: production worker and Shadow preserve partial GETs, never retry POST.

PySide6 import is required for actions, but no Qt event loop, actual HTTP
server, paid model or POST transport is started. Local journal is real.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.ui import actions
from criba import dossier_workflow
from test_dossier_batch_phase15_integration import (
    ENDPOINT, OnlyGet, lookup, prepared, project,
)
from test_shadow_supra_archived_get_phase22 import old_sheet
from test_shadow_supra_stale_callback_phase09 import harness, window


class Struct(SimpleNamespace):
    def model_dump(self, *args, **kwargs):
        return vars(self).copy()


def typed_lookup(dossier):
    src = lookup(dossier)
    raw = src["posture"]["criba_dossier_receipt"]
    posture = Struct(
        project_id=src["posture"]["project_id"],
        stage=src["posture"]["stage"],
        criba_dossier_receipt=Struct(**raw),
        checkpoints=[],
    )
    fields = {k: v for k, v in src.items() if k != "posture"}
    fields.update({
        "status": "blocked", "status_scope": "WORKFLOW_EXECUTION_ONLY",
        "completion_status": "BLOCKED", "workflow_status": "BLOCKED",
        "verification_status": "FAIL", "secure_sandbox_status": "NOT_VERIFIED",
        "persisted_artifact_error_kind": None,
    })
    return Struct(**fields, posture=posture)


class FakeOutcome:
    def __init__(self, dossier):
        project_id = project(dossier)
        self.post = Struct(
            project_id=project_id, status="blocked",
            completion_status="BLOCKED", workflow_status="BLOCKED",
            verification_status="FAIL", secure_sandbox_status="NOT_VERIFIED",
            scientific_status="NOT_VALIDATED",
            criba_mechanism_execution_status="NOT_EXECUTED", stage="BLOCKED",
        )

    def report(self, _read_fn):
        return {"synthetic_workflow_result": "BLOCKED"}


class FakeWorkflow:
    submits = []
    fail_at = 2

    def __init__(self, client):
        self.client = client

    def submit(self, **kwargs):
        dossier = kwargs["dossier"]
        self.submits.append(dossier["dossier_id"])
        if len(self.submits) >= self.fail_at:
            raise TimeoutError("synthetic second POST indeterminate")
        return FakeOutcome(dossier)


class FakeClient:
    config = Struct(endpoint=ENDPOINT)

    def __init__(self, dossiers):
        self.by_project = {project(d): d for d in dossiers}
        self.get_calls = []

    def health(self):
        return Struct(status="healthy")

    def get_project(self, identity):
        self.get_calls.append(identity)
        return typed_lookup(self.by_project[identity])


def test_worker_fsyncs_first_get_before_second_post_can_fail(
    monkeypatch, tmp_path,
):
    key, original = prepared(tmp_path)
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    FakeWorkflow.submits = []
    FakeWorkflow.fail_at = 2
    monkeypatch.setattr(dossier_workflow, "DossierWorkflow", FakeWorkflow)
    client = FakeClient(original)
    with pytest.raises(TimeoutError, match="second POST"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert FakeWorkflow.submits == [d["dossier_id"] for d in original]
    assert client.get_calls == [project(original[0])]
    state = journal._state(journal._events(tmp_path / journal.JOURNAL))[key]
    assert state["remote"] == "UNKNOWN"
    assert state["dispatch_started"] is True
    assert set(state["partial_readbacks"]) == {original[0]["dossier_id"]}
    assert not any(
        e["event"] == "REMOTE_READBACK_OBSERVED"
        for e in journal._events(tmp_path / journal.JOURNAL)
    )


def test_invalid_first_get_stops_before_second_post(
    monkeypatch, tmp_path,
):
    key, original = prepared(tmp_path)
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    FakeWorkflow.submits = []
    FakeWorkflow.fail_at = 99
    monkeypatch.setattr(dossier_workflow, "DossierWorkflow", FakeWorkflow)

    class InvalidClient(FakeClient):
        def get_project(self, identity):
            result = super().get_project(identity)
            result.persisted_artifact_status = "UNVERIFIABLE"
            return result

    with pytest.raises(ValueError, match="does not bind"):
        actions._execute_supra_dossiers(
            original, InvalidClient(original),
            batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert FakeWorkflow.submits == [original[0]["dossier_id"]]
    state = journal._state(journal._events(tmp_path / journal.JOURNAL))[key]
    assert state["partial_readbacks"] == {}
    assert state["remote"] == "UNKNOWN"


def test_failed_partial_fsync_stops_before_second_post(
    monkeypatch, tmp_path,
):
    key, original = prepared(tmp_path)
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    FakeWorkflow.submits = []
    FakeWorkflow.fail_at = 99
    monkeypatch.setattr(dossier_workflow, "DossierWorkflow", FakeWorkflow)
    genuine_append = sd._append_historial

    def fail_partial(path, event):
        if event.get("event") == "REMOTE_PARTIAL_READBACK_OBSERVED":
            raise OSError("simulated fsync failure")
        genuine_append(path, event)

    monkeypatch.setattr(sd, "_append_historial", fail_partial)
    with pytest.raises(OSError, match="simulated fsync"):
        actions._execute_supra_dossiers(
            original, FakeClient(original),
            batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert FakeWorkflow.submits == [original[0]["dossier_id"]]
    assert len(journal._events(tmp_path / journal.JOURNAL)) == 4
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"


def test_ui_get_failure_uses_exact_partial_sweep_without_post(
    monkeypatch, tmp_path,
):
    import criba.integrations as integrations

    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])] = TimeoutError("uncertain")
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)

    class ContextClient:
        def __enter__(self):
            return client

        def __exit__(self, *args):
            return False

    monkeypatch.setattr(integrations, "SupraClient", ContextClient)
    result = actions._reconciliar_lote_supra_get(
        key, "phase15-run", "Synthetic recovery problem",
    )
    assert result["status"] == "UNKNOWN"
    report = result["partial_diagnostics"]
    assert report["fresh_verified"] == 1
    assert report["journal_partials"] == 1
    assert [row["get_status"] for row in report["rows"]] == [
        "FRESH_PLANNING_RECEIPT_VERIFIED", "GET_UNAVAILABLE_UNKNOWN",
    ]
    assert client.calls == [
        project(original[0]), project(original[1]),
        project(original[0]), project(original[1]),
    ]
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"


def test_shadow_callback_shows_partial_counts_but_no_full_receipt(
    harness, tmp_path,
):
    workers, errors = harness
    key, original = prepared(tmp_path)
    win = window(old_sheet())
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1 and errors == []
    client = OnlyGet(original)
    client.responses[project(original[1])] = TimeoutError("GET")
    from criba.dossier_batch_recovery import inspeccionar_lote_parcial_por_get

    report = {
        "batch_id": key, "status": "UNKNOWN", "reason": "GET_FAILED",
        "checked": 1, "expected": 2,
        "partial_diagnostics": inspeccionar_lote_parcial_por_get(
            key, client, tmp_path, registrar=True,
        ),
    }
    workers[0].signals.done.emit(report)
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    assert "1/2 recibos actuales" in win.refs["ideaSummary"].text
    assert "lote completo NO CONFIRMADO" in win.refs["ideaSummary"].text
    assert "sin reenvío POST" in win.refs["ideaSummary"].text
    assert len(journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "partial_readbacks"
    ]) == 1


def test_mismatched_partial_report_stays_hidden_in_shadow(
    harness, tmp_path,
):
    workers, errors = harness
    key, original = prepared(tmp_path)
    win = window(old_sheet())
    actions.on_desarrollar_supra(win)
    from criba.dossier_batch_recovery import inspeccionar_lote_parcial_por_get

    wrong = inspeccionar_lote_parcial_por_get(
        key, OnlyGet(original), tmp_path, registrar=False,
    )
    wrong["batch_id"] = "batch-unrelated"
    workers[0].signals.done.emit({
        "batch_id": key, "status": "UNKNOWN", "partial_diagnostics": wrong,
    })
    assert win.invent_sheet["dossier_recovery_view_state"] == "UNKNOWN"
    assert win.invent_sheet["dossier_partial_diagnostics"] is None
    assert "recibos actuales" not in win.refs["ideaSummary"].text
