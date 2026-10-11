"""Golden fingerprint vectors for the CRIBA side of the dossier envelope.

SUPRA owns the canonical vectors in
``docs/contracts/criba_supra_envelope_fingerprints.json``; its own suite reads
the same file. Two independent implementations computing one contract is only
safe if both are pinned to the same numbers, so this file asserts the CRIBA
values and ``supra/tests/test_criba_envelope_vectors.py`` asserts the SUPRA
ones. Neither suite imports the other package.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any

import pytest
from criba.integrations.supra_client import _dossier_payload_fingerprint

VECTORS_PATH = (
    Path(__file__).resolve().parents[3]
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


@pytest.mark.parametrize("vector", _vectors(), ids=lambda v: v["id"])
def test_criba_fingerprint_matches_the_golden_vector(vector: dict[str, Any]) -> None:
    assert _dossier_payload_fingerprint(vector["dossier"]) == vector["fingerprint"]


def test_omitted_and_explicit_defaults_are_one_payload() -> None:
    complete = _by_id("complete-defaults")
    omitted = _by_id("defaults-omitted")
    assert _dossier_payload_fingerprint(omitted["dossier"]) == complete["fingerprint"]


def test_creado_at_is_not_part_of_identity() -> None:
    stamped = _by_id("creado-at-stamped")
    complete = _by_id("complete-defaults")
    assert _dossier_payload_fingerprint(stamped["dossier"]) == complete["fingerprint"]


def test_a_real_change_changes_the_identity() -> None:
    baseline = _dossier_payload_fingerprint(_by_id("complete-defaults")["dossier"])
    changed = _dossier_payload_fingerprint(_by_id("with-evidence")["dossier"])
    assert changed != baseline


def test_unicode_normalization_stays_explicit() -> None:
    dossier = dict(_by_id("complete-defaults")["dossier"])
    composed = _dossier_payload_fingerprint({**dossier, "hipotesis": "café"})
    decomposed = _dossier_payload_fingerprint(
        {**dossier, "hipotesis": unicodedata.normalize("NFD", "café")}
    )
    assert composed != decomposed


def test_non_finite_numbers_have_no_identity() -> None:
    dossier = dict(_by_id("complete-defaults")["dossier"])
    with pytest.raises(ValueError):
        _dossier_payload_fingerprint({**dossier, "evidence_delivered": [{"v": float("nan")}]})


def test_key_ordering_does_not_change_the_identity() -> None:
    dossier = _by_id("complete-defaults")["dossier"]
    forward = _dossier_payload_fingerprint(dossier)
    backward = _dossier_payload_fingerprint(dict(reversed(list(dossier.items()))))
    assert forward == backward
