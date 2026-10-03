"""Probe 4: which REAL fields does a deterministic CRIBA idea carry that could
honestly fill the 8 required discriminant-protocol fields?

Prints the fields for several ideas so the mapping is designed from measured
data, not from a guess.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "criba-blackforge" / "src"))

from criba.engine import activate  # noqa: E402

PROBLEM = (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro."
)
packet = activate(PROBLEM)
ideas = packet["innovation"]["ideas"]

FIELDS = (
    "title", "description", "mechanism_causal", "mechanism_explanation",
    "expected_effect", "broken_assumption", "rupture", "difference_from_known",
    "difference_signature", "known_space_element", "evidence", "query_anchor",
    "operator", "family", "family2",
)

for idx in (0, 5, 17, 40):
    idea = ideas[idx]
    print("=" * 78)
    print(f"idea[{idx}] id={idea['id']} causal_claim={idea.get('causal_claim')}")
    for f in FIELDS:
        val = idea.get(f)
        print(f"  {f}: {json.dumps(val, ensure_ascii=False)[:260]}")
    cv = idea.get("causal_variables", {})
    for k in ("evidencia_requerida", "si_falla", "mecanismo_control", "relacion_confianza"):
        print(f"  causal_variables.{k}: {json.dumps(cv.get(k), ensure_ascii=False)[:200]}")

print("=" * 78)
print("packet-level keys of interest:")
print("  rupture:", json.dumps(packet.get("rupture"), ensure_ascii=False)[:600])
print("  experiment:", json.dumps(packet.get("experiment"), ensure_ascii=False)[:900])
print("  decision:", json.dumps(packet.get("decision"), ensure_ascii=False)[:600])
print("  selected_current:", json.dumps(packet.get("selected_current"), ensure_ascii=False)[:600])