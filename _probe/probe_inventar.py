"""Throwaway probe: what does the REAL inventar service produce without an LLM?

Prints reality only (no asserts) so the vertical slice is designed from measured
behaviour instead of reading code and guessing.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "criba-blackforge"
sys.path.insert(0, str(ROOT / "src"))

# Keep the probe off the user's real state.
os.environ.setdefault("CRIBA_MODEL_CONFIG", str(Path(tempfile.mkdtemp(prefix="astra-probe-")) / "models.json"))

from criba.inventar import invent  # noqa: E402

problem = (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro."
)

print("== calling real inventar service ==")
sheet = invent(problem)
print("sheet keys:", sorted(sheet.keys()))
print("totals:", json.dumps(sheet["totals"], ensure_ascii=False))
print("n entries:", len(sheet["entries"]))
for i, entry in enumerate(sheet["entries"], 1):
    print(f"--- entry {i} ---")
    print("  keys:", sorted(entry.keys()))
    print("  estado_interpretacion:", entry.get("estado_interpretacion"))
    print("  candidate_id:", repr(entry.get("candidate_id")))
    print("  claim_id:", repr(entry.get("claim_id")))
    print("  hipotesis:", str(entry.get("hipotesis"))[:160])
    print("  mecanismo:", str(entry.get("mecanismo"))[:160])
    print("  prueba_concreta:", str(entry.get("prueba_concreta"))[:120])
    print("  observable:", str(entry.get("observable"))[:120])
    print("  metrica:", str(entry.get("metrica"))[:120])
    print("  regla_decision:", str(entry.get("regla_decision"))[:120])
    print("  condicion_fracaso:", str(entry.get("condicion_fracaso"))[:120])
    print("  resultado_favorable_mecanismo:", str(entry.get("resultado_favorable_mecanismo"))[:120])
    print("  resultado_favorable_alternativa:", str(entry.get("resultado_favorable_alternativa"))[:120])
    print("  evidencia_local_usada:", str(entry.get("evidencia_local_usada"))[:120])
    print("  interpretacion_error:", str(entry.get("interpretacion_error"))[:200])