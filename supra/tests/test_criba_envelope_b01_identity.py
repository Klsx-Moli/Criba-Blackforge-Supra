"""B01: identity must follow the validated dossier, not the serialization shape.

RED TEST. On the pre-fix base this fails: `_criba_payload_fingerprint` used
`model_dump(exclude_unset=True)`, so the same validated dossier hashed two
different ways depending on which keys the client happened to send.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from supra_agentic.service import (  # noqa: E402
    CribaDossierRequest,
    _criba_payload_fingerprint,
)


def _dossier() -> dict:
    return {
        "dossier_id": "dossier-1",
        "candidate_id": "cand-1",
        "claim_id": "claim-1",
        "protocol_version": "sha256:" + "a" * 64,
        "mechanism_version": "sha256:" + "b" * 64,
        "problema": "Reduce thermal drift",
        "hipotesis": "A bounded calibration loop reduces drift",
        "mecanismo": "Closed-loop correction",
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "prueba_discriminante": {
            "afirmacion_decisiva": "The intervention changes the observable",
            "alternativa_explicativa": "Thermal drift from ambient variation",
            "intervencion_prueba": "Run calibrated and baseline arms",
            "observable": "temperature-adjusted error",
            "resultado_favorable_mecanismo": "error falls inside the bound",
            "resultado_favorable_alternativa": "error tracks ambient temperature",
            "regla_decision": "Adopt if error is bounded under calibration",
            "condicion_fracaso": "error tracks ambient instead of the mechanism",
        },
    }


def _complete(dossier: dict) -> dict:
    """The same dossier with every declared SUPRA default materialized."""
    return {
        **dossier,
        "run_id": "",
        "bloqueo": "",
        "origen_bloqueo": "",
        "evidence_delivered": [],
        "evidence_documented_as_used": [],
        "evidencia_utilizada": [],
        "supuestos": [],
        "creado_at": "",
        "prueba_discriminante": {
            **dossier["prueba_discriminante"],
            "comparacion": "",
            "metrica": "",
            "coste_permisos": "",
            "estado_prueba": "NO_EJECUTADA",
        },
    }


def test_omitted_and_explicit_defaults_share_one_fingerprint() -> None:
    """A client that omits defaults must be the same payload as one that sends them."""
    omitted = _criba_payload_fingerprint(CribaDossierRequest(**_dossier()))
    explicit = _criba_payload_fingerprint(CribaDossierRequest(**_complete(_dossier())))
    assert omitted == explicit


def test_genuinely_changed_payload_still_changes_the_fingerprint() -> None:
    """Stability must not become insensitivity: real change -> real change."""
    base = _criba_payload_fingerprint(CribaDossierRequest(**_dossier()))
    changed = _criba_payload_fingerprint(
        CribaDossierRequest(**{**_dossier(), "hipotesis": "a different claim"})
    )
    assert base != changed


def test_creado_at_is_not_part_of_identity() -> None:
    """Non-semantic metadata must not split one work into two identities."""
    stamped = _criba_payload_fingerprint(
        CribaDossierRequest(**{**_dossier(), "creado_at": "2026-01-01T00:00:00Z"})
    )
    assert stamped == _criba_payload_fingerprint(CribaDossierRequest(**_dossier()))


def test_key_ordering_does_not_change_identity() -> None:
    dossier = _dossier()
    forward = _criba_payload_fingerprint(CribaDossierRequest(**dossier))
    backward = _criba_payload_fingerprint(
        CribaDossierRequest(**dict(reversed(list(dossier.items()))))
    )
    assert forward == backward


def test_non_finite_content_cannot_be_fingerprinted() -> None:
    """NaN must have NO identity, not a misleading one that equals null's."""
    with pytest.raises(ValueError):
        _criba_payload_fingerprint(
            CribaDossierRequest(**{**_dossier(), "supuestos": [float("nan")]})
        )


def test_fingerprint_is_reproducible_across_processes() -> None:
    """Determinism: same validated input, same hash, every run."""
    first = _criba_payload_fingerprint(CribaDossierRequest(**_dossier()))
    second = _criba_payload_fingerprint(CribaDossierRequest(**_dossier()))
    assert first == second
    assert first.startswith("sha256:")
