"""M3 · contrato de procedencia verificado contra el servidor SUPRA REAL.

Este probe es la contraparte del que reprodujo la limitación de K1. Antes del
cambio, el mismo recorrido daba:

    artefacto corrupto + proceso vivo -> 200 status_source=PERSISTED_STATE
                                        storage_errors == []

Ahora exige lo contrario, y lo exige talking con un uvicorn de verdad
(subprocess propio, su venv, storage temporal, httpx sobre TCP). No usa
TestClient: el punto de M3 es precisamente que la etiqueta se emitía en el
cable, y un doble de test no la exercise.

Recorrido completo:
    Shadow-side contract -> POST real -> leer en caliente -> corrupcionar el
    artefacto -> leer en caliente -> listado -> reiniciar -> leer en frio.

Exit != 0 si el servidor miente.
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

STORAGE = Path(tempfile.mkdtemp(prefix="astra-m3-storage-"))
LOG = Path(tempfile.mkdtemp(prefix="astra-m3-log-")) / "uvicorn.log"

failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}" + (f" :: {detail}" if detail else ""))
    if not ok:
        failures.append(label)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


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


def parses(raw: str) -> bool:
    try:
        json.loads(raw)
    except Exception:
        return False
    return True


project_id = "astra-m3-probe"
port = free_port()
endpoint = f"http://127.0.0.1:{port}"
print(f"SUPRA real en {endpoint} (storage={STORAGE})")
server = start(port)

try:
    # 1) ejecución real por la superficie pública
    created = httpx.post(
        f"{endpoint}/api/v1/projects",
        json={"objective": "M3: a live read must not claim state it did not read",
              "project_id": project_id},
        timeout=60.0,
    )
    check("POST real del proyecto", created.status_code == 201, str(created.status_code))
    if created.status_code != 201:
        raise SystemExit(1)
    truth = created.json()

    artifact = STORAGE / f"{project_id}.json"
    check("el artefacto existe en disco", artifact.is_file(), str(artifact))

    # 2) lectura en caliente: el estado es correcto, la procedencia también
    warm = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("GET en caliente responde 200", warm.status_code == 200, str(warm.status_code))
    warm_body = warm.json()
    print("\n--- lectura EN CALIENTE (caché en memoria) ---")
    for key in ("status", "stage", "workflow_status", "verification_status",
                "scientific_status", "status_source", "persisted_artifact_status"):
        print(f"  {key}: {warm_body.get(key)}")
    check("el estado servido es el real, no se perdió nada",
          warm_body["status"] == truth["status"] and warm_body["stage"] == truth["stage"],
          f"{warm_body['status']}/{warm_body['stage']}")
    check("NO se etiqueta como PERSISTED_STATE (no se leyó disco)",
          warm_body["status_source"] == "IN_PROCESS_MEMORY_CACHE",
          warm_body["status_source"])
    check("y declara que el artefacto durable coincide con la caché",
          warm_body["persisted_artifact_status"] == "MATCHES_CACHE",
          warm_body["persisted_artifact_status"])

    # 3) corrupción externa con el proceso vivo
    artifact.write_text("{ corrupto por un actor externo", encoding="utf-8")
    check("el artefacto en disco ya no es JSON", not parses(artifact.read_text(encoding="utf-8")))

    hot = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0).json()
    print("\n--- lectura EN CALIENTE con artefacto corrupto ---")
    for key in ("status", "stage", "status_source", "persisted_artifact_status"):
        print(f"  {key}: {hot.get(key)}")
    check("sigue sirviendo el estadoTrue (no se tira estado correcto)",
          hot["stage"] == truth["stage"], hot["stage"])
    check("sigue sin robar la etiqueta de persistido",
          hot["status_source"] == "IN_PROCESS_MEMORY_CACHE", hot["status_source"])
    check("y declara la copia durable INVERIFICABLE",
          hot["persisted_artifact_status"] == "UNVERIFIABLE",
          hot["persisted_artifact_status"])

    errors = httpx.get(f"{endpoint}/api/v1/projects", timeout=30.0).json()["storage_errors"]
    reported = {item["project_id"]: item["error"] for item in errors}
    check("el listado ya NO oculta la corrupción detrás de la caché",
          reported.get(project_id) == "PERSISTED_STATE_CORRUPT_OR_INCOMPATIBLE",
          f"storage_errors={errors}")

    # 4) reinicio: la lectura en frío SÍ viene del artefacto
    print("\n--- reinicio del proceso (mismo storage) ---")
    stop(server)
    server = start(port)

    cold = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("tras reiniciar, el GET es 500 (falla cerrado, no 404)", cold.status_code == 500,
          str(cold.status_code))
    check("el cuerpo declara corrupción, no ausencia",
          "corrupt" in cold.text.lower(), cold.text[:140])

    # 5) un proyecto sano sobrevive y se declara leído del artefacto
    healthy_id = "astra-m3-healthy"
    httpx.post(f"{endpoint}/api/v1/projects",
               json={"objective": "M3: a cold read of a healthy artifact is persisted state",
                     "project_id": healthy_id}, timeout=60.0)
    stop(server)
    server = start(port)
    healthy = httpx.get(f"{endpoint}/api/v1/projects/{healthy_id}", timeout=30.0)
    check("un artefacto sano se lee 200 tras reiniciar", healthy.status_code == 200,
          str(healthy.status_code))
    healthy_body = healthy.json()
    print("\n--- lectura EN FRÍO de un artefacto sano ---")
    for key in ("status", "stage", "status_source", "persisted_artifact_status"):
        print(f"  {key}: {healthy_body.get(key)}")
    check("y ahí sí se declara leído del estado persistido",
          healthy_body["status_source"] == "PERSISTED_STATE", healthy_body["status_source"])
    check("con el artefacto verificado explícitamente",
          healthy_body["persisted_artifact_status"] == "VERIFIED_FROM_ARTIFACT",
          healthy_body["persisted_artifact_status"])

    # 6) las demarcaciones de siempre siguen en pie
    check("PLANNED != EXECUTED: la prueba no se declara ejecutada",
          healthy_body["scientific_status"] == "NOT_VALIDATED"
          and healthy_body["secure_sandbox_status"] != "ISOLATED_BOUND_PASS",
          f"{healthy_body['scientific_status']}/{healthy_body['secure_sandbox_status']}")
    check("BLOCKED != success",
          not (healthy_body["status"] == "success"
               and healthy_body["verification_status"] in {"FAIL", "NOT_EVALUATED"}),
          f"{healthy_body['status']}/{healthy_body['verification_status']}")
finally:
    stop(server)

print("\n=== RESULTADO ===")
if failures:
    print("CONTRATO DE PROCEDENCIA INCUMPLIDO por el servidor real:")
    for item in failures:
        print("  -", item)
    raise SystemExit(1)
print("CONTRATO M3 VERIFICADO CONTRA EL SERVIDOR REAL.")
print("La limitación de K1 queda DECIDIDA: el caché es aceptable, la etiqueta no.")