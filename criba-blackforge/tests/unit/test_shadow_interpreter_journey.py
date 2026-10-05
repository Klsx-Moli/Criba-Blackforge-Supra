"""Regresiones del selector y de las salidas visibles del intérprete en Shadow.

No prueba píxeles: fija el contrato funcional que la prueba visible ejercerá
sobre el EXE nuevo. La composición se crea con widgets Qt reales.
"""
from __future__ import annotations

import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from verification.interpreter_cases import resultado

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QPlainTextEdit

CRIBA_ROOT = Path(__file__).resolve().parents[2]
for candidate in (CRIBA_ROOT, CRIBA_ROOT / "shadow_ui"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

_puerto = importlib.import_module("criba.interprete.puerto")
InterpretationResult = _puerto.InterpretationResult
Provenance = _puerto.Provenance
_default_proponer = importlib.import_module("criba.inventar")._default_proponer
actions = importlib.import_module("criba.ui.actions")


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    return QApplication.instance() or QApplication([])


def _provenance() -> Provenance:
    return Provenance(
        interpreter_backend="openai_compatible",
        provider="nous_oauth_subscription_proxy",
        model_requested="stealth/space-bunny-alpha",
        model_reported="stealth/space-bunny-alpha",
        endpoint="http://127.0.0.1:8645/v1",
        timestamp="2026-10-03T03:00:00Z",
        duration_ms=123,
        prompt_version="proponer-v1",
        schema_version="propuesta-1",
        request_id="req-visible-1",
        fallback_used=False,
        raw_output_sha256="a" * 64,
    )


class _InterpreteFalso:
    backend = "openai_compatible"
    provider = "nous_oauth_subscription_proxy"
    model = "stealth/space-bunny-alpha"

    def __init__(self) -> None:
        self.calls = 0

    def operativo(self) -> tuple[bool, str]:
        return True, "endpoint y modelo disponibles"

    def proponer(self, *_args: Any, **_kwargs: Any) -> InterpretationResult:
        self.calls += 1
        raw = json.dumps(
            {
                "hipotesis": f"h{self.calls}",
                "mecanismo": f"m{self.calls}",
                "aportacion_por_tecnica": ["a", "b"],
                "supuestos": ["s"],
                "prueba_concreta": "p",
            },
            ensure_ascii=False,
        )
        return resultado(
            hipotesis=f"h{self.calls}",
            provenance=_provenance(),
            raw_output=raw,
            finish_reason="stop",
            completion_tokens=321,
            reasoning_tokens=0,
        )


def test_default_proponer_conserva_diagnostico_visible_sin_alterar_contrato():
    interprete = _InterpreteFalso()
    campos = _default_proponer(
        "problema",
        {"title": "A+B", "method1": "A", "method2": "B"},
        {"title": "dominio"},
        interprete=interprete,
    )
    assert campos["estado"] == "PROPUESTA"
    assert campos["interpretacion_raw_output"].startswith("{")
    assert campos["interpretacion_finish_reason"] == "stop"
    assert campos["interpretacion_usage"] == {
        "completion_tokens": 321,
        "reasoning_tokens": 0,
    }
    assert campos["interpretacion_provenance"]["request_id"] == "req-visible-1"


def test_run_inventar_fija_una_instancia_de_interprete_por_run(monkeypatch, tmp_path):
    interprete = _InterpreteFalso()
    construcciones: list[str] = []
    progresos: list[dict[str, Any]] = []

    def construir(backend: str):
        construcciones.append(backend)
        return interprete

    def invent_falso(problem: str, *, store: Any, proponer: Any, **_kwargs: Any):
        ideas = [
            {"title": "i1", "method1": "A", "method2": "B"},
            {"title": "i2", "method1": "C", "method2": "D"},
        ]
        entradas = []
        for idea in ideas:
            proposal = proponer(problem, idea, {"title": "d"}, [])
            entradas.append(
                {
                    "title": idea["title"],
                    "prior_art": {"verdict": "UNRESOLVED"},
                    "estado_interpretacion": proposal["estado"],
                    "hipotesis": proposal["hipotesis"],
                    "mecanismo": proposal["mecanismo"],
                    "interpretacion_error": proposal["error"],
                    "interpretacion_raw_output": proposal["interpretacion_raw_output"],
                    "interpretacion_finish_reason": proposal["interpretacion_finish_reason"],
                    "interpretacion_usage": proposal["interpretacion_usage"],
                    "interpretacion_provenance": proposal["interpretacion_provenance"],
                }
            )
        return {
            "query": problem,
            "seed": 1,
            "mode": "stratified",
            "entries": entradas,
            "totals": {
                "ideas": 2,
                "pending_interpretation": 0,
                "unresolved": 2,
                "partial_prior_art": 0,
                "survived_search": 0,
            },
        }

    monkeypatch.setattr("criba.interprete.seleccion.construir_interprete", construir)
    monkeypatch.setattr("criba.inventar.invent", invent_falso)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _sheet: tmp_path / "ledger.jsonl")
    monkeypatch.setattr("criba.intelligence.refresh.default_store", lambda: object())

    sheet = actions._run_inventar(
        "problema",
        backend="openai_compatible",
        progress=progresos.append,
        cancel_requested=lambda: False,
    )

    assert construcciones == ["openai_compatible"], "una configuración/instancia por run"
    assert interprete.calls == 2
    assert sheet["interpreter"]["model_requested"] == "stealth/space-bunny-alpha"
    assert [p["completed"] for p in progresos] == [1, 2]


def test_shadow_expone_selector_real_y_salidas_copiables(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "shadow.sqlite3"))
    try:
        selector = win.topcards.interpreter_selector
        assert selector.count() == 2
        assert selector.itemData(1) == "local_llama"
        assert "experimental" in selector.itemText(1)
        assert selector.itemData(0) == "openai_compatible"
        assert "Nous/Hermes" in selector.itemText(0)
        assert "Space Bunny" in selector.itemText(0)
        assert "local" in win.topcards.interpreter_status.text().lower()
        for widget in (
            win.candidates.raw_output,
            win.candidates.interpretation_output,
            win.candidates.dossier_output,
            win.candidates.supra_output,
        ):
            assert isinstance(widget, QPlainTextEdit)
            assert widget.isReadOnly(), "la salida debe ser seleccionable/copiable, no editable"
    finally:
        win.close()
        qapp.processEvents()


def test_shadow_expone_boton_guardar_idea_y_respeta_estado(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "save-button.sqlite3"))
    win.show()
    qapp.processEvents()
    try:
        button = win.candidates.save_idea
        assert button.text() == "💾 Guardar"
        assert button.isVisible(), "el botón debe estar visible en la interfaz"
        assert not button.isEnabled(), "sin packet no se puede guardar una idea"
        win.packet = {
            "original_query": "problema de prueba",
            "innovation": {"ideas": [{"title": "idea guardable"}]},
        }
        win.refs["rankingModel"].set_rows(
            [{"id": "idea-1", "title": "idea guardable", "score": 0.8}]
        )
        button.setEnabled(True)
        assert button.isEnabled()
    finally:
        win.close()
        qapp.processEvents()


def test_todas_pendientes_muestra_operacion_terminada_sin_fingir_exito(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "pending.sqlite3"))
    sheet = {
        "query": "problema pendiente",
        "seed": 8,
        "mode": "stratified",
        "entries": [
            {
                "title": "candidato sin interpretación",
                "estado_interpretacion": "PENDIENTE_INTERPRETACION",
                "hipotesis": "",
                "mecanismo": "",
                "aportacion_por_tecnica": [],
                "supuestos": [],
                "prueba_concreta": "",
                "ruta_desbloqueo": "",
                "interpretacion_error": "timeout",
                "interpretacion_raw_output": "",
                "interpretacion_finish_reason": "",
                "interpretacion_usage": {},
                "interpretacion_provenance": _provenance().sin_secretos(),
                "prior_art": {"verdict": "UNRESOLVED"},
            }
        ],
        "totals": {
            "ideas": 1,
            "pending_interpretation": 1,
            "unresolved": 1,
            "partial_prior_art": 0,
            "survived_search": 0,
        },
        "interpreter": {
            "provider": "nous_oauth_subscription_proxy",
            "model_requested": "stealth/space-bunny-alpha",
            "conectado": True,
            "motivo": "endpoint y modelo disponibles",
        },
    }
    try:
        actions._on_invented(win, sheet)
        nav = win.nav["navInventar"]
        assert nav.state == "done", "done solo significa que el worker terminó"
        assert "0/1 propuestas válidas" in str(nav.state_msg)
        assert "0 propuestas válidas" in win.refs["ideaEstadoChip"].text()
        assert "interpretación pendiente: 1" in win.refs["ideaSummary"].text()
        assert "timeout" in win.candidates.raw_output.toPlainText()
        assert "MOTIVO\ntimeout" in win.candidates.interpretation_output.toPlainText()
        assert win.candidates.output_tabs.currentWidget() is win.candidates.interpretation_output
        assert not win.right_panel.supra.isEnabled(), (
            "sin propuesta válida no se puede iniciar SUPRA"
        )
    finally:
        win.close()
        qapp.processEvents()


def test_nuevo_problema_limpia_resultados_anteriores_y_su_identidad(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "stale.sqlite3"))
    win.invent_sheet = {"query": "run viejo", "entries": [{"title": "viejo"}]}
    win.candidates.raw_output.setPlainText("SALIDA DEL RUN VIEJO")
    win.candidates.interpretation_output.setPlainText("INTERPRETACIÓN DEL RUN VIEJO")
    win.candidates.dossier_output.setPlainText("DOSSIER DEL RUN VIEJO")
    win.candidates.supra_output.setPlainText("GET DEL RUN VIEJO")
    try:
        actions._apply_new_problem(win, "run nuevo")
        assert win.invent_sheet is None
        assert win.candidates.raw_output.toPlainText() == ""
        assert win.candidates.interpretation_output.toPlainText() == ""
        assert win.candidates.dossier_output.toPlainText() == ""
        assert win.candidates.supra_output.toPlainText() == ""
        assert "VIEJO" not in win.refs["ideaSummary"].text()
    finally:
        win.close()
        qapp.processEvents()


def test_on_invented_renderiza_bruto_interpretacion_y_provenance(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "render.sqlite3"))
    raw = '{"hipotesis":"h completa","mecanismo":"m completo"}'
    sheet = {
        "query": "problema visible",
        "seed": 7,
        "mode": "stratified",
        "entries": [
            {
                "title": "candidato",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "h completa",
                "mecanismo": "m completo",
                "aportacion_por_tecnica": ["a", "b"],
                "supuestos": ["s"],
                "prueba_concreta": "prueba",
                "ruta_desbloqueo": "",
                "interpretacion_error": "",
                "interpretacion_raw_output": raw,
                "interpretacion_finish_reason": "stop",
                "interpretacion_usage": {"completion_tokens": 100, "reasoning_tokens": 0},
                "interpretacion_provenance": _provenance().sin_secretos(),
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
        "interpreter": {
            "backend": "openai_compatible",
            "provider": "nous_oauth_subscription_proxy",
            "model_requested": "stealth/space-bunny-alpha",
            "conectado": True,
            "motivo": "endpoint y modelo disponibles",
            "etiqueta": "OPERATIVO",
            "experimental": False,
        },
    }
    try:
        actions._on_invented(win, sheet)
        assert raw in win.candidates.raw_output.toPlainText()
        interpretada = win.candidates.interpretation_output.toPlainText()
        assert "h completa" in interpretada and "m completo" in interpretada
        assert "stealth/space-bunny-alpha" in interpretada
        assert "Finalización: stop" in interpretada
        assert "req-visible-1" in interpretada
        assert win.right_panel.supra.isEnabled(), (
            "una propuesta válida habilita el siguiente borde SUPRA"
        )
    finally:
        win.close()
        qapp.processEvents()


def test_interpretacion_muestra_un_candidato_por_vez_y_navega(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "navigate.sqlite3"))
    sheet = {
        "query": "reducir la fatiga en el cuerpo humano",
        "seed": 4,
        "mode": "stratified",
        "entries": [
            {
                "title": "ritmo circadiano adaptativo",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "h uno",
                "mecanismo": "m uno",
                "aportacion_por_tecnica": ["a uno"],
                "supuestos": ["s uno"],
                "prueba_concreta": "p uno",
                "ruta_desbloqueo": "",
                "interpretacion_error": "",
                "interpretacion_raw_output": "RAW-UNO",
                "interpretacion_finish_reason": "stop",
                "interpretacion_usage": {"completion_tokens": 10},
                "interpretacion_provenance": _provenance().sin_secretos(),
                "prior_art": {"verdict": "UNRESOLVED"},
            },
            {
                "title": "microdescansos biofeedback",
                "estado_interpretacion": "PROPUESTA",
                "hipotesis": "h dos",
                "mecanismo": "m dos",
                "aportacion_por_tecnica": ["a dos"],
                "supuestos": ["s dos"],
                "prueba_concreta": "p dos",
                "ruta_desbloqueo": "",
                "interpretacion_error": "",
                "interpretacion_raw_output": "RAW-DOS",
                "interpretacion_finish_reason": "stop",
                "interpretacion_usage": {"completion_tokens": 20},
                "interpretacion_provenance": _provenance().sin_secretos(),
                "prior_art": {"verdict": "UNRESOLVED"},
            },
        ],
        "totals": {
            "ideas": 2,
            "pending_interpretation": 0,
            "unresolved": 2,
            "partial_prior_art": 0,
            "survived_search": 0,
        },
        "interpreter": {
            "provider": "nous_oauth_subscription_proxy",
            "model_requested": "stealth/space-bunny-alpha",
            "conectado": True,
            "motivo": "endpoint y modelo disponibles",
        },
    }
    try:
        actions._on_invented(win, sheet)
        candidates = win.candidates
        assert candidates.output_tabs.currentWidget() is candidates.interpretation_output
        assert "h uno" in candidates.interpretation_output.toPlainText()
        assert "h dos" not in candidates.interpretation_output.toPlainText()
        assert "RAW-UNO" in candidates.raw_output.toPlainText()
        assert "RAW-DOS" not in candidates.raw_output.toPlainText()
        assert candidates.interpreter_position.text() == "Interpretación 1 de 2"
        assert not candidates.interpreter_previous.isEnabled()
        assert candidates.interpreter_next.isEnabled()

        candidates.interpreter_next.click()
        qapp.processEvents()

        assert "h dos" in candidates.interpretation_output.toPlainText()
        assert "h uno" not in candidates.interpretation_output.toPlainText()
        assert "RAW-DOS" in candidates.raw_output.toPlainText()
        assert "RAW-UNO" not in candidates.raw_output.toPlainText()
        assert candidates.interpreter_position.text() == "Interpretación 2 de 2"
        assert candidates.interpreter_previous.isEnabled()
        assert not candidates.interpreter_next.isEnabled()
    finally:
        win.close()
        qapp.processEvents()


def _lookup_falso(project_id: str = "proj-real-1") -> SimpleNamespace:
    receipt = SimpleNamespace(model_dump=lambda: {"criba_dossier_id": "dossier-real-1"})
    posture = SimpleNamespace(criba_dossier_receipt=receipt)
    return SimpleNamespace(
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
        project_id=project_id,
        stage="BLOCKED",
        posture=posture,
    )


def test_dossier_interpretado_hace_post_y_get_en_la_misma_ruta():
    llamadas: list[tuple[str, str]] = []
    lookup = _lookup_falso()
    posted = SimpleNamespace(
        project_id="proj-real-1",
        status="blocked",
        completion_status="BLOCKED",
        workflow_status="BLOCKED",
        verification_status="FAIL",
        secure_sandbox_status="RESTRICTED_BOUND_PASS_NOT_ISOLATED",
        scientific_status="NOT_VALIDATED",
        criba_mechanism_execution_status="NOT_EXECUTED",
        stage="BLOCKED",
    )

    class _Cliente:
        config = SimpleNamespace(endpoint="http://127.0.0.1:8765")

        def health(self):
            return SimpleNamespace(model_dump=lambda: {"status": "healthy"})

        def run_project(self, **kwargs):
            llamadas.append(("POST", str(kwargs.get("project_id") or "auto")))
            return posted

        def get_project(self, project_id: str):
            llamadas.append(("GET", project_id))
            return lookup

    dossier = {"dossier_id": "dossier-real-1"}
    report = actions._execute_supra_dossiers([dossier], client=_Cliente())
    assert llamadas == [("POST", "auto"), ("GET", "proj-real-1")]
    assert report["dossiers"] == [dossier]
    assert report["runs"][0]["read"]["status_source"] == "PERSISTED_STATE"
    assert report["runs"][0]["read"]["persisted_artifact_status"] == (
        "VERIFIED_FROM_ARTIFACT"
    )


def test_post_get_y_dossier_se_renderizan_separados_en_shadow(qapp, tmp_path):
    from shadow_window import ShadowWindow

    win = ShadowWindow(database=str(tmp_path / "supra-render.sqlite3"))
    dossier = {"dossier_id": "dossier-real-1", "mecanismo": "m real"}
    report = {
        "dossiers": [dossier],
        "runs": [
            {
                "dossier_id": "dossier-real-1",
                "project_id": "proj-real-1",
                "completion_status": "BLOCKED",
                "secure_sandbox_status": "RESTRICTED_BOUND_PASS_NOT_ISOLATED",
                "criba_mechanism_execution_status": "NOT_EXECUTED",
                "read": actions._supra_lookup_read(_lookup_falso()),
            }
        ],
    }
    win.invent_sheet = {"query": "q", "entries": []}
    try:
        actions._on_supra_dossiers_done(win, report)
        assert "dossier-real-1" in win.candidates.dossier_output.toPlainText()
        supra_text = win.candidates.supra_output.toPlainText()
        assert "proj-real-1" in supra_text
        assert "PERSISTED_STATE" in supra_text
        assert "VERIFIED_FROM_ARTIFACT" in supra_text
        assert win.candidates.output_tabs.currentWidget() is win.candidates.supra_output
    finally:
        win.close()
        qapp.processEvents()


def test_reapertura_recupera_ultimo_get_y_dossier_local(monkeypatch):
    lookup = _lookup_falso("proj-reopen-1")

    class _Cliente:
        config = SimpleNamespace(endpoint="http://127.0.0.1:8765")

        def health(self):
            return SimpleNamespace(model_dump=lambda: {"status": "healthy"})

        def list_projects(self, *, limit: int):
            assert limit == 1
            return SimpleNamespace(projects=[{"project_id": "proj-reopen-1"}])

        def get_project(self, project_id: str):
            assert project_id == "proj-reopen-1"
            return lookup

    dossier = {"dossier_id": "dossier-real-1", "mecanismo": "m recuperado"}
    monkeypatch.setattr(
        "criba.supra_dossier.cargar_ultimo_dossier", lambda: dossier, raising=False
    )
    report = actions._load_latest_supra(client=_Cliente())
    assert report["project_id"] == "proj-reopen-1"
    assert report["read"]["status_source"] == "PERSISTED_STATE"
    assert report["dossier"] == dossier


def test_dossier_interpretado_mapea_solo_contenido_declarado_al_protocolo():
    sd = importlib.import_module("criba.supra_dossier")
    entry = {
        "candidate_id": "candidate-interpreted",
        "run_id": "run-interpreted",
        "hipotesis": "el consumo baja manteniendo rendimiento",
        "mecanismo": "control por humedad y reparación de fugas",
        "prueba_concreta": "comparar m3 por tonelada y fallar si no baja 15%",
        "supuestos": ["la humedad medida representa la zona radicular"],
    }
    dossier = sd.preparar_dossier(entry, "reducir consumo de agua")
    protocol = dossier["prueba_discriminante"]
    assert protocol["observable"] == entry["prueba_concreta"]
    assert protocol["alternativa_explicativa"] == entry["supuestos"][0]
    assert protocol["resultado_favorable_mecanismo"] == entry["hipotesis"]
    assert protocol["resultado_favorable_alternativa"] == entry["supuestos"][0]
    assert protocol["regla_decision"] == entry["prueba_concreta"]
    assert all("inventad" not in str(value).lower() for value in protocol.values())


def test_dossier_respeta_cribashadow_home_y_se_recupera(monkeypatch, tmp_path):
    sd = importlib.import_module("criba.supra_dossier")
    home = tmp_path / "shadow-home"
    monkeypatch.setenv("CRIBASHADOW_HOME", str(home))
    dossier = {"dossier_id": "dossier-visible", "tipo": "plan", "mecanismo": "m"}
    path = sd.guardar_dossier(dossier)
    assert path.parent == home / "dossiers"
    assert sd.cargar_ultimo_dossier() == dossier


@pytest.mark.parametrize(
    ("error_kind", "expected"),
    [
        ("CORRUPT_JSON", "NO VERIFICABLE (JSON CORRUPTO)"),
        ("INCOMPATIBLE_SCHEMA", "NO VERIFICABLE (ESQUEMA INCOMPATIBLE)"),
        ("UNREADABLE", "NO VERIFICABLE (ARTEFACTO NO LEGIBLE)"),
        (None, "NO VERIFICABLE (CAUSA NO INFORMADA)"),
    ],
)
def test_shadow_distingue_la_causa_de_un_artefacto_no_verificable(
    error_kind: str | None, expected: str
) -> None:
    read = {"persisted_artifact_status": "UNVERIFIABLE"}
    if error_kind is not None:
        read["persisted_artifact_error_kind"] = error_kind
    assert actions._artifact_text(read) == expected


def test_shadow_lookup_no_descarta_la_clasificacion_del_artefacto() -> None:
    lookup = _lookup_falso()
    lookup.status_source = "IN_PROCESS_MEMORY_CACHE"
    lookup.persisted_artifact_status = "UNVERIFIABLE"
    lookup.persisted_artifact_error_kind = "INCOMPATIBLE_SCHEMA"

    read = actions._supra_lookup_read(lookup)

    assert read["persisted_artifact_error_kind"] == "INCOMPATIBLE_SCHEMA"
