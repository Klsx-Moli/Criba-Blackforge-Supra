"""Fixture generator for synthetic evidence injection in E2E tests.

Produces an in-memory IntelligenceStore populated with observational documents
relevant to the test problem ("reducir el consumo de agua en el riego agricola").
This lets the interpreter reason over explicit observations rather than
formulating hypotheses from a bare abstract problem statement.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from criba.intelligence.storage.store import IntelligenceStore


_EVIDENCE_DOCS: list[dict[str, Any]] = [
    {
        "doc_id": "obs-agriculture-water-001",
        "observation_id": "obs-001",
        "source_id": "synthetic_e2e_fixture",
        "title": "Water table decline and night irrigation evaporation reduction",
        "abstract": (
            "Observational studies from 2023-2025 document a 0.4 m/year decline "
            "in the water table across 12 agricultural valleys. Ground-penetrating "
            "radar surveys show soil moisture depletion at 0-30 cm depth during "
            "peak irrigation months (April-September). The correlation between "
            "continuous flood irrigation and water table decline is r=0.78 "
            "(p<0.001)."
        ),
        "url": "https://fixture.local/obs/agriculture-water-001",
        "published": "2026-10-15",
        "epistemic_status": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        "provenance": {
            "source_id": "synthetic_e2e_fixture",
            "retrieved_at": "2026-10-17T16:53:00Z",
            "scientific_validation": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        },
    },
    {
        "doc_id": "obs-agriculture-water-002",
        "observation_id": "obs-002",
        "source_id": "synthetic_e2e_fixture",
        "title": "Soil cracking patterns under deficit irrigation vs. continuous flooding",
        "abstract": (
            "Field trials in 2024 across 3 regions show that intermittent deficit "
            "irrigation reduces water consumption by 28-42% compared to continuous "
            "flooding, without yield reduction. Soil cracking was observed within "
            "48-72 hours after flood recession, indicating deep percolation loss "
            "of 12-18% of applied water under continuous flooding protocols. "
            "Measured soil moisture: 12% (deficit) vs 18% (continuous flood)."
        ),
        "url": "https://fixture.local/obs/agriculture-water-002",
        "published": "2026-10-15",
        "epistemic_status": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        "provenance": {
            "source_id": "synthetic_e2e_fixture",
            "retrieved_at": "2026-10-17T16:53:00Z",
            "scientific_validation": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        },
    },
    {
        "doc_id": "obs-agriculture-water-003",
        "observation_id": "obs-003",
        "source_id": "synthetic_e2e_fixture",
        "title": "Temporal separation of irrigation cycles and evaporation reduction",
        "abstract": (
            "Experimental data from 15 farms shows that shifting irrigation to "
            "night-time hours (22:00-06:00) reduces evaporation losses by 32% "
            "compared to daytime irrigation. The temporal separation between "
            "application and peak solar radiation is the primary causal factor. "
            "Soil temperature differentials drive capillary action differently "
            "under separated vs. synchronized timing."
        ),
        "url": "https://fixture.local/obs/agriculture-water-003",
        "published": "2026-10-15",
        "epistemic_status": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        "provenance": {
            "source_id": "synthetic_e2e_fixture",
            "retrieved_at": "2026-10-17T16:53:00Z",
            "scientific_validation": "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED",
        },
    },
]


def load_synthetic_evidence_schema() -> dict[str, Any]:
    """Load the synthetic evidence schema fixture for E2E tests."""
    fixture_path = Path(__file__).resolve().parents[2] / "fixtures" / "e2e-synthetic-evidence-schema.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def build_evidence_store(tmp_path: Path) -> IntelligenceStore:
    """Create an IntelligenceStore with synthetic observational documents.

    This store can be passed to invent(store=...) so the interpreter
    receives local evidence about water-agriculture observations.
    """
    import tempfile

    db_path = tmp_path / "evidence_store.sqlite3"
    store = IntelligenceStore(str(db_path))
    store.save_documents(_EVIDENCE_DOCS)
    return store


def assert_valid_proposal(response: dict[str, Any], fixture: dict[str, Any]) -> None:
    """Validate an E2E proposal response against the evidence schema contract."""
    assert response["proposal"] is not None, "la propuesta no debe ser None con evidencia suficiente"
    assert 0.0 <= response["confidence"] <= 1.0
    assert response["confidence"] >= fixture["expected_behavior"]["minimum_confidence"]
    assert set(response["evidence_ids"]).issubset(
        {o["observation_id"] for o in fixture["observations"]}
    )
    assert response["risks"], "debe identificar riesgos"
    assert response["verification_steps"], "debe definir pasos de verificacion"


def assert_abstention_or_request(response: dict[str, Any]) -> None:
    """Validate that a no-evidence response is an honest abstention or request."""
    if response.get("proposal") is None:
        assert response.get("requested_evidence"), "debe solicitar evidencia cuando se abstiene"
    else:
        assert response["confidence"] < 0.6, "confianza debe ser baja sin evidencia"
