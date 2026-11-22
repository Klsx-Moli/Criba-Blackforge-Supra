"""F25: persisted partial GET receipts are not batch completion or proof of POST.

Real fsynced JSONL, original PREPARED lineage, replay and shared lock. GET
only is simulated. No SUPRA POST, model call or database fixture mutation.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from criba import dossier_batch as journal
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import (
    _readback, inspeccionar_lote_parcial_por_get, reconciliar_lote_por_get,
)
from test_dossier_batch_phase15_integration import (
    ENDPOINT, OnlyGet, dossiers, lookup, prepared, project,
)


def inspect(key, client, tmp_path, *, registrar=True, **kwargs):
    return inspeccionar_lote_parcial_por_get(
        key, client, tmp_path, registrar=registrar, **kwargs,
    )


def test_second_get_failure_persists_first_receipt_but_not_batch_success(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])] = TimeoutError("indeterminate GET")
    result = inspect(key, client, tmp_path)
    assert result["status"] == "PARTIAL_DIAGNOSTIC_ONLY"
    assert result["fresh_verified"] == 1
    assert result["journal_partials"] == 1
    assert result["full_batch_recorded"] is False
    assert [r["get_status"] for r in result["rows"]] == [
        "FRESH_PLANNING_RECEIPT_VERIFIED", "GET_UNAVAILABLE_UNKNOWN",
    ]
    events = journal._events(tmp_path / journal.JOURNAL)
    assert len(events) == 4
    assert events[-1]["event"] == "REMOTE_PARTIAL_READBACK_OBSERVED"
    assert journal._state(events)[key]["remote"] == "UNKNOWN"
    assert not any(e["event"] == "REMOTE_READBACK_OBSERVED" for e in events)


def test_all_individual_positive_gets_still_do_not_confirm_complete_batch(tmp_path):
    key, original = prepared(tmp_path)
    result = inspect(key, OnlyGet(original), tmp_path)
    assert result["fresh_verified"] == 2
    assert result["journal_partials"] == 2
    assert result["full_batch_recorded"] is False
    state = journal._state(journal._events(tmp_path / journal.JOURNAL))[key]
    assert state["remote"] == "UNKNOWN"
    assert len(state["partial_readbacks"]) == 2
    assert reconciliar_lote_por_get(key, OnlyGet(original), tmp_path)[
        "status"
    ] == "READBACK_OBSERVED"
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "remote"
    ] == "READBACK_OBSERVED"


def test_repeat_inspection_idempotent_under_same_original_receipt(tmp_path):
    key, original = prepared(tmp_path)
    inspect(key, OnlyGet(original), tmp_path)
    before = (tmp_path / journal.JOURNAL).read_bytes()
    replay = inspect(key, OnlyGet(original), tmp_path)
    assert replay["journal_partials"] == 2
    assert replay["fresh_verified"] == 2
    assert all(row["partial_written_now"] is False for row in replay["rows"])
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_failure_first_dossier_does_not_hide_later_confirmed_get(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[0])] = TimeoutError("first unavailable")
    result = inspect(key, client, tmp_path)
    assert result["fresh_verified"] == 1
    assert result["rows"][0]["get_status"] == "GET_UNAVAILABLE_UNKNOWN"
    assert result["rows"][1]["get_status"] == "FRESH_PLANNING_RECEIPT_VERIFIED"
    state = journal._state(journal._events(tmp_path / journal.JOURNAL))[key]
    assert set(state["partial_readbacks"]) == {original[1]["dossier_id"]}


@pytest.mark.parametrize("failure", [
    TimeoutError("timeout"),
    KeyError("404 not found"),
    ConnectionError("offline"),
])
def test_failed_get_is_unknown_not_absence_of_remote_post(tmp_path, failure):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[0])] = failure
    report = inspect(key, client, tmp_path)
    assert report["rows"][0]["get_status"] == "GET_UNAVAILABLE_UNKNOWN"
    assert report["rows"][1]["get_status"] == "FRESH_PLANNING_RECEIPT_VERIFIED"
    assert report["journal_partials"] == 1


def test_invalid_remote_receipt_never_creates_a_partial_event(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])]["posture"][
        "criba_dossier_receipt"
    ]["payload_fingerprint"] = "sha256:" + "f" * 64
    report = inspect(key, client, tmp_path)
    assert report["rows"][1]["get_status"] == "UNBOUND_READBACK_UNKNOWN"
    assert report["journal_partials"] == 1
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key][
        "remote"
    ] == "UNKNOWN"


def test_dry_run_remains_strictly_read_only(tmp_path):
    key, original = prepared(tmp_path)
    path = tmp_path / journal.JOURNAL
    before = path.read_bytes()
    report = inspect(key, OnlyGet(original), tmp_path, registrar=False)
    assert report["fresh_verified"] == 2
    assert report["journal_partials"] == 0
    assert path.read_bytes() == before


def test_wrong_lineage_cannot_perform_get_or_record_receipts(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    before = (tmp_path / journal.JOURNAL).read_bytes()
    report = inspect(
        key, client, tmp_path,
        expected_run_id="some-other-run",
    )
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "INTENT_LINEAGE_MISMATCH"
    assert report["rows"] == []
    assert client.calls == []
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_changed_origin_prevents_all_get_and_journal_writes(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original, endpoint="https://other.example")
    before = (tmp_path / journal.JOURNAL).read_bytes()
    report = inspect(key, client, tmp_path)
    assert report["reason"] == "ENDPOINT_MISMATCH"
    assert client.calls == []
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_partial_receipt_conflicting_or_foreign_row_fails_closed(tmp_path):
    key, original = prepared(tmp_path)
    row = _readback(original[0], lookup(original[0]))
    assert row is not None
    assert journal.registrar_readback_parcial(
        key, row, tmp_path, endpoint=ENDPOINT,
    )
    before = (tmp_path / journal.JOURNAL).read_bytes()
    wrong = deepcopy(row)
    wrong["dossier_id"] = "foreign"
    with pytest.raises(ValueError, match="not in original batch"):
        journal.registrar_readback_parcial(
            key, wrong, tmp_path, endpoint=ENDPOINT,
        )
    forged = deepcopy(row)
    forged["read"]["receipt"]["payload_fingerprint"] = "sha256:" + "0" * 64
    with pytest.raises(ValueError, match="readback"):
        journal.registrar_readback_parcial(
            key, forged, tmp_path, endpoint=ENDPOINT,
        )
    assert (tmp_path / journal.JOURNAL).read_bytes() == before


def test_parseable_duplicate_partial_marker_rejected_on_replay(tmp_path):
    key, original = prepared(tmp_path)
    inspect(key, OnlyGet(original), tmp_path)
    path = tmp_path / journal.JOURNAL
    old_events = journal._events(path)
    sd._append_historial(path, old_events[-1])
    with pytest.raises(ValueError, match="duplicate or foreign identity"):
        journal._state(journal._events(path))


def test_forged_partial_marker_wrong_endpoint_or_fingerprint_rejected(tmp_path):
    key, original = prepared(tmp_path)
    inspect(key, OnlyGet(original), tmp_path)
    for changed_field, value in (
        ("endpoint", "https://other.example"),
        ("fingerprint", "0" * 64),
    ):
        path = tmp_path / journal.JOURNAL
        old_events = journal._events(path)
        before = path.read_bytes()
        old_events[-1][changed_field] = value
        path.write_text(
            "".join(json.dumps(e) + "\n" for e in old_events),
            encoding="utf-8",
        )
        with pytest.raises(ValueError, match="partial readback lineage mismatch"):
            journal._state(journal._events(path))
        path.write_bytes(before)


def test_corrupt_tail_preserved_and_partial_inspection_fails_closed(tmp_path):
    key, original = prepared(tmp_path)
    path = tmp_path / journal.JOURNAL
    with path.open("ab") as output:
        output.write(b'{"event":')
    before = path.read_bytes()
    with pytest.raises(ValueError, match="batch journal corrupt"):
        inspect(key, OnlyGet(original), tmp_path)
    assert path.read_bytes() == before


def test_partial_receipts_survive_independent_process_restart(tmp_path):
    key, original = prepared(tmp_path)
    client = OnlyGet(original)
    client.responses[project(original[1])] = TimeoutError("GET 2")
    inspect(key, client, tmp_path)
    command = (
        "import json,sys\n"
        "from pathlib import Path\n"
        "sys.path.insert(0,sys.argv[1])\n"
        "from criba.dossier_batch import _events,_state,JOURNAL\n"
        "batch=_state(_events(Path(sys.argv[2])/JOURNAL))[sys.argv[3]]\n"
        "print(json.dumps({'remote':batch['remote'],"
        "'partial':sorted(batch['partial_readbacks'])}))\n"
    )
    run = subprocess.run(
        [sys.executable, "-c", command,
         str(Path(__file__).resolve().parents[2] / "src"),
         str(tmp_path), key],
        capture_output=True, text=True, check=True, timeout=20,
    )
    observed = json.loads(run.stdout.strip())
    assert observed == {
        "remote": "UNKNOWN",
        "partial": [original[0]["dossier_id"]],
    }


def test_two_concurrent_get_inspections_deduplicate_partial_events(tmp_path):
    key, original = prepared(tmp_path)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _i: inspect(key, OnlyGet(original), tmp_path), (1, 2),
        ))
    assert all(r["fresh_verified"] == 2 for r in results)
    state = journal._state(journal._events(tmp_path / journal.JOURNAL))[key]
    assert len(state["partial_readbacks"]) == 2
    assert len(journal._events(tmp_path / journal.JOURNAL)) == 5


def test_local_corruption_during_get_invalidates_all_fresh_claims(tmp_path):
    key, original = prepared(tmp_path)
    path = tmp_path / "dossiers.jsonl"

    class MutatingGet(OnlyGet):
        def get_project(self, project_id):
            reply = super().get_project(project_id)
            if len(self.calls) == 2:
                path.write_text(
                    path.read_text(encoding="utf-8").replace(
                        "mechanism-1", "forged-mechanism",
                    ), encoding="utf-8",
                )
            return reply

    result = inspect(key, MutatingGet(original), tmp_path)
    assert result["status"] == "UNKNOWN"
    assert result["fresh_verified"] == 0
    assert result["rows"] == []
    assert result["reason"] == "LOCAL_HISTORY_CHANGED_DURING_GET"


def test_partial_append_failure_never_reports_it_as_a_durable_receipt(
    tmp_path, monkeypatch,
):
    key, original = prepared(tmp_path)
    genuine = sd._append_historial

    def fail_partials(path, event):
        if event.get("event") == "REMOTE_PARTIAL_READBACK_OBSERVED":
            raise OSError("synthetic fsync failure")
        genuine(path, event)

    monkeypatch.setattr(sd, "_append_historial", fail_partials)
    report = inspect(key, OnlyGet(original), tmp_path)
    assert report["fresh_verified"] == 0
    assert report["journal_partials"] == 0
    assert all(
        r["get_status"] == "JOURNAL_WRITE_UNCONFIRMED"
        for r in report["rows"]
    )
    assert len(journal._events(tmp_path / journal.JOURNAL)) == 3


def test_full_readback_subsequent_partial_get_never_rewrites_old_receipts(tmp_path):
    key, original = prepared(tmp_path)
    assert reconciliar_lote_por_get(
        key, OnlyGet(original), tmp_path,
    )["status"] == "READBACK_OBSERVED"
    path = tmp_path / journal.JOURNAL
    before = path.read_bytes()
    report = inspect(key, OnlyGet(original), tmp_path)
    assert report["full_batch_recorded"] is True
    assert report["fresh_verified"] == 2
    assert path.read_bytes() == before



def test_oversized_partial_sweep_does_not_launch_unbounded_gets(tmp_path):
    originals = []
    for n in range(65):
        d = deepcopy(dossiers()[0])
        d["dossier_id"] = f"dossier-large-{n}"
        d["candidate_id"] = f"candidate-large-{n}"
        originals.append(d)
    key = journal.guardar_lote_dossiers(originals, tmp_path)["batch_id"]
    assert journal.marcar_envio_incierto(key, tmp_path, endpoint=ENDPOINT)
    client = OnlyGet(originals)
    source = tmp_path / journal.JOURNAL
    before = source.read_bytes()
    result = inspect(key, client, tmp_path)
    assert result["reason"] == "PARTIAL_SWEEP_LIMIT_EXCEEDED"
    assert result["status"] == "UNKNOWN"
    assert result["expected"] == 65
    assert result["rows"] == []
    assert client.calls == []
    assert source.read_bytes() == before
