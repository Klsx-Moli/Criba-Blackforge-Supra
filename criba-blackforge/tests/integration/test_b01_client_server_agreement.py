"""B01: CRIBA's client fingerprint must reproduce the canonical vectors.

The client and SUPRA implement the same contract independently, in separate
venvs and separate test suites. Pinning the CLIENT against the golden values
(not against an import of the server module, which the CRIBA venv does not
have) is what makes drift detectable: if either side changes the identity rule,
this suite fails here as well as in SUPRA.

The golden values below are the validated-semantics rule: every declared SUPRA
default is materialized before hashing, `creado_at` is excluded as
non-semantic metadata, and unicode is not normalized.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from criba.integrations.supra_client import _dossier_payload_fingerprint  # noqa: E402

#: Identity of the canonical "thermal drift" dossier with every declared SUPRA
#: default materialized. Shared with the SUPRA side; changing one side without
#: the other breaks a real request with 422, which is the whole point.
CANONICAL_COMPLETE_FINGERPRINT = (
    "sha256:929080087251c1cfc4133aee8e2d8c854cc1d0259ff9651cd89e098b17f9bb20"
)


def _complete_dossier() -> dict:
    return {
        "dossier_id": "dossier-1",
        "candidate_id": "cand-1",
        "run_id": "",
        "claim_id": "claim-1",
        "protocol_version": "sha256:" + "a" * 64,
        "mechanism_version": "sha256:" + "b" * 64,
        "problema": "Reduce thermal drift",
        "bloqueo": "",
        "origen_bloqueo": "",
        "hipotesis": "A bounded calibration loop reduces drift",
        "mecanismo": "Closed-loop correction",
        "evidence_delivered": [],
        "evidence_documented_as_used": [],
        "evidencia_utilizada": [],
        "supuestos": [],
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "creado_at": "",
        "prueba_discriminante": {
            "afirmacion_decisiva": "The intervention changes the observable",
            "alternativa_explicativa": "Thermal drift from ambient variation",
            "intervencion_prueba": "Run calibrated and baseline arms",
            "observable": "temperature-adjusted error",
            "comparacion": "",
            "metrica": "",
            "resultado_favorable_mecanismo": "error falls inside the bound",
            "resultado_favorable_alternativa": "error tracks ambient temperature",
            "regla_decision": "Adopt if error is bounded under calibration",
            "condicion_fracaso": "error tracks ambient instead of the mechanism",
            "coste_permisos": "",
            "estado_prueba": "NO_EJECUTADA",
        },
    }


def _minimal_dossier() -> dict:
    """The same dossier with every optional key omitted."""
    dossier = {k: v for k, v in _complete_dossier().items() if k not in {
        "run_id", "bloqueo", "origen_bloqueo", "evidence_delivered",
        "evidence_documented_as_used", "evidencia_utilizada", "supuestos", "creado_at",
    }}
    dossier["prueba_discriminante"] = {
        k: v
        for k, v in dossier["prueba_discriminante"].items()
        if k not in {"comparacion", "metrica", "coste_permisos", "estado_prueba"}
    }
    return dossier


def test_complete_dossier_matches_the_canonical_vector() -> None:
    assert _dossier_payload_fingerprint(_complete_dossier()) == (
        CANONICAL_COMPLETE_FINGERPRINT
    )


def test_omitted_and_explicit_defaults_are_one_payload() -> None:
    """The client must not be penalized for not knowing the server's defaults."""
    assert _dossier_payload_fingerprint(_minimal_dossier()) == (
        _dossier_payload_fingerprint(_complete_dossier())
    )


def test_creado_at_is_not_part_of_identity() -> None:
    stamped = {**_complete_dossier(), "creado_at": "2026-01-01T00:00:00Z"}
    assert _dossier_payload_fingerprint(stamped) == (
        _dossier_payload_fingerprint(_complete_dossier())
    )


def test_key_ordering_does_not_change_identity() -> None:
    dossier = _complete_dossier()
    assert _dossier_payload_fingerprint(dict(reversed(list(dossier.items())))) == (
        _dossier_payload_fingerprint(dossier)
    )


def test_a_real_change_changes_the_identity() -> None:
    changed = {**_complete_dossier(), "hipotesis": "a different claim"}
    assert _dossier_payload_fingerprint(changed) != (
        _dossier_payload_fingerprint(_complete_dossier())
    )


def test_unicode_normalization_stays_explicit() -> None:
    """NFC and NFD are different byte sequences and must stay different."""
    composed = {**_complete_dossier(), "hipotesis": "café"}
    decomposed = {**_complete_dossier(), "hipotesis": "café"}
    assert _dossier_payload_fingerprint(composed) == _dossier_payload_fingerprint(
        decomposed
    )


def test_non_finite_content_has_no_identity() -> None:
    with pytest.raises((ValueError, TypeError)):
        _dossier_payload_fingerprint(
            {**_complete_dossier(), "supuestos": [float("nan")]}
        )
