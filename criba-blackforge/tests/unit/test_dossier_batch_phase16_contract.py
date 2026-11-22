"""Phase16: unbound reservation and execution-state anti-Goodhart sentinels."""
from __future__ import annotations

import pytest

from criba import dossier_batch as b
from criba import supra_dossier as sd
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from test_dossier_batch_phase15_integration import ENDPOINT, OnlyGet, dossiers, events, prepared


def test_new_remote_attempt_requires_endpoint_with_no_journal_mutation(tmp_path):
    key = b.guardar_lote_dossiers(dossiers(), tmp_path)["batch_id"]
    before = (tmp_path / b.JOURNAL).read_bytes()
    with pytest.raises(ValueError, match="endpoint"):
        b.marcar_envio_incierto(key, tmp_path)
    assert (tmp_path / b.JOURNAL).read_bytes() == before
    assert b._state(events(tmp_path))[key]["remote"] == "NOT_ATTEMPTED"


@pytest.mark.parametrize("channel,value", [
    ("scientific_status", "VALIDATED"),
    ("criba_mechanism_execution_status", "COMPLETED"),
    ("criba_planning_receipt_status", "NOT_APPLICABLE"),
])
def test_full_local_readback_denies_conflicting_top_level_claims(tmp_path, channel, value):
    key, records = prepared(tmp_path)
    client = OnlyGet(records)
    client.responses[next(iter(client.responses))][channel] = value
    report = reconciliar_lote_por_get(key, client, tmp_path)
    assert report["status"] == "UNKNOWN"
    assert len(events(tmp_path)) == 3
    assert b._state(events(tmp_path))[key]["remote"] == "UNKNOWN"


def test_legacy_phase14_marker_never_promotes_until_new_verified_get(tmp_path):
    key, records = prepared(tmp_path)
    # Earlier F14 marker had endpoint and receipt, but omitted top-level
    # mechanism execution and planning status, so it is insufficient today.
    from criba.dossier_batch_recovery import _readback
    runs = [_readback(record, OnlyGet(records).responses[
        "astram2-" + __import__("hashlib").sha256(record["dossier_id"].encode()).hexdigest()[:32]
    ]) for record in records]
    sd._append_historial(
        tmp_path / b.JOURNAL,
        b._event("REMOTE_READBACK_OBSERVED", key, endpoint=ENDPOINT, runs=runs),
    )
    state = b._state(events(tmp_path))[key]
    assert state["remote"] == "UNKNOWN"
    assert state["legacy_readback_unverified"]
    result = reconciliar_lote_por_get(key, OnlyGet(records), tmp_path)
    assert result["status"] == "READBACK_OBSERVED"
    assert events(tmp_path)[-1]["evidence_version"] == "criba-batch-readback/2"
    assert b._state(events(tmp_path))[key]["remote"] == "READBACK_OBSERVED"


def test_replayed_v2_event_rejects_top_level_forgery(tmp_path):
    import json
    key, records = prepared(tmp_path)
    assert reconciliar_lote_por_get(key, OnlyGet(records), tmp_path)["status"] == "READBACK_OBSERVED"
    items = events(tmp_path)
    items[-1]["runs"][0]["read"]["scientific_status"] = "VALIDATED"
    path = tmp_path / b.JOURNAL
    path.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")
    with pytest.raises(ValueError, match="readback"):
        b._state(b._events(path))
