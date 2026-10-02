"""M2 · E2E de la SLICE VERTICAL REAL, sin mocks en la ruta certificada.

  ShadowWindow (offscreen) -> botón real -> actions.on_supra_vertical
  -> núcleo determinista de CRIBA -> dossier real -> SupraClient real (httpx/TCP)
  -> uvicorn supra_agentic.service:app real -> persistencia en disco
  -> GET /api/v1/projects/{id} -> la interfaz muestra el estado
  -> reinicio del servidor -> GET de nuevo

El servidor SUPRA es un SUBPROCESSO real de su propio componente; no hay
TestClient, ni MockTransport, ni monkeypatch del cliente en esta ruta. El
dossier que se inspecciona se CAPTURA envolviendo el despacho (no
sustituyéndolo), de modo que el objeto observado es el que cruzó la red.

El recorrido se ejecuta UNA vez por módulo y las aserciones leen ese resultado:
cuatro recorridos idénticos sólo multiplicarían el tiempo sin añadir cobertura.

Este archivo es el criterio de aceptación de la tarjeta: si esto pasa, un
usuario puede pulsar desde Shadow y ver un estado real de SUPRA.

Sentinela de mutación:
  * eliminar el GET de ``_execute_supra_vertical`` ->
    ``test_slice_reads_real_state_back_into_the_interface``
  * hardcodear ``status="success"`` en la UI ->
    ``test_blocked_is_shown_as_blocked_not_as_success``
  * rellenar una obligación del protocolo con un placeholder -> este archivo entero
  * romper el read path -> ``test_m2_read_path_channels.py``
"""

from __future__ import annotations

import os
import socket
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
SUPRA_SRC = REPO.parent / "supra" / "src"
CRIBA_SRC = REPO / "src"
SHADOW_UI = REPO / "shadow_ui"

pytest.importorskip("PySide6")

# The SUPRA venv is a separate component environment; each side runs under the
# interpreter that actually owns its package (measured: the SUPRA venv has no
# PySide6, so importing its server from the CRIBA interpreter is not a test).
SUPRA_PYTHON = REPO.parent / "supra" / ".venv" / "Scripts" / "python.exe"
if not SUPRA_PYTHON.is_file():  # pragma: no cover - environment guard
    pytest.skip("SUPRA venv not present; the real component cannot be launched")

# TemporaryDirectory objects must outlive the functions that create them: a
# collected directory is deleted out from under the state singleton and every
# assertion then fails with FileNotFoundError, which is a fixture artifact.
_LIVE_TEMP_DIRS: list[tempfile.TemporaryDirectory] = []

PROBLEM = (
    "Reducir el número de permisos excesivos concedidos a un agente sin perder "
    "trazabilidad de las decisiones."
)


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class _RealSupra:
    """The real SUPRA HTTP service, as a child process of its own component."""

    def __init__(self, storage: Path) -> None:
        self.storage = storage
        self.port = _free_port()
        self.endpoint = f"http://127.0.0.1:{self.port}"
        self.log_path = storage.parent / "astra-m2-uvicorn.log"
        self.proc: subprocess.Popen | None = None

    def start(self) -> None:
        self.log_path.write_text("", encoding="utf-8")
        handle = open(self.log_path, "a", encoding="utf-8")
        self.proc = subprocess.Popen(
            [str(SUPRA_PYTHON), "-m", "uvicorn", "supra_agentic.service:app",
             "--host", "127.0.0.1", "--port", str(self.port), "--log-level", "warning"],
            cwd=str(REPO.parent / "supra"),
            stdout=handle, stderr=subprocess.STDOUT,
            env={
                **os.environ,
                "PYTHONPATH": str(SUPRA_SRC),
                "SUPRA_STORAGE_DIR": str(self.storage),
                "SUPRA_USE_MODEL": "false",
            },
        )
        for _ in range(90):
            try:
                if httpx.get(f"{self.endpoint}/health", timeout=3.0).status_code == 200:
                    return
            except Exception:
                pass
            if self.proc.poll() is not None:
                break
            time.sleep(1.0)
        raise AssertionError(
            "el servidor SUPRA real no respondió /health: "
            + self.log_path.read_text(encoding="utf-8")[-2000:]
        )

    def stop(self) -> None:
        if self.proc is None:
            return
        self.proc.terminate()
        try:
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            self.proc.kill()
        self.proc = None

    def get_project(self, project_id: str) -> httpx.Response:
        return httpx.get(f"{self.endpoint}/api/v1/projects/{project_id}", timeout=30.0)


@dataclass
class _Slice:
    dossier: dict
    project_id: str
    summary: str
    chip: str
    title: str
    server_before_restart: dict = field(default_factory=dict)
    # VISIBILIDAD real, no solo el texto. ``QLabel.text()`` devuelve el
    # contenido también de un widget oculto, asi que leer el texto no
    # acredita que el estado se viera. Sin estos dos campos, un chip escrito
    # sobre un widget oculto pasaba la suite: fue exactamente lo que ocurria
    # con el arranque, que llama set_detail_empty(True) y oculta el chip.
    chip_visible: bool = False
    caption_visible: bool = True


@pytest.fixture(scope="module")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    for path in (str(CRIBA_SRC), str(SHADOW_UI)):
        if path not in sys.path:
            sys.path.insert(0, path)
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv)
    yield app
    app.processEvents()


@pytest.fixture(scope="module")
def slice_result(qapp):
    """Run the slice ONCE against a real SUPRA server and keep the outcome."""
    tmpdir = tempfile.TemporaryDirectory(prefix="astra-m2-storage-")
    _LIVE_TEMP_DIRS.append(tmpdir)
    storage = Path(tmpdir.name)
    supra = _RealSupra(storage)
    supra.start()

    os.environ["SUPRA_ENDPOINT"] = supra.endpoint
    os.environ["CRIBA_MODEL_CONFIG"] = str(storage / "models.json")

    from criba.ui import actions
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from shadow_window import ShadowWindow

    window = ShadowWindow()
    window.show()
    qapp.processEvents()
    try:
        # 1) create the project through the canonical header path
        window.header.problem_input.setText(PROBLEM)
        window.header.problem_input.returnPressed.emit()
        qapp.processEvents()
        assert window.problem == PROBLEM, "el proyecto no se creó desde la cabecera"

        # 2) the real deterministic CRIBA core (no LLM, no fixture)
        actions.on_generar(window)
        deadline = time.time() + 240
        while time.time() < deadline and window.packet is None:
            qapp.processEvents()
            time.sleep(0.05)
        assert window.packet is not None, "el núcleo real no produjo packet"
        assert window.packet["innovation"]["ideas"], "el packet no trae ideas"

        # 3) press the real widget. The dispatch is WRAPPED, never replaced, so
        #    the captured dossier is the object that crossed the network.
        dispatched: list[dict] = []
        real_execute = actions._execute_supra_vertical

        def _capturing(dossier, project_id, client=None):
            dispatched.append(dossier)
            return real_execute(dossier, project_id, client=client)

        actions._execute_supra_vertical = _capturing
        try:
            QTest.mouseClick(window.right_panel.supra_e2e, Qt.MouseButton.LeftButton)
            qapp.processEvents()
            deadline = time.time() + 240
            while time.time() < deadline and getattr(window, "_live_workers", []):
                qapp.processEvents()
                time.sleep(0.05)
            qapp.processEvents()
        finally:
            actions._execute_supra_vertical = real_execute

        assert len(dispatched) == 1, "el dossier real no cruzó la ruta"
        chip = window.refs["ideaEstadoChip"]
        outcome = _Slice(
            dossier=dispatched[0],
            project_id=window.refs["ideaTitle"].text().replace("SUPRA ", "").strip(),
            summary=window.refs["ideaSummary"].text(),
            chip=chip.text(),
            title=window.refs["ideaTitle"].text(),
            # isVisibleTo(window) y no isVisible(): un widget se considera
            # visible solo si todas sus ancestras lo son, asi que esto mide
            # lo que el usuario veria, no un flag local.
            chip_visible=bool(chip.isVisibleTo(window)),
            caption_visible=bool(window.candidates.detail_caption.isVisibleTo(window)),
        )
        response = supra.get_project(outcome.project_id)
        assert response.status_code == 200, response.text[:400]
        outcome.server_before_restart = response.json()

        # 4) persistence, measured: kill the process and read the state back
        supra.stop()
        supra.start()
        restarted = supra.get_project(outcome.project_id)
        assert restarted.status_code == 200, restarted.text[:400]
        outcome.server_after_restart = restarted.json()
        yield outcome
    finally:
        window.close()
        qapp.processEvents()
        supra.stop()


def test_slice_reads_real_state_back_into_the_interface(slice_result: _Slice) -> None:
    dossier = slice_result.dossier
    prueba = dossier["prueba_discriminante"]
    for field_name in (
        "afirmacion_decisiva", "alternativa_explicativa", "intervencion_prueba",
        "observable", "resultado_favorable_mecanismo",
        "resultado_favorable_alternativa", "regla_decision", "condicion_fracaso",
    ):
        assert str(prueba.get(field_name) or "").strip(), f"obligación vacía: {field_name}"
    assert dossier["estado"] == "SUPRA_EJECUCION_PENDIENTE"
    assert prueba["estado_prueba"] == "NO_EJECUTADA"

    assert "PERSISTED_STATE" in slice_result.summary, slice_result.summary
    assert "NO CONFIRMADA" not in slice_result.summary
    assert slice_result.project_id.startswith("astram2"), slice_result.project_id
    assert "SUPRA" in slice_result.chip


def test_real_state_is_actually_visible_not_just_written(slice_result: _Slice) -> None:
    """El estado tiene que LLEGAR A LA INTERFAZ, no solo existir en el widget.

    ``.text()`` funciona igual con el widget oculto, asi que este criterio no
    podia acreditarse leyendo texto: mide visibilidad real. Regresion medida: el
    arranque llama ``set_detail_empty(True)`` y oculta el chip, de modo que el
    estado devuelto por SUPRA se escribia en un widget que nadie veia mientras la
    suite pasaba. Se rompe este test -> ``actions._on_supra_vertical_done``
    vuelve a escribir sin encender el chip.
    """
    assert slice_result.chip_visible, (
        "el chip de estado real de SUPRA NO es visible: se escribió en un widget "
        "oculto. El recorrido no llega a la interfaz."
    )
    # La cabecera «Idea seleccionada» sigue oculta a proposito: el resultado de
    # SUPRA no es un candidato y nombrarlo seria una afirmacion falsa.
    assert not slice_result.caption_visible, (
        "la cabecera 'idea seleccionada' no debe anunciarse para un resultado de SUPRA"
    )


def test_slice_reads_real_state_back_into_the_interface_persisted(slice_result: _Slice) -> None:
    """What the interface claims must be what the server actually persisted."""
    dossier = slice_result.dossier
    body = slice_result.server_before_restart
    assert str(body["status"]) in slice_result.summary
    assert str(body["stage"]) in slice_result.summary
    assert body["status_source"] == "PERSISTED_STATE"
    receipt = body["posture"]["criba_dossier_receipt"]
    assert receipt["criba_dossier_id"] == dossier["dossier_id"]
    assert receipt["execution_status"] == "NOT_EXECUTED"
    assert receipt["scientific_status"] == "NOT_VALIDATED"
    assert receipt["receipt_scope"] == "PLANNED_DISCRIMINANT_PROTOCOL_ONLY"


def test_blocked_is_shown_as_blocked_not_as_success(slice_result: _Slice) -> None:
    """B02: BLOCKED != success, in the interface and in the persisted state."""
    body = slice_result.server_before_restart
    summary = slice_result.summary
    assert body["status"] != "success" or body["verification_status"] == "PASS"
    if body["status"] != "blocked":
        pytest.skip(f"esta corrida terminó {body['status']}; no aplica el caso BLOCKED")
    assert "status blocked" in summary, summary
    assert "workflow BLOCKED" in summary, summary
    assert "status success" not in summary, summary
    # Every mention of EXECUTED must be negated by NO.
    assert summary.upper().count("NO EJECUTADO") == summary.upper().count("EJECUTADO"), summary
    assert "VALIDADO" not in summary.upper() or "NOT_VALIDATED" in summary.upper()


def test_persisted_state_survives_a_server_restart(slice_result: _Slice) -> None:
    before = slice_result.server_before_restart
    after = slice_result.server_after_restart
    assert after["status"] == before["status"]
    assert after["stage"] == before["stage"]
    assert after["status_source"] == "PERSISTED_STATE"
    assert (after["posture"].get("criba_dossier_receipt") or {}).get(
        "criba_dossier_id") == slice_result.dossier["dossier_id"]


def test_slice_fails_closed_when_supra_is_unreachable(qapp) -> None:
    """No SUPRA means "not confirmed", never a fabricated success."""
    dead_port = _free_port()
    os.environ["SUPRA_ENDPOINT"] = f"http://127.0.0.1:{dead_port}"
    from criba.ui import actions
    from shadow_window import ShadowWindow

    window = ShadowWindow()
    window.show()
    qapp.processEvents()
    try:
        window.header.problem_input.setText(PROBLEM)
        window.header.problem_input.returnPressed.emit()
        qapp.processEvents()
        actions.on_generar(window)
        deadline = time.time() + 240
        while time.time() < deadline and window.packet is None:
            qapp.processEvents()
            time.sleep(0.05)
        assert window.packet is not None

        QTestClick(window, qapp)
        summary = window.refs["ideaSummary"].text()
        assert "NO CONFIRMADA" in summary, summary
        assert "status success" not in summary
        assert window.errorBanner.isVisibleTo(window)
    finally:
        window.close()
        qapp.processEvents()


def QTestClick(window, qapp) -> None:  # noqa: N802 - test helper, not an API
    """Click the real button and wait for the real worker to finish."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    QTest.mouseClick(window.right_panel.supra_e2e, Qt.MouseButton.LeftButton)
    qapp.processEvents()
    deadline = time.time() + 120
    while time.time() < deadline and getattr(window, "_live_workers", []):
        qapp.processEvents()
        time.sleep(0.05)
    qapp.processEvents()
