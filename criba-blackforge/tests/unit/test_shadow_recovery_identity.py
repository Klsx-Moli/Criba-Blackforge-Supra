"""Recovery must bind a local dossier to the remote receipt, not local recency.

Unit scope: real local JSONL and Qt widgets; the HTTP client is a declared stub.
The native Windows / real HTTP reproduction is preserved in the run evidence.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from criba.supra_dossier import guardar_dossier, preparar_dossier
from criba.ui import actions


def _dossier(candidate: str) -> dict:
    return preparar_dossier(
        {
            "candidate_id": candidate,
            "hipotesis": f"hipótesis de {candidate}",
            "mecanismo": f"mecanismo de {candidate}",
            "prueba_concreta": "contraste unitario",
            "supuestos": ["alternativa declarada"],
        },
        f"caso unitario {candidate}",
    )


def _client(receipt: dict | None):
    lookup = SimpleNamespace(
        status="blocked",
        status_scope="WORKFLOW_EXECUTION_ONLY",
        completion_status="BLOCKED",
        workflow_status="BLOCKED",
        verification_status="FAIL",
        scientific_status="NOT_VALIDATED",
        secure_sandbox_status="RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        criba_planning_receipt_status="PRESERVED_NOT_EXECUTED",
        criba_mechanism_execution_status="NOT_EXECUTED",
        status_source="PERSISTED_STATE",
        persisted_artifact_status="VERIFIED_FROM_ARTIFACT",
        persisted_artifact_error_kind=None,
        stage="BLOCKED",
        posture=SimpleNamespace(
            criba_dossier_receipt=SimpleNamespace(model_dump=lambda: receipt) if receipt else None
        ),
    )
    return SimpleNamespace(
        config=SimpleNamespace(endpoint="http://unit.invalid"),
        health=lambda: SimpleNamespace(model_dump=lambda: {"status": "healthy"}),
        list_projects=lambda **kwargs: SimpleNamespace(projects=[{"project_id": "remote-case"}]),
        get_project=lambda project_id: lookup,
    )


def _receipt(dossier: dict) -> dict:
    return {
        "criba_dossier_id": dossier["dossier_id"],
        "criba_candidate_id": dossier["candidate_id"],
        **{k: dossier[k] for k in ("claim_id", "mechanism_version", "protocol_version")},
    }


def test_recovery_loads_receipt_bound_dossier_not_newer_unsent_draft(monkeypatch, tmp_path):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    sent = _dossier("sent")
    newer = _dossier("unsent")
    guardar_dossier(sent)
    guardar_dossier(newer)
    report = actions._load_latest_supra(client=_client(_receipt(sent)))
    assert report["dossier"] == sent, "recovery attached an unrelated newer local dossier"
    assert report["read"]["receipt"]["criba_dossier_id"] == report["dossier"]["dossier_id"]


@pytest.mark.parametrize(
    "field", ["candidate_id", "claim_id", "mechanism_version", "protocol_version"]
)
def test_recovery_rejects_local_identity_that_disagrees_with_receipt(monkeypatch, tmp_path, field):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    local = _dossier("local")
    guardar_dossier(local)
    receipt = _receipt(local)
    remote_key = "criba_candidate_id" if field == "candidate_id" else field
    receipt[remote_key] = "different-authoritative-value"
    report = actions._load_latest_supra(client=_client(receipt))
    assert report["dossier"] is None, f"local {field} does not match recovered receipt"


@pytest.mark.parametrize("receipt_case", ["absent", "not-local", "blank", "padded"])
def test_recovery_never_falls_back_to_latest_unrelated_dossier(monkeypatch, tmp_path, receipt_case):
    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    local = _dossier("local")
    guardar_dossier(local)
    receipt = _receipt(local)
    if receipt_case == "absent":
        receipt = None
    else:
        receipt["criba_dossier_id"] = {
            "not-local": "unknown-id",
            "blank": "",
            "padded": " " + local["dossier_id"] + " ",
        }[receipt_case]
    report = actions._load_latest_supra(client=_client(receipt))
    assert report["dossier"] is None
    assert report["read"]["scientific_status"] == "NOT_VALIDATED"


def test_recovery_without_local_dossier_clears_previous_dossier_panel(monkeypatch, tmp_path):
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = ShadowWindow(database=str(tmp_path / "ui.sqlite3"))
    try:
        win.candidates.dossier_output.setPlainText("DOSSIER DE OTRO PROYECTO")
        report = actions._load_latest_supra(client=_client(None))
        actions._on_supra_restore_done(win, report)
        assert win.candidates.dossier_output.toPlainText() == "", "stale dossier survived recovery"
        assert "remote-case" in win.candidates.supra_output.toPlainText()
    finally:
        win.close()
        app.processEvents()


def test_vertical_slice_preserves_dossier_before_dispatch(monkeypatch, tmp_path):
    import json
    import sys
    from pathlib import Path

    from criba.supra_dossier import cargar_dossier
    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = ShadowWindow(database=str(tmp_path / "vertical.sqlite3"))
    queued = []
    monkeypatch.setattr(actions, "_start_worker", lambda window, worker: queued.append(worker))
    try:
        win.problem = "Recuperar resultados sin mezclar proyectos"
        win.packet = actions.activate(win.problem)
        actions.on_supra_vertical(win)
        assert len(queued) == 1
        displayed = json.loads(win.candidates.dossier_output.toPlainText())
        assert cargar_dossier(displayed["dossier_id"]) == displayed, (
            "UI says dossier preserved, but it was only in memory before dispatch"
        )
    finally:
        win.close()
        app.processEvents()


def test_vertical_double_submit_does_not_create_two_remote_attempts(monkeypatch, tmp_path):
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = ShadowWindow(database=str(tmp_path / "duplicate.sqlite3"))
    queued = []
    monkeypatch.setattr(actions, "_start_worker", lambda window, worker: queued.append(worker))
    try:
        win.problem = "Recuperar resultados sin duplicar intentos"
        win.packet = actions.activate(win.problem)
        actions.on_supra_vertical(win)
        actions.on_supra_vertical(win)
        assert len(queued) == 1, "double submit queued two remote attempts"
    finally:
        win.close()
        app.processEvents()


def test_storage_failure_prevents_remote_dispatch(monkeypatch, tmp_path):
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = ShadowWindow(database=str(tmp_path / "storage-failure.sqlite3"))
    queued, errors = [], []
    monkeypatch.setattr(actions, "_start_worker", lambda window, worker: queued.append(worker))
    monkeypatch.setattr(
        actions, "show_error", lambda window, title, message: errors.append(message)
    )

    def fail_save(dossier):
        raise OSError("controlled disk write failure")

    monkeypatch.setattr("criba.supra_dossier.guardar_dossier", fail_save)
    try:
        win.problem = "No despachar antes de preservar el intento"
        win.packet = actions.activate(win.problem)
        actions.on_supra_vertical(win)
        assert queued == []
        assert any("controlled disk write failure" in error for error in errors)
        assert not getattr(win, "_supra_vertical_running", False)
    finally:
        win.close()
        app.processEvents()


@pytest.mark.parametrize("outcome", ["done", "fail"])
def test_vertical_inflight_guard_releases_on_terminal_callback(monkeypatch, tmp_path, outcome):
    import sys
    from pathlib import Path

    from PySide6.QtWidgets import QApplication

    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "shadow_ui"))
    from shadow_window import ShadowWindow

    monkeypatch.setenv("CRIBASHADOW_HOME", str(tmp_path))
    app = QApplication.instance() or QApplication([])
    win = ShadowWindow(database=str(tmp_path / "release.sqlite3"))
    queued = []
    monkeypatch.setattr(actions, "_start_worker", lambda window, worker: queued.append(worker))
    try:
        win.problem = "Liberar sólo el intento finalizado"
        win.packet = actions.activate(win.problem)
        actions.on_supra_vertical(win)
        assert win._supra_vertical_running is True
        if outcome == "done":
            read = actions._supra_lookup_read(_client(None).get_project("remote-case"))
            queued[0].signals.done.emit(
                {"read": read, "project_id": "remote-case", "endpoint": "unit"}
            )
        else:
            queued[0].signals.fail.emit("controlled transport failure")
        app.processEvents()
        assert win._supra_vertical_running is False
    finally:
        win.close()
        app.processEvents()
