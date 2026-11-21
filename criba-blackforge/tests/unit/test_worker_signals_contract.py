"""Regresion: Worker.signals debe exponer todo lo que la UI conecta.

Defecto reproducido en el .exe empaquetado (logs/supra-server.log):

    File "criba\\ui\\model_settings_dialog.py", line 450, in _test_profile
  AttributeError: '_Signals' object has no attribute 'finished'

`_Signals` solo declara done/fail/progress, pero model_settings_dialog._test_profile
conecta worker.signals.finished dos veces (seguridad y parada del timer). Cada
 pulsacion de "Comprobar" lanzaba AttributeError dentro del slot de Qt, dejando
el boton deshabilitado y la respiracion activa sin red de seguridad.

Criterio de aceptacion: toda senal que la UI conecte existe en _Signals y emite.
"""
from __future__ import annotations

import sys


def test_signals_expone_finished():
    from criba.ui.actions import Worker

    w = Worker(lambda: 1)
    assert hasattr(w.signals, "finished"), (
        f"_Signals expone {sorted(a for a in dir(w.signals) if not a.startswith('_'))}"
    )


def test_signals_expone_done_fail_progress():
    from criba.ui.actions import Worker

    w = Worker(lambda: 1)
    for name in ("done", "fail", "progress"):
        assert hasattr(w.signals, name), f"falta signals.{name}"


def test_toda_conexion_de_la_dialog_es_valida():
    """Las dos conexiones de model_settings_dialog deben resolverse."""
    from criba.ui.actions import Worker

    w = Worker(lambda: 1)
    conectadas = []
    for attr in ("done", "fail", "finished"):
        sig = getattr(w.signals, attr, None)
        if sig is None:
            continue
        try:
            sig.connect(lambda *a: None)
            conectadas.append(attr)
        except (AttributeError, TypeError) as exc:
            raise AssertionError(f"signals.{attr} no conectable: {exc}") from exc
    assert "finished" in conectadas, (
        f"signals.finished sigue sin existir; conectables={conectadas}"
    )


def test_finished_emite_al_terminar_el_worker():
    """finished debe emitirse despues de done/fail, no solo existir."""
    from PySide6.QtCore import QEventLoop, QThreadPool, QTimer
    from PySide6.QtWidgets import QApplication

    from criba.ui.actions import Worker

    # El singleton sobrevive al test: otros tests del proceso crean QWidget.
    app = QApplication.instance() or QApplication(["worker-test", "-platform", "offscreen"])
    assert isinstance(app, QApplication)
    vistos: list[str] = []
    w = Worker(lambda: "ok")
    w.signals.done.connect(lambda _r: vistos.append("done"))
    w.signals.finished.connect(lambda: vistos.append("finished"))

    loop = QEventLoop()
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    w.signals.finished.connect(loop.quit)
    timer.start(4000)
    QThreadPool.globalInstance().start(w)
    loop.exec()
    timer.stop()
    assert vistos == ["done", "finished"], f"orden/ausencia: {vistos}"


if __name__ == "__main__":
    fallos = 0
    for nombre, fn in sorted(globals().items()):
        if not nombre.startswith("test_") or not callable(fn):
            continue
        try:
            fn()
            print(f"  PASS {nombre}")
        except Exception as exc:
            fallos += 1
            print(f"  FAIL {nombre}: {type(exc).__name__}: {exc}")
    print(f"\nRESULTADO: {fallos} fallos")
    sys.exit(1 if fallos else 0)