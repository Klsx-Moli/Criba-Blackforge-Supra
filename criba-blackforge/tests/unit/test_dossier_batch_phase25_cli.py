"""F25: CLI never returns success for a partial GET audit, even 2/2 positive.

Production parser, real fsynced journal and GET-only fake transport. No POST.
"""
from __future__ import annotations

import json

from criba import dossier_batch as batch
from criba import supra_dossier as sd
from criba import dossier_batch_recovery as recovery
from criba.integrations import supra_client
from test_dossier_batch_phase15_integration import OnlyGet, prepared, project


class ContextOnlyGet(OnlyGet):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _setup(monkeypatch, tmp_path, *, fail_second=False):
    key, original = prepared(tmp_path)
    client = ContextOnlyGet(original)
    if fail_second:
        client.responses[project(original[1])] = TimeoutError("unknown GET")
    monkeypatch.setattr(sd, "_dossiers_dir", lambda override=None: tmp_path)
    monkeypatch.setattr(supra_client, "SupraClient", lambda: client)
    return key, original, client


def test_inspect_partial_cli_dry_run_writes_nothing_and_exits_nonzero(
    monkeypatch, tmp_path, capsys,
):
    key, original, client = _setup(monkeypatch, tmp_path)
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    rc = recovery.main(["--batch-id", key, "--inspect-partial", "--dry-run"])
    output = json.loads(capsys.readouterr().out.strip())
    assert rc == 2
    assert output["status"] == "PARTIAL_DIAGNOSTIC_ONLY"
    assert output["fresh_verified"] == len(original)
    assert output["journal_partials"] == 0
    assert journal.read_bytes() == before
    assert client.calls == [project(d) for d in original]


def test_inspect_partial_cli_records_individual_get_without_batch_confirmation(
    monkeypatch, tmp_path, capsys,
):
    key, original, client = _setup(monkeypatch, tmp_path)
    rc = recovery.main(["--batch-id", key, "--inspect-partial"])
    output = json.loads(capsys.readouterr().out.strip())
    assert rc == 2
    assert output["fresh_verified"] == 2
    assert output["journal_partials"] == 2
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["remote"] == "UNKNOWN"
    assert len(state["partial_readbacks"]) == 2
    assert client.calls == [project(d) for d in original]


def test_partial_cli_with_failed_get_reports_unknown_not_absent_post(
    monkeypatch, tmp_path, capsys,
):
    key, _original, _client = _setup(
        monkeypatch, tmp_path, fail_second=True,
    )
    rc = recovery.main(["--batch-id", key, "--inspect-partial"])
    output = json.loads(capsys.readouterr().out.strip())
    assert rc == 2
    assert output["fresh_verified"] == 1
    assert output["rows"][1]["get_status"] == "GET_UNAVAILABLE_UNKNOWN"
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"


def test_normal_cli_can_confirm_only_after_full_v2_readback(
    monkeypatch, tmp_path, capsys,
):
    key, _original, _client = _setup(monkeypatch, tmp_path)
    rc = recovery.main(["--batch-id", key])
    output = json.loads(capsys.readouterr().out.strip())
    assert rc == 0
    assert output["status"] == "READBACK_OBSERVED"
    assert output["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert output["journal_recorded"] is True
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "remote"
    ] == "READBACK_OBSERVED"


def test_normal_cli_partial_failure_cannot_report_success(
    monkeypatch, tmp_path, capsys,
):
    key, _original, _client = _setup(
        monkeypatch, tmp_path, fail_second=True,
    )
    rc = recovery.main(["--batch-id", key])
    output = json.loads(capsys.readouterr().out.strip())
    assert rc == 2
    assert output["status"] == "UNKNOWN"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3
