"""F21: production journal/GET -> headless Shadow presenter.

Real local fsync, lock, replay and GET reconciliation; only HTTP simulated.
No POST, model call or Qt dependency.
"""
from __future__ import annotations

from criba import dossier_batch as journal
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from criba.ui.supra_batch_status import present_batch_recovery
from test_dossier_batch_phase15_integration import OnlyGet, prepared, project


def test_fresh_get_fsynced_receipt_only_planning(tmp_path):
    key, records = prepared(tmp_path)
    result = reconciliar_lote_por_get(key, OnlyGet(records), tmp_path)
    assert present_batch_recovery(result)["state"] == "FRESH_JOURNALED"
    assert result["scientific_status"] == "NOT_VALIDATED"
    assert result["mechanism_execution"] == "NOT_EXECUTED"
    assert journal._state(journal._events(tmp_path / journal.JOURNAL))[key]["remote"] == "READBACK_OBSERVED"


def test_dry_run_get_is_fresh_but_not_journaled(tmp_path):
    key, records = prepared(tmp_path)
    path = tmp_path / journal.JOURNAL
    before = path.read_bytes()
    result = reconciliar_lote_por_get(
        key, OnlyGet(records), tmp_path, registrar=False,
    )
    assert present_batch_recovery(result)["state"] == "FRESH_NOT_JOURNALED"
    assert path.read_bytes() == before
    assert journal._state(journal._events(path))[key]["remote"] == "UNKNOWN"


def test_offline_get_after_confirmed_receipt_is_only_historical(tmp_path):
    key, records = prepared(tmp_path)
    assert reconciliar_lote_por_get(
        key, OnlyGet(records), tmp_path,
    )["journal_recorded"] is True
    client = OnlyGet(records)
    client.responses[project(records[0])] = TimeoutError("offline")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    view = present_batch_recovery(result)
    assert view["state"] == "HISTORICAL_ONLY"
    assert view["fresh_get_status"] == "GET_FAILED"
    assert "HISTÓRICO" in view["summary"]


def test_unknown_get_failure_is_not_historical(tmp_path):
    key, records = prepared(tmp_path)
    client = OnlyGet(records)
    client.responses[project(records[0])] = TimeoutError("offline")
    assert present_batch_recovery(
        reconciliar_lote_por_get(key, client, tmp_path),
    )["state"] == "UNKNOWN"


def test_wrong_lineage_prevents_get_and_promotion(tmp_path):
    key, records = prepared(tmp_path)
    client = OnlyGet(records)
    result = reconciliar_lote_por_get(
        key, client, tmp_path,
        expected_run_id="other-run",
        expected_problem="Synthetic recovery problem",
    )
    assert result["reason"] == "INTENT_LINEAGE_MISMATCH"
    assert client.calls == []
    assert present_batch_recovery(result)["state"] == "UNKNOWN"


def test_unverified_artifact_never_promotes(tmp_path):
    key, records = prepared(tmp_path)
    client = OnlyGet(records)
    client.responses[project(records[0])]["persisted_artifact_status"] = "MISSING"
    assert present_batch_recovery(
        reconciliar_lote_por_get(key, client, tmp_path),
    )["state"] == "UNKNOWN"


def test_partial_get_cannot_promote_even_one_valid_receipt(tmp_path):
    key, records = prepared(tmp_path)
    client = OnlyGet(records)
    client.responses[project(records[-1])] = TimeoutError("later GET")
    result = reconciliar_lote_por_get(key, client, tmp_path)
    assert result["checked"] == 1
    assert present_batch_recovery(result)["state"] == "UNKNOWN"


def test_concurrent_get_single_recorded_event_presents_fresh(tmp_path):
    key, records = prepared(tmp_path)
    final_id = project(records[-1])

    class RacingGet(OnlyGet):
        def get_project(self, identity):
            value = super().get_project(identity)
            if identity == final_id:
                other = reconciliar_lote_por_get(
                    key, OnlyGet(records), tmp_path,
                )
                assert other["journal_recorded"] is True
            return value

    result = reconciliar_lote_por_get(key, RacingGet(records), tmp_path)
    assert result["reason"] == "JOURNAL_CONFIRMED_CONCURRENTLY"
    assert present_batch_recovery(result)["state"] == "FRESH_JOURNALED"
    assert len(journal._events(tmp_path / journal.JOURNAL)) == 4
