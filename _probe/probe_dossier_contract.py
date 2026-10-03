"""Probe 2: (a) is the local llama-server alive? (b) does a dossier built from the
REAL deterministic CRIBA core satisfy SUPRA's validated schema?

No asserts: this prints what actually happens so the slice is built on measured
behaviour, not on reading code.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
sys.path.insert(0, str(ROOT / "criba-blackforge" / "src"))
sys.path.insert(0, str(ROOT / "supra" / "src"))

# ---- (a) local model server -------------------------------------------------
import httpx  # noqa: E402

try:
    t0 = time.time()
    r = httpx.get("http://127.0.0.1:8080/health", timeout=5.0)
    print("llama-server /health:", r.status_code, r.text[:300], f"({time.time()-t0:.2f}s)")
except Exception as exc:
    print("llama-server NOT reachable:", type(exc).__name__, str(exc)[:200])

# ---- (b) deterministic CRIBA core -> dossier -> SUPRA schema ---------------
from criba.engine import activate  # noqa: E402
from criba.supra_dossier import preparar_dossier  # noqa: E402

PROBLEM = (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro."
)
packet = activate(PROBLEM)
ideas = packet["innovation"]["ideas"]
print("\nn_ideas:", len(ideas))
idea = ideas[0]
print("idea id:", idea["id"], "| title:", idea["title"][:90])
print("expected_effect:", str(idea.get("expected_effect"))[:300])
print("mechanism_explanation:", str(idea.get("mechanism_explanation"))[:300])
print("causal_claim:", idea.get("causal_claim"))

# What does the entry shape that preparar_dossier expects look like? Map the
# deterministic idea onto the entry contract and see what SUPRA then accepts.
entry = {
    "candidate_id": idea["id"],
    "claim_id": None,
    "hipotesis": f"{idea['title']} aplicado a: {PROBLEM}",
    "mecanismo": idea.get("mechanism_causal", ""),
    "prueba_concreta": idea.get("expected_effect", "") or "",
    "observable": idea.get("mechanism_explanation", "") or "",
    "supuestos": [],
}
dossier = preparar_dossier(entry, PROBLEM)
print("\ndossier keys:", sorted(dossier.keys()))
print("candidate_id:", dossier["candidate_id"])
print("claim_id:", dossier["claim_id"])
print("protocol_version:", dossier["protocol_version"])
prueba = dossier["prueba_discriminante"]
for k, v in prueba.items():
    print(f"  prueba.{k} = {str(v)[:110]!r}")

from supra_agentic.service import CreateProjectRequest  # noqa: E402

try:
    CreateProjectRequest(
        objective="x" * 40,
        criba_dossier=dossier,
        criba_integration_version="criba-supra/1",
        criba_payload_fingerprint="sha256:" + "0" * 64,
    )
    print("\nSUPRA schema: ACCEPTED")
except Exception as exc:
    print("\nSUPRA schema REJECTED:", type(exc).__name__)
    print(str(exc)[:2500])

# And the client-side fingerprint over the same dossier:
from criba.integrations.supra_client import _dossier_payload_fingerprint  # noqa: E402

from supra_agentic.service import _criba_payload_fingerprint  # noqa: E402

client_fp = _dossier_payload_fingerprint(dossier)
try:
    validated = CreateProjectRequest.CribaDossierRequest.model_validate(dossier)
    server_fp = _criba_payload_fingerprint(validated)
except Exception as exc:
    server_fp = f"<cannot validate: {type(exc).__name__}>"
print("\nclient fingerprint:", client_fp)
print("server fingerprint:", server_fp)
print("AGREE:", client_fp == server_fp)