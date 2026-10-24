"""F5 — regresión: el informe completo de selección debe llegar al artefacto por episodio.

RED antes del fix (verificado 2026-10-22, `criba-blackforge/.venv` Python 3.11.15):
`run_condition("C_CRIBA", ..., criba_fn=criba_fn)` persistía un record sin
`pool_size`, `valid_size`, `quality_floor`, `discarded_by_floor`, `tie_sets` ni
`opportunity_accounting`. La información existía en memoria (el `report` de
`select_finalists`) pero se descartaba en `criba_adapter.criba_fn`.

Tras el fix, el contrato instrumentado es `run_criba_selection` (devuelve
`CribaResult` con candidatos + informe ligados). El contrato heredado
`criba_fn` (lista) declara REPORT_UNAVAILABLE.
"""
from __future__ import annotations

import json

from benchmarks.innovation.criba_adapter import criba_fn, run_criba_selection
from benchmarks.innovation.harness import exportar, run_condition

_PROBLEMA = {
    "id": "G01",
    "texto": "Detectar abuso de permisos en agentes de software autónomos",
}

REQUIRED_REPORT_KEYS = (
    "pool_size",
    "valid_size",
    "quality_floor",
    "discarded_by_floor",
    "tie_sets",
    "opportunity_accounting",
)


def test_selection_report_survives_to_persisted_artifact(tmp_path) -> None:
    """El informe completo de selección debe estar en el artefacto por episodio."""
    record = run_condition(
        "C_CRIBA", _PROBLEMA, seed=7, n_candidatos=4, criba_fn=run_criba_selection
    )
    assert record["status"] == "OK"

    out = exportar({"runs": [record]}, tmp_path / "episode.json")
    persisted = json.loads(out.read_text(encoding="utf-8"))

    blob = json.dumps(persisted, ensure_ascii=False)
    for key in REQUIRED_REPORT_KEYS:
        assert key in blob, (
            f"F5: el artefacto persistido pierde '{key}' del informe de selección"
        )


def test_selection_report_is_structured_not_free_text(tmp_path) -> None:
    """El informe debe ser un objeto recuperable, no una cadena incrustada."""
    record = run_condition(
        "C_CRIBA", _PROBLEMA, seed=7, n_candidatos=4, criba_fn=run_criba_selection
    )
    report = record["selection_report"]
    assert isinstance(report, dict), "el informe debe ser un objeto recuperable"
    for key in REQUIRED_REPORT_KEYS:
        assert key in report, f"F5: el informe no contiene '{key}'"
    assert isinstance(report["discarded_by_floor"], list)
    assert isinstance(report["tie_sets"], list)


def test_legacy_criba_fn_declares_report_unavailable() -> None:
    """El contrato heredado no aporta informe: REPORT_UNAVAILABLE explícito."""
    record = run_condition(
        "C_CRIBA", _PROBLEMA, seed=7, n_candidatos=4, criba_fn=criba_fn
    )
    assert record["selection_report"]["status"] == "REPORT_UNAVAILABLE"
    assert "pool_size" not in record["selection_report"]


def test_criba_fn_signature_unchanged() -> None:
    """El contrato público de criba_fn (texto, seed, n) no cambia."""
    import inspect

    sig = inspect.signature(criba_fn)
    assert list(sig.parameters) == ["problema_texto", "seed", "n_candidatos"]
