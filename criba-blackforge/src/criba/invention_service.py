"""Shared desktop orchestration of the existing invention engine and interpreter.

No selector/scoring/provider fallback is implemented here. Configuration is frozen
for one run; cancellation prevents the next request, not the one already in flight.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def run_invention(
    problem: str,
    *,
    backend: str | None = None,
    model: str | None = None,
    progress: Callable[[dict[str, Any]], None] | None = None,
    cancel_requested: Callable[[], bool] | None = None,
    methods: list[dict[str, Any]] | None = None,
    mode: str = "stratified",
    seed: int | None = None,
    batch_size: int | None = None,
    top: int | None = None,
    history_storage: Any = True,
    write_ledger: bool = True,
) -> dict[str, Any]:
    from .intelligence.refresh import default_store
    from .interprete.seleccion import (
        construir_interprete,
        estado_interprete,
        seleccion_por_defecto,
    )
    from .inventar import _default_proponer, append_ledger, invent

    chosen = backend or seleccion_por_defecto()
    interpreter = construir_interprete(chosen, model=model)
    interpreter_state = estado_interprete(interpreter)
    completed = 0

    def propose(
        query: str,
        idea: dict[str, Any],
        domain: dict[str, Any] | None,
        evidence: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        nonlocal completed
        if cancel_requested is not None and cancel_requested():
            from .inventar import _pending_proposal

            result = _pending_proposal("cancelado por operador")
        else:
            result = _default_proponer(
                query, idea, domain, evidence=evidence, interprete=interpreter
            )
        completed += 1
        if progress is not None:
            progress(
                {
                    "completed": completed,
                    "candidate": str(idea.get("title") or "")[:100],
                    "status": result.get("estado", "PENDIENTE_INTERPRETACION"),
                }
            )
        return result

    options: dict[str, Any] = {}
    if methods is not None:
        options["methods"] = methods
    if mode != "stratified":
        options["mode"] = mode
    if seed is not None:
        options["seed"] = seed
    if batch_size is not None:
        options["batch_size"] = batch_size
    if top is not None:
        options["top"] = top
    if history_storage is not True:
        options["history_storage"] = history_storage
    sheet = invent(problem, store=default_store(), proponer=propose, **options)
    if write_ledger:
        sheet["ledger_path"] = str(append_ledger(sheet))
    sheet["interpreter"] = interpreter_state
    sheet["cancel_requested"] = bool(cancel_requested and cancel_requested())
    return sheet
