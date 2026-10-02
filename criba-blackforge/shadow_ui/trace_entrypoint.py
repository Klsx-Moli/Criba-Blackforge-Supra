"""Shadow UI entrypoint CON TRACING para prueba humana física.

Registra runtime_button_trace.log (CSV) con cada clic real y cada entrada/salida
de callback de actions.py. NO modifica actions.py en disco — monkeypatch solo en
runtime. La app se lanza en plataforma windows (visible) para prueba física.

Formato: timestamp, event, control, widget, enabled, callback_enter, callback_exit,
exception, problem_before, problem_after, packet_before, packet_after, dialog,
rowCount, candidate_id, ideas_count
"""
from __future__ import annotations

import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

ART = Path(r"C:\Users\KLSX\Music\INTERESANTE\UIEDITION\artifacts\criba-shadow-live")
LOG = ART / "runtime_button_trace.log"

logger = logging.getLogger("shadow_trace")
logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(LOG, mode="w", encoding="utf-8")
handler.setFormatter(logging.Formatter("%(message)s"))
logger.handlers = [handler]  # handler único (fichero de traza)

def _ts() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def _state_snapshot(win) -> dict:
    """Snapshot del estado compartido para comparar antes/después."""
    try:
        packet = getattr(win, "packet", None)
        ideas = (len(packet["innovation"]["ideas"]) if packet and isinstance(packet, dict)
                 and isinstance(packet.get("innovation"), dict) else None)
        return {
            "problem": str(getattr(win, "problem", "") or "")[:60],
            "packet_present": packet is not None,
            "ideas_count": ideas,
            "sources_updated": getattr(win, "sources_updated_at", None) is not None,
            "invent_sheet_present": getattr(win, "invent_sheet", None) is None,
            "saved_ids_count": len(getattr(win, "saved_ids", set()) or []),
            "selected_candidate": getattr(win, "_ctx", None) and getattr(win._ctx, "selected_candidate_id", None),
            "row_count": win.refs["rankingModel"].rowCount() if hasattr(win, "refs") else None,
            "tab_index": win.candidates.tabs.currentIndex() if hasattr(win, "candidates") else None,
        }
    except Exception as exc:
        return {"error": str(exc)}


def _wrap_action(name: str, win):
    """Envuelve actions.<name> con logging de entrada/salida/exception."""
    from criba.ui import actions as actions_mod
    real = getattr(actions_mod, name)

    def wrapper(*args, **kwargs):
        before = _state_snapshot(win)
        logger.info("%s | ENTER | %s | problem=%s | packet=%s | rows=%s",
                    _ts(), name, before["problem"], before["packet_present"], before["row_count"])
        try:
            result = real(*args, **kwargs)
            after = _state_snapshot(win)
            logger.info("%s | EXIT  | %s | problem=%s | packet=%s | rows=%s | ideas=%s | selected=%s",
                        _ts(), name, after["problem"], after["packet_present"],
                        after["row_count"], after["ideas_count"], after["selected_candidate"])
            return result
        except BaseException as exc:
            logger.info("%s | ERROR | %s | %s", _ts(), name, exc)
            raise
    return wrapper


def install_tracing(win):
    """Instala tracing sobre todos los botones reales y callbacks de actions."""
    from criba.ui import actions as actions_mod
    from PySide6.QtCore import SIGNAL
    from PySide6.QtWidgets import QPushButton, QTabWidget

    # 1. Callbacks de actions.py
    for fn_name in ("on_nueva_idea", "on_generar", "on_inventar", "on_evaluar",
                    "on_red", "on_historial", "on_retro", "on_memoria",
                    "on_tecnicas", "on_modelos", "on_blackforge", "on_supra",
                    "on_actualizar", "on_ver_todas", "on_tab_changed",
                    "on_desarrollar_supra", "on_guardar", "on_hibrido"):
        if hasattr(actions_mod, fn_name):
            setattr(actions_mod, fn_name, _wrap_action(fn_name, win))

    # 2. Botones reales: log del click ANTES de que llegue al callback
    seen = set()
    for btn in win.findChildren(QPushButton):
        key = id(btn)
        if key in seen:
            continue
        seen.add(key)
        text = btn.text().strip()
        # registrar receptors actuales
        receivers = btn.receivers(SIGNAL("clicked()"))
        logger.info("%s | WIDGET | %s | receivers=%d | objectName=%s",
                    _ts(), text, receivers, btn.objectName())

    # 3. Tab widget
    for tab in win.findChildren(QTabWidget):
        logger.info("%s | WIDGET | tabwidget | tabs=%d | current=%d",
                    _ts(), tab.count(), tab.currentIndex())


def main() -> int:
    from PySide6.QtWidgets import QApplication
    qt_app = QApplication.instance() or QApplication(sys.argv)

    from shadow_window import ShadowWindow

    db_path = ART / "_trace_tmp" / "criba.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    win = ShadowWindow(db_path)
    win.showMaximized()
    win.show()
    qt_app.processEvents()

    install_tracing(win)

    def _git(*args: str) -> str:
        """Dato git en vivo (antes estaba fijado a mano y mentía al reusar)."""
        try:
            return subprocess.run(["git", *args], cwd=ROOT, capture_output=True,
                                  text=True, timeout=10).stdout.strip() or "?"
        except Exception:
            return "?"

    logger.info("%s | START | HEAD=%s | branch=%s | problem=%s | packet=%s",
                _ts(), _git("rev-parse", "--short", "HEAD"),
                _git("rev-parse", "--abbrev-ref", "HEAD"),
                win.problem, win.packet is not None)

    try:
        ret = qt_app.exec()
    finally:
        logger.info("%s | END | ret=%d", _ts(), ret)
    return ret


if __name__ == "__main__":
    raise SystemExit(main())
