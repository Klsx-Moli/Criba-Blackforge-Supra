"""Pruebas aisladas de IMP-05 — round-trip SUPRA del dossier de la campaña.

Aisladas: MockTransport (sin socket real), tmp_path (sin base productiva),
solo funciones existentes del cliente. No ejecutan runtime productivo.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx

from criba.integrations.supra_client import (
    SupraClient,
    SupraClientConfig,
    _dossier_payload_fingerprint,
    objective_from_dossier,
)

from lab.imp05_supra_roundtrip import (
    build_campaign_dossier,
    _mock_transport,
    run_roundtrip,
)


def test_dossier_lineage_is_complete() -> None:
    d = build_campaign_dossier()
    for field in ("dossier_id", "candidate_id", "claim_id", "mechanism_version", "protocol_version"):
        v = d[field]
        assert isinstance(v, str) and v.strip(), f"{field} debe ser texto no vacío"
    assert d["mechanism_version"].startswith("sha256:")
    assert d["protocol_version"].startswith("sha256:")


def test_fingerprint_is_canonical_sha256() -> None:
    d = build_campaign_dossier()
    fp = _dossier_payload_fingerprint(d)
    assert fp.startswith("sha256:") and len(fp) == 7 + 64


def test_roundtrip_preserves_double_identity(tmp_path: Path) -> None:
    receipt = run_roundtrip(tmp_path)
    # Doble identificado sobrevive el round-trip.
    assert receipt["integration_version"] == "criba-supra/1"
    assert receipt["payload_fingerprint"] == receipt["_expected_fingerprint"]
    assert receipt["payload_fingerprint"].startswith("sha256:")


def test_receipt_not_promoted_beyond_planning(tmp_path: Path) -> None:
    receipt = run_roundtrip(tmp_path)
    assert receipt["receipt_scope"] == "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"
    assert receipt["execution_status"] == "NOT_EXECUTED"
    assert receipt["scientific_status"] == "NOT_VALIDATED"


def test_lineage_matches_sent_dossier(tmp_path: Path) -> None:
    receipt = run_roundtrip(tmp_path)
    d = build_campaign_dossier()
    assert receipt["criba_dossier_id"] == d["dossier_id"]
    assert receipt["criba_candidate_id"] == d["candidate_id"]
    assert receipt["claim_id"] == d["claim_id"]
    assert receipt["mechanism_version"] == d["mechanism_version"]
    assert receipt["protocol_version"] == d["protocol_version"]


def test_evidence_written_to_temp_only(tmp_path: Path) -> None:
    run_roundtrip(tmp_path)
    p = tmp_path / "triz_supra_lab" / "dossier_sent.json"
    assert p.exists()
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["dossier_id"] == "ACADEMICO-TRIZ-INVENTIVA-20261028"


def test_blank_lineage_rejected_before_transport(tmp_path: Path) -> None:
    """El cliente rechaza lineage en blanco ANTES de tocar el transporte."""
    d = build_campaign_dossier()
    d["dossier_id"] = ""
    fp = _dossier_payload_fingerprint(d)
    client = SupraClient(
        SupraClientConfig(endpoint="http://127.0.0.1:8000"),
        transport=_mock_transport(fp),
    )
    raised = False
    try:
        client.run_project(objective=objective_from_dossier(d), criba_dossier=d)
    except ValueError:
        raised = True
    finally:
        client.close()
    assert raised, "lineage en blanco debe rechazarse antes del transporte"
