"""S06 integración: Shadow action -> T104/T111 -> MCDA consumer -> dossier.

Verifica que ``_build_ranking_rows`` (controller ShadowCRIBAintérprete) enriquece
cada idea sin ``value_score`` (ausente) con el score MCDA canónico producido por
el adapter (T104/T111 sobre corpus real), preservando el contrato None != 0.0.
"""
from __future__ import annotations

import json

from criba.ui.actions import _build_ranking_rows


def _packet_with_real_family() -> dict:
    """Packet minimal con un idea que lleva family resoluble del catalog real.

    No fabrica method_ids: el adapter resuelve por family (fallback canónico)
    sobre el catalog runtime ``criba.catalog.methods``.
    """
    return {
        "innovation": {
            "ideas": [
                {
                    "id": "idea-001",
                    "title": "innovacion de catalog real",
                    "description": "caso de integracion",
                    "family": "ciencia_realidad",  # familia real del corpus
                    "family1": "ciencia_realidad",
                    "family2": "",
                    "method_ids": [],  # ausencia real: el adapter resuelve por family
                    "convergence": {},  # sin value_score -> absent case
                }
            ]
        }
    }


def test_build_ranking_rows_produce_value_score_canónico_para_family_real() -> None:
    """Con family resoluble: value_score proviene del MCDA canónico, no de 0/0.5."""
    rows = _build_ranking_rows(_packet_with_real_family())
    assert len(rows) == 1
    row = rows[0]
    assert row["value_score"] is not None, "family real debe producir score MCDA"
    assert 0.0 <= row["value_score"] <= 1.0
    assert row["evaluada"] is True


def test_build_ranking_rows_adjunta_dossier_mcda_serializable() -> None:
    """El dossier MCDA se serializa (estado/procedencia) para readback/restart."""
    rows = _build_ranking_rows(_packet_with_real_family())
    mcda = rows[0]["mcda"]
    assert mcda is not None
    # serializable a JSON (persistencia Shadow)
    serialized = json.dumps(mcda)
    again = json.loads(serialized)
    assert {"composite", "coverage", "present_count", "dimensions", "unknown_dimensions"} <= set(again)
    # provenance de T104/T111 presente
    sources = [d["source"] for d in again["dimensions"] if d["source"]]
    assert "T104:corpus_confidence" in sources
    assert "T111:granularity_feasibility" in sources


def test_build_ranking_rows_preserva_value_score_existente() -> None:
    """Si el idea YA tiene value_score (proveniente externo), no se sobre-escribe."""
    packet = _packet_with_real_family()
    packet["innovation"]["ideas"][0]["convergence"] = {"value_score": 0.42}
    rows = _build_ranking_rows(packet)
    assert rows[0]["value_score"] == 0.42
    assert rows[0]["mcda"] is None  # no se regenera si ya existía


def test_build_ranking_rows_ausencia_real_no_es_cero() -> None:
    """Family inexistente: value_score None (ausencia), NUNCA 0.0 fabricado."""
    packet = {
        "innovation": {
            "ideas": [
                {"id": "x", "family": "familia_imposible_zzz", "method_ids": [],
                 "convergence": {}}
            ]
        }
    }
    rows = _build_ranking_rows(packet)
    assert rows[0]["value_score"] is None
    assert rows[0]["evaluada"] is False
    assert rows[0]["mcda"] is None


def test_build_ranking_rows_none_no_se_serializa_como_cero() -> None:
    """El absent value_score viaja como None a persistencia, no como 0.0 (contrato S05)."""
    packet = _packet_with_real_family()
    packet["innovation"]["ideas"][0]["family"] = "familia_imposible_zzz"
    rows = _build_ranking_rows(packet)
    row = rows[0]
    # JSON roundtrip: None persiste como null, no como 0.0
    rt = json.loads(json.dumps(row))
    assert rt["value_score"] is None
    assert rt["mcda"] is None
