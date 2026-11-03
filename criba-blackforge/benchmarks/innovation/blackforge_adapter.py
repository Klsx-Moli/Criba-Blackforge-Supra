"""Adaptador real de la condición D_BLACKFORGE al motor compartido.

BLACKFORGE no es un prompt distinto: ejecuta la lotería sobre su catálogo
inmutable y el mismo selector diversity-aware que CRIBA. Esta ruta mide la
selección determinista y la estructura de los cruces, no la redacción del
modelo. La síntesis con modelo pertenece al producto (Shadow/BLACKFORGE) y a
las condiciones A_DIRECT/B_STRONG_PROMPT del harness.

Sin modelo, sin red y sin fabricar propuestas: los candidatos son cruces
estructurados con methods/classes/genome. Un cruce no es una propuesta validada.
"""

from __future__ import annotations

import copy
from typing import Any, cast

from benchmarks.innovation.criba_adapter import _opportunity_accounting


class BlackforgeResult:
    """Resultado explícito de D_BLACKFORGE para un episodio."""

    __slots__ = ("candidates", "selection_report")

    def __init__(
        self,
        candidates: list[dict[str, Any]],
        selection_report: dict[str, Any] | None = None,
    ) -> None:
        self.candidates = candidates
        self.selection_report = selection_report


def _idea_to_candidate(idea: dict[str, Any], index: int, seed: int) -> dict[str, Any]:
    """Map a BLACKFORGE lottery cross to the harness candidate contract."""
    classes = [str(value) for value in (idea.get("class1"), idea.get("class2")) if value]
    methods = [str(value) for value in (idea.get("method1"), idea.get("method2")) if value]
    family = str(idea.get("family") or idea.get("family1") or "")
    if not family:
        family = classes[0] if classes else "unknown"
    genome = idea.get("genome")
    if not isinstance(genome, dict) or not genome:
        genome = {"mechanism": [], "classes": classes}
    return {
        "idea_id": f"bf-{seed}-{index:02d}",
        "title": str(idea.get("title") or ""),
        "description": str(idea.get("description") or ""),
        "score": float(idea.get("score", 0.0) or 0.0),
        "genome": genome,
        "family": family,
        "methods": methods,
        "classes": classes,
        "source": "BLACKFORGE",
        "mode": idea.get("mode"),
        "prueba_concreta": None,
    }


def run_blackforge_selection(
    problema_texto: str,
    seed: int,
    n_candidatos: int,
    *,
    mode: str = "optimized",
    records: list[dict[str, Any]] | None = None,
) -> BlackforgeResult:
    """Ejecuta la ruta determinista de BLACKFORGE y devuelve candidatos + informe.

    ``mode`` usa los mismos modos que la UI (optimized/associative/pure/
    alternating/stratified). ``records`` permite inyectar el catálogo en
    pruebas; por defecto se usa el catálogo BLACKFORGE real.
    """
    from criba.blackforge_catalog import records as bf_records
    from criba.diversity_selector import select_finalists
    from criba.lottery import LotteryEngine

    source = records if records is not None else bf_records()
    methods = [dict(record) for record in source]
    if len(methods) < 2:
        raise ValueError("BLACKFORGE requiere al menos dos métodos")
    engine = LotteryEngine.from_methods(methods, seed=seed)
    engine.run_round(
        mode,
        batch_size=max(8, int(n_candidatos) * 2),
        query=problema_texto,
    )
    pool = engine.get_top_ideas(max(8, int(n_candidatos) * 4))
    finalists, report = select_finalists(pool, int(n_candidatos))
    selection_report = dict(report or {})
    selection_report["pipeline"] = "blackforge_fn"
    selection_report["opportunity_accounting"] = _opportunity_accounting(engine, pool, finalists)
    candidates = [
        _idea_to_candidate(idea, index, seed)
        for index, idea in enumerate(finalists[: max(0, int(n_candidatos))])
    ]
    return BlackforgeResult(copy.deepcopy(candidates), copy.deepcopy(selection_report))


def blackforge_fn(problema_texto: str, seed: int, n_candidatos: int) -> list[dict[str, Any]]:
    """Contrato heredado: sólo candidatos, sin informe atribuible."""
    return run_blackforge_selection(problema_texto, seed, n_candidatos).candidates


def coerce_result(result: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Normaliza BlackforgeResult, tuplas o listas sin heredar informes ajenos."""
    if isinstance(result, BlackforgeResult):
        report = result.selection_report
        if report is None:
            return result.candidates, {
                "instrumented": False,
                "status": "REPORT_UNAVAILABLE",
                "reason": "blackforge_fn_callback_did_not_supply_selection_report",
            }
        return result.candidates, report
    from benchmarks.innovation.criba_adapter import _coerce_result

    candidates, report = _coerce_result(result)
    return cast(list[dict[str, Any]], candidates), report
