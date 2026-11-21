"""Regression test: SUPRA worker done signal must be processed via QEventLoop.

Bug: on_desarrollar_supra() starts a Worker in QThreadPool and connects
worker.signals.done to _on_supra_dossiers_done. However, QTest.qWait(n)
does NOT pump cross-thread signals (Qt::QueuedConnection). If the worker
finishes before the test's processEvents() loop polls, the 'done' signal
gets queued but processed AFTER the loop exits — the assertion on
ideaEstadoChip happens BEFORE the signal handler runs, causing a flaky
failure: "SUPRA pendiente" still visible instead of "SUPRA bloqueado".

Fix: _start_worker should use a proper QEventLoop (like _wait_for_sheet)
to ensure cross-thread signals are delivered before the function returns
to the synchronous caller. This regression reproduces the timing gap.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
pytest.importorskip("PySide6")

from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from criba.ui import actions
from criba.ui.main_window import CribaMainWindow


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _wait_for_condition(qapp, condition_fn, timeout_ms=5000):
    """Wait for a condition using QEventLoop (pumps cross-thread signals).

    Uses QTimer + QEventLoop instead of QTest.qWait, which does NOT pump
    cross-thread queued signals. This is the canonical pattern for
    waiting on Worker signals in Qt tests.
    """
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(loop.quit)
    timer.start(100)  # Check every 100ms

    def _check():
        qapp.processEvents()
        if condition_fn():
            timer.stop()
            loop.quit()

    QTimer.singleShot(0, _check)
    QTimer.singleShot(timeout_ms, loop.quit)
    loop.exec()
    timer.stop()
    return condition_fn()


def test_supra_worker_signal_processed_via_eventloop(qapp, tmp_path, monkeypatch) -> None:
    """REGRESSION: QTest.qWait does not pump cross-thread signals.

    When on_desarrollar_supra starts a Worker for _execute_supra_dossiers,
    the done signal crosses threads (from QThreadPool worker thread to main
    GUI thread). QTest.qWait(10) will NOT deliver this signal — we need
    QEventLoop to pump the event queue.

    This test reproduces the timing gap: if qWait is used instead of
    QEventLoop, _on_supra_dossiers_done runs AFTER assertions, causing
    flaky failures.
    """
    sheet = {
        "query": "permisos",
        "seed": 42,
        "mode": "stratified",
        "entries": [
            {
                "candidate_id": "test-race-01",
                "title": "A x B",
                "score": 0.5,
                "score_kind": "heuristica_local",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "Hipótesis test",
                "mecanismo": "Mecanismo causa-efecto test",
                "interpretacion_error": "",
                "prueba_concreta": "medir X",
                "ruta_desbloqueo": "sustituir_mecanismo",
                "prior_art": {
                    "verdict": "UNRESOLVED",
                    "queries": [],
                    "rounds": 0,
                    "mutations": 0,
                    "detail": "test",
                },
            }
        ],
        "ficha_bloqueo": {"bloqueo": "test", "origen_bloqueo": "hipotesis"},
    }

    dossier_paths = []
    monkeypatch.setattr(
        "criba.supra_dossier.guardar_dossier",
        lambda d, directory=None: (dossier_paths.append(d), tmp_path / "d.jsonl")[1],
    )
    monkeypatch.setattr("criba.supra_dossier._dossiers_dir", lambda override=None: tmp_path)

    dispatched: list[list[dict]] = []

    def fake_execute(dossiers, client=None):
        dispatched.append(dossiers)
        return {
            "health": {"status": "ok", "service": "SUPRA"},
            "runs": [
                {
                    "dossier_id": dossiers[0]["dossier_id"],
                    "project_id": "proj-test-race",
                    "status": "blocked",
                    "completion_status": "BLOCKED",
                    "workflow_status": "BLOCKED",
                    "verification_status": "FAIL",
                    "secure_sandbox_status": "RESTRICTED_BOUND_PASS_NOT_ISOLATED",
                    "scientific_status": "NOT_VALIDATED",
                    "criba_mechanism_execution_status": "NOT_EXECUTED",
                    "stage": "BLOCKED",
                }
            ],
        }

    monkeypatch.setattr(actions, "_execute_supra_dossiers", fake_execute)

    win = CribaMainWindow()
    try:
        win.invent_sheet = sheet
        actions.on_desarrollar_supra(win)

        # KEY: Must use QEventLoop, NOT QTest.qWait, to pump cross-thread signals
        result = _wait_for_condition(
            qapp,
            lambda: len(getattr(win, "_live_workers", [])) == 0,
            timeout_ms=5000,
        )

        assert result, (
            "REGRESSION: QTest.qWait no bombea señales cross-thread; "
            "el worker terminó pero el signal 'done' no se procesó. "
            "Usar QEventLoop con QTimer para esperar condiciones cross-thread."
        )

        assert dispatched, "el dossier nunca se despachó a SUPRA"

        # The done handler must have run before we assert
        summary = win.refs["ideaSummary"].text().upper()
        assert "NO EJECUTADO" in summary, (
            f"REGRESSION: señal 'done' no procesada: summary={summary!r}"
        )
    finally:
        win.close()
