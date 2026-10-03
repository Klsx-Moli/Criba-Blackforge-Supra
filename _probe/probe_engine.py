"""Throwaway probe: what the REAL deterministic CRIBA core returns, and is a
local model profile usable? Prints reality only (no asserts).
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "criba-blackforge"
sys.path.insert(0, str(ROOT / "src"))

out = []


def emit(*a):
    line = " ".join(str(x) for x in a)
    out.append(line)
    print(line, flush=True)


t0 = time.time()
from criba.engine import activate  # noqa: E402

emit("import engine:", round(time.time() - t0, 2), "s")

problem = (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro."
)
t0 = time.time()
packet = activate(problem)
emit("activate:", round(time.time() - t0, 2), "s")
emit("packet keys:", sorted(packet.keys()))
ideas = packet["innovation"]["ideas"]
emit("n_ideas:", len(ideas))
emit("idea0 keys:", sorted(ideas[0].keys()))
emit("idea0:", json.dumps(ideas[0], ensure_ascii=False)[:2500])

# Local model profile reality
try:
    from criba.model_config import load_model_settings, active_model_label

    s = load_model_settings()
    emit("model settings enabled:", s.enabled)
    emit("active profile:", s.active_profile())
    emit("active label:", active_model_label(s))
except Exception as exc:
    emit("model_config error:", type(exc).__name__, exc)

emit("NOUS_API_KEY set:", bool(os.environ.get("NOUS_API_KEY")))
emit("CRIBA_LOCAL_MODEL:", os.environ.get("CRIBA_LOCAL_MODEL"))

(Path(__file__).parent / "probe_engine.out").write_text(
    "\n".join(out) + "\n", encoding="utf-8"
)