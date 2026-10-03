"""Captura de la ventana REAL de Shadow tras el slice vertical.

Offscreen render + grab: prueba que el estado de SUPRA es VISIBLE, no solo que
existe en un diccionario. Escribe el PNG y el texto que la ventana muestra.
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
OUT = HERE / "m2_slice_window.png"

STORAGE = Path(tempfile.mkdtemp(prefix="astra-m2-shot-"))
os.environ["SUPRA_STORAGE_DIR"] = str(STORAGE)
os.environ["SUPRA_USE_MODEL"] = "false"
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["CRIBA_MODEL_CONFIG"] = str(STORAGE / "models.json")
for path in (str(CRIBA_SRC), str(SUPRA_SRC), str(SHADOW_UI)):
    if path not in sys.path:
        sys.path.insert(0, path)

import httpx  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


port = free_port()
endpoint = f"http://127.0.0.1:{port}"
log = open(STORAGE.parent / "shot-uvicorn.log", "w", encoding="utf-8")
server = subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "supra_agentic.service:app",
     "--host", "127.0.0.1", "--port", str(port), "--log-level", "warning"],
    cwd=str(ROOT / "supra"), stdout=log, stderr=subprocess.STDOUT,
    env={**os.environ, "PYTHONPATH": str(SUPRA_SRC), "SUPRA_STORAGE_DIR": str(STORAGE)},
)
try:
    for _ in range(60):
        try:
            if httpx.get(f"{endpoint}/health", timeout=3.0).status_code == 200:
                break
        except Exception:
            time.sleep(1.0)
    os.environ["SUPRA_ENDPOINT"] = endpoint

    app = QApplication.instance() or QApplication(sys.argv)
    from shadow_window import ShadowWindow
    from criba.ui import actions

    window = ShadowWindow()
    window.resize(1680, 1050)
    window.show()
    app.processEvents()

    window.header.problem_input.setText(
        "Reducir el número de permisos excesivos concedidos a un agente sin "
        "perder trazabilidad de las decisiones."
    )
    window.header.problem_input.returnPressed.emit()
    app.processEvents()

    actions.on_generar(window)
    deadline = time.time() + 240
    while time.time() < deadline and window.packet is None:
        app.processEvents()
        time.sleep(0.05)
    assert window.packet is not None

    QTest.mouseClick(window.right_panel.supra_e2e, Qt.MouseButton.LeftButton)
    app.processEvents()
    deadline = time.time() + 240
    while time.time() < deadline and getattr(window, "_live_workers", []):
        app.processEvents()
        time.sleep(0.05)
    app.processEvents()

    # El detalle del candidato debe ser visible: sin candidato seleccionado la
    # ventana muestra su texto honesto y no hay nada que mostrar.
    view = window.candidates.view
    if view.model().rowCount() > 0:
        view.selectRow(0)
        app.processEvents()

    window.grab().save(str(OUT))
    print("PNG:", OUT)
    print("title:  ", window.refs["ideaTitle"].text())
    print("chip:   ", window.refs["ideaEstadoChip"].text())
    print("summary:", window.refs["ideaSummary"].text())

    # La imagen offscreen sale con glifos tofu (fuente del host, no del
    # producto), así que la prueba de VISIBILIDAD es la lectura del árbol de
    # widgets vivos: qué texto renderiza la ventana y si está visible.
    print("\n--- texto RENDERIZADO por widgets visibles ---")
    app.processEvents()
    for label, widget in (
        ("botón slice", window.right_panel.supra_e2e),
        ("nota slice", window.right_panel.findChildren(type(window.errorBannerText))[0]
         if False else None),
        ("detalle título", window.refs["ideaTitle"]),
        ("detalle chip", window.refs["ideaEstadoChip"]),
        ("detalle resumen", window.refs["ideaSummary"]),
    ):
        if widget is None:
            continue
        text = widget.text() if hasattr(widget, "text") else ""
        visible = widget.isVisible() and not widget.isHidden()
        print(f"  [{'VISIBLE' if visible else 'OCULTO '}] {label}: {text[:190]}")

    # Recorrido completo: ningún texto de la ventana empieza por 'shadow.'
    raw = set()
    for widget in window.findChildren(object):
        for attr in ("text", "placeholderText", "toolTip"):
            try:
                value = getattr(widget, attr)()
            except Exception:
                continue
            if isinstance(value, str) and value.startswith("shadow."):
                raw.add(value)
    print("  claves i18n crudas renderizadas:", sorted(raw) or "NINGUNA")
    window.close()
finally:
    server.terminate()
    try:
        server.wait(timeout=15)
    except subprocess.TimeoutExpired:
        server.kill()