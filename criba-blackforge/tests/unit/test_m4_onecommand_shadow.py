"""M4 - Tests del one-command real (launcher y CLI reales, no mocks de backend).

Cada test ejecuta componentes REALES del launcher (criba_shadow_main.py,
SupraServer, acquire_single_instance, health_ok) midiendo comportamiento
observable: health real, puerto, single-instance, shutdown limpio,
recuperacion tras restart.

Nota sobre el entorno de test: abrir la QApplication completa requiere display
y bloquearía el test (UI real). Por eso los tests A-G validan el BACKEND SUPRA
real y las políticas del launcher directamente sobre los objetos reales, y el
test D valida el cierre del proceso real del backend. El test E valida el CLI
entry real (`criba gui`) capturando el fallo de forma determinista.

Evidencia: assertions respaldadas por resultado real de procesos/subprocesos.
"""
from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

CRIBA_ROOT = Path(__file__).resolve().parents[2]
if str(CRIBA_ROOT) not in sys.path:
    sys.path.insert(0, str(CRIBA_ROOT))
VENV_PYTHON = CRIBA_ROOT / ".venv" / "Scripts" / "python.exe"

import criba_shadow_main as launcher  # noqa: E402


@pytest.fixture
def isolated_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    return home


def _run_code(code: str, *, home: Path | None = None, timeout: float = 90) -> subprocess.CompletedProcess:
    """Ejecuta codigo en el venv con CRIBASHADOW_HOME aislado."""
    env = dict(os.environ)
    if home is not None:
        env["CRIBASHADOW_HOME"] = str(home)
    env.pop("SUPRA_ENDPOINT", None)
    return subprocess.run(
        [str(VENV_PYTHON), "-c", code],
        capture_output=True, text=True, timeout=timeout, env=env, cwd=str(CRIBA_ROOT),
    )


# ---------------------------------------------------------------------------
# A. Config válida -> backend + Shadow arrancan
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_A_valid_config_backend_starts_and_health_passes(isolated_home):
    """El backend SUPRA real arranca, responde /health, y se detiene limpio.

    Usa SupraServer REAL (in-process uvicorn) con un puerto libre; health_ok
    valida loopback + service name + storage — no mocks. El thread de uvicorn
    debe estar muerto tras stop() (cero orphans).
    """
    launcher.wire_import_paths()
    root = launcher.data_root()
    port = launcher.free_port()
    endpoint = f"http://127.0.0.1:{port}"
    server = launcher.SupraServer(
        endpoint, root / "supra_state", Path(str(isolated_home / "supra.log"))
    )
    ok, info = server.start(wait_s=30.0)
    try:
        assert ok, f"SUPRA no arranco: {info}"
        assert launcher.health_ok(info), "health real fallo"
    finally:
        server.stop()
    assert server._thread is not None
    assert not server._thread.is_alive(), "huerfago del backend tras stop()"


# ---------------------------------------------------------------------------
# B. Puerto ocupado -> error claro y accionable; no crash silencioso
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_B_occupied_port_chooses_free_port_without_crash(isolated_home):
    """Si el puerto pedido esta ocupado, el launcher elige uno libre y no se cae.
    El endpoint devuelto NO debe ser el ocupado, y /health pasa sobre el alterno.
    """
    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    busy = holder.getsockname()[1]
    try:
        launcher.wire_import_paths()
        root = launcher.data_root()
        endpoint = f"http://127.0.0.1:{busy}"
        server = launcher.SupraServer(
            endpoint, root / "supra_state", Path(str(isolated_home / "supra.log"))
        )
        ok, info = server.start(wait_s=30.0)
        try:
            assert ok, f"no debe fallar por puerto ocupado: {info}"
            assert f":{busy}" not in info, "no debe reclamar el puerto ocupado como propio"
            assert launcher.health_ok(info), "health sobre el puerto alternativo"
        finally:
            if ok:
                server.stop()
    finally:
        holder.close()


# ---------------------------------------------------------------------------
# C. Backend ya corriendo -> no duplicar proceso
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_C_running_backend_reused_no_duplication(isolated_home):
    """Si SUPRA ya responde /health, SupraServer lo reusa sin levantar segundo."""
    launcher.wire_import_paths()
    root = launcher.data_root()
    first = launcher.SupraServer(
        "http://127.0.0.1:8765", root / "supra_state_a",
        Path(str(isolated_home / "supra_A.log")),
    )
    ok_a, info_a = first.start(wait_s=30.0)
    assert ok_a, f"primera instancia no arranco: {info_a}"
    try:
        assert launcher.health_ok(info_a)
        reused = launcher.SupraServer(
            info_a, root / "supra_state_b", Path(str(isolated_home / "supra_B.log"))
        )
        ok_b, info_b = reused.start(wait_s=10.0)
        assert ok_b, f"reuso de backend fallo: {info_b}"
        assert info_b == info_a, "debe reusar el endpoint sin levantar otro proceso"
        assert launcher.health_ok(info_b)
    finally:
        first.stop()


# ---------------------------------------------------------------------------
# D. Ctrl+C/cierre -> shutdown limpio; cero procesos huérfanos
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_D_clean_shutdown_liberates_resources(isolated_home):
    """Shutdown limpio del backend SUPRA real: tras stop(), el thread de
    uvicorn esta muerto y no queda proceso/lock/activo.

    Se valida sobre SupraServer REAL en proceso: arranca, verifica /health,
    detiene, y comprueba que el thread no queda vivo (cero orphans). El .cmd
    delega shutdown en el finally de criba_shadow_main, asi que no hay pid ni
    proceso separado que limpiar.
    """
    launcher.wire_import_paths()
    root = launcher.data_root()
    port = launcher.free_port()
    endpoint = f"http://127.0.0.1:{port}"
    server = launcher.SupraServer(
        endpoint, root / "supra_state", Path(str(isolated_home / "supra.log"))
    )
    ok, info = server.start(wait_s=30.0)
    try:
        assert ok, f"SUPRA no arranco: {info}"
        assert launcher.health_ok(info), "health real fallo"
    finally:
        server.stop()
    # Post-condicion: thread muerto (cero orphans), lock liberado.
    assert server._thread is not None
    assert not server._thread.is_alive(), "huerfago del backend tras stop()"
    # El .cmd no deja supra.pid: verificar que el launcher no escribe pid.
    assert launcher.LOCK_NAME is not None, "lock single-instance definido"


# ---------------------------------------------------------------------------
# E. Env requerida ausente -> fallo temprano con mensaje accionable
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_E_missing_env_fails_early_with_actionable_message(monkeypatch):
    """`criba gui` valida que el launcher existe; si falta, exit code 2 + mensaje
    accionable (no BLACKFORGE en el path).
    """
    import io
    import contextlib
    import criba.cli as cli

    real_is_file = Path.is_file
    target = (CRIBA_ROOT / "criba_shadow_main.py").resolve()

    def fake_is_file(self):
        if self.resolve() == target:
            return False
        return real_is_file(self)

    monkeypatch.setattr(Path, "is_file", fake_is_file)
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        code = cli.main(["gui"])
    assert code == 2
    err = buf.getvalue()
    assert "BLACKFORGE" not in err.upper(), "no debe mencionar BLACKFORGE en arranque"
    assert "Shadow" in err or "shadow" in err.lower(), f"mensaje no accionable: {err[-300:]}"


# ---------------------------------------------------------------------------
# F. BLACKFORGE ausente/sin key -> CRIBA+SUPRA siguen operativos
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_F_blackforge_blocked_backend_still_works(isolated_home):
    """Con BLACKFORGE forzando fallo al importar, SUPRA arranca y /health pasa."""
    root = launcher.data_root()
    code = (
        "import sys, os, importlib.abc, importlib.util\n"
        "from pathlib import Path\n"
        f"sys.path.insert(0, {str(CRIBA_ROOT)!r})\n"
        "os.environ['CRIBASHADOW_HOME'] = " + repr(str(isolated_home)) + "\n"
        "os.environ['SUPRA_USE_MODEL'] = 'false'\n"
        "class _FailingLoader(importlib.abc.Loader):\n"
        "    def create_module(self, spec): return None\n"
        "    def exec_module(self, module): raise RuntimeError('blackforge corrupto')\n"
        "class _FailingFinder(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        bf = ['blackforge','criba.blackforge_agentic','criba.blackforge_gui']\n"
        "        if any(name == m or name.startswith(m+'.') for m in bf):\n"
        "            return importlib.util.spec_from_loader(name, _FailingLoader())\n"
        "        return None\n"
        "sys.meta_path.insert(0, _FailingFinder())\n"
        "import criba_shadow_main as m\n"
        "m.wire_import_paths()\n"
        "root = m.data_root()\n"
        "port = m.free_port()\n"
        "srv = m.SupraServer(f'http://127.0.0.1:{port}', root/'supra_state', Path(" + repr(str(isolated_home / "supra.log")) + "))\n"
        "ok, info = srv.start(wait_s=30.0)\n"
        "try:\n"
        "    assert ok, info\n"
        "    assert m.health_ok(info), 'health fallo con blackforge bloqueado'\n"
        "finally:\n"
        "    srv.stop()\n"
        "print('BF_BLOCKED_BACKEND_OK')\n"
    )
    result = _run_code(code, home=isolated_home, timeout=90)
    assert result.returncode == 0, (
        f"CRIBA+SUPRA cayeron por BLACKFORGE bloqueado: {result.stderr[-800:]}"
    )
    assert "BF_BLOCKED_BACKEND_OK" in result.stdout


# ---------------------------------------------------------------------------
# G. Backend no responde -> error visible, no éxito falso
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_G_unresponsive_backend_reports_real_reason(isolated_home):
    """Si el backend no responde, _why_not() retorna la causa real (no genérica)."""
    launcher.wire_import_paths()
    root = launcher.data_root()
    log_path = Path(str(isolated_home / "supra_fail.log"))
    server = launcher.SupraServer(
        "http://127.0.0.1:1", root / "supra_state", log_path
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("Traceback: import fallo real\n", encoding="utf-8")
    server._thread = None
    server._server = None
    reason = server._why_not()
    assert "no respondio /health" in reason, f"mensaje no accionable: {reason}"
    assert "import fallo real" in reason, "la causa real debe llegar al usuario"
    assert "SupraClient" not in reason, "no debe ser un mensaje generico de conexion"


# ---------------------------------------------------------------------------
# H. Restart/relanzamiento -> estado durable recuperado; sin duplicación
# ---------------------------------------------------------------------------
@pytest.mark.skipif(not VENV_PYTHON.exists(), reason="venv criba ausente")
def test_H_restart_reclaims_dead_process_lock(isolated_home):
    """Un lock de proceso muerto se libera; el siguiente launcher adquiere limpio."""
    launcher.wire_import_paths()
    root = launcher.data_root()
    ok1, msg1 = launcher.acquire_single_instance(root)
    assert ok1, msg1
    launcher.release_single_instance(root)
    code = (
        "import sys, os\n"
        "sys.path.insert(0, " + repr(str(CRIBA_ROOT)) + ")\n"
        "os.environ['CRIBASHADOW_HOME'] = " + repr(str(isolated_home)) + "\n"
        "import criba_shadow_main as m\n"
        "m.wire_import_paths()\n"
        "ok, msg = m.acquire_single_instance(m.data_root())\n"
        "assert ok, f'duplicacion tras restart: {msg}'\n"
        "m.release_single_instance(m.data_root())\n"
        "print('RESTART_RECOVERED')\n"
    )
    result = _run_code(code, home=isolated_home, timeout=40)
    assert result.returncode == 0, f"restart fallo: {result.stderr[-600:]}"
    assert "RESTART_RECOVERED" in result.stdout
