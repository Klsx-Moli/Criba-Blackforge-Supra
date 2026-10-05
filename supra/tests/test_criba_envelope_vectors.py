"""Golden fingerprint vectors for the SUPRA side of the dossier envelope.

CRIBA owns the canonical vectors in
``docs/contracts/criba_supra_envelope_fingerprints.json``; its own suite reads
the same file. This file asserts the SUPRA values are recomputed from the
VALIDATED model, so a fingerprint that drifts because of a serialization
accident rather than the content fails here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from supra_agentic.service import (
    CribaDossierRequest,
    _criba_payload_fingerprint,
)

VECTORS_PATH = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "contracts"
    / "criba_supra_envelope_fingerprints.json"
)


def _vectors() -> list[dict[str, Any]]:
    data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    return list(data["vectors"])


def _by_id(vector_id: str) -> dict[str, Any]:
    for vector in _vectors():
        if vector["id"] == vector_id:
            return vector
    raise AssertionError(f"unknown envelope vector {vector_id!r}")


def test_vector_file_is_present_and_declares_its_contract() -> None:
    data = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))
    assert data["envelope"] == "criba-supra/1"
    assert data["version"] == "criba-supra-envelope-vectors/1"
    assert len(data["vectors"]) >= 4


def test_interpreter_context_is_preserved_without_promoting_it_to_execution():
    from supra_agentic.service import _criba_dossier_receipt

    vector = _vectors()[0]
    data = dict(vector["dossier"])
    data["interpretacion"] = {"critica": {"evaluation_status": "CRITIQUED"},
                              "incertidumbre": "no hay ensayo"}
    dossier = CribaDossierRequest.model_validate(data)
    receipt = _criba_dossier_receipt(dossier, integration_version="criba-supra/1",
        payload_fingerprint=_criba_payload_fingerprint(dossier), request_fingerprint="test")
    assert receipt["interpretacion"]["incertidumbre"] == "no hay ensayo"
    assert receipt["execution_status"] == "NOT_EXECUTED"
    assert receipt["scientific_status"] == "NOT_VALIDATED"


@pytest.mark.parametrize("vector", _vectors(), ids=lambda v: v["id"])
def test_supra_fingerprint_matches_the_golden_vector(vector: dict[str, Any]) -> None:
    dossier = CribaDossierRequest(**vector["dossier"])
    assert _criba_payload_fingerprint(dossier) == vector["fingerprint"]


def test_omitted_and_explicit_defaults_are_one_payload() -> None:
    complete = CribaDossierRequest(**_by_id("complete-defaults")["dossier"])
    omitted = CribaDossierRequest(**_by_id("defaults-omitted")["dossier"])
    assert _criba_payload_fingerprint(omitted) == _criba_payload_fingerprint(complete)


def test_creado_at_is_not_part_of_identity() -> None:
    stamped = CribaDossierRequest(**_by_id("creado-at-stamped")["dossier"])
    complete = CribaDossierRequest(**_by_id("complete-defaults")["dossier"])
    assert _criba_payload_fingerprint(stamped) == _criba_payload_fingerprint(complete)


def test_a_real_change_changes_the_identity() -> None:
    baseline = CribaDossierRequest(**_by_id("complete-defaults")["dossier"])
    changed = CribaDossierRequest(**_by_id("with-evidence")["dossier"])
    assert _criba_payload_fingerprint(changed) != _criba_payload_fingerprint(baseline)


def test_key_ordering_does_not_change_the_identity() -> None:
    dossier = _by_id("complete-defaults")["dossier"]
    forward = _criba_payload_fingerprint(CribaDossierRequest(**dossier))
    backward = _criba_payload_fingerprint(
        CribaDossierRequest(**dict(reversed(list(dossier.items()))))
    )
    assert forward == backward
