"""F19: restart receipts and concurrent GET, with real JSONL and locks.

Only external GET and CLI client instantiation are faked. No POST; no models.
Tests never mutate user data: every journal is in pytest tmp_path.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import main, reconciliar_lote_por_get
from criba.integrations import supra_client
from test_dossier_batch_phase15_integration import (
    ENDPOINT, OnlyGet, events, prepared, project,
)


def _confirm(tmp_path: Path):
    key, original = prepared(tmp_path)
    report = reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)
    assert report["status"] == "READBACK_OBSERVED"
    assert report["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert journal._state(events(tmp_path))[key]["remote"] == "READBACK_OBSERVED"
    return key, original


def test_restart_offline_preserves_prior_receipt_but_fresh_get_fails(tmp_path):
    key, original = _confirm(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[0])] = TimeoutError("offline")
    before = (tmp_path / journal.JOURNAL).read_bytes()
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["reason"] == "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED"
    assert result["fresh_get_status"] == "GET_FAILED"
    assert result["checked"] == 0
    assert result["journal_recorded"] is True
    assert result["scientific_status"] == "NOT_VALIDATED"
    assert result["mechanism_execution"] == "NOT_EXECUTED"
    assert (tmp_path / journal.JOURNAL).read_bytes() == before
    assert client.calls == [project(original[0])]


def test_mismatched_fresh_get_reports_historical_not_current_proof(tmp_path):
    key, original = _confirm(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])]["posture"]["stage"] = "UNTRUSTED"
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["reason"] == "PREVIOUSLY_RECORDED_NOT_FRESHLY_VERIFIED"
    assert result["fresh_get_status"] == "READBACK_NOT_DURABLY_BOUND"
    assert result["checked"] == 1
    assert len(events(tmp_path)) == 4


def test_unknown_without_persisted_v2_remains_unknown_when_offline(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[0])] = TimeoutError("offline")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "GET_FAILED"
    assert len(events(tmp_path)) == 3


def test_two_reconcilers_one_fsynced_event(tmp_path):
    key, original = prepared(tmp_path)
    last = project(original[-1])

    class RacyClient(OnlyGet):
        def get_project(self, identifier):
            lookup = super().get_project(identifier)
            if identifier == last:
                other = reconciliar_lote_por_get(
                    key, OnlyGet(original), tmp_path,
                )
                assert other["status"] == "READBACK_OBSERVED"
            return lookup

    result = reconciliar_lote_por_get(key, RacyClient(original), tmp_path)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["reason"] == "JOURNAL_CONFIRMED_CONCURRENTLY"
    assert result["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert result["journal_recorded"] is True
    assert len(events(tmp_path)) == 4
    assert journal._state(events(tmp_path))[key]["remote"] == "READBACK_OBSERVED"


def test_tampered_local_history_after_prior_confirmation_blocks_all_get(tmp_path):
    key, original = _confirm(tmp_path)
    history = tmp_path / "dossiers.jsonl"
    history.write_text(
        history.read_text(encoding="utf-8").replace(
            "mechanism-1", "altered-mechanism",
        ), encoding="utf-8",
    )
    client = OnlyGet(original)
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "LOCAL_HISTORY_MISMATCH"
    assert client.calls == []


def test_tamper_during_get_prevents_returning_stale_persisted_status(tmp_path):
    key, original = _confirm(tmp_path)
    history = tmp_path / "dossiers.jsonl"

    class TamperingGet(OnlyGet):
        def get_project(self, identifier):
            value = super().get_project(identifier)
            if len(self.calls) == 1:
                history.write_text(
                    history.read_text(encoding="utf-8").replace(
                        "mechanism-1", "altered-mechanism",
                    ), encoding="utf-8",
                )
            return value

    result = reconciliar_lote_por_get(
        key, TamperingGet(original), tmp_path,
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "LOCAL_OR_JOURNAL_CHANGED_DURING_GET"


def test_legacy_unversioned_marker_does_not_promote_historical_status(tmp_path):
    key, original = prepared(tmp_path)
    sd._append_historial(
        tmp_path / journal.JOURNAL,
        journal._event("REMOTE_READBACK_OBSERVED", key, endpoint=ENDPOINT, runs=[]),
    )
    assert journal._state(events(tmp_path))[key]["remote"] == "UNKNOWN"
    client = OnlyGet(original)
    client.responses[project(original[0])] = TimeoutError("offline")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "GET_FAILED"


def test_corruption_inserted_during_get_fails_closed(tmp_path):
    key, original = _confirm(tmp_path)
    path = tmp_path / journal.JOURNAL

    class CorruptingGet(OnlyGet):
        def get_project(self, identifier):
            value = super().get_project(identifier)
            if len(self.calls) == 1:
                with path.open("ab") as stream:
                    stream.write(b"{bad-json}\n")
            return value

    with pytest.raises(ValueError, match="batch journal corrupt"):
        reconciliar_lote_por_get(key, CorruptingGet(original), tmp_path)


def test_wrong_endpoint_blocks_fresh_and_historical_claim_without_get(tmp_path):
    key, original = _confirm(tmp_path)
    client = OnlyGet(original, endpoint="https://different.example")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "ENDPOINT_MISMATCH"
    assert client.calls == []


def test_already_recorded_dry_run_offline_has_no_writes(tmp_path):
    key, original = _confirm(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[0])] = TimeoutError("offline")
    before = (tmp_path / journal.JOURNAL).read_bytes()
    result = reconciliar_lote_por_get(key, client, tmp_path, registrar=False)
    assert result["status"] == "READBACK_OBSERVED"
    assert result["fresh_get_status"] == "GET_FAILED"
    assert result["journal_recorded"]
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


@pytest.mark.parametrize("report, expected_exit", [
    ({"status": "READBACK_OBSERVED", "fresh_get_status": "GET_FAILED"}, 2),
    ({"status": "READBACK_OBSERVED",
      "fresh_get_status": "READBACK_NOT_DURABLY_BOUND"}, 2),
    ({"status": "READBACK_OBSERVED",
      "fresh_get_status": "VERIFIED_FROM_ARTIFACT"}, 0),
    ({"status": "UNKNOWN", "reason": "GET_FAILED"}, 2),
])
def test_cli_exit_code_requires_fresh_get_not_only_historical_status(
    monkeypatch, capsys, report, expected_exit,
):
    class Client:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    from criba import dossier_batch_recovery as recovery
    monkeypatch.setattr(supra_client, "SupraClient", Client)
    monkeypatch.setattr(
        recovery, "reconciliar_lote_por_get", lambda *args, **kwargs: report,
    )
    assert main(["--batch-id", "batch-synthetic"]) == expected_exit
    assert json.loads(capsys.readouterr().out) == report



def test_separate_python_process_reopens_fsynced_v2_receipt_without_post(tmp_path):
    """Actual second interpreter, not another call in the same process."""
    key, _ = _confirm(tmp_path)
    before = (tmp_path / journal.JOURNAL).read_bytes()
    child = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from criba import dossier_batch as b\n"
        "directory = Path(sys.argv[2])\n"
        "state = b._state(b._events(directory / b.JOURNAL))\n"
        "print(json.dumps({'remote':state[sys.argv[3]]['remote'],"
        "'pending':b.recuperar_lotes_pendientes(directory)}, sort_keys=True))\n"
    )
    result = subprocess.run(
        [
            sys.executable, "-c", child,
            str(Path(__file__).resolve().parents[2] / "src"),
            str(tmp_path), key,
        ],
        text=True, capture_output=True, check=True, timeout=20,
    )
    reopened = json.loads(result.stdout.strip())
    assert reopened == {"remote": "READBACK_OBSERVED", "pending": []}
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_separate_python_process_fails_closed_on_corrupt_v2_journal(tmp_path):
    key, _ = _confirm(tmp_path)
    path = tmp_path / journal.JOURNAL
    with path.open("ab") as handle:
        handle.write(b'{"schema":"criba-dossier-batch/1","event":')
    child = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, sys.argv[1])\n"
        "from criba import dossier_batch as b\n"
        "b._state(b._events(Path(sys.argv[2]) / b.JOURNAL))\n"
    )
    result = subprocess.run(
        [
            sys.executable, "-c", child,
            str(Path(__file__).resolve().parents[2] / "src"), str(tmp_path),
        ],
        text=True, capture_output=True, timeout=20,
    )
    assert result.returncode != 0
    assert "batch journal corrupt" in result.stderr
    assert path.read_bytes().endswith(b'{"schema":"criba-dossier-batch/1","event":')
