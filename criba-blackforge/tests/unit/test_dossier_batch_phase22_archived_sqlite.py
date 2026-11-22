"""F22: SQLite invention saved before SUPRA + original fsynced JSONL journal.

The journal is never replaced with a fake. No HTTP, POST, model or Qt.
Includes an independent interpreter process to verify restart behavior.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from criba import dossier_batch as batch
from criba import supra_dossier as sd
from criba.invention_lineage import verify_archived_invention
from criba.storage import Storage
from criba.ui.supra_batch_resume import resolve_archived_batch
from test_dossier_batch_phase15_integration import dossiers, prepared


def _archive_before_supra(tmp_path: Path):
    store_path = tmp_path / "session_history.sqlite3"
    store = Storage(store_path)
    sheet = {
        "query": "Synthetic recovery problem", "run_id": "phase15-run",
        "entries": [{
            "candidate_id": "candidate-1",
            "run_id": "phase15-run",
            "estado_interpretacion": "PROPUESTA",
            "hipotesis": "Synthetic archived hypothesis",
            "mecanismo": "Synthetic archived mechanism",
            "interpretacion_error": "",
        }],
    }
    identity = store.save_invention(sheet)
    row = Storage(store_path).get(identity)
    verify_archived_invention(row)
    assert "dossier_batch_id" not in row["packet"]["sheet"]
    assert "dossier_remote_state" not in row["packet"]["sheet"]
    return store_path, identity, row["packet"]["sheet"]


def test_sqlite_saved_before_remote_reservation_can_recover_original_ids(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    key, original = prepared(tmp_path)
    assert archived.get("dossier_batch_id") is None
    recovered = resolve_archived_batch(archived, tmp_path)
    assert recovered["batch_id"] == key
    assert recovered["remote_state"] == "UNKNOWN"
    assert recovered["committed"] is True
    assert recovered["dossiers"] == [d["dossier_id"] for d in original]
    assert "dossier_batch_id" not in archived
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_true_new_session_without_journal_is_not_promoted(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    assert resolve_archived_batch(archived, tmp_path) is None
    assert not (tmp_path / batch.JOURNAL).exists()


def test_corrupt_or_missing_record_claimed_by_archived_sheet_fails_closed(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    archived["dossier_batch_id"] = "batch-not-in-journal"
    archived["dossier_remote_state"] = "UNKNOWN"
    with pytest.raises(ValueError, match="missing local journal"):
        resolve_archived_batch(archived, tmp_path)


def test_mismatched_claimed_id_cannot_redirect_get_to_another_batch(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    archived["dossier_batch_id"] = "batch-another-run"
    with pytest.raises(ValueError, match="conflicts with original journal"):
        resolve_archived_batch(archived, tmp_path)


@pytest.mark.parametrize("key,value", [
    ("run_id", None),
    ("run_id", " phase15-run"),
    ("query", None),
    ("query", "Synthetic recovery problem "),
])
def test_invalid_archived_lineage_with_remote_hint_is_not_replayed(
    tmp_path, key, value,
):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    archived["dossier_remote_state"] = "UNKNOWN"
    archived[key] = value
    with pytest.raises(ValueError, match="run_id"):
        resolve_archived_batch(archived, tmp_path)


def test_same_run_with_other_problem_rejected_as_conflict(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    archived["query"] = "Other problem"
    with pytest.raises(ValueError, match="problem conflicts"):
        resolve_archived_batch(archived, tmp_path)


def test_tampered_dossier_history_blocks_lookup_without_network(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    path = tmp_path / "dossiers.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "mechanism-1", "altered-mechanism",
        ), encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing or changed local dossier"):
        resolve_archived_batch(archived, tmp_path)


def test_torn_journal_tail_cannot_be_ignored(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    journal = tmp_path / batch.JOURNAL
    with journal.open("ab") as output:
        output.write(b'{"schema":"criba-dossier-batch/1","event":')
    original_bytes = journal.read_bytes()
    with pytest.raises(ValueError, match="batch journal corrupt"):
        resolve_archived_batch(archived, tmp_path)
    assert journal.read_bytes() == original_bytes


def test_local_prepared_but_not_committed_is_not_remote_ready(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    original = dossiers()
    key = batch._batch_id("phase15-run", "Synthetic recovery problem")
    intent = batch._event(
        "PREPARED", key, run_id="phase15-run",
        problema="Synthetic recovery problem",
        fingerprint=batch._fingerprint(original), dossiers=original,
    )
    sd._append_historial(tmp_path / batch.JOURNAL, intent)
    recovered = resolve_archived_batch(archived, tmp_path)
    assert recovered["batch_id"] == key
    assert recovered["remote_state"] == "NOT_ATTEMPTED"
    assert recovered["committed"] is False
    assert not (tmp_path / "dossiers.jsonl").exists()


def test_prepared_locally_but_never_reserved_stays_not_attempted(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    original = dossiers()
    key = batch.guardar_lote_dossiers(original, tmp_path)["batch_id"]
    recovered = resolve_archived_batch(archived, tmp_path)
    assert recovered["batch_id"] == key
    assert recovered["remote_state"] == "NOT_ATTEMPTED"
    assert recovered["committed"] is True


def test_stale_archived_status_does_not_override_fsynced_remote_state(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    key, _ = prepared(tmp_path)
    archived["dossier_batch_id"] = key
    archived["dossier_remote_state"] = "NOT_ATTEMPTED"
    recovered = resolve_archived_batch(archived, tmp_path)
    assert recovered["remote_state"] == "UNKNOWN"


def test_independent_python_interpreter_reopens_sqlite_then_journal(tmp_path):
    db, identity, _ = _archive_before_supra(tmp_path)
    key, original = prepared(tmp_path)
    source = Path(__file__).resolve().parents[2] / "src"
    child = (
        "import json, sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0,sys.argv[1])\n"
        "from criba.storage import Storage\n"
        "from criba.invention_lineage import verify_archived_invention\n"
        "from criba.ui.supra_batch_resume import resolve_archived_batch\n"
        "row = Storage(Path(sys.argv[2])).get(sys.argv[3])\n"
        "verify_archived_invention(row)\n"
        "result = resolve_archived_batch(row['packet']['sheet'],Path(sys.argv[4]))\n"
        "print(json.dumps(result,sort_keys=True))\n"
    )
    reopened = subprocess.run(
        [sys.executable, "-c", child, str(source), str(db), identity,
         str(tmp_path)],
        check=True, capture_output=True, text=True, timeout=20,
    )
    observed = json.loads(reopened.stdout.strip())
    assert observed["batch_id"] == key
    assert observed["remote_state"] == "UNKNOWN"
    assert observed["dossiers"] == [d["dossier_id"] for d in original]
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_duplicate_parseable_journal_key_rejected_before_lookup(tmp_path):
    _, _, archived = _archive_before_supra(tmp_path)
    prepared(tmp_path)
    journal = tmp_path / batch.JOURNAL
    original = journal.read_text(encoding="utf-8")
    journal.write_text(
        original.replace('"batch_id":', '"batch_id":"forged","batch_id":', 1),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="batch journal corrupt") as exc:
        resolve_archived_batch(archived, tmp_path)
    assert "duplicate JSON key" in str(exc.value.__cause__)



@pytest.mark.parametrize("field, value", [
    ("dossiers", ["dossier-previous"]),
    ("dossiers_path", "C:/old/dossiers.jsonl"),
    ("dossier_batch_id", None),
    ("dossier_remote_state", None),
])
def test_partial_archive_provenance_without_journal_cannot_authorize_fresh_post(
    tmp_path, field, value,
):
    _, _, archived = _archive_before_supra(tmp_path)
    archived[field] = value
    with pytest.raises(ValueError, match="missing local journal"):
        resolve_archived_batch(archived, tmp_path)
