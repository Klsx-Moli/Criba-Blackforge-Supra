"""F27: GET evidence may not inherit the origin of a changed SUPRA client.

Uses real JSONL, fsync and locked journal. Only GET responses are simulated;
there are no real network calls, POSTs or models.
"""
from __future__ import annotations

import pytest

from criba import dossier_batch as batch
from criba.dossier_batch_recovery import (
    inspeccionar_lote_parcial_por_get, reconciliar_lote_por_get,
)
from test_dossier_batch_phase15_integration import (
    ENDPOINT, OnlyGet, prepared, project,
)

OTHER = "https://other-supra.example"


class SwitchAfterGet(OnlyGet):
    def __init__(self, originals, *, switch_at=1):
        super().__init__(originals)
        self.switch_at = switch_at

    def get_project(self, identity):
        answer = super().get_project(identity)
        if len(self.calls) == self.switch_at:
            self.config.endpoint = OTHER
        return answer


class SwitchOnFailure(OnlyGet):
    def get_project(self, identity):
        self.calls.append(identity)
        self.config.endpoint = OTHER
        raise TimeoutError("origin changed while GET was pending")


def state(tmp_path, key):
    return batch._state(batch._events(tmp_path / batch.JOURNAL))[key]


def test_full_get_change_during_first_response_is_unknown_not_a_receipt(tmp_path):
    key, originals = prepared(tmp_path)
    client = SwitchAfterGet(originals)
    report = reconciliar_lote_por_get(key, client, tmp_path)
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "ENDPOINT_CHANGED_DURING_GET"
    assert len(client.calls) == 1
    assert state(tmp_path, key)["remote"] == "UNKNOWN"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_full_get_change_during_second_response_does_not_commit_v2(tmp_path):
    key, originals = prepared(tmp_path)
    client = SwitchAfterGet(originals, switch_at=2)
    report = reconciliar_lote_por_get(key, client, tmp_path)
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "ENDPOINT_CHANGED_DURING_GET"
    assert len(client.calls) == 2
    assert state(tmp_path, key)["remote"] == "UNKNOWN"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_partial_get_change_never_records_wrong_origin_receipt(tmp_path):
    key, originals = prepared(tmp_path)
    report = inspeccionar_lote_parcial_por_get(
        key, SwitchAfterGet(originals), tmp_path, registrar=True,
    )
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "ENDPOINT_CHANGED_DURING_GET"
    assert report["fresh_verified"] == 0
    assert state(tmp_path, key)["partial_readbacks"] == {}
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_partial_get_change_second_request_keeps_only_first_true_receipt(tmp_path):
    key, originals = prepared(tmp_path)
    report = inspeccionar_lote_parcial_por_get(
        key, SwitchAfterGet(originals, switch_at=2),
        tmp_path, registrar=True,
    )
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "ENDPOINT_CHANGED_DURING_GET"
    assert report["fresh_verified"] == 0
    journal_state = state(tmp_path, key)
    assert journal_state["remote"] == "UNKNOWN"
    assert set(journal_state["partial_readbacks"]) == {originals[0]["dossier_id"]}
    assert [x["event"] for x in batch._events(tmp_path / batch.JOURNAL)].count(
        "REMOTE_PARTIAL_READBACK_OBSERVED"
    ) == 1


@pytest.mark.parametrize("inspector", [
    lambda key, client, directory: reconciliar_lote_por_get(key, client, directory),
    lambda key, client, directory: inspeccionar_lote_parcial_por_get(
        key, client, directory, registrar=True,
    ),
])
def test_endpoint_drift_when_get_raises_is_not_misclassified_as_ordinary_404(
    tmp_path, inspector,
):
    key, originals = prepared(tmp_path)
    report = inspector(key, SwitchOnFailure(originals), tmp_path)
    assert report["status"] == "UNKNOWN"
    assert report["reason"] == "ENDPOINT_CHANGED_DURING_GET"
    assert state(tmp_path, key)["remote"] == "UNKNOWN"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_wrong_endpoint_before_any_get_prohibits_remote_io(tmp_path):
    key, originals = prepared(tmp_path)
    client = OnlyGet(originals, endpoint=OTHER)
    report = reconciliar_lote_por_get(key, client, tmp_path)
    assert report["reason"] == "ENDPOINT_MISMATCH"
    assert client.calls == []
    assert state(tmp_path, key)["remote"] == "UNKNOWN"


def test_stable_endpoint_remains_eligible_for_real_v2_get_receipt(tmp_path):
    key, originals = prepared(tmp_path)
    client = OnlyGet(originals, endpoint=ENDPOINT)
    report = reconciliar_lote_por_get(key, client, tmp_path)
    assert report["status"] == "READBACK_OBSERVED"
    assert report["journal_recorded"] is True
    assert client.calls == [project(originals[0]), project(originals[1])]
    assert state(tmp_path, key)["remote"] == "READBACK_OBSERVED"
