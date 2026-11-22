"""F24: SUPRA worker must fsync a unique start claim BEFORE network.

Qt is needed to import production actions. No actual HTTP, POST, model or
paid provider. The journal/lock/fsync are real in tmp_path.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from criba import dossier_batch as batch
from criba.ui import actions
from test_dossier_batch_phase15_integration import ENDPOINT, dossiers
from test_shadow_supra_stale_callback_phase09 import harness, sheet, window
from test_shadow_supra_first_dispatch_phase23 import _prepared, old_sheet


class HealthCrash:
    def __init__(self, endpoint=ENDPOINT):
        self.config = SimpleNamespace(endpoint=endpoint)
        self.health_calls = 0

    def health(self):
        self.health_calls += 1
        raise RuntimeError("synthetic health failure (no remote call)")


def reserved(tmp_path):
    original = dossiers()
    key = batch.guardar_lote_dossiers(original, tmp_path)["batch_id"]
    assert batch.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)
    return key, original


def test_actual_worker_claims_before_health(tmp_path, monkeypatch):
    key, original = reserved(tmp_path)
    client = HealthCrash()
    before = batch._events(tmp_path / batch.JOURNAL)
    assert len(before) == 3
    with pytest.raises(RuntimeError, match="synthetic health failure"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 1
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["dispatch_started"] is True
    assert state["remote"] == "UNKNOWN"


def test_duplicate_real_worker_blocked_before_health_and_post(tmp_path):
    key, original = reserved(tmp_path)
    batch.reclamar_inicio_envio_remoto(key, original, tmp_path, endpoint=ENDPOINT)
    client = HealthCrash()
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already claimed"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 0
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_real_worker_denies_forged_payload_before_health(tmp_path):
    key, original = reserved(tmp_path)
    client = HealthCrash()
    original[0]["mecanismo"] = "forged"
    with pytest.raises(ValueError, match="payload differs"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 0
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_real_worker_denies_changed_endpoint_before_claim(tmp_path):
    key, original = reserved(tmp_path)
    client = HealthCrash(endpoint="https://other.example")
    with pytest.raises(ValueError, match="endpoint changed"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 0
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_real_worker_denies_missing_expected_endpoint_before_health(tmp_path):
    key, original = reserved(tmp_path)
    client = HealthCrash()
    with pytest.raises(ValueError, match="requires original endpoint"):
        actions._execute_supra_dossiers(original, client, batch_id=key)
    assert client.health_calls == 0
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_after_fsynced_reservation_qt_pool_crash_keeps_unknown_and_releases_token(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    key, _ = _prepared(tmp_path)
    win = window(old_sheet())
    monkeypatch.setattr(
        actions, "_confirm_first_prepared_dispatch", lambda *_args: True,
    )

    def pool_crashed(_win, _worker):
        raise RuntimeError("synthetic Qt pool failure")

    monkeypatch.setattr(actions, "_start_worker", pool_crashed)
    actions.on_desarrollar_supra(win)
    assert len(workers) == 0
    assert len(errors) == 1 and "recuperar solo por GET" in errors[0][2]
    assert win._supra_submission_token is None
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3

    # No second POST, even though no worker ever ran. Explicit GET only.
    calls = []
    monkeypatch.setattr(
        actions, "_start_worker", lambda _win, worker: workers.append(worker),
    )
    monkeypatch.setattr(
        actions, "_execute_supra_dossiers",
        lambda *_args, **_kw: pytest.fail("second POST forbidden"),
    )
    monkeypatch.setattr(
        actions, "_reconciliar_lote_supra_get",
        lambda batch_id, run_id, problem:
            calls.append((batch_id, run_id, problem))
            or {"status": "UNKNOWN"},
    )
    actions.on_desarrollar_supra(win)
    assert len(workers) == 1
    workers[0].fn()
    assert calls == [(key, "phase15-run", "Synthetic recovery problem")]


def test_new_batch_qt_launch_crash_preserves_unknown_without_second_post(
    harness, monkeypatch, tmp_path,
):
    workers, errors = harness
    win = window(sheet("fresh24", "one"))
    monkeypatch.setattr(
        actions, "_start_worker",
        lambda *_args: (_ for _ in ()).throw(RuntimeError("pool unavailable")),
    )
    actions.on_desarrollar_supra(win)
    assert len(workers) == 0
    assert len(errors) == 1 and "recuperar solo por GET" in errors[0][2]
    assert win._supra_submission_token is None
    assert win.invent_sheet["dossier_remote_state"] == "UNKNOWN"
    key = win.invent_sheet["dossier_batch_id"]
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"


def test_worker_claim_timeout_keeps_unknown_and_refuses_restart(tmp_path):
    key, original = reserved(tmp_path)
    try:
        actions._execute_supra_dossiers(
            original, HealthCrash(), batch_id=key, expected_endpoint=ENDPOINT,
        )
    except RuntimeError:
        pass
    else:
        pytest.fail("synthetic health failure should be raised")
    with pytest.raises(ValueError, match="already claimed"):
        actions._execute_supra_dossiers(
            original, HealthCrash(), batch_id=key, expected_endpoint=ENDPOINT,
        )
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["remote"] == "UNKNOWN"
    assert state["dispatch_started"] is True



def test_real_worker_uses_detached_dossiers_if_caller_mutates_during_health(
    tmp_path, monkeypatch,
):
    from criba import dossier_workflow as workflow

    key, original = reserved(tmp_path)
    first_before = original[0]["mecanismo"]
    passed = []

    class MutatingClient:
        config = SimpleNamespace(endpoint=ENDPOINT)

        def health(self):
            # A different thread/callback edits the original input after the
            # fsynced worker claim. This must not change the POST payload.
            original[0]["mecanismo"] = "forged after worker claim"
            original.reverse()
            return SimpleNamespace(model_dump=lambda: {"synthetic": True})

    class NoPostWorkflow:
        def __init__(self, client):
            self.client = client

        def submit(self, **kwargs):
            dossier = kwargs["dossier"]
            passed.append(dossier)
            assert dossier["mecanismo"] == first_before
            assert dossier["dossier_id"] == "dossier-first-1"
            assert dossier is not original[0]
            raise RuntimeError("stopped before any actual POST")

    monkeypatch.setattr(workflow, "DossierWorkflow", NoPostWorkflow)
    with pytest.raises(RuntimeError, match="stopped before any actual POST"):
        actions._execute_supra_dossiers(
            original, MutatingClient(), batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert len(passed) == 1
    assert passed[0]["mecanismo"] == first_before
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "dispatch_started"
    ] is True


def test_worker_rejects_unversioned_historical_unknown_before_network(
    tmp_path,
):
    from criba import supra_dossier as sd

    original = dossiers()
    key = batch.guardar_lote_dossiers(original, tmp_path)["batch_id"]
    sd._append_historial(
        tmp_path / batch.JOURNAL,
        batch._event("REMOTE_UNKNOWN", key, endpoint=ENDPOINT),
    )
    client = HealthCrash()
    with pytest.raises(ValueError, match="historical UNKNOWN"):
        actions._execute_supra_dossiers(
            original, client, batch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 0
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"
