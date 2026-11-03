"""EF05 read-path contract: a persisted planning receipt must stay readable.

Regression for the EF05 defect (blank ``criba_dossier_id`` made the whole GET
unreadable, so recovery raised SUPRA_READ_FAILED and the consumer could not see
that the remote project was BLOCKED with a planning receipt).

Contract enforced here, on the REAL transport model (SupraCribaPlanningReceipt):

  * a canonical valid receipt round-trips with its scope and statuses intact;
  * a receipt with an empty ``criba_dossier_id`` is still a readable unbound
    planning record: no ValidationError, no total read failure;
  * the write path still rejects blank lineage before transport, so the read
    relaxation is not a licence to submit an unbound dossier;
  * a padded ``criba_dossier_id`` is NOT silently normalised: the transport
    model accepts it as a string, but binding rejects it (no alias).

Mutation: restore ``criba_dossier_id: str = Field(min_length=1)`` and the
empty-id case fails; remove the write-path blank check and the blank-lineage
write case fails. Both are deliberate kills.
"""
from __future__ import annotations

import os
from types import SimpleNamespace

import httpx
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from criba.integrations.supra_client import (  # noqa: E402
    SupraCribaPlanningReceipt,
    SupraClient,
    SupraClientConfig,
    SupraClientError,
)

BASE_RECEIPT = {
    "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
    "execution_status": "NOT_EXECUTED",
    "scientific_status": "NOT_VALIDATED",
    "criba_dossier_id": "dossier-ef05-valid",
    "criba_candidate_id": "candidate-ef05",
    "claim_id": "claim-ef05",
    "mechanism_version": "sha256:" + "a" * 64,
    "protocol_version": "sha256:" + "b" * 64,
    "integration_version": "criba-supra/1",
    "payload_fingerprint": "sha256:" + "c" * 64,
}


def _lookup_payload(receipt: dict) -> dict:
    return {
        "status": "blocked",
        "status_scope": "WORKFLOW_EXECUTION_ONLY",
        "completion_status": "BLOCKED",
        "workflow_status": "BLOCKED",
        "verification_status": "FAIL",
        "scientific_status": "NOT_VALIDATED",
        "secure_sandbox_status": "RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "idempotent_replay": False,
        "status_source": "PERSISTED_STATE",
        "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
        "project_id": "astram2-ef05",
        "stage": "BLOCKED",
        "posture": {
            "project_id": "astram2-ef05",
            "stage": "BLOCKED",
            "final_output": None,
            "error_message": None,
            "criba_dossier_receipt": receipt,
        },
    }


def _client(receipt: dict) -> SupraClient:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/health":
            return httpx.Response(200, json={"status": "ok", "service": "supra", "version": "test"})
        if request.url.path == "/api/v1/projects/ef05-project":
            return httpx.Response(200, json=_lookup_payload(receipt))
        raise AssertionError("unexpected path " + request.url.path)

    return SupraClient(
        SupraClientConfig(endpoint="https://supra.ef05.invalid", timeout=2),
        transport=httpx.MockTransport(handler),
    )


def test_canonical_receipt_round_trips_without_promotion() -> None:
    with _client(dict(BASE_RECEIPT)) as client:
        lookup = client.get_project("ef05-project")
    receipt = lookup.posture.criba_dossier_receipt
    assert receipt.criba_dossier_id == "dossier-ef05-valid"
    assert receipt.receipt_scope == "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
    assert receipt.execution_status == "NOT_EXECUTED"
    assert receipt.scientific_status == "NOT_VALIDATED"
    assert lookup.scientific_status == "NOT_VALIDATED"


def test_empty_criba_dossier_id_is_readable_not_a_total_failure() -> None:
    """EF05: an empty persisted id must not make the whole GET unreadable."""
    empty = {**BASE_RECEIPT, "criba_dossier_id": ""}
    with _client(empty) as client:
        lookup = client.get_project("ef05-project")
    receipt = lookup.posture.criba_dossier_receipt
    assert receipt.criba_dossier_id == ""
    # planning scope is still declared; nothing was promoted
    assert receipt.execution_status == "NOT_EXECUTED"
    assert receipt.scientific_status == "NOT_VALIDATED"


def test_blank_id_receipt_validates_on_the_transport_model() -> None:
    empty = {**BASE_RECEIPT, "criba_dossier_id": ""}
    receipt = SupraCribaPlanningReceipt.model_validate(empty)
    assert receipt.criba_dossier_id == ""


def test_binding_rejects_blank_id_without_internal_exception() -> None:
    """Blank id stays an unbound record; it must not raise to the consumer."""
    from criba.dossier_workflow import DossierWorkflow

    workflow = DossierWorkflow()
    lookup = SimpleNamespace(
        project_id="ef05-project",
        posture=SimpleNamespace(criba_dossier_receipt={**BASE_RECEIPT, "criba_dossier_id": ""}),
    )
    local, code, reason = workflow.bind_local(lookup)
    assert local is None
    assert code == "RECEIPT_IDENTITY_INVALID"
    assert reason == "Receipt con identidad no exacta."


def test_binding_rejects_padded_id_without_silent_normalisation() -> None:
    from criba.dossier_workflow import DossierWorkflow

    workflow = DossierWorkflow()
    lookup = SimpleNamespace(
        project_id="ef05-project",
        posture=SimpleNamespace(
            criba_dossier_receipt={**BASE_RECEIPT, "criba_dossier_id": " dossier-ef05-valid "}
        ),
    )
    local, code, _reason = workflow.bind_local(lookup)
    assert local is None
    assert code == "RECEIPT_IDENTITY_INVALID"


def test_binding_rejects_missing_identity_key() -> None:
    from criba.dossier_workflow import DossierWorkflow

    workflow = DossierWorkflow()
    receipt = {k: v for k, v in BASE_RECEIPT.items() if k != "criba_dossier_id"}
    lookup = SimpleNamespace(
        project_id="ef05-project",
        posture=SimpleNamespace(criba_dossier_receipt=receipt),
    )
    local, code, _reason = workflow.bind_local(lookup)
    assert local is None
    assert code == "RECEIPT_IDENTITY_INVALID"


def test_write_path_still_rejects_blank_lineage_before_transport() -> None:
    """The read relaxation must not become a licence to submit a blank id."""

    def forbidden(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("transport must not be called for a blank lineage")

    with SupraClient(
        SupraClientConfig(endpoint="https://supra.ef05.invalid", timeout=2),
        transport=httpx.MockTransport(forbidden),
    ) as client:
        with pytest.raises(ValueError, match="non-blank"):
            client.run_project(
                objective="EF05 blank lineage must be rejected before transport",
                criba_dossier={
                    "dossier_id": "", "candidate_id": "candidate-ef05",
                    "claim_id": "claim-ef05",
                    "mechanism_version": "sha256:" + "a" * 64,
                    "protocol_version": "sha256:" + "b" * 64,
                },
            )


def test_read_still_rejects_a_receipt_promoted_to_execution() -> None:
    """The EF05 relaxation must not widen the scope/executed contract."""
    promoted = {**BASE_RECEIPT, "execution_status": "EXECUTED"}
    with _client(promoted) as client:
        with pytest.raises(SupraClientError, match="violated response contract"):
            client.get_project("ef05-project")
