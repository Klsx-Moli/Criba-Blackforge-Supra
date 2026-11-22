"""F27: CLI send cannot bypass the fsynced single-dispatch journal.

All journal operations are real. Only the workflow-side HTTP transport is
simulated. No paid model, external POST, UI or ASTRA execution occurs.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from types import SimpleNamespace

import pytest

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.dossier_workflow import Bindings, DossierWorkflow, WorkflowError
from criba.dossier_workflow_cli import _send_one_journal_bound, main
from test_dossier_batch_phase15_integration import ENDPOINT, OnlyGet, dossiers, project


class FakeOutcome:
    def report(self):
        return {"workflow_schema": "criba-dossier-workflow/1", "post": None}


class FakeWorkflow:
    def __init__(self, records, *, mode="ok", endpoint=ENDPOINT):
        self.records = records
        self.mode = mode
        self.client = OnlyGet(records, endpoint=endpoint)
        self.submissions = []
        self.http_calls = 0

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def load_local(self, identity):
        for d in self.records:
            if d["dossier_id"] == identity:
                return deepcopy(d)
        raise WorkflowError("LOCAL_DOSSIER_MISSING", "load", "not found")

    def http(self):
        self.http_calls += 1
        return self.client

    def submit(self, payload, project_id, **opts):
        self.submissions.append((deepcopy(payload), project_id, opts))
        if self.mode == "error":
            raise WorkflowError("SYNTHETIC_POST", "submit", "uncertain",
                                retryable=True, remote_unknown=False)
        if self.mode == "crash":
            raise RuntimeError("synthetic worker crash")
        if self.mode == "bad-get":
            self.client.responses[project(payload)][
                "persisted_artifact_status"
            ] = "UNVERIFIABLE"
        if self.mode == "offline-get":
            self.client.responses[project(payload)] = TimeoutError("GET offline")
        return FakeOutcome()


@pytest.fixture
def home(monkeypatch, tmp_path):
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    return tmp_path


@pytest.fixture
def original():
    return [deepcopy(dossiers()[0])]


def save(home, records):
    return journal.guardar_lote_dossiers(records, home)["batch_id"]


def cli(wf, identity, capsys, *opts):
    rc = main(["send", "--dossier-id", identity, *opts],
              workflow_factory=lambda _endpoint: wf)
    return rc, json.loads(capsys.readouterr().out)


def state(home, key):
    return journal._state(journal._events(home / journal.JOURNAL))[key]


def test_default_send_denied_before_any_remote_call(home, original, capsys):
    key = save(home, original)
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys)
    assert rc == 2 and report["error"]["code"] == "CLI_CONFIRMATION_REQUIRED"
    assert wf.http_calls == 0 and wf.submissions == []
    assert state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_unjournaled_and_unbound_dossier_deny_explicit_send(home, original, capsys):
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_SINGLE_BATCH_REQUIRED"
    assert wf.http_calls == 0
    original[0].pop("run_id")
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_JOURNAL_LINEAGE_REQUIRED"
    assert wf.submissions == []


def test_multiple_dossiers_cannot_consume_batch_by_one_cli_send(home, capsys):
    records = dossiers()
    key = save(home, records)
    wf = FakeWorkflow(records)
    rc, report = cli(wf, records[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_SINGLE_BATCH_REQUIRED"
    assert wf.http_calls == 0
    assert state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_forged_project_id_denied_before_reservation(home, original, capsys):
    key = save(home, original)
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys,
                     "--confirm-first-send", "--project-id", "astram2-wrong")
    assert rc == 2 and report["error"]["code"] == "CLI_PROJECT_ID_MISMATCH"
    assert wf.submissions == [] and state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_first_send_creates_one_claim_and_v2_receipt_only(home, original, capsys):
    key = save(home, original)
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 0 and report["operation_status"] == "PLANNING_RECEIPT_JOURNALED_ONLY"
    assert report["scientific_status"] == "NOT_VALIDATED"
    assert report["mechanism_execution"] == "NOT_EXECUTED"
    assert report["authorizes_retry"] is False
    assert len(wf.submissions) == 1
    payload, identity, opts = wf.submissions[0]
    assert payload == original[0] and payload is not original[0]
    assert identity == project(original[0])
    assert opts["expected_endpoint"] == ENDPOINT
    assert [e["event"] for e in journal._events(home / journal.JOURNAL)] == [
        "PREPARED", "LOCAL_COMMITTED", "REMOTE_UNKNOWN",
        "REMOTE_DISPATCH_STARTED", "REMOTE_READBACK_OBSERVED",
    ]
    assert state(home, key)["remote"] == "READBACK_OBSERVED"


def test_second_explicit_send_after_success_cannot_repost(home, original, capsys):
    key = save(home, original)
    wf = FakeWorkflow(original)
    assert cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")[0] == 0
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_REMOTE_ALREADY_RESERVED"
    assert len(wf.submissions) == 1 and state(home, key)["remote"] == "READBACK_OBSERVED"


def test_unknown_reservation_cannot_start_another_worker(home, original, capsys):
    key = save(home, original)
    assert journal.marcar_envio_incierto(key, home, endpoint=ENDPOINT)
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_REMOTE_ALREADY_RESERVED"
    assert report["error"]["remote_outcome_unknown"] is True
    assert wf.submissions == [] and state(home, key)["remote"] == "UNKNOWN"


@pytest.mark.parametrize("mode", ["error", "crash"])
def test_post_failure_after_claim_never_promotes_unknown(home, original, capsys, mode):
    key = save(home, original)
    wf = FakeWorkflow(original, mode=mode)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["remote_outcome_unknown"] is True
    assert report["error"]["retryable"] is False or mode == "crash"
    assert state(home, key)["remote"] == "UNKNOWN"
    assert state(home, key)["dispatch_started"] is True
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["error"]["code"] == "CLI_REMOTE_ALREADY_RESERVED"
    assert len(wf.submissions) == 1


@pytest.mark.parametrize("mode", ["bad-get", "offline-get"])
def test_unverified_get_is_not_success_and_does_not_allow_repost(
    home, original, capsys, mode,
):
    key = save(home, original)
    wf = FakeWorkflow(original, mode=mode)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["operation_status"] == "REMOTE_UNKNOWN_READBACK_UNCONFIRMED"
    assert report["remote_outcome_unknown"] is True
    assert report["authorizes_retry"] is False
    assert state(home, key)["remote"] == "UNKNOWN"
    assert len(wf.submissions) == 1


def test_invalid_origin_denied_without_remote_reservation(home, original, capsys):
    key = save(home, original)
    wf = FakeWorkflow(original, endpoint="https://u:p@host/private")
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["operation_status"] == "INPUT_OR_IO_ERROR"
    assert wf.submissions == [] and state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_existing_output_file_cannot_cause_a_post(home, original, tmp_path):
    key = save(home, original)
    out = tmp_path / "already.json"
    out.write_text("original", encoding="utf-8")
    wf = FakeWorkflow(original)
    rc = main(["send", "--dossier-id", original[0]["dossier_id"],
               "--confirm-first-send", "--output", str(out)],
              workflow_factory=lambda _ep: wf)
    assert rc == 2 and wf.http_calls == 0
    assert out.read_text(encoding="utf-8") == "original"
    assert state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_dossier_history_tamper_blocks_cli_before_remote(home, original, capsys):
    key = save(home, original)
    path = home / "dossiers.jsonl"
    path.write_text(path.read_text(encoding="utf-8").replace(
        "mechanism-1", "forged-mechanism",
    ), encoding="utf-8")
    wf = FakeWorkflow(original)
    rc, report = cli(wf, original[0]["dossier_id"], capsys, "--confirm-first-send")
    assert rc == 2 and report["operation_status"] == "INPUT_OR_IO_ERROR"
    assert wf.http_calls == 0 and state(home, key)["remote"] == "NOT_ATTEMPTED"


def test_reservation_race_denied_no_duplicate_post(home, original, monkeypatch):
    key = save(home, original)
    genuine = journal.reservar_primer_envio_preparado

    def racing(*args, **kwargs):
        assert journal.marcar_envio_incierto(key, home, endpoint=ENDPOINT)
        return genuine(*args, **kwargs)

    monkeypatch.setattr(journal, "reservar_primer_envio_preparado", racing)
    wf = FakeWorkflow(original)
    args = argparse.Namespace(
        dossier_id=original[0]["dossier_id"], confirm_first_send=True,
        project_id=None, use_model=False, provider=None, model=None,
        domain="criba_blackforge", no_disruptive=False,
    )
    with pytest.raises(WorkflowError, match="CLI_FIRST_RESERVATION_REJECTED"):
        _send_one_journal_bound(wf, args)
    assert wf.submissions == [] and state(home, key)["remote"] == "UNKNOWN"


def test_two_concurrent_cli_sends_claim_only_one_worker(home, original):
    key = save(home, original)
    workflows = [FakeWorkflow(original), FakeWorkflow(original)]

    def attempt(wf):
        args = argparse.Namespace(
            dossier_id=original[0]["dossier_id"], confirm_first_send=True,
            project_id=None, use_model=False, provider=None, model=None,
            domain="criba_blackforge", no_disruptive=False,
        )
        try:
            return _send_one_journal_bound(wf, args)[1]
        except WorkflowError:
            return 2

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, workflows))
    assert sorted(results) == [0, 2]
    assert sum(len(wf.submissions) for wf in workflows) == 1
    assert state(home, key)["remote"] == "READBACK_OBSERVED"


def test_real_workflow_prepost_origin_drift_rejected_without_post(original):
    payload = original[0]

    class Drift:
        config = SimpleNamespace(endpoint=ENDPOINT)

        def health(self):
            self.config.endpoint = "https://drift.example"
            return SimpleNamespace(status="healthy")

        def run_project(self, **_kwargs):
            pytest.fail("remote POST must not run after endpoint drift")

    bindings = Bindings(
        prepare=lambda entry, problem: payload,
        save=lambda value: None,
        load=lambda identity: payload,
        fingerprint=lambda value: "sha256:" + "a" * 64,
        objective=lambda value: "objective",
        project_id=lambda value: value,
    )
    worker = DossierWorkflow(client=Drift(), bindings=bindings)
    with pytest.raises(WorkflowError) as e:
        worker.submit(payload, expected_endpoint=ENDPOINT)
    assert e.value.code == "CLI_ENDPOINT_CHANGED"
    assert e.value.remote_unknown is True
