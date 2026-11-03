from __future__ import annotations

import pytest

from criba.evidence_modes import (
    apply_evidence_mode,
    evidence_banner,
    evidence_status,
    get_evidence_mode,
)
from criba.ui.proposal_view import format_proposal


def _sheet() -> dict:
    return {
        "query": "problema sintetico",
        "entries": [
            {
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "Hipotesis",
                "mecanismo": "Mecanismo",
            }
        ],
    }


def test_unknown_mode_is_rejected() -> None:
    with pytest.raises(ValueError):
        get_evidence_mode("inventado")


def test_modes_are_distinct_and_creative_is_not_validated() -> None:
    creative = get_evidence_mode("creative")
    exploratory = get_evidence_mode("exploratory")
    validated = get_evidence_mode("validated")

    assert creative.status == "NO VALIDADO"
    assert exploratory.status == "NO VALIDADO"
    assert validated.status == "VALIDACIÓN PENDIENTE"
    assert validated.requires_supra_pass is True
    assert creative.requires_supra_pass is False


def test_apply_mode_copies_sheet_and_entries() -> None:
    original = _sheet()
    applied = apply_evidence_mode(original, "exploratory")

    assert applied is not original
    assert applied["entries"][0] is not original["entries"][0]
    assert original["entries"][0].get("evidence_mode") is None
    assert applied["evidence_mode"] == "exploratory"
    assert applied["entries"][0]["evidence_mode"] == "exploratory"
    assert applied["evidence_status"] == "NO VALIDADO"


def test_validated_mode_is_pending_until_supra_pass() -> None:
    entry = {"evidence_mode": "validated"}
    assert evidence_status(entry) == "VALIDACIÓN PENDIENTE"
    assert "VALIDACIÓN PENDIENTE" in evidence_banner(entry)
    assert "Validado" not in evidence_banner(entry).splitlines()[0]
    entry["verification_status"] = "PASS"
    assert evidence_status(entry) == "VALIDADO"


def test_format_proposal_renders_each_mode_without_promoting_it() -> None:
    creative = _sheet()["entries"][0]
    creative["evidence_mode"] = "creative"
    text = format_proposal(creative)
    assert "MODO CREATIVO · NO VALIDADO" in text
    assert "no comprobadas" in text

    exploratory = _sheet()["entries"][0]
    exploratory["evidence_mode"] = "exploratory"
    text = format_proposal(exploratory)
    assert "MODO EXPLORATORIO · NO VALIDADO" in text
    assert "no es evidencia" in text

    validated = _sheet()["entries"][0]
    validated["evidence_mode"] = "validated"
    text = format_proposal(validated)
    assert "MODO VALIDADO · VALIDACIÓN PENDIENTE" in text
    assert "verification PASS" in text


def test_legacy_entries_default_to_creative() -> None:
    text = format_proposal(_sheet()["entries"][0])
    assert "MODO CREATIVO · NO VALIDADO" in text
    assert "Propuesta creativa" in text
