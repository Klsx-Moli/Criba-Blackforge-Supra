"""CribaShadow — launchpoint de la CRIBA Shadow UI canónica (paquete local).

Tres reglas que este archivo hace cumplir y que no son opcionales:

1. UN SOLO ESCRITOR. El almacenamiento se abre con un lock por directorio de
   datos. Si otra instancia ya lo tiene, se dice con un error real y se sale.
   Dos procesos peleándose por el mismo SQLite no son "dos ventanas", son dos
   escritores sobre los mismos proyectos.

2. SUPRA SE ARRANCA O SE CONECTA, NUNCA SE INVENTA. Se consulta /health. Si no
   responde, se levanta en proceso y se espera a que responda de verdad. Si no
   llega, se muestra el log real, no un "error de conexion".

3. EL ESTADO NO VIVE EN EL BUNDLE. Ni en un temporal ni junto al .exe. Vive en
   un directorio de usuario escribible, y se puede redirigir con
   CRIBASHADOW_HOME para probar sin tocar los proyectos existentes.

Sin secretos: aqui no se lee ni se escribe ninguna credencial. SUPRA corre con
SUPRA_USE_MODEL=false, asi que no necesita ninguna llave fisica.
"""

from __future__ import annotations

import inspect
import json
import os
import socket
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, TextIO

if TYPE_CHECKING:  # uvicorn se importa al arrancar, no al importar el launcher
    import uvicorn

APP_NAME = "CribaShadow"
LOCK_NAME = "CribaShadow.lock"
SUPRA_LOG_NAME = "supra-server.log"


# --------------------------------------------------------------------------
# Rutas: el bundle congelado y el arbol de fuentes se resuelven igual
# --------------------------------------------------------------------------
def bundle_root() -> Path:
    """Raiz de los recursos. Congelado apunta a _MEIPASS; fuente, al repo."""
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return Path(__file__).resolve().parent


def data_root() -> Path:
    """Directorio de estado: persistente, escribible y fuera del bundle."""
    override = os.getenv("CRIBASHADOW_HOME")
    base = (
        Path(override)
        if override
        else (Path(os.getenv("LOCALAPPDATA") or Path.home()) / "CRIBA-Blackforge")
    )
    base.mkdir(parents=True, exist_ok=True)
    return base


def wire_import_paths() -> None:
    """Que funcionen los imports con o sin congelar.

    Shadow UI: shadow_window / shadow_context son modulos sueltos, no paquete.
    SUPRA: supra_agentic, que vive al lado del repo en el monorepo.
    """
    root = bundle_root()
    candidates = [
        root,
        root / "src",
        root / "shadow_ui",
        root / "supra_src",
        root.parent / "supra" / "src",
        root.parent.parent / "supra" / "src",
    ]
    for path in candidates:
        text = str(path)
        if path.is_dir() and text not in sys.path:
            sys.path.insert(0, text)


# --------------------------------------------------------------------------
# 1. Un solo escritor
# --------------------------------------------------------------------------
def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return code.value == STILL_ACTIVE
            return False
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


# The lock is held by the operating system, not by the PID written to disk.
# A PID check followed by write_text() allowed two simultaneous first launches.
# Keep the guard inode/file stable even after release: unlinking it opens a
# second race between processes holding the old and new inodes.
_LOCK_MUTEX = threading.Lock()
_LOCK_HANDLE: TextIO | None = None
_LOCK_PATH: Path | None = None
_LOCK_BYTE = 4096  # Windows byte-range lock beyond JSON metadata: readers can inspect PID.


def _lock_handle(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(_LOCK_BYTE)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock_handle(handle: TextIO) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(_LOCK_BYTE)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def acquire_single_instance(root: Path) -> tuple[bool, str]:
    """Acquire a process-lifetime OS lock before touching the PID metadata."""
    global _LOCK_HANDLE, _LOCK_PATH
    lock = root / LOCK_NAME
    with _LOCK_MUTEX:
        if _LOCK_HANDLE is not None:
            return False, f"{APP_NAME} ya ha adquirido el bloqueo en este proceso."
        try:
            handle = lock.open("a+b")
        except OSError as exc:
            return False, f"No se pudo abrir el bloqueo de {APP_NAME}: {exc}"
        try:
            _lock_handle(handle)
        except OSError:
            handle.close()
            try:
                other = json.loads(lock.read_text(encoding="utf-8"))
                pid = other.get("pid", "?")
                started = other.get("started", "?")
            except (OSError, ValueError, TypeError, AttributeError):
                pid, started = "desconocido", "desconocida"
            return False, (
                f"Ya hay otra instancia de {APP_NAME} (pid {pid}, "
                f"abierta {started}). Bloqueo del sistema operativo ocupado."
            )

        try:
            handle.seek(0)
            handle.truncate(0)
            handle.write(json.dumps({
                "pid": os.getpid(),
                "started": time.strftime("%Y-%m-%d %H:%M:%S"),
            }).encode("utf-8"))
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            try:
                _unlock_handle(handle)
            finally:
                handle.close()
            raise
        _LOCK_HANDLE = handle
        _LOCK_PATH = lock.resolve()
        return True, ""


def release_single_instance(root: Path) -> None:
    """Release only this process's OS lock; never unlink the guard file."""
    global _LOCK_HANDLE, _LOCK_PATH
    with _LOCK_MUTEX:
        if _LOCK_HANDLE is None or _LOCK_PATH != (root / LOCK_NAME).resolve():
            return
        handle = _LOCK_HANDLE
        _LOCK_HANDLE = None
        _LOCK_PATH = None
        try:
            _unlock_handle(handle)
        finally:
            handle.close()


# --------------------------------------------------------------------------
# 2. SUPRA: conectar si responde, arrancar si no, decir la verdad si falla
# --------------------------------------------------------------------------
def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def endpoint_port(endpoint: str) -> int:
    tail = endpoint.rsplit(":", 1)[-1].split("/")[0]
    return int(tail) if tail.isdigit() else 8765


def health_ok(endpoint: str, timeout: float = 2.0) -> bool:
    """Accept only a *local, correctly identified* SUPRA service.

    An arbitrary HTTP 200 or an unrelated /health endpoint is not proof that
    we can safely transmit a dossier. Redirects and non-loopback endpoints are
    also rejected by the bundled local launcher.
    """
    from urllib.parse import urlsplit

    try:
        parsed = urlsplit(endpoint)
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
            or parsed.username is not None
            or parsed.password is not None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            return False
        url = f"{endpoint.rstrip('/')}/health"
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            if response.status != 200 or response.geturl() != url:
                return False
            payload = json.load(response)
        return (
            isinstance(payload, dict)
            and payload.get("status") == "healthy"
            and payload.get("service") == "supra-agentic-taskmaster"
            and isinstance(payload.get("storage"), dict)
        )
    except (urllib.error.URLError, OSError, ValueError, TypeError, UnicodeError):
        return False

_STREAM_LOCK = threading.Lock()
_BOUND_STREAMS: tuple[TextIO, ...] = ()


def ensure_streams(log_path: Path) -> tuple[TextIO, ...]:
    """Engancha stdout/stderr a un log real cuando no hay consola. Idempotente.

    Un ejecutable de ventana (console=False) arranca con sys.stdout y
    sys.stderr a None. uvicorn configura sus handlers con "ext://sys.stderr" y
    su formatter llama isatty() sobre ese stream, de modo que dictConfig
    revienta con

        ValueError: Unable to configure formatter 'default'
        AttributeError: 'NoneType' object has no attribute 'isatty'

    Medido el 2026-10-03 contra el paquete real: poner solo use_colors=False
    hace que Config se construya, pero el StreamHandler queda con stream=None y
    el texto del log se pierde en silencio (0 bytes). Por eso esto no es
    opcional ni un adorno: sin un stream real, "mostrar errores reales" es
    falso.

    Los streams se enlazan UNA vez por proceso y viven hasta que el proceso
    acaba: abrir uno nuevo en cada arranque perderia los registros emitidos
    antes, y cerrarlos en cada parada dejaria a logging escribiendo en un
    descriptor cerrado.
    """
    global _BOUND_STREAMS
    with _STREAM_LOCK:
        if _BOUND_STREAMS:
            return _BOUND_STREAMS  # ya enlazados en este proceso
        opened: list[TextIO] = []
        for name in ("stdout", "stderr"):
            if getattr(sys, name, None) is None:
                handle: TextIO = open(log_path, "a", encoding="utf-8", buffering=1)
                setattr(sys, name, handle)
                opened.append(handle)
        _BOUND_STREAMS = tuple(opened)
        return _BOUND_STREAMS


def _startup_trace(root: Path, message: str) -> None:
    """Leave a bounded startup breadcrumb for windowed frozen builds."""
    try:
        path = root / "logs" / "launcher-startup.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    except OSError:
        pass


def flush_bound_streams() -> None:
    """Vuelca lo pendiente sin cerrar: logging puede seguir usando los streams."""
    with _STREAM_LOCK:
        for handle in _BOUND_STREAMS:
            try:
                handle.flush()
            except (OSError, ValueError):
                pass


class SupraServer:
    """SUPRA real en un hilo de este mismo proceso, con parada limpia."""

    def __init__(self, endpoint: str, storage: Path, log_path: Path) -> None:
        self.endpoint = endpoint
        self.storage = storage
        self.log_path = log_path
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None
        self.bound_streams: tuple[TextIO, ...] = ()

    # Kwarg que se代号 en una version antigua de uvicorn y que no existe en
    # 0.52/0.53. Se listan para que el guard de arriba sea explicito y para que
    # el test de regresion falle si alguien lo vuelve a pasar.
    _UNSUPPORTED_CONFIG_KWARGS = {"install_signal_handlers"}

    def start(self, wait_s: float = 60.0) -> tuple[bool, str]:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.bound_streams = ensure_streams(self.log_path)
        port = endpoint_port(self.endpoint)
        if not health_ok(self.endpoint):
            port = free_port()  # el puerto pedido esta ocupado: usa uno libre y no chocas
            self.endpoint = f"http://127.0.0.1:{port}"
        # SupraClient lee este valor. Sin publicarlo, la UI podía arrancar el
        # servidor en un puerto real y enviar el dossier al 8000 por defecto.
        os.environ["SUPRA_ENDPOINT"] = self.endpoint
        os.environ["SUPRA_STORAGE_DIR"] = str(self.storage)
        os.environ["SUPRA_USE_MODEL"] = "false"

        import uvicorn
        from supra_agentic.service import app

        # uvicorn 0.52/0.53: el control de senales vive en Server.capture_signals(),
        # no en Config, y ya es seguro en un hilo (si el hilo actual no es el
        # principal no instala ningun handler). Por eso no se pasa nada aqui: un
        # kwarg inventado rompia el arranque con TypeError en el paquete.
        # La firma se comprueba en tests/unit/test_criba_shadow_launcher.py.
        supported = set(inspect.signature(uvicorn.Config.__init__).parameters)
        unexpected = self._UNSUPPORTED_CONFIG_KWARGS & supported
        if unexpected:
            raise RuntimeError(
                f"estos kwargs no existen en uvicorn {uvicorn.__version__}: {unexpected}"
            )

        # use_colors=False: en una app de ventana no hay terminal, y el
        # DefaultFormatter de uvicorn acaba llamando a sys.stdout/sys.stderr
        # .isatty(). Con streams reales (ensure_streams) eso ya no revienta,
        # pero dejar los colores desactivados hace la intencion explicita y
        # quita una dependencia del API de uvicorn de la que no hay que
        # depender. El fallo real de 2026-10-03 fue:
        #   ValueError: Unable to configure formatter 'default'
        #   AttributeError: 'NoneType' object has no attribute 'isatty'
        config = uvicorn.Config(
            app,
            host="127.0.0.1",
            port=port,
            log_level="warning",
            use_colors=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, name="supra-uvicorn", daemon=True)
        self._thread.start()

        deadline = time.monotonic() + wait_s
        while time.monotonic() < deadline:
            if health_ok(self.endpoint):
                return True, self.endpoint
            if not self._thread.is_alive():
                break
            time.sleep(0.5)
        return False, self._why_not()

    def _why_not(self) -> str:
        """El motivo real, con el log del servidor si lo hay."""
        tail = ""
        if self.log_path.is_file():
            tail = self.log_path.read_text(encoding="utf-8", errors="replace")[-1800:]
        reason = f"SUPRA no respondio /health. endpoint={self.endpoint} storage={self.storage}"
        if self._thread is not None and not self._thread.is_alive():
            reason += " El hilo del servidor murio al arrancar."
        if tail:
            reason += "\n\n--- ultimo log de SUPRA ---\n" + tail
        else:
            reason += "\n(No hay log: revisa que el paquete traiga supra_agentic.)"
        return reason

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread is not None:
            self._thread.join(timeout=15.0)
        # Los streams NO se cierran aqui: viven con el proceso. Cerrarlos
        # dejaria a logging escribiendo sobre un descriptor cerrado, que es
        # justo el fallo que ensure_streams viene a evitar.
        flush_bound_streams()


# --------------------------------------------------------------------------
# Arranque
# --------------------------------------------------------------------------
def _fatal(title: str, detail: str) -> int:
    """Error real en pantalla. Si no hay Qt todavia, al menos en consola."""
    text = f"{title}\n\n{detail}"
    try:
        from PySide6.QtWidgets import QApplication, QMessageBox

        app = QApplication.instance() or QApplication(sys.argv)
        QMessageBox.critical(None, f"{APP_NAME} — {title}", detail)
        del app
    except Exception:
        print(text, file=sys.stderr)
    return 2


def configure_frozen_gui_environment() -> None:
    """A shipped GUI must not inherit an offscreen test backend."""
    if getattr(sys, "frozen", False):
        os.environ.pop("QT_QPA_PLATFORM", None)


def main() -> int:
    root = data_root()
    _startup_trace(root, "main:entered")
    lock_ok, lock_msg = acquire_single_instance(root)
    _startup_trace(root, f"lock:{lock_ok}")
    if not lock_ok:
        return _fatal("Ya hay otra instancia abierta", lock_msg)

    log_handle = None
    supra: SupraServer | None = None
    try:
        wire_import_paths()
        configure_frozen_gui_environment()
        _startup_trace(root, "paths:wired")
        (root / "logs").mkdir(parents=True, exist_ok=True)
        log_path = root / "logs" / SUPRA_LOG_NAME
        log_handle = open(log_path, "a", encoding="utf-8")

        # An existing SUPRA service may belong to a different application or
        # user-data directory. Never adopt it merely because it occupies the
        # default port. Reuse only on explicit opt-in and verified /health.
        configured_endpoint = os.getenv("SUPRA_ENDPOINT", "").strip()
        if configured_endpoint and health_ok(configured_endpoint):
            os.environ["SUPRA_ENDPOINT"] = configured_endpoint
            print(f"[{APP_NAME}] SUPRA configurado en {configured_endpoint}.")
        else:
            endpoint = f"http://127.0.0.1:{free_port()}"
            supra = SupraServer(endpoint, root / "supra_state", log_path)
            ok, info = supra.start()
            if not ok:
                return _fatal("No se pudo arrancar SUPRA", info)
            print(f"[{APP_NAME}] SUPRA propio arrancado en {info}")

        _startup_trace(root, "supra:ready")
        from criba.ui import actions as ui_actions
        from PySide6.QtWidgets import QApplication
        from shadow_window import ShadowWindow

        app = QApplication.instance() or QApplication(sys.argv)
        app.setApplicationName(APP_NAME)
        _startup_trace(root, "qt:application")

        window = ShadowWindow(database=str(root / "criba.sqlite3"))
        _startup_trace(root, "qt:window-created")
        window.showMaximized()
        window.show()
        window.raise_()
        window.activateWindow()
        _startup_trace(
            root,
            f"qt:window-shown visible={window.isVisible()} "
            f"minimized={window.isMinimized()} winid={int(window.winId())}",
        )
        ui_actions.on_restore_latest_supra(window)
        _startup_trace(root, "qt:restore-started")
        # Explicit, isolated CI probe of the *frozen* EXE: the normal runtime
        # has no automation, and the probe refuses the user's real data dir.
        probe_mode = os.environ.get("CRIBASHADOW_BUNDLE_PROBE", "")
        if probe_mode:
            from shadow_bundle_probe import start_bundle_probe
            start_bundle_probe(app, window, root, probe_mode)
        return int(app.exec())
    except Exception as exc:  # noqa: BLE001 - aqui el error real es el producto
        import traceback

        detail = f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()[-2500:]}"
        try:
            error_path = root / "logs" / "launcher-error.log"
            error_path.parent.mkdir(parents=True, exist_ok=True)
            error_path.write_text(detail, encoding="utf-8")
        except OSError:
            pass
        return _fatal("Fallo al arrancar", detail)
    finally:
        if supra is not None:
            supra.stop()
        if log_handle is not None:
            log_handle.close()
        release_single_instance(root)


if __name__ == "__main__":
    raise SystemExit(main())
