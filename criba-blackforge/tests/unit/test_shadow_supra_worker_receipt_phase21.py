"""F21: worker ack cannot promote a planning receipt without bound status.

No PySide6, real SUPRA, HTTP or journal writes: tests only the truthful UI
boundary. The fsynced journal itself has independent phase15-20 tests.
"""
from __future__ import annotations

from copy import deepcopy

import pytest

from criba.ui.supra_batch_status import submitted_batch_receipt_valid


def valid_report():
    return {
        "batch_id": "batch-1",
        "journal_recorded": True,
        "runs": [{
            "dossier_id": "dossier-1",
            "scientific_status": "NOT_VALIDATED",
            "criba_mechanism_execution_status": "NOT_EXECUTED",
            "read": {
                "status_source": "PERSISTED_STATE",
                "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
                "scientific_status": "NOT_VALIDATED",
                "criba_mechanism_execution_status": "NOT_EXECUTED",
                "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
                "receipt": {
                    "criba_dossier_id": "dossier-1",
                    "criba_candidate_id": "candidate-1",
                    "claim_id": "claim-1",
                    "mechanism_version": "sha256:" + "a" * 64,
                    "protocol_version": "sha256:" + "b" * 64,
                    "payload_fingerprint": "sha256:" + "c" * 64,
                    "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
                    "integration_version": "criba-supra/1",
                    "execution_status": "NOT_EXECUTED",
                    "scientific_status": "NOT_VALIDATED",
                },
            },
        }],
    }


def test_valid_worker_ack_is_presentable_only_as_planning_receipt():
    assert submitted_batch_receipt_valid(valid_report(), ["dossier-1"], "batch-1")


@pytest.mark.parametrize("path, value", [
    (("journal_recorded",), False),
    (("journal_recorded",), 1),
    (("batch_id",), "different-batch"),
    (("runs", 0, "scientific_status"), "VALIDATED"),
    (("runs", 0, "scientific_status"), None),
    (("runs", 0, "criba_mechanism_execution_status"), "COMPLETED"),
    (("runs", 0, "dossier_id"), "wrong-dossier"),
    (("runs", 0, "read"), None),
    (("runs", 0, "read", "status_source"), "IN_PROCESS_MEMORY_CACHE"),
    (("runs", 0, "read", "persisted_artifact_status"), "MISSING"),
    (("runs", 0, "read", "scientific_status"), "PASS"),
    (("runs", 0, "read", "criba_mechanism_execution_status"), "EXECUTED"),
    (("runs", 0, "read", "criba_planning_receipt_status"), "UNKNOWN"),
    (("runs", 0, "read", "receipt", "criba_dossier_id"), "other"),
    (("runs", 0, "read", "receipt", "receipt_scope"), "EXECUTED_MECHANISM"),
    (("runs", 0, "read", "receipt", "integration_version"), None),
    (("runs", 0, "read", "receipt", "execution_status"), "EXECUTED"),
    (("runs", 0, "read", "receipt", "scientific_status"), "VALIDATED"),
])
def test_mutation_rejected_even_when_worker_claims_journal(path, value):
    report = deepcopy(valid_report())
    target = report
    for component in path[:-1]:
        target = target[component]
    target[path[-1]] = value
    assert not submitted_batch_receipt_valid(report, ["dossier-1"], "batch-1")


@pytest.mark.parametrize("ids", [
    None, [], [None], [True], ["dossier-1", "dossier-1"],
    ["other-dossier"], [" dossier-1"], ["dossier-1", "second"],
])
def test_untrusted_batch_id_sets_never_authorize_ack(ids):
    assert not submitted_batch_receipt_valid(valid_report(), ids, "batch-1")


def test_two_rows_must_both_be_bound_not_just_first():
    report = valid_report()
    second = deepcopy(report["runs"][0])
    second["dossier_id"] = "dossier-2"
    second["read"]["receipt"]["criba_dossier_id"] = "dossier-2"
    report["runs"].append(second)
    assert submitted_batch_receipt_valid(
        report, ["dossier-2", "dossier-1"], "batch-1",
    )
    report["runs"][1]["read"]["receipt"]["execution_status"] = "EXECUTED"
    assert not submitted_batch_receipt_valid(
        report, ["dossier-2", "dossier-1"], "batch-1",
    )


def test_unexpected_or_missing_rows_do_not_count_as_complete():
    report = valid_report()
    assert not submitted_batch_receipt_valid(report, ["dossier-1", "dossier-2"], "batch-1")
    report["runs"] = []
    assert not submitted_batch_receipt_valid(report, ["dossier-1"], "batch-1")



@pytest.mark.parametrize("field, value", [
    ("criba_candidate_id", None),
    ("criba_candidate_id", " "),
    ("claim_id", None),
    ("claim_id", ""),
    ("mechanism_version", None),
    ("mechanism_version", "sha256:bad"),
    ("protocol_version", "sha256:" + "Z" * 64),
    ("payload_fingerprint", None),
    ("payload_fingerprint", "sha256:" + "0" * 63),
    ("payload_fingerprint", "sha256:" + "G" * 64),
])
def test_missing_or_malformed_receipt_lineage_is_rejected(field, value):
    report = valid_report()
    report["runs"][0]["read"]["receipt"][field] = value
    assert not submitted_batch_receipt_valid(report, ["dossier-1"], "batch-1")
