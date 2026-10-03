"""Prueba de ejecución REAL del recorrido M2, con la salida del servidor.

No forma parte del commit de M2: es la sonda que imprime la EVIDENCIA del
recorrido completo (peticion, respuesta, persistencia tras reinicio) para
poder citarla. Usa los mismos componentes reales que el test de aceptación.

Salida esperada: el dossier que cruza la red, el estado real de SUPRA, y el
mismo estado después de matar y arrancar el servidor otra vez.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1] / "criba-blackforge"
sys.path.insert(0, str(REPO / "src"))
sys.path.insert(0, str(REPO / "shadow_ui"))

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import socket  # noqa: E402

import httpx  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

SUPRA_PYTHON = REPO.parent / "supra" / ".venv" / "Scripts" / "python.exe"
SUPRA_SRC = REPO.parent / "supra" / "src"

PROBLEM = (
    "Reducir el número de permisos excesivos concedidos a un agente sin perder "
    "trazabilidad de las decisiones."
)


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def start(storage: Path, port: int) -> subprocess.Popen:
    log = open(storage.parent / "uvicorn.log", "a", encoding="utf-8")
    p = subprocess.Popen(
        [str(SUPRA_PYTHON), "-m", "uvicorn", "supra_agentic.service:app",
         "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
        cwd=str(REPO.parent / "supra"),
        stdout=log, stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(SUPRA_SRC),
             "SUPRA_STORAGE_DIR": str(storage), "SUPRA_USE_MODEL": "false"},
    )
    for _ in range(90):
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=3.0).status_code == 200:
                return p
        except Exception:
            pass
        if p.poll() is not None:
            raise SystemExit("uvicorn murio:\n" + (storage.parent / "uvicorn.log").read_text()[-2000:])
        time.sleep(1.0)
    raise SystemExit("SUPRA no respondio /health")


def main() -> int:
    tmp = tempfile.TemporaryDirectory(prefix="astra-m2-evidence-")
    storage = Path(tmp.name)
    port = free_port()
    proc = start(storage, port)
    os.environ["SUPRA_ENDPOINT"] = f"http://127.0.0.1:{port}"
    os.environ["CRIBA_MODEL_CONFIG"] = str(storage / "models.json")

    print("=" * 78)
    print("EVIDENCIA M2 · RECORRIDO REAL, SIN MOCKS")
    print("=" * 78)
    print(f"SUPRA real   : http://127.0.0.1:{port}  (uvicorn, supra/.venv)")
    print(f"storage      : {storage}")

    # Confirma que SUPRA usa NUESTRO storage, no el del usuario.
    chk = subprocess.run(
        [str(SUPRA_PYTHON), "-c",
         "import os,sys;sys.path.insert(0,os.environ['PYTHONPATH']);"
         "from supra_agentic.state_manager import state_manager as s;"
         "print(getattr(s,'storage_dir','?'));print(getattr(s,'storage_mode','?'))"],
        capture_output=True, text=True, env={**os.environ, "SUPRA_STORAGE_DIR": str(storage)},
    )
    print(f"state_manager: {chk.stdout.strip() or chk.stderr.strip()[-300:]}")

    from criba.ui import actions
    from shadow_window import ShadowWindow

    app = QApplication.instance() or QApplication(sys.argv)
    win = ShadowWindow()
    win.show()
    app.processEvents()

    try:
        # 1) proyecto desde la cabecera
        win.header.problem_input.setText(PROBLEM)
        win.header.problem_input.returnPressed.emit()
        app.processEvents()
        print(f"\n[1] proyecto creado desde la cabecera: {win.problem[:60]}...")

        # 2) nucleo REAL
        actions.on_generar(win)
        dl = time.time() + 240
        while time.time() < dl and win.packet is None:
            app.processEvents(); time.sleep(0.05)
        ideas = win.packet["innovation"]["ideas"]
        print(f"[2] nucleo determinista REAL: {len(ideas)} ideas")

        # 3) dossier real
        idea = ideas[0]
        dossier = actions._prepare_dossier_for_selected_idea(win)
        print(f"[3] dossier real: {dossier['dossier_id']}  estado={dossier['estado']}")
        pd = dossier["prueba_discriminante"]
        print(f"    H1 (hipotesis)          : {pd.get('afirmacion_decisiva','')[:90]}")
        print(f"    H2 (alternativa)        : {pd.get('alternativa_explicativa','')[:90]}")
        print(f"    mecanismo               : {pd.get('mecanismo','')[:90]}")
        print(f"    observable              : {pd.get('observable','')[:90]}")
        print(f"    regla de decision       : {pd.get('regla_decision','')[:90]}")
        print(f"    condicion de fracaso    : {pd.get('condicion_fracaso','')[:90]}")
        print(f"    estado_prueba           : {pd.get('estado_prueba')}")

        # 4) boton real -> SupraClient real -> SUPRA real
        captured: list[dict] = []
        real_exec = actions._execute_supra_vertical

        def cap(d, pid, client=None):
            captured.append(d)
            return real_exec(d, pid, client=client)

        actions._execute_supra_vertical = cap
        pid_value = None
        try:
            win.right_panel.supra_e2e.click()
            dl = time.time() + 240
            while time.time() < dl and getattr(win, "_live_workers", []):
                app.processEvents(); time.sleep(0.05)
            app.processEvents()
        finally:
            actions._execute_supra_vertical = real_exec

        project_id = win.refs["ideaTitle"].text().replace("SUPRA ", "").strip()
        pid_value = project_id
        print(f"\n[4] SupraClient REAL -> SUPRA API REAL: proyecto {project_id}")
        print(f"    chip VISIBLE={win.refs['ideaEstadoChip'].isVisibleTo(win)} "
              f"texto={win.refs['ideaEstadoChip'].text()!r}")

        # 5) estado real de la API
        body = httpx.get(f"http://127.0.0.1:{port}/api/v1/projects/{project_id}",
                         timeout=30.0).json()
        print("\n[5] GET /api/v1/projects/{id} — canales SEPARADOS:")
        for k in ("status", "status_scope", "completion_status", "workflow_status",
                  "stage", "verification_status", "scientific_status",
                  "secure_sandbox_status", "criba_planning_receipt_status",
                  "criba_mechanism_execution_status", "status_source"):
            print(f"    {k:38} = {body.get(k)}")
        rc = body["posture"].get("criba_dossier_receipt") or {}
        print(f"    receipt.criba_dossier_id           = {rc.get('criba_dossier_id')}")
        print(f"    receipt.execution_status           = {rc.get('execution_status')}")
        print(f"    receipt.scientific_status          = {rc.get('scientific_status')}")
        print(f"    receipt.receipt_scope              = {rc.get('receipt_scope')}")

        print("\n[6] LO QUE LA INTERFAZ MUESTRA (texto literal del widget):")
        print(f"    {win.refs['ideaTitle'].text()}")
        print(f"    {win.refs['ideaSummary'].text()}")

        # 7) persistencia: matar y arrancar
        proc.terminate(); proc.wait(timeout=20)
        proc = start(storage, port)
        after = httpx.get(f"http://127.0.0.1:{port}/api/v1/projects/{project_id}",
                          timeout=30.0).json()
        same = after["status"] == body["status"] and after["stage"] == body["stage"]
        print(f"\n[7] SERVIDOR REINICIADO · estado persistido identico: {same}")
        print(f"    status {after['status']} · stage {after['stage']} · "
              f"source {after['status_source']}")
        print(f"    receipt tras reinicio = "
              f"{(after['posture'].get('criba_dossier_receipt') or {}).get('criba_dossier_id')}")

        print("\n" + "=" * 78)
        print(f"CONTRATOS: BLOCKED!=success -> status={after['status']}; "
              f"PERSISTED->{after['status_source']}; "
              f"ejecucion mecanismo CRIBA={after.get('criba_mechanism_execution_status')}")
        print("=" * 78)
        return 0
    finally:
        win.close(); app.processEvents()
        proc.terminate()
        try:
            proc.wait(timeout=20)
        except Exception:
            proc.kill()


if __name__ == "__main__":
    raise SystemExit(main())