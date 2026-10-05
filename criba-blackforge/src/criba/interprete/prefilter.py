"""Prefiltrado causal top-N antes de la interpretación del modelo.

Reemplaza al juez de BASURA (umbral 0.9 inalcanzable) con un filtro que
garantiza que las candidatas tengan tangibilidad causal real:

- Dh governor: 0.45 <= D_H <= 0.85 (zona sweet-spot Kauffman).
- SOTA taboo: rechaza clichés del estado del arte (99 patrones).
- novelty recortado a [0.65, 0.85]: banda de serendipia asociativa.

NO promete EXTRAORDINARIA: promete candidatos con tangibilidad causal.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Any

from criba.core.adjacent_possible import (
    SOTA_TABOO_PATTERNS,
    AdjacentPossibleGovernor,
)


def _novelty_band(idea: dict[str, Any], lo: float = 0.65, hi: float = 0.85) -> bool:
    """Idea dentro de la banda de serendipia asociativa. Si no hay novelty, pasa (no filtra)."""
    convergence = idea.get("convergence")
    if convergence is not None and not isinstance(convergence, dict):
        return False
    n = (convergence or {}).get("novelty")
    if n is None:
        return True
    if isinstance(n, bool):
        return False
    try:
        value = float(n)
        return math.isfinite(value) and lo <= value <= hi
    except (ValueError, TypeError):
        return False


def dh_out_of_range(
    idea: dict[str, Any], governor: AdjacentPossibleGovernor | None = None
) -> float | None:
    """Retorna D_H ajustado. None si cae fuera de [0.45, 0.85].

    Usa causal_axes_changed (los ejes que REALMENTE mutó el operador),
    no todos los causal_variables que difieren del base.
    """
    # El engine registra los ejes realmente mutados en causal_axes_changed
    axes_moved = idea.get("causal_axes_changed", [])
    g = governor or AdjacentPossibleGovernor()
    contract = g.evaluate_proposal(
        proposal_id=idea.get("id", "x"),
        target_axiom=idea.get("known_space_element", "problema"),
        intervention=idea["description"],
        causal_axes_moved=axes_moved,
        domain=idea.get("domain", "general"),
    )
    if g.min_dist <= contract.adjacent_distance <= g.max_dist:
        return contract.adjacent_distance
    return None


def sota_taboo_violations(idea: dict[str, Any]) -> list[str]:
    text = f"{idea.get('description', '')} {idea.get('mechanism_causal', '')}".lower()
    return sorted(
        p for p in SOTA_TABOO_PATTERNS if re.search(r"(?<!\w)" + re.escape(p) + r"(?!\w)", text)
    )


class PreFilter:
    """Filtra el conjunto de ideas producidas por activate() a top-N candidatas
    con tangibilidad causal. Deterministic (seed no afecta el orden de salida
    dentro de un mismo lote — preserva el orden del motor)."""

    def __init__(
        self,
        top_n: int = 12,
        dh_lo: float = 0.45,
        dh_hi: float = 0.85,
        novelty_lo: float = 0.65,
        novelty_hi: float = 0.85,
        strict: bool = True,
    ) -> None:
        self.top_n = top_n
        self.dh_lo = dh_lo
        self.dh_hi = dh_hi
        self.novelty_lo = novelty_lo
        self.novelty_hi = novelty_hi
        self.strict = strict
        # Un juez débil exige más cautela; nunca amplía el conjunto admisible.
        if not strict:
            self.novelty_lo = max(novelty_lo, 0.70)
            self.novelty_hi = min(novelty_hi, 0.80)
        self.governor = AdjacentPossibleGovernor(min_dist=dh_lo, max_dist=dh_hi)

    def apply(self, ideas: Sequence[dict[str, Any]]) -> dict[str, Any]:
        """Retorna {candidates, dropped, stats} con top-N candidatas."""
        candidates: list[dict[str, Any]] = []
        dropped: list[dict[str, Any]] = []
        dh_rejected = tabu_rejected = novelty_rejected = invalid_rejected = 0

        for idea in ideas:
            if (
                not isinstance(idea, dict)
                or not isinstance(idea.get("id"), str)
                or not idea["id"].strip()
                or not isinstance(idea.get("description"), str)
                or not idea["description"].strip()
                or not isinstance(idea.get("causal_axes_changed", []), list)
                or any(not isinstance(a, str) for a in idea.get("causal_axes_changed", []))
            ):
                invalid_rejected += 1
                dropped.append(
                    {
                        "id": idea.get("id") if isinstance(idea, dict) else None,
                        "reason": "entrada_invalida",
                    }
                )
                continue
            # 1. SOTA taboo primero (rechaza clichés del estado del arte)
            v = sota_taboo_violations(idea)
            if v:
                tabu_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "sota_taboo", "violations": v[:3]})
                continue
            # 2. Dh governor (rango causal [0.45, 0.85])
            dh = dh_out_of_range(idea, self.governor)
            if dh is None:
                dh_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "dh_fuera_rango"})
                continue
            # 3. Novelty band (serendipia asociativa)
            if not _novelty_band(idea, self.novelty_lo, self.novelty_hi) or (
                not self.strict and (idea.get("convergence") or {}).get("novelty") is None
            ):
                novelty_rejected += 1
                dropped.append({"id": idea.get("id"), "reason": "novelty_fuera_banda"})
                continue
            idea = dict(idea)
            idea["prefilter"] = {"dh": dh, "novelty_band": [self.novelty_lo, self.novelty_hi]}
            candidates.append(idea)

        top = candidates[: self.top_n]

        return {
            "candidates": top,
            "dropped": dropped,
            "stats": {
                "total_input": len(ideas),
                "kept": len(candidates),
                "selected": len(top),
                "dh_rejected": dh_rejected,
                "tabu_rejected": tabu_rejected,
                "novelty_rejected": novelty_rejected,
                "invalid_rejected": invalid_rejected,
                "dh_range": [self.dh_lo, self.dh_hi],
                "novelty_band": [self.novelty_lo, self.novelty_hi],
            },
        }
