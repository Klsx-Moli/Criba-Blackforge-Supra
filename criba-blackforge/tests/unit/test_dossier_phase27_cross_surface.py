"""F27: multi-entrypoint batch authority and conservative JSONL readers.

These are regression contracts for real on-disk journaling and the production
workflow, not proof of remote delivery, causal results, or GUI acceptance.
Never contact SUPRA or an external model.
"""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace

import pytest

from criba import dossier_batch as batch
from criba.dossier_batch_forensics import inspeccionar_journal
from criba.dossier_workflow import DossierWorkflow, WorkflowError
from test_dossier_batch_phase13 import dossiers


ENDPOINT = "https://supra.example"


class NoPostClient:
    def __init__(self, on_health=None):
        self.config = SimpleNamespace(endpoint=ENDPOINT)
        self.on_health = on_health
        self.health_calls = 0
        self.post_calls = 0

    def health(self):
        self.health_calls += 1
        if self.on_health:
            result = self.on_health()
            if result is not None:
                return result
        raise RuntimeError("synthetic health failure before POST")

    def run_project(self, **_kwargs):
        self.post_calls += 1
        raise AssertionError("POST must never occur in F27 regression")


def prepared(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    directory = tmp_path / "dossiers"
    items = dossiers(run="phase27-run")
    saved = batch.guardar_lote_dossiers(items, directory)
    return directory, saved["batch_id"], items


def test_runtime_journal_rejects_complete_json_without_final_newline(tmp_path, monkeypatch):
    directory, _, originals = prepared(tmp_path, monkeypatch)
    path = directory / batch.JOURNAL
    raw = path.read_bytes()
    assert raw.endswith(b"\n")
    path.write_bytes(raw[:-1])
    before = path.read_bytes()
    with pytest.raises(ValueError, match="unterminated"):
        batch.guardar_lote_dossiers(originals, directory)
    assert path.read_bytes() == before
    assert inspeccionar_journal(directory)["classification"] == "JOURNAL_UNTERMINATED_TAIL"


def test_forensic_dossier_history_rejects_complete_json_without_newline(tmp_path, monkeypatch):
    directory, _, _ = prepared(tmp_path, monkeypatch)
    path = directory / "dossiers.jsonl"
    data = path.read_bytes()
    assert data.endswith(b"\n")
    path.write_bytes(data[:-1])
    report = inspeccionar_journal(directory)
    assert report["classification"] == "DOSSIER_HISTORY_PARSE_INVALID"
    assert report["local_replay_parseable"] is False


def test_direct_workflow_cannot_bypass_batch_dispatch_claim(tmp_path, monkeypatch):
    _, _, items = prepared(tmp_path, monkeypatch)
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(items[0])
    assert client.health_calls == client.post_calls == 0


def test_direct_workflow_cannot_rename_id_to_escape_same_run(tmp_path, monkeypatch):
    _, _, items = prepared(tmp_path, monkeypatch)
    changed = deepcopy(items[0])
    changed["dossier_id"] = "alternate-id-same-run"
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(changed)
    assert client.health_calls == client.post_calls == 0


def test_unclaimed_batch_id_is_not_post_authority(tmp_path, monkeypatch):
    _, key, items = prepared(tmp_path, monkeypatch)
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(
            items[0], batch_dispatch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == client.post_calls == 0


def test_worker_claim_allows_only_original_payload_to_reach_health(tmp_path, monkeypatch):
    directory, key, items = prepared(tmp_path, monkeypatch)
    assert batch.marcar_envio_incierto(key, directory, endpoint=ENDPOINT)
    accepted = batch.reclamar_inicio_envio_remoto(
        key, items, directory, endpoint=ENDPOINT,
    )
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="SUPRA_UNAVAILABLE"):
        DossierWorkflow(client=client).submit(
            accepted[0], batch_dispatch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == 1
    assert client.post_calls == 0


@pytest.mark.parametrize("mutation", ["id", "payload", "endpoint", "other-batch"])
def test_worker_claim_rejects_forged_submission(
    tmp_path, monkeypatch, mutation,
):
    directory, key, items = prepared(tmp_path, monkeypatch)
    batch.marcar_envio_incierto(key, directory, endpoint=ENDPOINT)
    accepted = batch.reclamar_inicio_envio_remoto(
        key, items, directory, endpoint=ENDPOINT,
    )
    payload = deepcopy(accepted[0])
    selected_key, origin = key, ENDPOINT
    if mutation == "id":
        payload["dossier_id"] = "forged-identity"
    elif mutation == "payload":
        payload["mecanismo"] = "changed after worker claim"
    elif mutation == "endpoint":
        origin = "https://other.example"
    else:
        selected_key = "batch-other-run"
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(
            payload, batch_dispatch_id=selected_key, expected_endpoint=origin,
        )
    assert client.health_calls == client.post_calls == 0


def test_standalone_dossier_without_batch_can_reach_health(tmp_path, monkeypatch):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    item = dossiers(run="new-unbatched-run")[0]
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="SUPRA_UNAVAILABLE"):
        DossierWorkflow(client=client).submit(item)
    assert client.health_calls == 1
    assert client.post_calls == 0


def test_concurrent_batch_intent_during_health_stops_pre_post(
    tmp_path, monkeypatch,
):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    item = dossiers(run="phase27-race")[0]
    directory = tmp_path / "dossiers"

    def create_competing_intent():
        batch.guardar_lote_dossiers([item], directory)
        return {"status": "UP"}

    client = NoPostClient(on_health=create_competing_intent)
    # Initial pre-health check sees no batch. After successful health, a
    # separate writer has committed PREPARED. The pre-POST recheck MUST kill
    # this path before the fake transport's forbidden run_project method.
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(item)
    assert client.health_calls == 1
    assert client.post_calls == 0


def test_unreadable_journal_never_opens_direct_submission(tmp_path, monkeypatch):
    directory, _, items = prepared(tmp_path, monkeypatch)
    path = directory / batch.JOURNAL
    path.write_bytes(path.read_bytes() + b'{"schema":"incomplete"')
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(items[0])
    assert client.health_calls == client.post_calls == 0


def test_claimed_batch_cannot_override_deterministic_project_id(
    tmp_path, monkeypatch,
):
    directory, key, items = prepared(tmp_path, monkeypatch)
    batch.marcar_envio_incierto(key, directory, endpoint=ENDPOINT)
    accepted = batch.reclamar_inicio_envio_remoto(
        key, items, directory, endpoint=ENDPOINT,
    )
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(
            accepted[0], project_id="unrelated-project",
            batch_dispatch_id=key, expected_endpoint=ENDPOINT,
        )
    assert client.health_calls == client.post_calls == 0


def test_cli_send_obeys_same_batch_boundary_without_network(
    tmp_path, monkeypatch, capsys,
):
    from criba.dossier_workflow_cli import main as dossier_cli_main

    directory, _, items = prepared(tmp_path, monkeypatch)
    client = NoPostClient()
    exit_status = dossier_cli_main(
        ["--home", str(tmp_path), "send", "--dossier-id", items[0]["dossier_id"]],
        workflow_factory=lambda _endpoint: DossierWorkflow(client=client),
    )
    output = capsys.readouterr()
    # CLI rejects multi-dossier batches even before asking for consent.
    assert exit_status == 2
    assert '"code": "CLI_SINGLE_BATCH_REQUIRED"' in output.out
    assert client.health_calls == client.post_calls == 0
    assert (directory / batch.JOURNAL).is_file()


def test_worker_with_claim_cannot_send_without_original_endpoint(
    tmp_path, monkeypatch,
):
    directory, key, items = prepared(tmp_path, monkeypatch)
    batch.marcar_envio_incierto(key, directory, endpoint=ENDPOINT)
    claimed = batch.reclamar_inicio_envio_remoto(
        key, items, directory, endpoint=ENDPOINT,
    )
    client = NoPostClient()
    with pytest.raises(WorkflowError, match="BATCH_DISPATCH_BOUNDARY"):
        DossierWorkflow(client=client).submit(
            claimed[0], batch_dispatch_id=key,
        )
    assert client.health_calls == client.post_calls == 0


def test_real_cli_claim_reaches_health_before_post_and_stays_unknown(
    tmp_path, monkeypatch, capsys,
):
    """A fake-workflow test cannot catch the missing batch_dispatch_id wire."""
    from criba.dossier_workflow_cli import main as dossier_cli_main

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    directory = tmp_path / "dossiers"
    item = dossiers(run="phase27-cli-single")[0]
    key = batch.guardar_lote_dossiers([item], directory)["batch_id"]
    client = NoPostClient()
    exit_status = dossier_cli_main(
        ["--home", str(tmp_path), "send", "--dossier-id", item["dossier_id"],
         "--confirm-first-send"],
        workflow_factory=lambda _endpoint: DossierWorkflow(client=client),
    )
    output = capsys.readouterr()
    assert exit_status == 2
    assert '"code": "SUPRA_UNAVAILABLE"' in output.out
    assert client.health_calls == 1
    assert client.post_calls == 0
    current = batch._state(batch._events(directory / batch.JOURNAL))[key]
    assert current["remote"] == "UNKNOWN"
    assert current["dispatch_started"] is True
