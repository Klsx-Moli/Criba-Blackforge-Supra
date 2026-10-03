"""K1 LIMITATION · reproducción por ejecución, no leída del código.

Reproduce exactamente lo que K1 declaró y que M3 debe DECIDIR:

  el state_manager de SUPRA sirve el estado desde su cache en memoria aunque
  el artefacto en disco esté corrupto; la corrupción emerge al reiniciar.

Servidor REAL (subprocess uvicorn del propio componente SUPRA, su venv),
storage temporal, cliente httpx real. Sin TestClient, sin mocks.

Salida: lo que REALMENTE ocurrió. Exit != 0 si la limitación no se reproduce.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

REPO = Path(__file__).resolve().parents[1]
SUPRA = REPO / "supra"
SUPRA_SRC = SUPRA / "src"
SUPRA_PYTHON = SUPRA / ".venv" / "Scripts" / "python.exe"

STORAGE = Path(tempfile.mkdtemp(prefix="astra-k1-storage-"))
LOG = Path(tempfile.mkdtemp(prefix="astra-k1-log-")) / "uvicorn.log"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}" + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _parses(raw: str) -> bool:
    try:
        json.loads(raw)
    except Exception:
        return False
    return True


def start(port: int) -> subprocess.Popen:
    handle = open(LOG, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [str(SUPRA_PYTHON), "-m", "uvicorn", "supra_agentic.service:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(SUPRA),
        stdout=handle, stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(SUPRA_SRC), "SUPRA_STORAGE_DIR": str(STORAGE),
             "SUPRA_USE_MODEL": "false"},
    )
    for _ in range(90):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=3.0).status_code == 200:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            break
        time.sleep(1.0)
    print(LOG.read_text(encoding="utf-8")[-2000:])
    raise SystemExit("SUPRA no arranco")


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=20)
    except subprocess.TimeoutExpired:
        proc.kill()


port = free_port()
endpoint = f"http://127.0.0.1:{port}"
print(f"SUPRA real en {endpoint} (storage={STORAGE})")
server = start(port)
project_id = "astra-k1-probe"

try:
    # 1) ejecución real por la superficie HTTP pública
    created = httpx.post(
        f"{endpoint}/api/v1/projects",
        json={"objective": "K1 probe: does a live read survive a corrupt artifact?",
              "project_id": project_id},
        timeout=60.0,
    )
    check("POST real del proyecto", created.status_code == 201, str(created.status_code))
    if created.status_code != 201:
        raise SystemExit(1)
    truth = created.json()
    print("\n--- estado real creado ---")
    for k in ("status", "stage", "workflow_status", "verification_status",
              "scientific_status", "secure_sandbox_status"):
        print(f"  {k}: {truth.get(k)}")

    artifact = STORAGE / f"{project_id}.json"
    check("el artefacto existe en disco", artifact.is_file(), str(artifact))
    original = artifact.read_text(encoding="utf-8")
    print(f"  artefacto: {len(original)} bytes, parsea como JSON={_parses(original)}")

    # 2) corrupción EXTERNA del artefacto mientras el proceso sigue vivo
    artifact.write_text("{ corrupto por un actor externo", encoding="utf-8")
    check("el artefacto en disco está corrupto ahora",
          not _parses(artifact.read_text(encoding="utf-8")),
          "el archivo ya no es JSON válido")

    # 3) la limitación declarada: el proceso VIVO sigue respondiendo 200
    live = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("con artefacto corrupto y proceso vivo, GET sigue 200 (cache en memoria)",
          live.status_code == 200, str(live.status_code))
    if live.status_code == 200:
        body = live.json()
        print("\n--- lo que el proceso VIVO afirma del estado ---")
        for k in ("status", "stage", "workflow_status", "verification_status",
                  "scientific_status", "status_source"):
            print(f"  {k}: {body.get(k)}")
        check("el estado servido es el MISMO que se creó",
              body.get("status") == truth.get("status") and body.get("stage") == truth.get("stage"),
              f"{body.get('status')}/{body.get('stage')}")
        check("y declara status_source=PERSISTED_STATE sin haber leído disco",
              body.get("status_source") == "PERSISTED_STATE")

    # el listado tampoco ve la corrupción del proyecto cacheado
    listing = httpx.get(f"{endpoint}/api/v1/projects", timeout=30.0).json()
    errors = listing.get("storage_errors") or []
    check("el listado NO reporta la corrupción de un proyecto ya cacheado",
          errors == [], f"storage_errors={errors}")

    # 4) la corrupción emerge al reiniciar el proceso
    print("\n--- reinicio del proceso (mismo storage) ---")
    stop(server)
    server = start(port)
    after = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("tras reiniciar, el GET ya NO es 200", after.status_code != 200, str(after.status_code))
    check("y falla CERRADO (500), no degrada a 404 ni a success",
          after.status_code == 500, str(after.status_code))
    check("el cuerpo declara corrupción, no ausencia",
          "corrupt" in after.text.lower(), after.text[:160])
    listing2 = httpx.get(f"{endpoint}/api/v1/projects", timeout=30.0).json()
    errors2 = listing2.get("storage_errors") or []
    check("el listado ahora SÍ declara la corrupción",
          any(e.get("project_id") == project_id for e in errors2), f"storage_errors={errors2}")

    print("\n=== LO QUE ESTA DECIDIENDO M3 ===")
    print("  Cache en memoria + etiqueta PERSISTED_STATE incondicional.")
    print("  Un artefacto corrupto se sigue sirviendo como PERSISTED_STATE hasta")
    print("  que el proceso reinicia, y entonces el mismo GET falla 500.")
finally:
    stop(server)

print("\n=== RESULTADO ===")
if failures:
    print("LA LIMITACION NO SE REPRODUJO:")
    for f in failures:
        print("  -", f)
    raise SystemExit(1)
print("LIMITACION DE K1 REPRODUCIDA CON EVIDENCIA EJECUTADA.")