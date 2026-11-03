"""Functional Qt journey over the real SQLite/history; synthetic input, no LLM."""

from __future__ import annotations

import copy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from criba.lottery import VALID_LOTTERY_MODES
from criba.ui import actions
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication, QDialog, QListWidget, QPushButton

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "shadow_ui"))
from shadow_window import ShadowWindow  # noqa: E402 - explicit standalone UI path


@pytest.fixture(scope="module")
def qapp():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def sheet():
    return {
        "run_id": "fixture-no-model-42",
        "query": "Reducir el agua desaprovechada al iniciar la ducha",
        "seed": 42,
        "mode": "stratified",
        "entries": [
            {
                "candidate_id": "fixture-candidate-1",
                "title": "Recuperación previa del agua fría",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "Guardar el agua inicial en un depósito para usos no potables.",
                "mecanismo": "Una válvula desvía el flujo inicial hacia un depósito independiente.",
                "incertidumbre": "Propuesta creativa, no comprobada.",
                "novedad": "Antecedentes no investigados.",
                "aportacion_por_tecnica": ["operación A", "operación B"],
                "supuestos": [],
                "prueba_concreta": "Medir litros recuperados frente a la ducha convencional.",
                "prueba": {"metrica": "litros recuperados"},
                "critica": {"objeciones": [], "incertidumbre": "no es una validación"},
                "interpretacion_raw_output": '{"synthetic_fixture": true}',
                "interpretacion_provenance": {"model_requested": "fixture-no-model"},
                "cross_operational_records": [
                    {"id": "A3-OP-GEN-01", "operator_record": {"execution_status": "NOT_EXECUTED"}}
                ],
                "prior_art": {"verdict": "UNRESOLVED"},
            }
        ],
        "totals": {
            "ideas": 1,
            "pending_interpretation": 0,
            "unresolved": 1,
            "partial_prior_art": 0,
            "survived_search": 0,
        },
    }


def test_shadow_exposes_the_actual_interpreter_selector(qapp, tmp_path):
    win = ShadowWindow(database=str(tmp_path / "selector-bridge.sqlite3"))
    try:
        assert win.interpreter_selector is win.topcards.interpreter_selector
    finally:
        win.close()
        qapp.processEvents()


def test_shadow_labels_show_configured_cloud_model_without_claiming_connection(
    qapp, tmp_path, monkeypatch
):
    monkeypatch.setenv("CRIBA_EXTERNAL_MODEL", "fixture/selected-model:free")
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "no-local-model.json"))
    win = ShadowWindow(database=str(tmp_path / "labels.sqlite3"))
    try:
        assert "fixture/selected-model:free" in win.topcards.interpreter_selector.itemText(0)
        assert "fixture/selected-model:free" in win.header.model_btn.text()
        assert "fixture/selected-model:free" in win.footer.model_block._title_label.text()
        assert "al generar" in win.header.model_btn.toolTip()
        assert "local" not in win.header.model_btn.text().casefold()
    finally:
        win.close()
        qapp.processEvents()


def test_shadow_model_selection_updates_all_labels(qapp, tmp_path):
    win = ShadowWindow(database=str(tmp_path / "selected-labels.sqlite3"))
    try:
        selector = win.topcards.interpreter_selector
        index = next(
            i for i in range(selector.count()) if isinstance(selector.itemData(i), (tuple, list))
        )
        model = selector.itemData(index)[1]
        selector.setCurrentIndex(index)
        qapp.processEvents()
        assert model in win.header.model_btn.text()
        assert model in win.footer.model_block._title_label.text()
        assert model in win.topcards.interpreter_status.text()
    finally:
        win.close()
        qapp.processEvents()


def test_model_label_refresh_preserves_choice_and_never_contacts_provider(
    qapp, tmp_path, monkeypatch
):
    def forbidden_request(*_args, **_kwargs):
        pytest.fail("refreshing a label must not contact a provider")

    monkeypatch.setattr("httpx.Client.send", forbidden_request)
    monkeypatch.setattr(
        "criba.model_config.load_model_settings",
        lambda: SimpleNamespace(enabled=True, active_profile=lambda: object()),
    )
    monkeypatch.setattr("criba.model_config.active_model_label", lambda *_args: "fixture local")
    win = ShadowWindow(database=str(tmp_path / "no-network-labels.sqlite3"))
    try:
        selector = win.topcards.interpreter_selector
        assert selector.currentData() == "openai_compatible"
        selector.setCurrentIndex(1)
        selected = selector.currentData()
        actions._refresh_interpreter_selector(win)
        assert selector.currentData() == selected
    finally:
        win.close()
        qapp.processEvents()


def test_normal_proposal_is_readable_and_diagnostics_are_optional(qapp, tmp_path, sheet):
    win = ShadowWindow(database=str(tmp_path / "readable.sqlite3"))
    try:
        actions._on_invented(win, sheet)
        candidates = win.candidates
        text = candidates.interpretation_output.toPlainText()
        assert sheet["entries"][0]["hipotesis"] in text
        assert sheet["entries"][0]["mecanismo"] in text
        assert '{"' not in text and '"metrica"' not in text
        assert "TRAZABILIDAD" not in text and "APORTACIÓN DE LA TÉCNICA" not in text
        assert not candidates.output_tabs.isTabVisible(1)
        candidates.mas_expandir_btn.click()
        assert candidates.output_tabs.isTabVisible(1)
        assert "fixture-no-model" in candidates.interpretation_output.toPlainText()
        assert "APORTACIÓN DE LA TÉCNICA" in candidates.interpretation_output.toPlainText()
        candidates.mas_expandir_btn.click()
        assert "TRAZABILIDAD" not in candidates.interpretation_output.toPlainText()
    finally:
        win.close()
        qapp.processEvents()


def test_blackforge_displays_and_saves_shared_proposal(qapp, tmp_path, sheet):
    from criba.ui.blackforge_window import BlackforgeWindow

    win = BlackforgeWindow(database=str(tmp_path / "blackforge.sqlite3"))
    try:
        win._apply_generation_result({"invention_sheet": sheet})
        assert win.invent_sheet == sheet
        dialog = win._proposal_dialog
        assert sheet["entries"][0]["mecanismo"] in dialog.output.toPlainText()
        assert "TRAZABILIDAD" not in dialog.output.toPlainText()
        dialog.save_button.click()
        records = win.store.list_sessions()
        assert len(records) == 1
        assert win.store.get(records[0]["id"])["packet"]["sheet"] == sheet
    finally:
        dialog = getattr(win, "_proposal_dialog", None)
        if dialog is not None:
            dialog.close()
        win.close()
        qapp.processEvents()


def test_shadow_mode_and_seed_controls_are_read(qapp, tmp_path):
    win = ShadowWindow(database=str(tmp_path / "controls.sqlite3"))
    try:
        assert win.topcards.mode_selector.currentData() == "stratified"
        index = win.topcards.mode_selector.findData("alternating")
        win.topcards.mode_selector.setCurrentIndex(index)
        win.topcards.seed_input.setText("123")
        assert actions._invention_controls(win) == ("alternating", 123)
        win.topcards.seed_input.clear()
        assert actions._invention_controls(win) == ("alternating", None)
        win.topcards.seed_input.setText("no-es-entero")
        with pytest.raises(ValueError):
            actions._invention_controls(win)
    finally:
        win.close()
        qapp.processEvents()


def test_shadow_run_inventar_forwards_mode_and_seed(monkeypatch, sheet):
    captured = {}

    def fake_run(problem, **kwargs):
        captured.update(kwargs)
        return copy.deepcopy(sheet)

    monkeypatch.setattr("criba.invention_service.run_invention", fake_run)
    result = actions._run_inventar(
        "q", mode="alternating", seed=123, history_storage=False
    )
    assert result == sheet
    assert captured["mode"] == "alternating"
    assert captured["seed"] == 123


def test_shadow_primary_generate_uses_canonical_invention_service(
    qapp, tmp_path, sheet, monkeypatch
):
    calls = []

    def fake_invent(query, **kwargs):
        calls.append((query, kwargs.get("history_storage")))
        return copy.deepcopy(sheet)

    monkeypatch.setattr("criba.inventar.invent", fake_invent)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _sheet: tmp_path / "ledger.jsonl")
    monkeypatch.setattr("criba.intelligence.refresh.default_store", lambda: None)
    monkeypatch.setattr(
        "criba.interprete.seleccion.construir_interprete",
        lambda *_a, **_k: SimpleNamespace(
            backend="openai_compatible",
            provider="test-double",
            model="fixture-no-model",
            operativo=lambda: (True, "double"),
        ),
    )
    win = ShadowWindow(database=str(tmp_path / "primary.sqlite3"))
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: loop.quit() if win.invent_sheet is not None else None)
    timer.start(30)
    QTimer.singleShot(5000, loop.quit)
    try:
        actions._apply_new_problem(win, sheet["query"])
        win.topcards.btn_gen.click()
        loop.exec()
        assert calls == [(sheet["query"], win.store)]
        assert (
            win.invent_sheet["entries"][0]["mecanismo"]
            in win.candidates.interpretation_output.toPlainText()
        )
    finally:
        timer.stop()
        win.close()
        qapp.processEvents()


def test_blackforge_execute_uses_canonical_invention_service(qapp, tmp_path, sheet, monkeypatch):
    from criba.ui.blackforge_window import BlackforgeWindow

    calls = []

    def fake_invent(query, **kwargs):
        calls.append((query, kwargs))
        return copy.deepcopy(sheet)

    monkeypatch.setattr("criba.inventar.invent", fake_invent)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _sheet: tmp_path / "ledger.jsonl")
    monkeypatch.setattr("criba.intelligence.refresh.default_store", lambda: None)
    monkeypatch.setattr(
        "criba.interprete.seleccion.construir_interprete",
        lambda *_a, **_k: SimpleNamespace(
            backend="openai_compatible",
            provider="test-double",
            model="fixture-no-model",
            operativo=lambda: (True, "double"),
        ),
    )
    monkeypatch.setenv("CRIBA_MODEL_CONFIG", str(tmp_path / "no-local-model.json"))
    win = BlackforgeWindow(database=str(tmp_path / "execute.sqlite3"), query=sheet["query"])
    win._select_mode("alternating")
    win.seed_input.setText("99")
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: loop.quit() if not win._busy else None)
    timer.start(30)
    QTimer.singleShot(5000, loop.quit)
    try:
        win.execute_button.click()
        loop.exec()
        assert [query for query, _kwargs in calls] == [sheet["query"]]
        assert calls[0][1]["mode"] == "alternating"
        assert calls[0][1]["seed"] == 99
        assert win.invent_sheet["query"] == sheet["query"]
        assert win._proposal_dialog.isVisible()
    finally:
        timer.stop()
        if win._proposal_dialog is not None:
            win._proposal_dialog.close()
        win.close()
        qapp.processEvents()


def test_shadow_and_blackforge_dispatch_every_lottery_mode_to_shared_service(
    tmp_path, sheet, monkeypatch
):
    """Paridad de cableado: ambas UI usan run_invention con los 5 modos.

    Shadow llega por ``actions._run_inventar`` (entrada exacta de sus botones);
    BLACKFORGE llega por ``BlackforgeWindow._execute`` con el Worker sincronizado
    para evitar Qt/hilos en la aserción. Ninguna ruta simula el servicio.
    """
    captured: list[tuple[str, dict]] = []

    def fake_run_invention(problem: str, **kwargs):
        captured.append((problem, kwargs))
        return copy.deepcopy(sheet)

    monkeypatch.setattr("criba.invention_service.run_invention", fake_run_invention)

    for mode in sorted(VALID_LOTTERY_MODES):
        captured.clear()
        actions._run_inventar(
            "paridad de generación", mode=mode, seed=123, history_storage=False
        )
        assert len(captured) == 1
        problem, kwargs = captured[0]
        assert problem == "paridad de generación"
        assert kwargs.get("mode", "stratified") == mode
        assert kwargs["seed"] == 123
        assert kwargs["history_storage"] is False

    class _SyncSignals:
        def __init__(self) -> None:
            self.done = self
            self.fail = self

        def connect(self, *_args, **_kwargs) -> None:
            pass

        def emit(self, *_args, **_kwargs) -> None:
            pass

    class _SyncWorker:
        def __init__(self, fn):
            self.fn = fn
            self.signals = _SyncSignals()

    def _sync_start(win, worker, operation: str = "") -> None:
        worker.fn()
        win._set_busy(False)

    monkeypatch.setattr("criba.ui.actions.Worker", _SyncWorker)
    monkeypatch.setattr("criba.ui.actions._start_worker", _sync_start)

    from criba.ui.blackforge_window import BlackforgeWindow

    win = BlackforgeWindow(database=str(tmp_path / "parity.sqlite3"), query="paridad de generación")
    try:
        for mode in sorted(VALID_LOTTERY_MODES):
            captured.clear()
            win._select_mode(mode)
            win.seed_input.setText("123")
            win._execute()
            assert len(captured) == 1
            problem, kwargs = captured[0]
            assert problem == "paridad de generación"
            assert kwargs.get("mode", "stratified") == mode
            assert kwargs["seed"] == 123
            assert kwargs["history_storage"] is win.store
            methods = kwargs["methods"]
            assert len(methods) == 750  # 723 BLACKFORGE + 27 operadores CRIBA
            method_ids = [
                str(method.get("id") or method.get("blackforge_id") or "")
                for method in methods
            ]
            assert any(method_id.startswith("BF-") for method_id in method_ids)
            assert any(method_id.startswith("OP-") for method_id in method_ids)
    finally:
        win.close()


def test_saved_proposal_survives_a_fresh_python_process(tmp_path, sheet):
    import json
    import os
    import subprocess

    from criba.storage import Storage

    database = tmp_path / "fresh-process.sqlite3"
    ident = Storage(database).save_invention(sheet, selected_index=0)
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(ROOT / "src")
    reader = (
        "import json,sys; from criba.storage import Storage; "
        "record=Storage(sys.argv[1]).get(sys.argv[2]); "
        "print(json.dumps(record, ensure_ascii=True))"
    )
    result = subprocess.run(
        [sys.executable, "-c", reader, str(database), ident],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    recovered = json.loads(result.stdout)
    assert recovered["id"] == ident
    assert recovered["packet"]["sheet"] == sheet
    assert recovered["packet"]["selected_index"] == 0
    assert recovered["status"] == "PROPUESTA"


def test_shadow_save_and_reopen_from_real_history(qapp, tmp_path, sheet):
    database = str(tmp_path / "history.sqlite3")
    first = ShadowWindow(database=database)
    try:
        actions._apply_new_problem(first, sheet["query"])
        actions._on_invented(first, sheet)
        assert first.packet is None, "a proposal is not a deterministic evaluation"
        assert first.candidates.save_idea.isEnabled()
        first.candidates.save_idea.click()
        saved = first.store.list_sessions()
        assert len(saved) == 1
        assert first.store.get(saved[0]["id"])["packet"]["sheet"] == sheet
        expected = copy.deepcopy(sheet)
    finally:
        first.close()
        qapp.processEvents()
    second = ShadowWindow(database=database)
    timer = QTimer()
    timer.setSingleShot(True)

    def load_first_history_row():
        dialog = QApplication.activeModalWidget()
        assert isinstance(dialog, QDialog)
        entries = dialog.findChild(QListWidget)
        assert entries is not None and entries.count() == 1
        entries.setCurrentRow(0)
        button = next(
            b for b in dialog.findChildren(QPushButton) if b.text() == "Cargar como idea activa"
        )
        button.click()

    timer.timeout.connect(load_first_history_row)
    timer.start(80)
    try:
        actions.on_historial(second)
        assert second.invent_sheet == expected
        assert (
            expected["entries"][0]["mecanismo"]
            in second.candidates.interpretation_output.toPlainText()
        )
        assert second.problem == expected["query"]
        assert second.store.list_sessions() == saved
    finally:
        timer.stop()
        second.close()
        qapp.processEvents()
