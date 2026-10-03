"""M2 · E2E REAL de la slice vertical, ejecutado contra el servidor SUPRA real.

No hay mocks en la ruta que se certifica:
  ShadowWindow (PySide6, offscreen) -> botón real -> actions.on_supra_vertical
  -> CRIBA core determinista -> preparar_dossier_desde_idea (real)
  -> SupraClient real (httpx sobre TCP) -> uvicorn supra_agentic.service:app
  -> persistencia en disco -> GET /api/v1/projects/{id} -> interfaz
  -> reinicio del servidor -> GET de nuevo (supervivencia real).

El dossier se captura del propio despacho (envuelto, NO sustituido) para poder
inspeccionar exactamente el que cruzó la red.

Imprime lo que REALMENTE ocurrió. Exit != 0 si el recorrido no se completa.
"""
from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[0]
SUPRA_SRC = ROOT / "supra" / "src"
CRIBA_SRC = ROOT / "criba-blackforge" / "src"
SHADOW_UI = ROOT / "criba-blackforge" / "shadow_ui"

STORAGE = Path(tempfile.mkdtemp(prefix="astra-m2-storage-"))
SUPRA_LOG = STORAGE.parent / "astra-m2-uvicorn.log"
os.environ["SUPRA_STORAGE_DIR"] = str(STORAGE)
os.environ["SUPRA_USE_MODEL"] = "false"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["CRIBA_MODEL_CONFIG"] = str(STORAGE / "models.json")

for path in (str(CRIBA_SRC), str(SUPRA_SRC), str(SHADOW_UI)):
    if path not in sys.path:
        sys.path.insert(0, path)

import httpx  # noqa: E402

failures: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    mark = "OK  " if condition else "FAIL"
    print(f"  [{mark}] {label}" + (f" :: {detail}" if detail else ""))
    if not condition:
        failures.append(label)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def start_supra(port: int) -> subprocess.Popen:
    log = open(SUPRA_LOG, "a", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "supra_agentic.service:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(ROOT / "supra"),
        stdout=log, stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(SUPRA_SRC), "SUPRA_STORAGE_DIR": str(STORAGE)},
    )
    for _ in range(60):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=3.0).status_code == 200:
                return proc
        except Exception:
            pass
        if proc.poll() is not None:
            break
        time.sleep(1.0)
    print(SUPRA_LOG.read_text(encoding="utf-8")[-2000:])
    raise SystemExit("SUPRA no arrancó")


def stop_supra(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()


port = free_port()
endpoint = f"http://127.0.0.1:{port}"
print(f"SUPRA real en {endpoint} (storage={STORAGE})")
server = start_supra(port)
check("servidor SUPRA real levantado", True)

try:
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    from shadow_window import ShadowWindow

    from criba.ui import actions

    # Captura del dossier REAL que se envía: se envuelve el despacho, no se
    # sustituye. El recorrido que se certifica sigue siendo el de producción.
    dispatched: list[dict] = []
    real_execute = actions._execute_supra_vertical

    def _capturing(dossier, project_id, client=None):
        dispatched.append(dossier)
        return real_execute(dossier, project_id, client=client)

    actions._execute_supra_vertical = _capturing

    os.environ["SUPRA_ENDPOINT"] = endpoint
    window = ShadowWindow()
    window.show()
    app.processEvents()

    PROBLEM = (
        "Reducir el número de permisos excesivos concedidos a un agente sin "
        "perder trazabilidad de las decisiones."
    )

    # 1) crear/abrir proyecto por la vía canónica del input de la cabecera
    window.header.problem_input.setText(PROBLEM)
    window.header.problem_input.returnPressed.emit()
    app.processEvents()
    check("proyecto creado desde Shadow", window.problem == PROBLEM, repr(window.problem)[:100])

    # 2) núcleo REAL de CRIBA (determinista, sin LLM)
    actions.on_generar(window)
    deadline = time.time() + 120
    while time.time() < deadline and window.packet is None:
        app.processEvents()
        time.sleep(0.05)
    check("núcleo CRIBA real generó packet", window.packet is not None)
    if window.packet is None:
        raise SystemExit(1)
    check("el packet trae ideas del núcleo",
          len(window.packet["innovation"]["ideas"]) > 0,
          f"{len(window.packet['innovation']['ideas'])} ideas")

    # 3) pulso del botón real -> SUPRA real -> GET -> interfaz
    QTest.mouseClick(window.right_panel.supra_e2e, Qt.MouseButton.LeftButton)
    app.processEvents()
    deadline = time.time() + 180
    while time.time() < deadline and getattr(window, "_live_workers", []):
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()

    summary = window.refs["ideaSummary"].text()
    chip = window.refs["ideaEstadoChip"].text()
    title = window.refs["ideaTitle"].text()
    print("\n--- lo que la interfaz muestra ---")
    print("  title:  ", title)
    print("  chip:   ", chip)
    print("  summary:", summary)

    check("el dossier real cruzó la ruta", len(dispatched) == 1)
    dossier = dispatched[0] if dispatched else {}
    prueba = dossier.get("prueba_discriminante", {})
    required = (
        "afirmacion_decisiva", "alternativa_explicativa", "intervencion_prueba",
        "observable", "resultado_favorable_mecanismo",
        "resultado_favorable_alternativa", "regla_decision", "condicion_fracaso",
    )
    empty = [k for k in required if not str(prueba.get(k) or "").strip()]
    check("dossier real con las 8 obligaciones", not empty, f"vacías: {empty}")
    check("estado del dossier sigue PENDIENTE",
          dossier.get("estado") == "SUPRA_EJECUCION_PENDIENTE")
    check("la prueba sigue NO EJECUTADA", prueba.get("estado_prueba") == "NO_EJECUTADA")

    check("la interfaz muestra estado leído del servidor", "PERSISTED_STATE" in summary)
    check("el botón no dejó estado de error", "NO CONFIRMADA" not in summary)
    check("el chip refleja el estado real de SUPRA", "SUPRA" in chip, chip)

    project_id = title.replace("SUPRA ", "").strip()
    check("la interfaz nombra un project_id real",
          project_id.startswith("astram2"), project_id)

    # 4) verificacion independiente por HTTP (no por lo que dice la UI)
    resp = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("GET directo al servidor devuelve 200", resp.status_code == 200, str(resp.status_code))
    body = resp.json() if resp.status_code == 200 else {}
    if body:
        print("\n--- GET directo (servidor) ---")
        for key in ("status", "status_scope", "completion_status", "workflow_status",
                    "verification_status", "scientific_status",
                    "secure_sandbox_status", "criba_planning_receipt_status",
                    "criba_mechanism_execution_status", "status_source"):
            print(f"  {key}: {body.get(key)}")
    check("estado persistido no es success sin motivo",
          not (body.get("status") == "success"
               and body.get("verification_status") in {"FAIL", "NOT_EVALUATED"}))
    receipt = (body.get("posture") or {}).get("criba_dossier_receipt")
    check("el receipt del dossier quedó persistido", isinstance(receipt, dict))
    if isinstance(receipt, dict):
        check("el receipt NO declara ejecución",
              receipt.get("execution_status") == "NOT_EXECUTED"
              and receipt.get("scientific_status") == "NOT_VALIDATED",
              f"{receipt.get('execution_status')}/{receipt.get('scientific_status')}")
        check("el receipt conserva la identidad del dossier",
              receipt.get("criba_dossier_id") == dossier.get("dossier_id"),
              f"{receipt.get('criba_dossier_id')} vs {dossier.get('dossier_id')}")
    check("lo que muestra la UI coincide con el servidor",
          str(body.get("status")) in summary and str(body.get("stage")) in summary,
          f"servidor={body.get('status')}/{body.get('stage')}")

    # 5) PERSISTENCIA REAL: reiniciar el servidor y volver a leer
    print("\n--- reinicio del servidor (mismo storage) ---")
    stop_supra(server)
    server = start_supra(port)
    resp2 = httpx.get(f"{endpoint}/api/v1/projects/{project_id}", timeout=30.0)
    check("tras reiniciar, el GET sigue 200", resp2.status_code == 200, str(resp2.status_code))
    if resp2.status_code == 200:
        body2 = resp2.json()
        check("el estado sobrevivió al reinicio",
              body2.get("status") == body.get("status")
              and body2.get("stage") == body.get("stage")
              and body2.get("status_source") == "PERSISTED_STATE",
              f"{body2.get('status')}/{body2.get('stage')}/{body2.get('status_source')}")
        check("el receipt sobrevivió al reinicio",
              ((body2.get("posture") or {}).get("criba_dossier_receipt") or {}).get(
                  "criba_dossier_id") == dossier.get("dossier_id"))

    window.close()
finally:
    stop_supra(server)

print("\n=== RESULTADO ===")
if failures:
    print("FALLOS:")
    for item in failures:
        print("  -", item)
    raise SystemExit(1)
print("SLICE VERTICAL REAL COMPLETA: Shadow -> CRIBA core -> dossier -> SUPRA real -> GET -> UI")
print("y el estado sobrevive a un reinicio del servidor (persistencia real).")