"""F23: explicit first dispatch of original PREPARED intent, without HTTP.

All state changes use production on-disk JSONL, cross-process lock and fsync;
the test never calls the provider. Test doubles do not replace the journal.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import subprocess
import sys
from pathlib import Path

import pytest

from criba import dossier_batch as batch
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from test_dossier_batch_phase15_integration import ENDPOINT, OnlyGet, dossiers


def _local(tmp_path: Path):
    originals = dossiers()
    key = batch.guardar_lote_dossiers(originals, tmp_path)["batch_id"]
    return key, originals


def _reserve(key, tmp_path, **changes):
    args = {
        "endpoint": ENDPOINT, "directory": tmp_path,
    }
    args.update(changes)
    return batch.reservar_primer_envio_preparado(
        key, "phase15-run", "Synthetic recovery problem", **args,
    )


def test_first_reservation_fsync_before_any_post_and_reuses_original_dossiers(tmp_path):
    key, originals = _local(tmp_path)
    path = tmp_path / batch.JOURNAL
    before = batch._events(path)
    assert len(before) == 2
    report = _reserve(key, tmp_path)
    assert report["reserved"] is True
    assert report["remote_state"] == "UNKNOWN"
    assert report["batch_id"] == key
    assert report["dossiers"] == originals
    assert report["endpoint"] == ENDPOINT
    assert report["path"] == str(tmp_path / "dossiers.jsonl")
    journal = batch._events(path)
    assert len(journal) == 3
    assert journal[-1]["event"] == "REMOTE_UNKNOWN"
    assert journal[-1]["endpoint"] == ENDPOINT
    assert batch._state(journal)[key]["remote"] == "UNKNOWN"
    assert not batch.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)


def test_duplicate_reservation_never_produces_another_remote_marker(tmp_path):
    key, _ = _local(tmp_path)
    _reserve(key, tmp_path)
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already reserved"):
        _reserve(key, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_invalid_endpoint_has_zero_journal_effect(tmp_path):
    key, _ = _local(tmp_path)
    before = (tmp_path / batch.JOURNAL).read_bytes()
    for origin in (None, "", "http://host/private", "https://user:secret@host",
                   "ftp://host", "https://host/?secret=1"):
        with pytest.raises(ValueError, match="endpoint"):
            _reserve(key, tmp_path, endpoint=origin)
        assert (tmp_path / batch.JOURNAL).read_bytes() == before


@pytest.mark.parametrize("run, problem", [
    ("another-run", "Synthetic recovery problem"),
    ("phase15-run", "different problem"),
    ("another-run", "different problem"),
    (" phase15-run", "Synthetic recovery problem"),
    ("phase15-run", ""),
    ("", "Synthetic recovery problem"),
])
def test_wrong_or_malformed_session_never_reserves(tmp_path, run, problem):
    key, _ = _local(tmp_path)
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="first dispatch"):
        batch.reservar_primer_envio_preparado(
            key, run, problem, endpoint=ENDPOINT, directory=tmp_path,
        )
    assert journal.read_bytes() == before


def test_local_not_committed_intent_never_authorizes_first_post(tmp_path):
    originals = dossiers()
    key = batch._batch_id("phase15-run", "Synthetic recovery problem")
    sd._append_historial(
        tmp_path / batch.JOURNAL,
        batch._event(
            "PREPARED", key, run_id="phase15-run",
            problema="Synthetic recovery problem",
            fingerprint=batch._fingerprint(originals), dossiers=originals,
        ),
    )
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="commit is incomplete"):
        _reserve(key, tmp_path)
    assert not (tmp_path / "dossiers.jsonl").exists()
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_local_history_tampering_rejected_without_marker(tmp_path):
    key, _ = _local(tmp_path)
    path = tmp_path / "dossiers.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "mechanism-1", "forged-mechanism",
        ), encoding="utf-8",
    )
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="original local dossier history changed"):
        _reserve(key, tmp_path)
    assert journal.read_bytes() == before


def test_unknown_attempt_can_only_go_to_get_not_another_post(tmp_path):
    key, originals = _local(tmp_path)
    assert batch.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already reserved"):
        _reserve(key, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before
    assert reconciliar_lote_por_get(
        key, OnlyGet(originals), tmp_path,
    )["status"] == "READBACK_OBSERVED"
    with pytest.raises(ValueError, match="already reserved"):
        _reserve(key, tmp_path)


def test_different_endpoint_after_reservation_cannot_reserve_again(tmp_path):
    key, _ = _local(tmp_path)
    _reserve(key, tmp_path)
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already reserved"):
        _reserve(key, tmp_path, endpoint="https://another.example")
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_parallel_first_dispatch_requests_leave_exactly_one_unknown(tmp_path):
    key, _ = _local(tmp_path)

    def try_reserve(_index):
        try:
            return _reserve(key, tmp_path)["reserved"]
        except ValueError as exc:
            assert "already reserved" in str(exc)
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        answers = list(pool.map(try_reserve, (1, 2)))
    assert sorted(answers) == [False, True]
    events = batch._events(tmp_path / batch.JOURNAL)
    assert [e["event"] for e in events].count("REMOTE_UNKNOWN") == 1
    assert len(events) == 3


def test_crash_after_fsync_in_new_process_never_allows_another_first_send(tmp_path):
    key, originals = _local(tmp_path)
    child = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0,sys.argv[1])\n"
        "from criba.dossier_batch import reservar_primer_envio_preparado\n"
        "result=reservar_primer_envio_preparado("
        "sys.argv[2],'phase15-run','Synthetic recovery problem',"
        "endpoint=sys.argv[4],directory=Path(sys.argv[3]))\n"
        "print(json.dumps(result, sort_keys=True))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", child,
         str(Path(__file__).resolve().parents[2] / "src"),
         key, str(tmp_path), ENDPOINT],
        capture_output=True, text=True, check=True, timeout=20,
    )
    reopened = json.loads(result.stdout.strip())
    assert reopened["dossiers"] == originals
    assert reopened["remote_state"] == "UNKNOWN"
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    assert batch._state(batch._events(journal))[key]["remote"] == "UNKNOWN"
    with pytest.raises(ValueError, match="already reserved"):
        _reserve(key, tmp_path)
    assert journal.read_bytes() == before


def test_corrupt_journal_tail_fails_closed_and_preserves_bytes(tmp_path):
    key, _ = _local(tmp_path)
    journal = tmp_path / batch.JOURNAL
    with journal.open("ab") as handle:
        handle.write(b'{"event":')
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="batch journal corrupt"):
        _reserve(key, tmp_path)
    assert journal.read_bytes() == before


def test_parseable_duplicate_journal_key_blocks_reservation(tmp_path):
    key, _ = _local(tmp_path)
    journal = tmp_path / batch.JOURNAL
    content = journal.read_text(encoding="utf-8")
    journal.write_text(
        content.replace('"batch_id":', '"batch_id":"fake","batch_id":', 1),
        encoding="utf-8",
    )
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="batch journal corrupt"):
        _reserve(key, tmp_path)
    assert journal.read_bytes() == before


def test_mutating_returned_dossier_does_not_rewrite_committed_intent(tmp_path):
    key, original = _local(tmp_path)
    observed = _reserve(key, tmp_path)
    observed["dossiers"][0]["mecanismo"] = "mutated after reservation"
    assert batch._state(batch._events(tmp_path / batch.JOURNAL))[key][
        "intent"
    ]["dossiers"] == original
