"""Probe 3: the REAL SUPRA server over HTTP.

Launches `uvicorn supra_agentic.service:app` on a dynamic loopback port with an
isolated storage dir, then drives it with the REAL CRIBA SupraClient:
POST /api/v1/projects (with a real deterministic-core dossier) -> GET -> verify
the status channels the read path publishes.

Prints reality only.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
SUPRA_SRC = ROOT / "supra" / "src"
CRIBA_SRC = ROOT / "criba-blackforge" / "src"
sys.path.insert(0, str(CRIBA_SRC))
sys.path.insert(0, str(SUPRA_SRC))

STORAGE = Path(tempfile.mkdtemp(prefix="astra-supra-storage-"))
os.environ["SUPRA_STORAGE_DIR"] = str(STORAGE)
os.environ["SUPRA_USE_MODEL"] = "false"


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


from criba.engine import activate  # noqa: E402
from criba.integrations.supra_client import SupraClient, SupraClientConfig  # noqa: E402
from criba.integrations.supra_client import _dossier_payload_fingerprint  # noqa: E402
from criba.supra_dossier import preparar_dossier  # noqa: E402

PROBLEM = (
    "Reducir el impacto ambiental de las baterías de litio sin aumentar el coste "
    "de fabricación ni comprometer el suministro."
)

packet = activate(PROBLEM)
idea = packet["innovation"]["ideas"][0]
cv = idea.get("causal_variables", {})

entry = {
    "candidate_id": idea["id"],
    "hipotesis": f"{idea['title']} — {PROBLEM}",
    "mecanismo": idea.get("mechanism_causal", ""),
    "prueba_concreta": idea.get("expected_effect", ""),
    "observable": f"señal de {cv.get('evidencia_requerida', 'evidencia requerida')}",
    "alternativa": idea.get("broken_assumption", ""),
    "si_falla": cv.get("si_falla", ""),
    "supuestos": [idea.get("rupture", "")],
}
dossier = preparar_dossier(
    entry,
    PROBLEM,
    alternativa_explicativa=entry["alternativa"],
)
# completar campos que SUPRA exige (min_length=1) y que preparar_dossier deja vacios
prueba = dossier["prueba_discriminante"]
prueba["resultado_favorable_mecanismo"] = f"si {idea.get('expected_effect','')[:120]}"
prueba["resultado_favorable_alternativa"] = f"si el efecto se explica por {entry['alternativa'][:80]}"
prueba["regla_decision"] = "adoptar si el observable cambia segun el mecanismo y no segun la alternativa"
dossier["prueba_discriminante"] = prueba
print("dossier fingerprint:", _dossier_payload_fingerprint(dossier))

from supra_agentic.service import CribaDossierRequest, _criba_payload_fingerprint  # noqa: E402

try:
    validated = CribaDossierRequest.model_validate(dossier)
    server_fp = _criba_payload_fingerprint(validated)
    print("server fingerprint:  ", server_fp)
    print("FINGERPRINTS AGREE:", server_fp == _dossier_payload_fingerprint(dossier))
except Exception as exc:
    print("SUPRA schema REJECTED:", type(exc).__name__, str(exc)[:1500])

port = free_port()
print("\nlaunching SUPRA on 127.0.0.1:%d (storage=%s)" % (port, STORAGE))
log = open(STORAGE.parent / "uvicorn.log", "w", encoding="utf-8")
proc = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "supra_agentic.service:app",
     "--host", "127.0.0.1", "--port", str(port), "--log-level", "info"],
    cwd=str(ROOT / "supra"),
    stdout=log, stderr=subprocess.STDOUT,
    env={**os.environ, "PYTHONPATH": str(SUPRA_SRC), "SUPRA_STORAGE_DIR": str(STORAGE)},
)

endpoint = f"http://127.0.0.1:{port}"
client = SupraClient(SupraClientConfig(endpoint=endpoint, timeout=120.0))
try:
    health = None
    for _ in range(60):
        try:
            health = client.health()
            break
        except Exception:
            if proc.poll() is not None:
                print("server died, log:")
                print((STORAGE.parent / "uvicorn.log").read_text(encoding="utf-8")[-4000:])
                raise SystemExit(1)
            time.sleep(1.0)
    print("health:", json.dumps(health.model_dump(), ensure_ascii=False)[:600])

    project_id = "astram2" + uuid.uuid4().hex[:8]
    from criba.integrations.supra_client import objective_from_dossier

    t0 = time.time()
    result = client.run_project(
        objective=objective_from_dossier(dossier),
        domain="criba_blackforge",
        allow_disruptive=True,
        project_id=project_id,
        criba_dossier=dossier,
    )
    print("\nPOST took %.1fs" % (time.time() - t0))
    print("status:              ", result.status)
    print("status_scope:        ", result.status_scope)
    print("completion_status:   ", result.completion_status)
    print("workflow_status:     ", result.workflow_status)
    print("verification_status: ", result.verification_status)
    print("scientific_status:   ", result.scientific_status)
    print("secure_sandbox:      ", result.secure_sandbox_status)
    print("criba_planning:      ", result.criba_planning_receipt_status)
    print("criba_execution:     ", result.criba_mechanism_execution_status)
    print("stage:               ", result.stage)
    print("project_id:          ", result.project_id)
    print("idempotent_replay:   ", result.idempotent_replay)

    lookup = client.get_project(project_id)
    print("\nGET lookup status:    ", lookup.status)
    print("GET posture stage:    ", lookup.posture.stage)
    print("GET has receipt:      ", lookup.posture.criba_dossier_receipt is not None)
    print("GET receipt scope:    ", lookup.posture.criba_dossier_receipt.receipt_scope)
    print("GET receipt exec:     ", lookup.posture.criba_dossier_receipt.execution_status)
    print("GET final_output keys:", sorted((lookup.posture.final_output or {}).keys()))
    print("GET error_message:    ", lookup.posture.error_message)

    listing = client.list_projects(limit=5)
    print("\nLIST count:", listing.count, "| first ids:",
          [p.get("project_id") for p in listing.projects][:5])
finally:
    client.close()
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("\n--- uvicorn log tail ---")
    print((STORAGE.parent / "uvicorn.log").read_text(encoding="utf-8")[-3000:])