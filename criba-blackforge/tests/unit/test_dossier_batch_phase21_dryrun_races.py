"""F21: dry-run GET must revalidate original local intent after I/O.

Uses production fsynced JSONL, recovery function and real lock; only GET is
simulated. This is a zero-POST, isolated tmp_path regression.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from criba import dossier_batch as batch
from criba.dossier_batch_recovery import reconciliar_lote_por_get
from test_dossier_batch_phase15_integration import OnlyGet, prepared, project


def test_unknown_dry_run_rechecks_local_dossiers_after_last_get(tmp_path):
    key, original = prepared(tmp_path)
    history = tmp_path / "dossiers.jsonl"

    class ConcurrentChange(OnlyGet):
        def get_project(self, identity):
            lookup = super().get_project(identity)
            if len(self.calls) == len(original):
                history.write_text(
                    history.read_text(encoding="utf-8").replace(
                        "mechanism-1", "forged-mechanism",
                    ), encoding="utf-8",
                )
            return lookup

    result = reconciliar_lote_por_get(
        key, ConcurrentChange(original), tmp_path, registrar=False,
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "LOCAL_OR_JOURNAL_CHANGED_DURING_GET"
    assert len(batch._events(tmp_path / batch.JOURNAL)) == 3


def test_unknown_dry_run_detects_torn_tail_added_during_get(tmp_path):
    key, original = prepared(tmp_path)
    journal = tmp_path / batch.JOURNAL

    class TornJournal(OnlyGet):
        def get_project(self, identity):
            lookup = super().get_project(identity)
            if len(self.calls) == len(original):
                with journal.open("ab") as stream:
                    stream.write(b'{"schema":"criba-dossier-batch/1","event":')
            return lookup

    with pytest.raises(ValueError, match="batch journal corrupt"):
        reconciliar_lote_por_get(
            key, TornJournal(original), tmp_path, registrar=False,
        )
    assert journal.read_bytes().endswith(
        b'{"schema":"criba-dossier-batch/1","event":'
    )


def test_unknown_dry_run_clean_intent_never_writes_receipt(tmp_path):
    key, original = prepared(tmp_path)
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    client = OnlyGet(original)
    report = reconciliar_lote_por_get(
        key, client, tmp_path, registrar=False,
    )
    assert report["status"] == "READBACK_OBSERVED"
    assert report["reason"] == "PERSISTED_PLANNING_RECEIPTS_ONLY"
    assert report["journal_recorded"] is False
    assert report["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert client.calls == [project(d) for d in original]
    assert journal.read_bytes() == before


def test_confirmed_dry_run_does_not_downgrade_clean_prior_receipt(tmp_path):
    key, original = prepared(tmp_path)
    assert reconciliar_lote_por_get(
        key, OnlyGet(original), tmp_path,
    )["journal_recorded"] is True
    journal = tmp_path / batch.JOURNAL
    before = journal.read_bytes()
    report = reconciliar_lote_por_get(
        key, OnlyGet(original), tmp_path, registrar=False,
    )
    assert report["status"] == "READBACK_OBSERVED"
    assert report["journal_recorded"] is True
    assert report["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert journal.read_bytes() == before


def test_unknown_dry_run_rereads_changed_parseable_journal(tmp_path):
    key, original = prepared(tmp_path)
    journal = tmp_path / batch.JOURNAL

    class ExtraUnknownEvent(OnlyGet):
        def get_project(self, identity):
            lookup = super().get_project(identity)
            if len(self.calls) == len(original):
                # An additional REMOTE_UNKNOWN is out-of-order and must fail
                # on parser replay, rather than be silently skipped.
                from criba import supra_dossier as sd
                sd._append_historial(
                    journal, batch._event(
                        "REMOTE_UNKNOWN", key, endpoint=self.config.endpoint,
                    ),
                )
            return lookup

    with pytest.raises(ValueError, match="out-of-order"):
        reconciliar_lote_por_get(
            key, ExtraUnknownEvent(original), tmp_path, registrar=False,
        )
