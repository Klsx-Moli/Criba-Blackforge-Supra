"""Semantic identity of the CRIBA->SUPRA dossier envelope.

The envelope fingerprint decides whether a retried request is the SAME
causal work (safe idempotent replay) or DIFFERENT work (409 conflict).
`exclude_unset=True` bases that identity on which keys the client happened to
serialize, not on the validated content: two payloads that mean exactly the
same thing got different fingerprints, so a legitimate retry was rejected as
a conflict.

Contract:

    same validated semantics   -> same fingerprint
    real semantic difference   -> different fingerprint

`creado_at` stays outside identity: it is non-semantic metadata.
"""

from __future__ import annotations

import unicodedata
from typing import Any

import pytest
from supra_agentic.service import (
    CreateProjectRequest,
    CribaDossierRequest,
    _criba_payload_fingerprint,
)

BASE_PROTOCOL: dict[str, Any] = {
    "afirmacion_decisiva": "The intervention changes the observable",
    "alternativa_explicativa": "Thermal drift from ambient variation",
    "intervencion_prueba": "Run calibrated and baseline arms",
    "observable": "temperature-adjusted error",
    "resultado_favorable_mecanismo": "error falls inside the bound",
    "resultado_favorable_alternativa": "error tracks ambient temperature",
    "regla_decision": "Adopt if error is bounded under calibration",
    "condicion_fracaso": "error tracks ambient instead of the mechanism",
}


def _dossier(**overrides: Any) -> CribaDossierRequest:
    payload: dict[str, Any] = {
        "dossier_id": "dossier-1",
        "candidate_id": "cand-1",
        "claim_id": "claim-1",
        "protocol_version": "sha256:" + "a" * 64,
        "mechanism_version": "sha256:" + "b" * 64,
        "problema": "Reduce thermal drift",
        "hipotesis": "A bounded calibration loop reduces drift",
        "mecanismo": "Closed-loop correction",
        "estado": "SUPRA_EJECUCION_PENDIENTE",
        "prueba_discriminante": dict(BASE_PROTOCOL),
    }
    protocol_overrides = overrides.pop("prueba_discriminante", None)
    payload.update(overrides)
    if protocol_overrides is not None:
        payload["prueba_discriminante"] = {
            **BASE_PROTOCOL,
            **protocol_overrides,
        }
    return CribaDossierRequest(**payload)


def test_omitted_and_explicit_defaults_share_one_fingerprint() -> None:
    omitted = _criba_payload_fingerprint(_dossier())
    explicit = _criba_payload_fingerprint(
        _dossier(
            run_id="",
            bloqueo="",
            origen_bloqueo="",
            evidence_delivered=[],
            evidence_documented_as_used=[],
            evidencia_utilizada=[],
            supuestos=[],
            creado_at="",
        )
    )
    assert omitted == explicit


def test_omitted_and_explicit_nested_defaults_share_one_fingerprint() -> None:
    omitted = _criba_payload_fingerprint(_dossier())
    explicit = _criba_payload_fingerprint(
        _dossier(
            prueba_discriminante={
                "comparacion": "",
                "metrica": "",
                "coste_permisos": "",
                "estado_prueba": "NO_EJECUTADA",
            }
        )
    )
    assert omitted == explicit


def test_fingerprint_is_independent_of_field_ordering() -> None:
    ordered = _dossier()
    reversed_input = CribaDossierRequest.model_validate(
        dict(reversed(list(ordered.model_dump().items())))
    )
    assert _criba_payload_fingerprint(ordered) == _criba_payload_fingerprint(
        reversed_input
    )


def test_every_semantic_field_change_changes_the_fingerprint() -> None:
    baseline = _criba_payload_fingerprint(_dossier())
    changes: list[dict[str, Any]] = [
        {"dossier_id": "dossier-2"},
        {"candidate_id": "cand-2"},
        {"claim_id": "claim-2"},
        {"protocol_version": "sha256:" + "c" * 64},
        {"mechanism_version": "sha256:" + "d" * 64},
        {"problema": "A different problem statement"},
        {"bloqueo": "A declared blocking condition"},
        {"origen_bloqueo": "reviewer"},
        {"hipotesis": "A different hypothesis"},
        {"mecanismo": "A different mechanism"},
        {"run_id": "run-9"},
        {"prueba_discriminante": {"observable": "a different observable"}},
        {
            "prueba_discriminante": {
                "regla_decision": "adopt only if the bound holds twice"
            }
        },
        {
            "prueba_discriminante": {
                "condicion_fracaso": "the observable does not discriminate"
            }
        },
        {
            "prueba_discriminante": {
                "resultado_favorable_mecanismo": "a different favourable outcome"
            }
        },
        {
            "prueba_discriminante": {
                "alternativa_explicativa": "a different rival explanation"
            }
        },
    ]
    for change in changes:
        assert _criba_payload_fingerprint(_dossier(**change)) != baseline, change


def test_evidence_lists_participate_in_identity() -> None:
    baseline = _criba_payload_fingerprint(_dossier())
    with_evidence = _criba_payload_fingerprint(
        _dossier(evidence_delivered=[{"id": "e1", "claim": "measured"}])
    )
    assert with_evidence != baseline

    reordered = _criba_payload_fingerprint(
        _dossier(
            evidence_delivered=[
                {"id": "e1", "claim": "measured"},
                {"id": "e2", "claim": "controlled"},
            ]
        )
    )
    different = _criba_payload_fingerprint(
        _dossier(
            evidence_delivered=[
                {"id": "e2", "claim": "controlled"},
                {"id": "e1", "claim": "measured"},
            ]
        )
    )
    # A list is ordered content: reordering evidence is a semantic change.
    assert reordered != different


def test_creado_at_is_not_part_of_identity() -> None:
    baseline = _criba_payload_fingerprint(_dossier())
    stamped = _criba_payload_fingerprint(_dossier(creado_at="2026-01-01T00:00:00Z"))
    assert baseline == stamped


def test_unicode_normalization_is_not_implicit() -> None:
    """Equivalent-looking text with different code points stays distinct.

    The payload is transmitted and persisted as given; silently folding NFC
    into NFD would make the fingerprint describe bytes the system never saw.
    """
    composed = _criba_payload_fingerprint(_dossier(hipotesis="café"))
    decomposed = _criba_payload_fingerprint(
        _dossier(hipotesis=unicodedata.normalize("NFD", "café"))
    )
    assert composed != decomposed
    assert _criba_payload_fingerprint(_dossier(hipotesis="café")) == composed


def test_fingerprint_is_reproducible_across_processes() -> None:
    """Same validated semantics -> same fingerprint, independent of history."""
    first = _criba_payload_fingerprint(_dossier())
    other = _criba_payload_fingerprint(
        _dossier(run_id="", bloqueo="", origen_bloqueo="", creado_at="")
    )
    assert first == other
    assert first.startswith("sha256:")
    assert len(first) == len("sha256:") + 64


def test_retried_request_with_explicit_defaults_is_not_a_conflict() -> None:
    """A semantically identical retry must survive the envelope validator."""
    dossier = _dossier()
    explicit = _dossier(
        run_id="",
        bloqueo="",
        origen_bloqueo="",
        evidence_delivered=[],
        evidence_documented_as_used=[],
        evidencia_utilizada=[],
        supuestos=[],
        creado_at="",
    )
    first = CreateProjectRequest(
        objective="Reduce thermal drift",
        project_id="fp-1",
        criba_dossier=dossier,
        criba_integration_version="criba-supra/1",
        criba_payload_fingerprint=_criba_payload_fingerprint(dossier),
    )
    second = CreateProjectRequest(
        objective="Reduce thermal drift",
        project_id="fp-1",
        criba_dossier=explicit,
        criba_integration_version="criba-supra/1",
        criba_payload_fingerprint=_criba_payload_fingerprint(explicit),
    )
    assert first.criba_payload_fingerprint == second.criba_payload_fingerprint


def test_genuinely_changed_payload_still_produces_a_different_fingerprint() -> None:
    original = _criba_payload_fingerprint(_dossier())
    changed = _criba_payload_fingerprint(_dossier(hipotesis="a different claim"))
    assert changed != original


def test_envelope_validator_rejects_a_fingerprint_that_does_not_match() -> None:
    dossier = _dossier()
    with pytest.raises(ValueError, match="fingerprint mismatch"):
        CreateProjectRequest(
            objective="Reduce thermal drift",
            project_id="fp-2",
            criba_dossier=dossier,
            criba_integration_version="criba-supra/1",
            criba_payload_fingerprint="sha256:" + "0" * 64,
        )


def test_non_finite_content_cannot_be_fingerprinted() -> None:
    """NaN/Infinity must not be silently canonicalized into an identity.

    ``json.dumps(allow_nan=False)`` refuses them. A dossier carrying a
    non-finite number therefore has no fingerprint at all, instead of one that
    depends on the interpreter's NaN repr. Folding them into ``None`` would be
    worse: it would make "not representable" and "absent" the same payload.
    """
    dossier = _dossier(evidence_delivered=[{"value": float("nan")}])
    with pytest.raises(ValueError):
        _criba_payload_fingerprint(dossier)

    infinite = _dossier(evidence_delivered=[{"value": float("inf")}])
    with pytest.raises(ValueError):
        _criba_payload_fingerprint(infinite)

    absent = _dossier(evidence_delivered=[{"value": None}])
    assert _criba_payload_fingerprint(absent).startswith("sha256:")
