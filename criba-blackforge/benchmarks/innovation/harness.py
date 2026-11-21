"""Harness benchmark v0 (megaprompt §45-§47): COMPARABILIDAD, no conclusiones.

Condiciones reservadas (misma evidencia/presupuesto cuando se ejecute de verdad):
- A_DIRECT:      prompt mínimo  «Genera N soluciones innovadoras para…»
- B_STRONG_PROMPT: prompt de innovación bien diseñado, sin CRIBA
- C_CRIBA:       mismo modelo vía cruces/selector/evidencia de CRIBA
- D_BLACKFORGE:  lotería + selector diversity-aware sobre el catálogo BLACKFORGE

Este harness v0 NO llama a ningún modelo: `model_fn` es inyectable (stub en
tests/smoke). Con modelo ausente las comparaciones quedan UNAVAILABLE. Un
smoke pequeño prueba funcionamiento, no superioridad (§48). Estudio completo:
DEFERRED_SEPARATE_STUDY.
"""
from __future__ import annotations

import copy
import hashlib
import json
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from benchmarks.diversity_measure import measure  # reutiliza métricas del contrato

DIR = Path(__file__).resolve().parent

CONDITIONS: dict[str, dict[str, str]] = {
    "A_DIRECT": {
        "plantilla": "Genera {n} soluciones innovadoras para: {problema}",
    },
    "B_STRONG_PROMPT": {
        "plantilla": (
            "Genera {n} soluciones para: {problema}\n"
            "Requisitos: mecanismo causal explícito, qué supuesto cambias, "
            "respecto de qué solución de referencia, restricciones conservadas, "
            "y una prueba mínima con condición de fracaso."
        ),
    },
    "C_CRIBA": {
        "plantilla": "CRIBA: cruces + selector diversity-aware + evidencia para: {problema}",
    },
    "D_BLACKFORGE": {
        "plantilla": "BLACKFORGE: lotería + selector diversity-aware para: {problema}",
    },
}


def _run_id(problema_id: str, condition: str, seed: int) -> str:
    digest = hashlib.sha256(f"{problema_id}|{condition}|{seed}".encode()).hexdigest()[:12]
    return f"bench-{digest}"


def run_condition(
    condition: str,
    problema: dict[str, Any],
    *,
    seed: int,
    n_candidatos: int = 3,
    model_fn: Callable[..., list[dict[str, Any]]] | None = None,
    criba_fn: Callable[[str, int, int], list[dict[str, Any]]] | None = None,
    invent_fn: Callable[[str, int, int], Any] | None = None,
    blackforge_fn: Callable[[str, int, int], Any] | None = None,
) -> dict[str, Any]:
    """Ejecuta UNA condición sobre UN problema. Sin modelo → UNAVAILABLE.

    Hallazgo 6 corregido:
    - ``model_fn`` recibe el prompt Y la semilla (firma ampliada vía
      ``_call_model`` para no romper callbacks de un solo argumento).
    - C_CRIBA NO es un prompt distinto: ejecuta el LOOP REAL de CRIBA via
      ``invent_fn`` (pipeline interpretado) o ``criba_fn`` (seleccion
      estructurada), inyectables. Sin ninguno queda UNAVAILABLE honesto:
      nunca se simula CRIBA con un prompt de texto.
    - D_BLACKFORGE ejecuta la lotería + selector reales del catálogo
      BLACKFORGE via ``blackforge_fn``. Sin callback queda UNAVAILABLE: nunca
      se sustituye por un prompt.
    """
    if condition not in CONDITIONS:
        raise ValueError(f"condición desconocida: {condition}")
    prompt = CONDITIONS[condition]["plantilla"].format(
        n=n_candidatos, problema=problema["texto"])
    record: dict[str, Any] = {
        "run_id": uuid.uuid4().hex,
        "bench_run_id": _run_id(problema["id"], condition, seed),
        "problem_id": problema["id"],
        "condition": condition,
        "seed": seed,
        "seed_source": "explicit",
        "prompt": prompt,
        "candidates": [],
        "metrics": None,
        "status": "UNAVAILABLE",
        "nota": "sin modelo configurado: comparación no ejecutada",
    }
    started = time.monotonic()
    if condition == "C_CRIBA":
        runner = invent_fn if invent_fn is not None else criba_fn
        if runner is not None:
            result = runner(problema["texto"], seed, n_candidatos)
            # El informe se liga a ESTA invocación, no a un estado de módulo.
            # `run_criba_selection` devuelve CribaResult (candidatos + informe
            # ligados). Un callback que devuelve la lista heredada declara
            # REPORT_UNAVAILABLE explícito: nunca hereda el de otro episodio.
            from benchmarks.innovation.criba_adapter import CribaResult, _coerce_result
            if isinstance(result, CribaResult):
                candidates = result.candidates
                selection_report = result.selection_report
            else:
                candidates, selection_report = _coerce_result(result)
            _normalizar_candidatos(candidates)
            # Copia profunda: la exportación no debe compartir listas anidadas
            # con el objeto en memoria.
            record["candidates"] = copy.deepcopy(candidates)
            record["metrics"] = measure(candidates[:n_candidatos], candidates)
            record["selection_report"] = copy.deepcopy(selection_report)
            record["status"] = "OK"
            if invent_fn is not None:
                record["nota"] = "loop CRIBA interpretado ejecutado via invent_fn"
                record["pipeline"] = "invent_fn"
            else:
                record["nota"] = "loop CRIBA real ejecutado via criba_fn"
                record["pipeline"] = "criba_fn"
            record["latencia_s"] = round(time.monotonic() - started, 3)
        else:
            record["nota"] = (
                "C_CRIBA requiere invent_fn (pipeline interpretado) o criba_fn "
                "(seleccion real); sin ellos UNAVAILABLE"
            )
    elif condition == "D_BLACKFORGE":
        if blackforge_fn is not None:
            from benchmarks.innovation.blackforge_adapter import coerce_result

            result = blackforge_fn(problema["texto"], seed, n_candidatos)
            candidates, selection_report = coerce_result(result)
            _normalizar_candidatos(candidates)
            record["candidates"] = copy.deepcopy(candidates)
            record["metrics"] = measure(candidates[:n_candidatos], candidates)
            record["selection_report"] = copy.deepcopy(selection_report)
            record["status"] = "OK"
            record["nota"] = "loop BLACKFORGE real ejecutado via blackforge_fn"
            record["pipeline"] = "blackforge_fn"
            record["latencia_s"] = round(time.monotonic() - started, 3)
        else:
            record["nota"] = (
                "D_BLACKFORGE requiere blackforge_fn (lotería + selector real); "
                "sin él UNAVAILABLE"
            )
    elif model_fn is not None:
        candidates = _call_model(model_fn, prompt, seed)
        _normalizar_candidatos(candidates)
        record["candidates"] = candidates
        record["metrics"] = measure(candidates[:n_candidatos], candidates)
        record["status"] = "OK"
        record["latencia_s"] = round(time.monotonic() - started, 3)
    return record


def _normalizar_candidatos(candidates: list[dict[str, Any]]) -> None:
    """Garantiza el contrato que `measure` exige: idea_id, genome y family.

    measure (benchmarks.diversity_measure) necesita ``idea_id`` y ``genome``
    para los pares y ``family`` para la cobertura. Se rellenan con valores
    honestos por defecto sin inventar contenido: family deriva de classes si
    existe, si no 'unknown' (que cuenta como familia propia, no como dato).
    """
    for i, c in enumerate(candidates):
        c.setdefault("idea_id", f"cand-{i:02d}")
        c.setdefault("genome", {})
        if "family" not in c or not c["family"]:
            clases = [x for x in (c.get("classes") or []) if x]
            c["family"] = clases[0] if clases else "unknown"


def _call_model(
    model_fn: Callable[..., list[dict[str, Any]]],
    prompt: str,
    seed: int,
) -> list[dict[str, Any]]:
    """Invoca model_fn propagando la semilla cuando la firma lo admite.

    Hallazgo 6: la semilla no llegaba al callback, así la condición no era
    reproducible. Se intenta (prompt, seed) y se degrada a (prompt) para
    compatibilidad con stubs de un solo argumento.
    """
    try:
        return model_fn(prompt, seed)
    except TypeError:
        return model_fn(prompt)


def run_smoke(model_fn: Callable[[str], list[dict[str, Any]]] | None = None,
              *, seed: int = 7,
              criba_fn: Callable[[str, int, int], list[dict[str, Any]]] | None = None,
              invent_fn: Callable[[str, int, int], Any] | None = None,
              blackforge_fn: Callable[[str, int, int], Any] | None = None,
              ) -> dict[str, Any]:
    """Smoke ≤10 problemas × todas las condiciones. Funcionalidad, no ciencia.

    C_CRIBA ejecuta el loop real de CRIBA vía ``criba_fn``; D_BLACKFORGE ejecuta
    la lotería + selector reales de BLACKFORGE vía ``blackforge_fn``. Sin el
    callback correspondiente, esa condición queda UNAVAILABLE honesto (nunca un
    prompt de texto como sustituto del motor).
    """
    data = json.loads((DIR / "problems_smoke.json").read_text(encoding="utf-8"))
    runs = [run_condition(cond, p, seed=seed, model_fn=model_fn,
                          criba_fn=criba_fn, invent_fn=invent_fn,
                          blackforge_fn=blackforge_fn)
            for p in data["problemas"] for cond in CONDITIONS]
    return {
        "dataset": data["version"],
        "n_problemas": len(data["problemas"]),
        "conditions": list(CONDITIONS),
        "runs": runs,
        "advertencia": "smoke funcional; NO concluye superioridad (§53)",
        "generado_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def exportar(report: dict[str, Any], out: Path) -> Path:
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out
