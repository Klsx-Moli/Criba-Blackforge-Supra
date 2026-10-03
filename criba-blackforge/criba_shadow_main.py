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


def acquire_single_instance(root: Path) -> tuple[bool, str]:
    """Toma el lock de instancia. Devuelve (conseguido, mensaje_real)."""
    lock = root / LOCK_NAME
    if lock.is_file():
        try:
            other = json.loads(lock.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            other = {}
        pid = int(other.get("pid") or 0)
        if pid and pid != os.getpid() and _pid_alive(pid):
            return False, (
                f"Ya hay una instancia de {APP_NAME} corriendo (pid {pid}, "
                f"abierta {other.get('started') or '?'}). Abrir una segunda "
                f"escribiria sobre los mismos proyectos a la vez.\n"
                f"Cierra esa ventana o termina ese proceso y vuelve a abrir."
            )
        lock.unlink(missing_ok=True)
    lock.write_text(
        json.dumps({"pid": os.getpid(), "started": time.strftime("%Y-%m-%d %H:%M:%S")}),
        encoding="utf-8",
    )
    return True, ""


def release_single_instance(root: Path) -> None:
    lock = root / LOCK_NAME
    try:
        if (
            lock.is_file()
            and json.loads(lock.read_text(encoding="utf-8")).get("pid") == os.getpid()
        ):
            lock.unlink(missing_ok=True)
    except (OSError, ValueError):
        pass


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
    try:
        with urllib.request.urlopen(f"{endpoint}/health", timeout=timeout) as response:
            return int(response.status) == 200
    except (urllib.error.URLError, OSError, ValueError):
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


def main() -> int:
    root = data_root()
    lock_ok, lock_msg = acquire_single_instance(root)
    if not lock_ok:
        return _fatal("Ya hay otra instancia abierta", lock_msg)

    log_handle = None
    supra: SupraServer | None = None
    try:
        wire_import_paths()
        (root / "logs").mkdir(parents=True, exist_ok=True)
        log_path = root / "logs" / SUPRA_LOG_NAME
        log_handle = open(log_path, "a", encoding="utf-8")

        endpoint = os.getenv("SUPRA_ENDPOINT", "http://127.0.0.1:8765").strip()
        if health_ok(endpoint):
            print(f"[{APP_NAME}] SUPRA ya responde en {endpoint}; no se arranca otro.")
        else:
            supra = SupraServer(endpoint, root / "supra_state", log_path)
            ok, info = supra.start()
            if not ok:
                return _fatal("No se pudo arrancar SUPRA", info)
            print(f"[{APP_NAME}] SUPRA arrancado en {info}")

        from PySide6.QtWidgets import QApplication
        from shadow_window import ShadowWindow

        app = QApplication.instance() or QApplication(sys.argv)
        app.setApplicationName(APP_NAME)

        window = ShadowWindow(database=str(root / "criba.sqlite3"))
        window.showMaximized()
        window.show()
        return int(app.exec())
    except Exception as exc:  # noqa: BLE001 - aqui el error real es el producto
        import traceback

        return _fatal(
            "Fallo al arrancar",
            f"{type(exc).__name__}: {exc}\n\n{traceback.format_exc()[-2500:]}",
        )
    finally:
        if supra is not None:
            supra.stop()
        if log_handle is not None:
            log_handle.close()
        release_single_instance(root)


if __name__ == "__main__":
    raise SystemExit(main())
