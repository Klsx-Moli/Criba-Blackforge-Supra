"""F20: reconciliation must bind the active sheet to fsynced PREPARED lineage.

Real temporary JSONL, replay state and locks. HTTP GET is simulated and
must never run for a different run_id or original problem.
"""
from __future__ import annotations

import pytest

from criba.dossier_batch_recovery import reconciliar_lote_por_get
from test_dossier_batch_phase15_integration import OnlyGet, prepared, project


@pytest.mark.parametrize("run_id, problem", [
    ("wrong-run", "Synthetic recovery problem"),
    ("phase15-run", "different problem"),
    ("wrong-run", "different problem"),
])
def test_wrong_sheet_lineage_blocks_get_and_any_journal_write(
    tmp_path, run_id, problem,
):
    key, originals = prepared(tmp_path)
    client = OnlyGet(originals)
    journal = tmp_path / "dossier_batches.jsonl"
    before = journal.read_bytes()
    result = reconciliar_lote_por_get(
        key, client, tmp_path,
        expected_run_id=run_id, expected_problem=problem,
    )
    assert result["status"] == "UNKNOWN"
    assert result["reason"] == "INTENT_LINEAGE_MISMATCH"
    assert result["checked"] == 0
    assert not client.calls
    assert journal.read_bytes() == before


def test_exact_sheet_lineage_reconciles_and_issues_only_expected_gets(tmp_path):
    key, originals = prepared(tmp_path)
    client = OnlyGet(originals)
    result = reconciliar_lote_por_get(
        key, client, tmp_path,
        expected_run_id="phase15-run",
        expected_problem="Synthetic recovery problem",
    )
    assert result["status"] == "READBACK_OBSERVED"
    assert result["fresh_get_status"] == "VERIFIED_FROM_ARTIFACT"
    assert client.calls == [project(d) for d in originals]
