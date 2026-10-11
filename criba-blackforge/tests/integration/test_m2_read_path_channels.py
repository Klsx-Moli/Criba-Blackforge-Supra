"""M2 · sentinel del read path: la respuesta persistida debe poder describirse.

Dos defectos reproducidos por ejecución contra el servidor real (2026-10-02),
ambos invisibles para la suite existente:

  D1  ``SupraProjectLookup.status`` era ``Literal["success"]``. El servidor
      publica ``status`` DERIVADO del stage persistido, así que un proyecto
      BLOCKED respondía ``{"status": "blocked", ...}`` y el cliente tiraba
      ``SupraClientError: SUPRA project lookup violated response contract``.
      El read path —el único camino que reconstruye estado tras un reinicio—
      no podía leer el estado que le toca reconstruir.

  D2  El read path tampoco publicaba status_scope / workflow_status /
      verification_status / scientific_status. Un consumidor tenía que
      deducirlos, y la única forma de deducir "validado" era mirar status.

Regla vieja preservada por ``test_get_project_returns_typed_planning_receipt_snapshot``
(delivered commit 0a05119): la identidad del receipt y su alcance NO EJECUTADO.
Lo que esa test afirmaba —``status == "success"`` con ``stage == "BLOCKED"``—
era el mismo defecto D2 que K1 ya corrigió en el servidor: el objeto se
contradecía a sí mismo. La aserción queda INVERTIDA y la regla nueva es la que
sostiene el read path.

Sentinela de mutación:
  * volver ``status`` a ``Literal["success"]`` -> ``test_blocked_project_is_readable``
  * borrar ``status_scope``/``workflow_status`` -> ``test_read_publishes_separated_channels``
  * relajar ``_check_outcome_channels`` -> ``test_read_still_rejects_contradictory_channels``
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from criba.integrations.supra_client import (  # noqa: E402
    SupraClient,
    SupraClientConfig,
    SupraClientError,
)


def _client(payload: dict, *, status_code: int = 200) -> SupraClient:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json=payload)

    return SupraClient(
        SupraClientConfig(endpoint="https://supra.test", timeout=2.0),
        transport=httpx.MockTransport(handler),
    )


def _read_payload(**overrides: object) -> dict:
    """The exact shape SUPRA's read path returns for a BLOCKED project."""
    payload = {
        "status": "blocked",
        "status_scope": "WORKFLOW_EXECUTION_ONLY",
        "completion_status": "BLOCKED",
        "workflow_status": "BLOCKED",
        "verification_status": "FAIL",
        "verification_scope": "TEXTUAL_STRATEGY_COVERAGE",
        "scientific_status": "NOT_VALIDATED",
        "secure_sandbox_status": "RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        "criba_planning_receipt_status": "PRESERVED_NOT_EXECUTED",
        "criba_mechanism_execution_status": "NOT_EXECUTED",
        "idempotent_replay": False,
        "project_id": "slice-real",
        "stage": "BLOCKED",
        "status_source": "PERSISTED_STATE",
        "persisted_artifact_status": "VERIFIED_FROM_ARTIFACT",
        "posture": {
            "project_id": "slice-real",
            "stage": "BLOCKED",
            "final_output": None,
            "error_message": None,
            "criba_dossier_receipt": {
                "receipt_scope": "PLANNED_DISCRIMINANT_PROTOCOL_ONLY",
                "execution_status": "NOT_EXECUTED",
                "scientific_status": "NOT_VALIDATED",
                "criba_dossier_id": "dossier-1",
                "criba_candidate_id": "I01",
                "claim_id": "claim-1",
                "mechanism_version": "sha256:" + "b" * 64,
                "protocol_version": "sha256:" + "a" * 64,
                "integration_version": "criba-supra/1",
                "payload_fingerprint": "sha256:" + "c" * 64,
            },
        },
    }
    payload.update(overrides)
    return payload


def test_blocked_project_is_readable() -> None:
    """D1: a persisted BLOCKED project is a real state the client must return.

    Measured against the running server: it answers 200 with ``status="blocked"``.
    The old model refused it, so the restart path could not read a blocked run.
    """
    with _client(_read_payload()) as client:
        loaded = client.get_project("slice-real")
    assert loaded.status == "blocked"
    assert loaded.completion_status == "BLOCKED"
    assert loaded.stage == "BLOCKED"


def test_read_publishes_separated_channels() -> None:
    """D2: the read must separate the channels the write path separates.

    ``status`` alone can never stand in for verification or for scientific
    validation; that collapse is exactly what this model used to invite.
    """
    with _client(_read_payload()) as client:
        loaded = client.get_project("slice-real")
    assert loaded.status_scope == "WORKFLOW_EXECUTION_ONLY"
    assert loaded.workflow_status == "BLOCKED"
    assert loaded.verification_status == "FAIL"
    assert loaded.scientific_status == "NOT_VALIDATED"
    assert loaded.secure_sandbox_status == "RESTRICTED_BOUND_PASS_NOT_ISOLATED"
    assert loaded.status_source == "PERSISTED_STATE"
    assert loaded.criba_planning_receipt_status == "PRESERVED_NOT_EXECUTED"
    assert loaded.criba_mechanism_execution_status == "NOT_EXECUTED"
    # A blocked workflow is not a success in any channel.
    assert loaded.status != "success"


def test_pending_project_is_readable() -> None:
    """A nonterminal persisted stage is UNKNOWN completion, not a contract error."""
    payload = _read_payload(
        status="pending",
        completion_status="NOT_COMPLETED",
        workflow_status="STRUCTURED",
        stage="STRUCTURED",
        verification_status="NOT_EVALUATED",
    )
    payload["posture"] = {**payload["posture"], "stage": "STRUCTURED"}
    with _client(payload) as client:
        loaded = client.get_project("slice-real")
    assert loaded.status == "pending"
    assert loaded.completion_status == "NOT_COMPLETED"


@pytest.mark.parametrize(
    "overrides",
    [
        pytest.param(
            {"status": "success", "completion_status": "COMPLETED",
             "workflow_status": "COMPLETED", "stage": "COMPLETED"},
            id="fail-verification-claimed-complete",
        ),
        pytest.param(
            {"status": "success", "completion_status": "COMPLETED",
             "workflow_status": "COMPLETED", "stage": "COMPLETED",
             "verification_status": "PASS",
             "secure_sandbox_status": "NOT_REPORTED"},
            id="completed-without-isolated-sandbox",
        ),
        pytest.param(
            {"status": "blocked", "completion_status": "BLOCKED",
             "workflow_status": "COMPLETED", "stage": "COMPLETED"},
            id="blocked-but-stage-completed",
        ),
        pytest.param({"status": "success"}, id="success-without-completion-fields"),
    ],
)
def test_read_still_rejects_contradictory_channels(overrides: dict) -> None:
    """Relaxing the model must not become a way to fabricate completion.

    The old rule —only ``status`` had to be ``success``— would have accepted the
    first two shapes, which is how a FAIL verification becomes a success.
    """
    payload = _read_payload(**overrides)
    if overrides.get("stage"):
        payload["posture"] = {**payload["posture"], "stage": overrides["stage"]}
    with _client(payload) as client:
        with pytest.raises(SupraClientError, match="project lookup violated response contract"):
            client.get_project("slice-real")


def test_read_rejects_summary_stage_that_contradicts_persisted_posture() -> None:
    """Two statements about one fact may not disagree."""
    payload = _read_payload(stage="COMPLETED")
    payload["posture"] = {**payload["posture"], "stage": "BLOCKED"}
    with _client(payload) as client:
        with pytest.raises(SupraClientError, match="project lookup violated response contract"):
            client.get_project("slice-real")


def test_read_requires_the_state_to_be_declared_as_persisted() -> None:
    """A read that does not say where it read from cannot claim reconstruction.

    M3: the rule survives the widening. ``status_source`` accepts the two
    provenances the server can actually report, and rejects anything else, so
    an undeclared provenance is still a contract violation.
    """
    payload = _read_payload(status_source="IN_MEMORY")
    with _client(payload) as client:
        with pytest.raises(SupraClientError, match="project lookup violated response contract"):
            client.get_project("slice-real")


def test_read_requires_the_durable_copy_verdict_to_be_declared() -> None:
    """M3: serving from cache must still say what the durable copy says.

    A memory-served posture is a real answer, but without this channel the
    consumer cannot tell a cache hit whose artifact still matches from one whose
    artifact is gone. Dropping the field re-creates K1's original defect one
    level down.
    """
    payload = _read_payload()
    del payload["persisted_artifact_status"]
    with _client(payload) as client:
        with pytest.raises(SupraClientError, match="project lookup violated response contract"):
            client.get_project("slice-real")


def test_read_accepts_a_memory_served_posture_with_its_verdict() -> None:
    """M3: the honest label must be usable, or only the dishonest one remains.

    Before M3 the client rejected this payload outright, which is why the server
    kept publishing ``PERSISTED_STATE`` for cache hits.
    """
    payload = _read_payload(
        status_source="IN_PROCESS_MEMORY_CACHE",
        persisted_artifact_status="UNVERIFIABLE",
    )
    with _client(payload) as client:
        loaded = client.get_project("slice-real")
    assert loaded.status_source == "IN_PROCESS_MEMORY_CACHE"
    assert loaded.persisted_artifact_status == "UNVERIFIABLE"
    # The blocked outcome is still not a success, whatever the provenance.
    assert loaded.status == "blocked"
    assert loaded.verification_status == "FAIL"


def test_read_keeps_rejecting_a_receipt_promoted_to_execution() -> None:
    """The old protection must survive the widened model.

    A read that reports EXECUTED for a PLANNED receipt is fabricating evidence,
    and widening ``status`` is not a licence to widen this.
    """
    payload = _read_payload()
    payload["posture"] = {
        **payload["posture"],
        "criba_dossier_receipt": {
            **payload["posture"]["criba_dossier_receipt"],
            "execution_status": "EXECUTED",
        },
    }
    with _client(payload) as client:
        with pytest.raises(SupraClientError, match="project lookup violated response contract"):
            client.get_project("slice-real")
