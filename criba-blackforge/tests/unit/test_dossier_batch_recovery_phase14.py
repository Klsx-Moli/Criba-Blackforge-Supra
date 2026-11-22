"""Phase14 GET-only recovery tests; HTTP and journal are isolated doubles.

These protect protocol behavior, not proof of a live SUPRA persistence layer.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from criba import dossier_batch as journal
from criba.dossier_batch_recovery import _expected_project, reconciliar_lote_por_get
from criba.integrations.supra_client import _dossier_payload_fingerprint

ENDPOINT = "http://127.0.0.1:8000"


def _dossiers():
    return [
        {
            "dossier_id": f"d-{n}", "candidate_id": f"c-{n}",
            "claim_id": f"cl-{n}", "mechanism_version": "sha256:" + "a" * 64,
            "protocol_version": "sha256:" + "b" * 64,
            "problema": "water", "run_id": "r1",
            "estado": "SUPRA_EJECUCION_PENDIENTE",
        }
        for n in (1, 2)
    ]


def _receipt(d):
    return {
        "criba_dossier_id": d["dossier_id"],
        "criba_candidate_id": d["candidate_id"],
        "claim_id": d["claim_id"],
        "mechanism_version": d["mechanism_version"],
        "protocol_version": d["protocol_version"],
        "integration_version": "criba-supra/1",
        "payload_fingerprint": _dossier_payload_fingerprint(d),
        "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
        "execution_status": "NOT_EXECUTED", "scientific_status": "NOT_VALIDATED",
    }


def _lookup(d):
    project = _expected_project(d["dossier_id"])
    return {
        "project_id": project, "stage": "BLOCKED",
        "status_source": "PERSISTED_STATE",
        "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
        "scientific_status": "NOT_VALIDATED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "posture": {
            "project_id": project, "stage": "BLOCKED",
            "criba_dossier_receipt": _receipt(d),
        },
    }


class FakeClient:
    def __init__(self, dossiers, endpoint=ENDPOINT):
        self.config = SimpleNamespace(endpoint=endpoint)
        self.responses = {_expected_project(d["dossier_id"]): _lookup(d)
                          for d in dossiers}
        self.calls = []

    def get_project(self, project_id):
        self.calls.append(("GET", project_id))
        result = self.responses[project_id]
        if isinstance(result, Exception):
            raise result
        return result

    def run_project(self, **_kwargs):
        raise AssertionError("POST is prohibited during reconciliation")


@pytest.fixture
def case(monkeypatch, tmp_path):
    dossiers = _dossiers()
    state = {
        "intent": {"dossiers": deepcopy(dossiers)},
        "committed": True, "remote": "UNKNOWN", "endpoint": ENDPOINT,
    }
    local = {d["dossier_id"]: deepcopy(d) for d in dossiers}
    commits = []
    monkeypatch.setattr(journal, "_state", lambda _events: {"batch-r1": state})
    monkeypatch.setattr(journal, "_events", lambda _path: [])
    monkeypatch.setattr(journal.sd, "_leer_historial",
                        lambda _path: (local, set(), []))
    monkeypatch.setattr(journal, "marcar_readback_observado",
                        lambda *args, **kwargs: commits.append((args, kwargs)))
    return dossiers, FakeClient(dossiers), tmp_path, state, local, commits


def test_two_exact_get_then_one_local_commit(case):
    _, client, path, _, _, commits = case
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["checked"] == 2 and result["journal_recorded"]
    assert len(client.calls) == 2 and len(commits) == 1
    assert commits[0][1]["endpoint"] == ENDPOINT


def test_dry_run_only_get_no_journal_commit(case):
    _, client, path, _, _, commits = case
    result = reconciliar_lote_por_get("batch-r1", client, path, registrar=False)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["journal_recorded"] is False and not commits


@pytest.mark.parametrize("mutation", [
    lambda x: x.update(project_id="other"),
    lambda x: x.update(status_source="IN_PROCESS_MEMORY_CACHE"),
    lambda x: x.update(persisted_artifact_status="MISSING"),
    lambda x: x.update(scientific_status="PASS"),
    lambda x: x.update(criba_mechanism_execution_status="COMPLETED"),
    lambda x: x["posture"].update(project_id="other"),
    lambda x: x["posture"].update(stage="COMPLETED"),
    lambda x: (x.update(stage=None), x["posture"].update(stage=None)),
    lambda x: x["posture"].update(criba_dossier_receipt=None),
    lambda x: x["posture"]["criba_dossier_receipt"].update(
        payload_fingerprint="sha256:" + "0" * 64),
    lambda x: x["posture"]["criba_dossier_receipt"].update(
        criba_candidate_id="other"),
])
def test_wrong_receipt_cache_or_project_stays_unknown(case, mutation):
    dossiers, client, path, _, _, commits = case
    mutation(client.responses[_expected_project(dossiers[0]["dossier_id"])])
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "READBACK_NOT_DURABLY_BOUND"
    assert not commits


def test_second_get_timeout_not_promoted(case):
    dossiers, client, path, _, _, commits = case
    client.responses[_expected_project(dossiers[1]["dossier_id"])] = TimeoutError()
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["status"] == "UNKNOWN"
    assert result["checked"] == 1 and result["reason"] == "GET_FAILED"
    assert not commits


def test_endpoint_mismatch_blocks_before_any_get(case):
    _, client, path, _, _, commits = case
    client.config.endpoint = "https://other"
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["reason"] == "ENDPOINT_MISMATCH"
    assert not client.calls and not commits


def test_legacy_unknown_without_endpoint_blocks_get(case):
    _, client, path, state, _, commits = case
    state["endpoint"] = None
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["reason"] == "ENDPOINT_NOT_BOUND"
    assert not client.calls and not commits


def test_changed_local_history_blocks_get(case):
    dossiers, client, path, _, local, commits = case
    local[dossiers[0]["dossier_id"]]["problema"] = "other"
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["reason"] == "LOCAL_HISTORY_MISMATCH"
    assert not client.calls and not commits


def test_missing_batch_fails_before_get(case):
    _, client, path, _, _, _ = case
    with pytest.raises(ValueError, match="batch_id"):
        reconciliar_lote_por_get("does-not-exist", client, path)
    assert not client.calls


def test_failed_local_audit_append_remains_unknown(case, monkeypatch):
    _, client, path, _, _, _ = case
    def fail(*args, **kwargs):
        raise OSError("disk-full")
    monkeypatch.setattr(journal, "marcar_readback_observado", fail)
    result = reconciliar_lote_por_get("batch-r1", client, path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "JOURNAL_COMMIT_UNCONFIRMED"
