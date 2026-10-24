"""T104 (Confidence) and T111 (Feasibility) as MCDA input producers.

These two canon techniques have no module in `intelligence/` and no producer in
the runtime. The runtime *does* have a real consumer of their dimension names:
`criba.mcda.score` accepts `inputs={"confidence": ..., "feasibility": ...}` with
`None` meaning UNKNOWN (excluded from the composite and reported as such), and
`sources={"confidence": "T104:..."}` to carry provenance per dimension.

This module is the minimal producer that feeds that consumer with **real corpus
data** (`data/methods/library_combined.json`): nothing is invented. Each function
returns `None` when the data is insufficient — `None` is "not evaluated", never a
measured 0.0.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping

# Granularity tiers ordered from most concrete to most abstract. A candidate
# built on a finer-grained method is more feasible to test locally.
_GRANULARITY_ORDER = {
    "micro_technique": 1.0,
    "technique": 0.8,
    "mechanism": 0.6,
    "method": 0.5,
    "framework": 0.35,
    "paradigm": 0.2,
    "theory": 0.1,
}

# Origins that are internal to the local corpus are more feasible than
# external references that would need to be acquired first.
_ORIGIN_ORDER = {
    "internal": 1.0,
    "derived": 0.7,
    "external": 0.4,
}

SOURCE_CONFIDENCE = "T104:corpus_confidence"
SOURCE_FEASIBILITY = "T111:granularity_feasibility"


def _granularity_score(granularity: object) -> float | None:
    if not isinstance(granularity, str):
        return None
    return _GRANULARITY_ORDER.get(granularity.strip().lower())


def _origin_score(origin: object) -> float | None:
    if not isinstance(origin, str):
        return None
    return _ORIGIN_ORDER.get(origin.strip().lower())


def confidence(
    method: Mapping[str, object] | None,
    *,
    sibling_methods: Iterable[Mapping[str, object]] = (),
) -> float | None:
    """T104 — confidence that the method family is supported by the corpus.

    Based only on explicit corpus fields: how many declared siblings share the
    same family, and whether the method carries declared evidence tags. A method
    with no declared family or no siblings is **not evaluated** (`None`), not
    confident (0.0) nor unconfident (1.0).
    """

    if not isinstance(method, Mapping):
        return None
    family = method.get("family")
    if not isinstance(family, str) or not family.strip():
        return None
    siblings = [
        m for m in sibling_methods
        if isinstance(m, Mapping) and m.get("family") == family
    ]
    if not siblings:
        return None
    with_evidence = sum(
        1 for m in siblings
        if isinstance(m.get("tags"), (list, tuple)) and m.get("tags")
    )
    ratio = with_evidence / len(siblings)
    return round(ratio, 6)


def feasibility(method: Mapping[str, object] | None) -> float | None:
    """T111 — feasibility of testing the method locally, from explicit fields.

    Uses only declared `granularity` and `origin`. A method lacking either field
    is **not evaluated** (`None`). No weights are invented: granularity and
    origin contribute equally when both are present.
    """

    if not isinstance(method, Mapping):
        return None
    gran = _granularity_score(method.get("granularity"))
    origin = _origin_score(method.get("origin"))
    if gran is None and origin is None:
        return None
    present = [v for v in (gran, origin) if v is not None]
    return round(sum(present) / len(present), 6)


def mcda_inputs(
    method: Mapping[str, object] | None,
    *,
    sibling_methods: Iterable[Mapping[str, object]] = (),
) -> dict[str, float | None]:
    """Produce the T104/T111 dimension inputs for `criba.mcda.score`."""

    return {
        "confidence": confidence(method, sibling_methods=sibling_methods),
        "feasibility": feasibility(method),
    }


def mcda_sources() -> dict[str, str]:
    """Provenance per dimension, as `criba.mcda.score(sources=...)` expects."""

    return {
        "confidence": SOURCE_CONFIDENCE,
        "feasibility": SOURCE_FEASIBILITY,
    }
