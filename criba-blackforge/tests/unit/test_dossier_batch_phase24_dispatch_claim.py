"""F24: one durable dispatch claim per journal-bound SUPRA batch.

Production JSONL, fsync, lock, replay and dossier integrity are not mocked.
Only the transport GET is simulated; there are no remote POST calls.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from criba import dossier_batch as batch
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from test_dossier_batch_phase15_integration import ENDPOINT, OnlyGet, dossiers


def local_reserved(directory: Path):
    original = dossiers()
    key = batch.guardar_lote_dossiers(original, directory)["batch_id"]
    assert batch.marcar_envio_incierto(key, directory, endpoint=ENDPOINT)
    return key, original


def claim(key, original, directory, *, endpoint=ENDPOINT):
    return batch.reclamar_inicio_envio_remoto(
        key, original, directory, endpoint=endpoint,
    )


def test_claim_adds_exactly_one_fsynced_event_without_claiming_http_success(tmp_path):
    key, original = local_reserved(tmp_path)
    assert claim(key, original, tmp_path) is None
    events = batch._events(tmp_path / batch.JOURNAL)
    assert [x["event"] for x in events] == [
        "PREPARED", "LOCAL_COMMITTED", "REMOTE_UNKNOWN",
        "REMOTE_DISPATCH_STARTED",
    ]
    state = batch._state(events)[key]
    assert state["remote"] == "UNKNOWN"
    assert state["dispatch_started"] is True
    assert not (tmp_path / "remote_http_receipt.json").exists()


def test_two_attempts_of_same_worker_cannot_claim_twice(tmp_path):
    key, original = local_reserved(tmp_path)
    claim(key, original, tmp_path)
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already claimed"):
        claim(key, original, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_unreserved_local_prepared_never_claims_dispatch(tmp_path):
    original = dossiers()
    key = batch.guardar_lote_dossiers(original, tmp_path)["batch_id"]
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="not pending UNKNOWN"):
        claim(key, original, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


@pytest.mark.parametrize("mutator", [
    lambda ds: ds.reverse(),
    lambda ds: ds.append(deepcopy(ds[0])),
    lambda ds: ds.pop(),
    lambda ds: ds.__setitem__(0, {**ds[0], "dossier_id": "fake-id"}),
    lambda ds: ds[0].__setitem__("mecanismo", "falsified"),
    lambda ds: ds[0].__setitem__("creado_at", "fake-time"),
])
def test_mutated_or_reordered_payload_never_issues_worker_claim(tmp_path, mutator):
    key, original = local_reserved(tmp_path)
    payloads = deepcopy(original)
    mutator(payloads)
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    with pytest.raises(ValueError, match="payload differs"):
        claim(key, payloads, tmp_path)
    assert journal.read_bytes() == before


@pytest.mark.parametrize("endpoint", [
    None, "", "http://other.example", "https://other.example",
    "http://127.0.0.1:8000/secret", "ftp://127.0.0.1:8000",
])
def test_endpoint_invalid_or_different_never_claims(tmp_path, endpoint):
    key, original = local_reserved(tmp_path)
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    with pytest.raises(ValueError):
        claim(key, original, tmp_path, endpoint=endpoint)
    assert journal.read_bytes() == before


def test_local_history_changed_after_reservation_blocks_worker_claim(tmp_path):
    key, original = local_reserved(tmp_path)
    path = tmp_path / "dossiers.jsonl"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "mechanism-1", "falsified-mechanism",
        ), encoding="utf-8",
    )
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="local dossier history changed"):
        claim(key, original, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_two_concurrent_worker_claims_only_one_wins(tmp_path):
    key, original = local_reserved(tmp_path)

    def attempt(_index):
        try:
            claim(key, original, tmp_path)
            return "CLAIMED"
        except ValueError as exc:
            assert "already claimed" in str(exc)
            return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, (0, 1)))
    assert sorted(results) == ["CLAIMED", "REJECTED"]
    assert [e["event"] for e in batch._events(
        tmp_path / batch.JOURNAL,
    )].count("REMOTE_DISPATCH_STARTED") == 1


def test_subprocess_claim_survives_restart_and_refuses_second_worker(tmp_path):
    key, original = local_reserved(tmp_path)
    command = (
        "import sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0,sys.argv[1])\n"
        "from criba.dossier_batch import reclamar_inicio_envio_remoto\n"
        "from criba.dossier_batch import _state, _events, JOURNAL\n"
        "source=Path(sys.argv[2])\n"
        "dossiers=_state(_events(source/JOURNAL))[sys.argv[3]]['intent']['dossiers']\n"
        "reclamar_inicio_envio_remoto(sys.argv[3],dossiers,source,endpoint=sys.argv[4])\n"
    )
    subprocess.run([
        sys.executable, "-c", command,
        str(Path(__file__).resolve().parents[2] / "src"),
        str(tmp_path), key, ENDPOINT,
    ], check=True, capture_output=True, text=True, timeout=20)
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))
    assert state[key]["dispatch_started"] is True
    assert state[key]["remote"] == "UNKNOWN"
    before = (tmp_path / batch.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="already claimed"):
        claim(key, original, tmp_path)
    assert (tmp_path / batch.JOURNAL).read_bytes() == before


def test_get_readback_after_worker_claim_still_supported_without_repost(tmp_path):
    key, original = local_reserved(tmp_path)
    claim(key, original, tmp_path)
    result = reconciliar_lote_por_get(
        key, OnlyGet(original), tmp_path,
    )
    assert result["status"] == "READBACK_OBSERVED"
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["remote"] == "READBACK_OBSERVED"
    assert state["dispatch_started"] is True
    with pytest.raises(ValueError, match="already claimed"):
        claim(key, original, tmp_path)


def test_legacy_unknown_and_v2_readback_remain_replayable_without_claim(tmp_path):
    key, original = local_reserved(tmp_path)
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["dispatch_started"] is False
    assert state["remote"] == "UNKNOWN"
    report = reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)
    assert report["status"] == "READBACK_OBSERVED"
    state = batch._state(batch._events(tmp_path / batch.JOURNAL))[key]
    assert state["dispatch_started"] is False
    assert state["remote"] == "READBACK_OBSERVED"


@pytest.mark.parametrize("mutation", ["wrong-endpoint", "wrong-fingerprint", "duplicate"])
def test_parseable_dispatch_marker_forgery_cannot_replay(tmp_path, mutation):
    key, original = local_reserved(tmp_path)
    claim(key, original, tmp_path)
    path = tmp_path / batch.JOURNAL
    records = batch._events(path)
    marker = deepcopy(records[-1])
    if mutation == "wrong-endpoint":
        marker["endpoint"] = "https://other.example"
        records[-1] = marker
    elif mutation == "wrong-fingerprint":
        marker["fingerprint"] = "0" * 64
        records[-1] = marker
    else:
        records.append(marker)
    path.write_text(
        "".join(json.dumps(item) + "\n" for item in records),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="dispatch start lineage mismatch|out-of-order"):
        batch._state(batch._events(path))


def test_dispatch_marker_before_remote_reservation_is_invalid(tmp_path):
    original = dossiers()
    key = batch.guardar_lote_dossiers(original, tmp_path)["batch_id"]
    marker = batch._event(
        "REMOTE_DISPATCH_STARTED", key, endpoint=ENDPOINT,
        fingerprint=batch._fingerprint(original),
    )
    sd._append_historial(tmp_path / batch.JOURNAL, marker)
    with pytest.raises(ValueError, match="out-of-order"):
        batch._state(batch._events(tmp_path / batch.JOURNAL))


def test_corrupt_tail_cannot_be_interpreted_as_empty_claim(tmp_path):
    key, original = local_reserved(tmp_path)
    path = tmp_path / batch.JOURNAL
    with path.open("ab") as output:
        output.write(b'{"event":')
    before = path.read_bytes()
    with pytest.raises(ValueError, match="batch journal corrupt"):
        claim(key, original, tmp_path)
    assert path.read_bytes() == before
