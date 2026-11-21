"""Fixture generator for synthetic evidence injection in E2E tests.

Produces an in-memory IntelligenceStore populated with observational documents
relevant to the test problem ("reducir el consumo de agua en el riego agricola").
This lets the interpreter reason over explicit observations rather than
formulating hypotheses from a bare abstract problem statement.

Retrieval is a bounded lexical FTS5 match (see
``criba.intelligence.evidence_context``): it selects documents whose title or
abstract share tokens with the query, so the fixture MUST use the same language
and vocabulary as the query. An English fixture is invisible to a Spanish
query, the retrieved context is empty, and the interpreter then abstains for
lack of evidence -- a correct Anti-Goodhart outcome, not a bug in the
interpreter. The fix is to supply discriminating evidence, never to force a
proposal.

The documents are ordered by epistemic role:

* ``obs-001`` baseline: quantitative steady state (input flow, line pressure,
  soil moisture, reference evapotranspiration) under daytime flood irrigation.
* ``obs-002`` anomaly: a controlled deficit protocol with magnitude, unit,
  window and experimental condition, plus its explicit measurement.
* ``obs-003`` discriminator: identical applied volume under two timings, the
  contrast that separates H1 (temporal separation of application from peak
  solar radiation) from H2 (total applied volume alone).

No document asserts demonstrated causality. Each states which observed pattern
is COMPATIBLE with a hypothesis and which pattern would WEAKEN it. Content is
intentionally realistic but fictional; it is not production data and it is not
independently validated evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from criba.intelligence.storage.store import IntelligenceStore

_RETRIEVED_AT = "2026-10-17T16:53:00Z"
_NAMESPACE = "agriculture.water.irrigation"
_OBS_SCHEMA = "criba.observation.v1"
_EPISTEMIC_STATUS = "SOURCE_CONTENT_NOT_INDEPENDENTLY_VALIDATED"


def _provenance(doc_id: str) -> dict[str, Any]:
    return {
        "source_id": "synthetic_e2e_fixture",
        "doc_id": doc_id,
        "retrieved_at": _RETRIEVED_AT,
        "scientific_validation": _EPISTEMIC_STATUS,
    }


def _metadata(obs_type: str, observation_id: str, **extra: Any) -> dict[str, Any]:
    return {
        "obs_type": obs_type,
        "obs_schema": _OBS_SCHEMA,
        "namespace": _NAMESPACE,
        "observation_id": observation_id,
        **extra,
    }


_EVIDENCE_DOCS: list[dict[str, Any]] = [
    {
        "doc_id": "obs-agriculture-water-001",
        "observation_id": "obs-001",
        "source_id": "synthetic_e2e_fixture",
        "title": (
            "Consumo de agua en riego agricola: linea base de caudal, presion y humedad "
            "del suelo"
        ),
        "abstract": (
            "Linea base observada en 8 parcelas de riego agricola por gravedad durante "
            "julio-septiembre de 2025, con riego diurno continuo de 09:00 a 17:00. El "
            "caudal de entrada medido fue 2.4 L/s con desviacion 0.1 L/s usando contador "
            "volumetrico; la presion en linea fue 2.8 bar; la humedad del suelo a 0-30 cm "
            "fue 18.0 por ciento sobre una capacidad de campo de 22 por ciento; la "
            "evapotranspiracion de referencia fue 4.2 mm/dia. El volumen aplicado medio fue "
            "6.1 mm/dia por parcela. La demanda hidrica del cultivo, estimada por balance "
            "hidrico del suelo, se mantuvo estable durante toda la ventana. Estos valores "
            "definen el consumo de agua esperado bajo el protocolo de riego diurno continuo "
            "y sirven como comparacion para cualquier cambio de horario o de volumen "
            "aplicado. Son observaciones de linea base: no establecen por si mismas la causa "
            "de ninguna perdida."
        ),
        "url": "https://fixture.local/obs/agriculture-water-001",
        "published": "2026-10-15",
        "language": "es",
        "epistemic_status": _EPISTEMIC_STATUS,
        "provenance": _provenance("obs-agriculture-water-001"),
        "metadata": _metadata(
            "baseline",
            "obs-001",
            volume_applied_mm_per_day=6.1,
            inflow_l_per_s=2.4,
            line_pressure_bar=2.8,
            soil_moisture_pct=18.0,
            reference_et_mm_per_day=4.2,
            experimental_condition="riego diurno continuo 09:00-17:00",
        ),
    },
    {
        "doc_id": "obs-agriculture-water-002",
        "observation_id": "obs-002",
        "source_id": "synthetic_e2e_fixture",
        "title": (
            "Riego deficitario intermitente reduce el consumo de agua agricola sin perdida "
            "de rendimiento: medicion de humedad del suelo"
        ),
        "abstract": (
            "Ensayo de campo comparativo en 3 regiones durante 2024 con n=15 parcelas. El "
            "protocolo de riego deficitario intermitente aplico el mismo caudal de entrada "
            "de 2.4 L/s que la linea base, con ciclos de supresion de 48 a 72 horas. El "
            "consumo de agua agricola medido cayo entre 28 y 42 por ciento respecto al riego "
            "continuo; la humedad del suelo a 0-30 cm fue 12.0 por ciento en la rama "
            "deficitaria frente a 18.0 por ciento en la continua. El rendimiento no mostro "
            "reduccion estadisticamente detectable en la ventana observada. La "
            "evapotranspiracion de referencia del periodo fue 4.1 mm/dia, comparable a la "
            "linea base, de modo que el descenso de consumo no se explica por una menor "
            "demanda atmosferica. Este patron es COMPATIBLE con una menor perdida por "
            "percolacion profunda bajo deficit controlado; seria DEBILITADO si el rendimiento "
            "hubiera caido de forma proporcional al recorte de volumen aplicado."
        ),
        "url": "https://fixture.local/obs/agriculture-water-002",
        "published": "2026-10-15",
        "language": "es",
        "epistemic_status": _EPISTEMIC_STATUS,
        "provenance": _provenance("obs-agriculture-water-002"),
        "metadata": _metadata(
            "anomaly",
            "obs-002",
            consumption_reduction_pct_range=[28, 42],
            soil_moisture_deficit_pct=12.0,
            soil_moisture_control_pct=18.0,
            suppression_cycles_h=[48, 72],
            reference_et_mm_per_day=4.1,
            experimental_condition="mismo caudal de entrada, supresion 48-72 h",
        ),
    },
    {
        "doc_id": "obs-agriculture-water-003",
        "observation_id": "obs-003",
        "source_id": "synthetic_e2e_fixture",
        "title": (
            "Riego nocturno frente a riego diurno a igual volumen aplicado: contraste "
            "temporal de evaporacion en riego agricola"
        ),
        "abstract": (
            "Contraste controlado en 12 parcelas pareadas durante agosto de 2025. Ambas "
            "ramas aplicaron el MISMO volumen de 6.0 mm/dia y el mismo caudal de entrada de "
            "2.4 L/s; solo cambio el horario, 22:00 a 06:00 frente a 09:00 a 17:00. La "
            "perdida por evaporacion medida en la rama nocturna fue 32 por ciento menor que "
            "en la diurna, 1.7 mm/dia frente a 2.5 mm/dia, con humedad del suelo a 0-30 cm de "
            "18.2 y 18.0 por ciento respectivamente y presion en linea de 2.8 bar en ambas "
            "ramas. Como el volumen aplicado fue identico, la diferencia de evaporacion no "
            "puede atribuirse al volumen total. H1 sostiene que el ahorro depende de la "
            "separacion temporal entre la aplicacion y la radiacion solar maxima; el patron "
            "de igual volumen con distinta evaporacion es COMPATIBLE con H1. H2 sostiene que "
            "el ahorro depende unicamente del volumen total aplicado; ese patron DEBILITA H2 "
            "como explicacion unica, porque el volumen se mantuvo constante entre ramas. Un "
            "resultado que DEBILITARIA H1 seria evaporacion y consumo iguales entre dia y "
            "noche a volumen controlado. Este contraste no demuestra causalidad: no se aislo "
            "el efecto de la temperatura del suelo ni el de la velocidad del viento."
        ),
        "url": "https://fixture.local/obs/agriculture-water-003",
        "published": "2026-10-15",
        "language": "es",
        "epistemic_status": _EPISTEMIC_STATUS,
        "provenance": _provenance("obs-agriculture-water-003"),
        "metadata": _metadata(
            "discriminator",
            "obs-003",
            hypotheses_compared=["H1_separacion_temporal", "H2_volumen_total"],
            evaporation_night_mm_per_day=1.7,
            evaporation_day_mm_per_day=2.5,
            evaporation_reduction_pct=32,
            applied_volume_mm_per_day=6.0,
            inflow_l_per_s=2.4,
            experimental_condition="mismo volumen y caudal; horario 22:00-06:00 vs 09:00-17:00",
        ),
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

    ``tmp_path`` may be a directory (the store database is created inside it)
    or the database path itself; the parent directory is created if missing.
    """
    tmp_path = Path(tmp_path)
    db_path = tmp_path / "evidence_store.sqlite3" if tmp_path.is_dir() else tmp_path
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
