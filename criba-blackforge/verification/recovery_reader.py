"""Lector de recuperación en proceso nuevo (CB-03).

Se ejecuta como subproceso Python independiente para probar que, tras un
reinicio real (memoria vacía), SUPRA recupera el proyecto DESDE EL DISCO y no
desde la caché del proceso previo.

Uso: python recovery_reader.py <root> <endpoint>
Imprime una única línea JSON con:
  project_id, status, status_source, persisted_artifact_status,
  mem_keys_before_get (debe estar vacía) y read (payload completo del GET).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

ROOT = Path(sys.argv[1]).resolve()
ENDPOINT = sys.argv[2]

os.environ["SUPRA_STORAGE_DIR"] = str(ROOT / "supra_state")
os.environ["SUPRA_USE_MODEL"] = "false"
os.environ["CRIBASHADOW_HOME"] = str(ROOT)
os.environ["CRIBA_MODEL_CONFIG"] = str(ROOT / "models.json")

CRIBA_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CRIBA_ROOT))
sys.path.insert(0, str(CRIBA_ROOT / "shadow_ui"))

import criba_shadow_main as launcher

launcher.wire_import_paths()

from supra_agentic.state import state_manager as sm

srv = launcher.SupraServer(ENDPOINT, ROOT / "supra_state", ROOT / "logs" / "recovery.log")
ok, ep = srv.start(wait_s=90.0)
if not ok:
    print(json.dumps({"error": ep}))
    raise SystemExit(3)

try:
    # Replicar el criterio del servidor SIN usar list_projects: ese método
    # puebla self._projects vía get_project (state.py:623) y el GET subsiguiente
    # reportaría MEMORY_CACHE, rompiendo la prueba de PERSISTED_STATE. En su
    # lugar se leen los artefactos JSON en disco directamente y se elige el más
    # reciente por updated_at (mismo criterio que state.py:647).
    artifact_files = sorted((ROOT / "supra_state").glob("proj-*.json"))
    if not artifact_files:
        print(json.dumps({"empty": True, "mem_keys": list(sm._projects.keys())}))
        raise SystemExit(0)
    mem_before = list(sm._projects.keys())
    candidates: list[tuple[float, str]] = []
    for p in artifact_files:
        try:
            payload = json.loads(p.read_text(encoding="utf-8"))
            updated = float(payload.get("updated_at") or 0.0)
            candidates.append((updated, p.stem))
        except Exception:
            continue  # un artefacto corrupto no debe tumbar la recuperación
    if not candidates:
        print(json.dumps({"empty": True, "no_valid": True}))
        raise SystemExit(0)
    candidates.sort(key=lambda x: x[0], reverse=True)
    pid = candidates[0][1]
    req = urllib.request.Request(ep + "/api/v1/projects/" + pid, method="GET")
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode())
    print(
        json.dumps(
            {
                "project_id": pid,
                "status": data.get("status"),
                "status_source": data.get("status_source"),
                "persisted_artifact_status": data.get("persisted_artifact_status"),
                "mem_keys_before_get": mem_before,
                "read": data,
            }
        )
    )
finally:
    srv.stop()
