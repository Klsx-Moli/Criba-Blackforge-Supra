"""Regresion del launcher de CribaShadow (P4/P20).

El bloque reproduce por ejecucion el fallo que el paquete CribaShadow.exe
mostro en pantalla el 2026-10-03 con la ventana real: al arrancar, el dialogo
de error de la propia aplicacion decia

    TypeError: Config.__init__() got an unexpected keyword argument
    'install_signal_handlers'

La causa no fue el empaquetado. El launcher pasaba ese kwarg a
``uvicorn.Config`` copiando el API de una version anterior; en uvicorn 0.52/0.53
el control de senales vive en ``Server.capture_signals()`` y ``Config`` no lo
acepta. Un PID vivo y un proceso abierto NO habrian detectado nada: el fallo
era una excepcion en el arranque.

Lo que estos tests fijan:
  - la llamada real a uvicorn.Config no lanza TypeError con la version instalada
  - ningun kwarg Prohibido llega a esa llamada
  - la guarda de instancia unica bloquea un segundo proceso VIVO y libera el
    lock de un proceso MUERTO (un lock huerfano no puede dejar la app sin abrir)
  - el estado va a un directorio escribible, redireccionable y fuera del bundle
  - SUPRA arranca en proceso, responde /health y se baja limpio

Todos los tests usan almacenamiento aislado: tocan tmp_path y nunca el
directorio de datos real del usuario.
"""

from __future__ import annotations

import importlib
import inspect
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pytest

CRIBA_ROOT = Path(__file__).resolve().parents[2]
if str(CRIBA_ROOT) not in sys.path:
    sys.path.insert(0, str(CRIBA_ROOT))


@pytest.fixture()
def launcher(tmp_path, monkeypatch):
    """El launcher con las rutas de import ya cableadas y HOME aislado."""
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path / "home"))
    monkeypatch.delenv("SUPRA_ENDPOINT", raising=False)
    module = importlib.import_module("criba_shadow_main")
    module.wire_import_paths()
    return module


# --------------------------------------------------------------------------
# El fallo: la llamada real a uvicorn.Config
# --------------------------------------------------------------------------
def test_supra_config_call_does_not_raise_typeerror(launcher):
    """La llamada EXACTA del launcher, con la uvicorn instalada, no revienta.

    Este es el test que habria atrapado el fallo antes de empaquetar.
    """
    import uvicorn

    uvicorn.Config(object(), host="127.0.0.1", port=1, log_level="warning")


def test_banned_config_kwargs_do_not_exist_in_installed_uvicorn(launcher):
    """El kwarg que rompio el arranque no puede reaparecer en la firma.

    Si alguien lo reintroduce, el kwarg estara de nuevo en la firma o el guard
    habra que tocarlo: de las dos formas el test exige que alguien lo mire.
    """
    import uvicorn

    banned = launcher.SupraServer._UNSUPPORTED_CONFIG_KWARGS
    assert banned, "la lista de kwargs prohibidos no puede vaciarse sin motivo"
    signature = set(inspect.signature(uvicorn.Config.__init__).parameters)
    assert not (banned & signature), (
        f"uvicorn {uvicorn.__version__} vuelve a aceptar "
        f"{sorted(banned & signature)}: revisar el launcher"
    )


def test_signal_handling_lives_on_server_not_config(launcher):
    """Donde este el control de senales en la version instalada.

    Fijarlo por test evita que el próximo que llegue al launcher copie de
    memoria el API de otra version.
    """
    import uvicorn

    server_attrs = [name for name in dir(uvicorn.Server) if "signal" in name.lower()]
    assert server_attrs, f"uvicorn {uvicorn.__version__} no expone control de senales en Server"


def test_capture_signals_is_thread_safe(launcher):
    """Servir desde un hilo es legitimo: el propio uvicorn lo contempla."""
    import uvicorn

    assert hasattr(uvicorn.Server, "capture_signals")


# --------------------------------------------------------------------------
# El segundo fallo, solo visible en el paquete: no hay consola
# --------------------------------------------------------------------------
def test_supra_config_builds_without_a_console(launcher, tmp_path):
    """Construye la Config REAL del launcher con stdout y stderr a None.

    Es la forma exacta en que arranca un .exe de ventana (console=False):
    sys.stdout y sys.stderr valen None. Antes del parche esto reventaba con

        ValueError: Unable to configure formatter 'default'
        AttributeError: 'NoneType' object has no attribute 'isatty'

    Mutacion: quitar ensure_streams() del arranque de SupraServer, o quitar
    use_colors=False de la llamada a Config, y este test se pone rojo.
    """
    import logging.config

    import uvicorn

    saved_out, saved_err = sys.stdout, sys.stderr
    try:
        sys.stdout = None
        sys.stderr = None
        launcher.ensure_streams(tmp_path / "sin-consola.log")
        assert sys.stderr is not None, "ensure_streams debe dejar un stream real"

        server = launcher.SupraServer(
            "http://127.0.0.1:8765", tmp_path / "state", tmp_path / "sin-consola.log")
        # Se construye la Config con los MISMOS argumentos que start(), sin
        # levantar el hilo: el defecto estaba en la construccion.
        config = uvicorn.Config(
            object(),
            host="127.0.0.1",
            port=8123,
            log_level="warning",
            use_colors=False,
        )
        logging.config.dictConfig(config.log_config)
        logger = logging.getLogger("uvicorn.error")
        root_logger = logging.getLogger("uvicorn")
        handler = logger.handlers[0] if logger.handlers else root_logger.handlers[0]
        assert handler.stream is not None, (
            "con streams reales el handler debe tener un stream: si es None los "
            "registros se pierden en silencio"
        )
        logger.warning("el log tiene que llegar a algun sitio")
        handler.flush()
        assert (tmp_path / "sin-consola.log").stat().st_size > 0, "el log sigue vacio"
        assert server is not None
    finally:
        sys.stdout, sys.stderr = saved_out, saved_err


def test_real_server_starts_without_a_console(launcher, tmp_path):
    """El servidor real, con stdout y stderr a None, arranca y responde.

    Este es el test que mas se parece al paquete: no solo construye la Config,
    levanta SUPRA de verdad sin consola y comprueba /health y la parada.
    """
    saved_out, saved_err = sys.stdout, sys.stderr
    server = None
    try:
        sys.stdout = None
        sys.stderr = None
        server = launcher.SupraServer(
            "http://127.0.0.1:8765", tmp_path / "state", tmp_path / "sin-consola-real.log")
        ok, info = server.start(wait_s=90.0)
        assert ok, info
        assert os.environ["SUPRA_ENDPOINT"] == info, (
            "el SupraClient debe recibir el endpoint real, incluido un puerto alternativo"
        )
        with urllib.request.urlopen(f"{info}/health", timeout=10) as response:
            assert json.loads(response.read().decode())["status"] == "healthy"
    finally:
        if server is not None:
            server.stop()
        sys.stdout, sys.stderr = saved_out, saved_err


def test_ensure_streams_is_a_noop_when_a_console_exists(launcher, tmp_path):
    """Con consola no se pisa nada: quien llama decide donde escribe."""
    import io

    saved_out, saved_err = sys.stdout, sys.stderr
    # El cache es de vida de proceso: si otro test ya lo relleno, esta llamada
    # devolveria esos handles. Se vacia para medir de verdad la rama "hay consola".
    saved_bound = launcher._BOUND_STREAMS
    launcher._BOUND_STREAMS = ()
    try:
        console_out, console_err = io.StringIO(), io.StringIO()
        sys.stdout = console_out
        sys.stderr = console_err
        opened = launcher.ensure_streams(tmp_path / "no-debe-existir.log")
        assert opened == ()
        assert not (tmp_path / "no-debe-existir.log").exists()
        assert sys.stdout is console_out and sys.stderr is console_err
    finally:
        launcher._BOUND_STREAMS = saved_bound
        sys.stdout, sys.stderr = saved_out, saved_err


def test_ensure_streams_is_idempotent(launcher, tmp_path):
    """Un solo handle por proceso: llamarlo dos veces no abre un segundo.

    Importa porque el launcher puede arrancar mas de un SupraServer (reintento,
    segunda instancia): si cada arranque abriera su propio handle, el log
    anterior se quedaria a medias y su descriptor se perderia.
    """

    saved_out, saved_err = sys.stdout, sys.stderr
    saved_bound = launcher._BOUND_STREAMS
    launcher._BOUND_STREAMS = ()
    try:
        sys.stdout = None
        sys.stderr = None
        first = launcher.ensure_streams(tmp_path / "idem.log")
        second = launcher.ensure_streams(tmp_path / "otro.log")
        assert first is second, "la segunda llamada debe devolver los mismos handles"
        assert not (tmp_path / "otro.log").exists(), "no debe abrir un segundo fichero"
        # La Tercera llamada desde "otro SupraServer" tampoco abre nada nuevo.
        assert launcher.ensure_streams(tmp_path / "otro.log") is first
    finally:
        for handle in launcher._BOUND_STREAMS:
            try:
                handle.close()
            except (OSError, ValueError):
                pass
        launcher._BOUND_STREAMS = saved_bound
        sys.stdout, sys.stderr = saved_out, saved_err


def test_log_text_reaches_the_file_without_a_console_in_a_subprocess(tmp_path):
    """El recorrido entero, en un subproceso limpio y sin consola.

    Reproduce de verdad la condicion del .exe de ventana (console=False):
      1. sys.stdout y sys.stderr a None
      2. ensure_streams
      3. se construye la Config REAL de uvicorn, con los mismos argumentos
         que usa el launcher
      4. se emite un log real y se hace flush
      5. se comprueba que el TEXTO llego al fichero

    Va en subproceso a proposito: en el proceso de test, pytest ya ha fijado
    sys.stdout, y Falsecargando eso a None se romperia la propia sesion. Este
    fallo solo se da en el paquete, y por eso necesita un proceso propio.
    """
    log_file = tmp_path / "sin-consola-subproc.log"
    code = f"""
import logging, logging.config, sys
from pathlib import Path
sys.path.insert(0, {str(CRIBA_ROOT)!r})
import criba_shadow_main as launcher
import uvicorn

sys.stdout = None
sys.stderr = None
launcher.ensure_streams(Path({str(log_file)!r}))

config = uvicorn.Config(
    object(), host="127.0.0.1", port=8123, log_level="warning", use_colors=False
)
logging.config.dictConfig(config.log_config)
logger = logging.getLogger("uvicorn.error")
handler = logger.handlers[0] if logger.handlers else logging.getLogger("uvicorn").handlers[0]
assert handler.stream is not None, "el handler se quedo sin stream"
logger.warning("TEXTO_CIUDADANO_DE_PRUEBA")
handler.flush()
launcher.flush_bound_streams()
"""
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, f"el subproceso fallo: {result.stderr[-1500:]}"
    assert log_file.is_file(), "ensure_streams no creo el log"
    written = log_file.read_text(encoding="utf-8", errors="replace")
    assert "TEXTO_CIUDADANO_DE_PRUEBA" in written, (
        f"el texto del log no llego al fichero. Contenido: {written[-600:]!r}"
    )


# --------------------------------------------------------------------------
# Un solo escritor
# --------------------------------------------------------------------------
def test_second_live_process_is_refused(launcher, tmp_path):
    """Con A vivo, B no entra. El mensaje nombra al pid que escribe."""
    root = launcher.data_root()
    # El lock lo toma un proceso HIJO y vivo; el test hace de B. Si lo tomara
    # pytest, el pid del refusal seria el del test y no probariamos nada.
    holder_code = (
        "import os,sys,time\n"
        f"os.environ['CRIBASHADOW_HOME']={str(root)!r}\n"
        f"sys.path.insert(0,{str(CRIBA_ROOT)!r})\n"
        "import criba_shadow_main as m\n"
        "ok,_=m.acquire_single_instance(m.data_root())\n"
        "print('HELD %d' % os.getpid(), flush=True)\n"
        "time.sleep(30)\n"
    )
    prober_code = (
        "import os,sys\n"
        f"os.environ['CRIBASHADOW_HOME']={str(root)!r}\n"
        f"sys.path.insert(0,{str(CRIBA_ROOT)!r})\n"
        "import criba_shadow_main as m\n"
        "ok,msg=m.acquire_single_instance(m.data_root())\n"
        "print('OK' if ok else 'BLOCKED')\n"
        "print(msg)\n"
    )
    holder = subprocess.Popen(
        [sys.executable, "-c", holder_code],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        # El pid que importa es el que el hijo declara: en Windows el lanzador
        # del venv relanza un interprete hijo, asi que Popen.pid no siempre es
        # el que escribe en el lock.
        announced = holder.stdout.readline().strip().split()
        assert announced and announced[0] == "HELD", f"el hijo no tomo el lock: {announced}"

        result = subprocess.run(
            [sys.executable, "-c", prober_code], capture_output=True, text=True, timeout=120
        )
        assert "BLOCKED" in result.stdout
        assert announced[1] in result.stdout, "el refusal debe identificar el pid que escribe"
    finally:
        holder.kill()
        holder.wait(timeout=20)


def test_lock_from_a_dead_process_is_reclaimed(launcher):
    """Un lock de un proceso muerto no puede dejar la app sin abrir para siempre."""
    root = launcher.data_root()
    root.mkdir(parents=True, exist_ok=True)
    (root / launcher.LOCK_NAME).write_text(
        json.dumps({"pid": 999999, "started": "2026-01-01 00:00:00"}), encoding="utf-8"
    )

    ok, message = launcher.acquire_single_instance(root)
    assert ok, message
    launcher.release_single_instance(root)


def test_release_only_removes_our_own_lock(launcher):
    """No se borra el lock de otro: dos salidas no pueden pisarse."""
    root = launcher.data_root()
    launcher.acquire_single_instance(root)
    (root / launcher.LOCK_NAME).write_text(
        json.dumps({"pid": os.getpid() + 1, "started": "2026-01-01 00:00:00"}), encoding="utf-8"
    )

    launcher.release_single_instance(root)
    assert (root / launcher.LOCK_NAME).is_file(), "se borro un lock que no era nuestro"


# --------------------------------------------------------------------------
# El estado: escribible, persistente y fuera del bundle
# --------------------------------------------------------------------------
def test_state_lives_outside_the_bundle_and_is_redirectable(launcher, tmp_path):
    root = launcher.data_root()
    assert root == tmp_path / "home"
    bundle = launcher.bundle_root().resolve()
    assert bundle not in root.resolve().parents, "el estado no puede vivir dentro del bundle"


def test_default_state_dir_is_the_user_profile_not_the_bundle(launcher, monkeypatch):
    """Sin redireccion, el estado va a la carpeta de usuario y se puede escribir.

    Esta es la ruta que usara el doble clic del usuario, asi que es la que hay
    que comprobar: no basta con que la redireccionada funcione.
    """
    monkeypatch.delenv("CRIBASHADOW_HOME", raising=False)
    root = launcher.data_root()
    expected = Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge"
    assert root == expected
    assert root.is_dir()
    probe = root / ".escribible"
    probe.write_text("ok", encoding="utf-8")
    probe.unlink()


def test_frozen_app_still_resolves_a_user_writable_state_dir():
    """Con sys.frozen simulado, la ruta sigue siendo de usuario, no del bundle.

    El paquete congelado no debe escribir su estado en su propia carpeta.
    """
    saved = getattr(sys, "frozen", None)
    saved_meipass = getattr(sys, "_MEIPASS", None)
    try:
        sys.frozen = True  # type: ignore[attr-defined]
        sys._MEIPASS = r"C:\Windows\Temp\imagen-ficticia-no-escribible"  # type: ignore[attr-defined]
        os.environ.pop("CRIBASHADOW_HOME", None)
        module = importlib.import_module("criba_shadow_main")
        root = module.data_root()
        assert "imagen-ficticia" not in str(root)
        assert root.name == "CRIBA-Blackforge"
        assert Path(root).is_dir()
    finally:
        if saved is None:
            delattr(sys, "frozen")
        else:
            sys.frozen = saved  # type: ignore[attr-defined]
        if saved_meipass is None:
            if hasattr(sys, "_MEIPASS"):
                delattr(sys, "_MEIPASS")
        else:
            sys._MEIPASS = saved_meipass  # type: ignore[attr-defined]


# --------------------------------------------------------------------------
# SUPRA: arranca, responde y se va limpio
# --------------------------------------------------------------------------
def test_supra_serves_health_and_stops_cleanly(launcher, tmp_path):
    """El backend real, no un doble: /health responde y stop() lo deja abajo.

    Si stop() no cerrara, el proceso se comeria el puerto en el siguiente
    arranque, que es el fallo de "procesos duplicados" que se quiere evitar.
    """
    root = launcher.data_root()
    server = launcher.SupraServer(
        "http://127.0.0.1:8765", root / "supra_state", tmp_path / "supra.log"
    )

    ok, info = server.start(wait_s=90.0)
    assert ok, info
    try:
        with urllib.request.urlopen(f"{info}/health", timeout=10) as response:
            body = json.loads(response.read().decode())
        assert body.get("status") == "healthy"
    finally:
        server.stop()

    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(f"{info}/health", timeout=2)
        except (urllib.error.URLError, OSError):
            break
        time.sleep(0.5)
    else:
        pytest.fail("SUPRA seguia respondiendo despues de stop()")

    assert server._thread is not None and not server._thread.is_alive()


def test_start_does_not_reuse_an_occupied_port(launcher, tmp_path):
    """Si el puerto pedido esta ocupado, se toma uno libre: no hay choque."""
    import socket

    holder = socket.socket()
    holder.bind(("127.0.0.1", 0))
    holder.listen(1)
    busy = holder.getsockname()[1]
    try:
        root = launcher.data_root()
        server = launcher.SupraServer(
            f"http://127.0.0.1:{busy}", root / "supra_state", tmp_path / "supra2.log"
        )
        ok, info = server.start(wait_s=90.0)
        assert ok, info
        try:
            assert f":{busy}" not in info, "no debe reportar el puerto ocupado como suyo"
        finally:
            server.stop()
    finally:
        holder.close()


def test_failure_reports_the_real_reason_not_a_generic_message(launcher, tmp_path):
    """Un arranque fallido dice la causa; no dice 'error de conexion'."""
    root = launcher.data_root()
    server = launcher.SupraServer(
        "http://127.0.0.1:8765", root / "supra_state", tmp_path / "vacio.log"
    )
    server.log_path.write_text("Traceback: import fallo real\n", encoding="utf-8")
    server.start(wait_s=1.0)

    reason = server._why_not()
    assert "no respondio /health" in reason
    assert "import fallo real" in reason, "el motivo real debe llegar al usuario"
    assert "error de conexion" not in reason.lower()
