"""Adaptador real de la condición C_CRIBA al LOOP de CRIBA (hallazgo 6).

C_CRIBA no es un prompt distinto: ejecuta el pipeline real — lotería
estratificada + selector diversity-aware sobre el catálogo de métodos — con la
semilla propagada (reproducible). Es lo que el harness necesita para que la
comparación mida a CRIBA y no a un texto de prompt.

Sin LLM: produce candidatos ESTRUCTURADOS (cruce de métodos + genoma), no
prosa interpretada. La interpretación por modelo pertenece a las condiciones
A_DIRECT/B_STRONG_PROMPT vía model_fn; medir CRIBA es medir su selección
determinista y su diversidad de mecanismos, no su redacción.
"""
from __future__ import annotations

import copy
from typing import Any


class CribaResult:
    """Resultado explícito de la condición C_CRIBA para un episodio.

    Vincula candidatos e informe de selección a la MISMA invocación: el harness
    recoge el informe del objeto devuelto, no de un estado de módulo. Un
    callback que devuelve la lista heredada no puede atribuir un informe ajeno.
    """

    __slots__ = ("candidates", "selection_report")

    def __init__(self, candidates: list[dict[str, Any]],
                 selection_report: dict[str, Any] | None = None) -> None:
        self.candidates = candidates
        self.selection_report = selection_report


def _opportunity_accounting(engine: Any, pool: list[dict[str, Any]],
                          finalists: list[dict[str, Any]]) -> dict[str, Any]:
    """Contabilidad de esta ruta, declarada explícitamente.

    El productor de ``invent()`` no se ejecuta en el adaptador: los campos
    desconocidos se declaran (nunca se convierten en cero implícito) y
    ``budget_complete`` queda en ``False`` si hay costes no medidos.
    """
    return {
        "generated_candidates": len(engine.all_ideas),
        "selection_candidates_considered": len(pool),
        "initial_finalists": len(finalists),
        "candidate_development_attempts": 0,
        "replacement_attempts": 0,
        "finalists": len(finalists),
        "provider_model_requests": 0,
        "provider_model_requests_authoritative": True,
        "provider_model_requests_scope": "CANDIDATE_PROPOSAL_AND_CRITIC_ONLY",
        "evaluation_calls_authoritative": False,
        "budget_complete": False,
        "scope": "LOCAL_PIPELINE_ACCOUNTING_ONLY",
    }


def _coerce_result(result: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Separa candidatos e informe del valor devuelto por ``criba_fn``.

    - ``CribaResult`` -> usa su ``selection_report`` (puede ser ``None``).
    - ``tuple`` ``(candidates, report)`` -> usa el report del par.
    - lista (contrato heredado) -> ``REPORT_UNAVAILABLE`` explícito; **nunca**
      hereda el informe de otra invocación.
    """
    if isinstance(result, CribaResult):
        candidates, report = result.candidates, result.selection_report
    elif isinstance(result, tuple) and len(result) == 2:
        candidates, report = result[0], result[1]
    else:
        candidates, report = result, None
    if report is None:
        return candidates, {
            "instrumented": False,
            "status": "REPORT_UNAVAILABLE",
            "reason": "criba_fn_callback_did_not_supply_selection_report",
        }
    return candidates, report


def run_criba_selection(problema_texto: str, seed: int,
                        n_candidatos: int) -> CribaResult:
    """Ejecuta el loop de selección y devuelve candidatos + informe ligados.

    El informe se construye en esta misma invocación: no hay estado de módulo
    del que otro episodio pueda leer.
    """
    from criba.catalog import methods as catalog_methods
    from criba.diversity_selector import select_finalists
    from criba.lottery import LotteryEngine

    engine = LotteryEngine.from_methods(catalog_methods(), seed=seed)
    engine.run_round(mode="stratified", batch_size=max(8, n_candidatos * 2),
                     query=problema_texto)
    pool = engine.get_top_ideas(max(n_candidatos * 4, 8))
    finalists, report = select_finalists(pool, n_candidatos)
    selection_report = dict(report or {})
    selection_report["opportunity_accounting"] = _opportunity_accounting(
        engine, pool, finalists
    )
    # El getter se (re)escribe SOLO aquí, por esta invocación. Cualquier otro
    # camino (criba_fn heredado, excepción, callback alternativo) deja el getter
    # vacío, de modo que no puede atribuirse un informe ajeno.
    _LAST_SELECTION_REPORT.clear()
    _LAST_SELECTION_REPORT["report"] = copy.deepcopy(selection_report)
    out: list[dict[str, Any]] = []
    for idx, idea in enumerate(finalists):
        out.append({
            "idea_id": str(idea.get("idea_id") or f"criba-{seed}-{idx:02d}"),
            "title": str(idea.get("title", "")),
            "description": str(idea.get("description", "")),
            "score": float(idea.get("score", 0.0)),
            "genome": idea.get("genome") or {},
            "family": idea.get("family") or "",
            "methods": [idea.get("method1", ""), idea.get("method2", "")],
            "classes": [idea.get("class1", ""), idea.get("class2", "")],
        })
    return CribaResult(out, selection_report)


def criba_fn(problema_texto: str, seed: int, n_candidatos: int) -> list[dict[str, Any]]:
    """Contrato heredado: devuelve sólo la lista de candidatos.

    Se conserva la firma y el tipo de retorno para no romper consumidores.
    Para obtener el informe ligado a la invocación, usar
    :func:`run_criba_selection` (devuelve ``CribaResult``).
    """
    return run_criba_selection(problema_texto, seed, n_candidatos).candidates


def last_selection_report() -> dict[str, Any]:
    """Informe ligado a la invocación más reciente de :func:`run_criba_selection`.

    Si la última invocación fue un ``criba_fn`` heredado (lista) o falló, no hay
    informe atribuible: devuelve ``{}`` y **nunca** un informe de otro
    episodio.
    """
    return _LAST_SELECTION_REPORT.get("report") or {}


# Informe de la última invocación instrumentada. Se escribe SOLO desde
# run_criba_selection; los callbacks heredados no lo tocan, de modo que un
# episodio sin instrumento no puede heredar el de otro.
_LAST_SELECTION_REPORT: dict[str, Any] = {}
