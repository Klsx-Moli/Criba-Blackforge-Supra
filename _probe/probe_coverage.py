"""Probe 5: coverage of the real fields needed for the 8 protocol obligations,
across ALL ideas the deterministic core produces.

Decides whether the slice can source every field from real data (and fail
loudly otherwise) instead of inventing content.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "criba-blackforge" / "src"))

from criba.engine import activate  # noqa: E402

REQUIRED_IDEA_FIELDS = (
    "id", "title", "mechanism_causal", "expected_effect",
    "broken_assumption", "known_space_element", "difference_from_known",
    "difference_signature", "causal_claim",
)

missing = Counter()
total = 0
for problem in (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro.",
    "Reducir el número de permisos excesivos concedidos a un agente.",
    "Evitar que un sistema service mesh se degrade sin invariant verification.",
):
    packet = activate(problem)
    for idea in packet["innovation"]["ideas"]:
        total += 1
        for f in REQUIRED_IDEA_FIELDS:
            if not str(idea.get(f) or "").strip():
                missing[f] += 1
        cv = idea.get("causal_variables") or {}
        for k in ("si_falla", "evidencia_requerida"):
            if not str(cv.get(k) or "").strip():
                missing[f"causal_variables.{k}"] += 1
        if not str(packet.get("experiment", {}).get("falsifiable_hypothesis") or "").strip():
            missing["experiment.falsifiable_hypothesis"] += 1

print("ideas examined:", total)
print("missing per field:", dict(missing) or "NINGUNO")

# Does difference_signature always parse into (axis, before, after) triples?
bad = 0
sample = None
packet = activate("Reducir el número de permisos excesivos concedidos a un agente.")
for idea in packet["innovation"]["ideas"]:
    sig = str(idea.get("difference_signature") or "")
    parts = [p for p in sig.strip("()").split("|") if p.strip()]
    triples = []
    for part in parts:
        if ":" not in part:
            bad += 1
            continue
        axis, _, values = part.partition(":")
        arrow = values.split("→")
        if len(arrow) != 2:
            bad += 1
            continue
        triples.append((axis.strip(), arrow[0].strip(), arrow[1].strip()))
    if not triples:
        bad += 1
    elif sample is None:
        sample = (idea["id"], sig, triples)
print("unparsable signatures:", bad)
print("sample:", sample)

# experiment block across problems
p = activate("Reducir el número de permisos excesivos concedidos a un agente.")
print("experiment:", p["experiment"])
print("decision:", p["decision"])