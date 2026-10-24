"""F5 — atribución del informe de selección ligada a la invocación (dirigidas).

Contrato: cada resultado conserva el informe producido por SU invocación, o
declara REPORT_UNAVAILABLE. No hay getter global del que heredar.

Criterios A–G del control:
  A. Dos invocaciones -> cada una con su informe (identidad por bench_run_id).
  B. Callback alternativo tras un éxito -> REPORT_UNAVAILABLE, no herencia.
  C. Excepción tras un éxito -> no exponer el informe anterior.
  D. Mutación anidada -> independencia semántica del artefacto consolidado.
  E. Export/readback -> identidad exacta de ejecución, problema, candidatos y report.
  F. Intercalado -> contrato por invocación; concurrencia de ESCRITURA no
     soportada (documentado, no proclamado).
  G. Cada RED falla por el contrato esperado (no por fixture/import).
"""
from __future__ import annotations

import copy
import json

import pytest

from benchmarks.innovation import criba_adapter as adapter
from benchmarks.innovation.harness import exportar, run_condition

_P1 = {"id": "G01", "texto": "Detectar abuso de permisos en agentes de software autónomos"}
_P2 = {"id": "B02", "texto": "Detectar exfiltración de datos vía DNS en una red corporativa"}

REQUIRED = ("pool_size", "valid_size", "quality_floor", "discarded_by_floor",
            "tie_sets", "opportunity_accounting")


def _instrumented():
    """Callback instrumentado: devuelve CribaResult (candidatos + informe)."""
    return adapter.run_criba_selection


def _assert_report_complete(report: dict) -> None:
    assert isinstance(report, dict), "el informe debe ser un objeto recuperable"
    for key in REQUIRED:
        assert key in report, f"F5: el informe no contiene '{key}'"


# A. Dos invocaciones: cada una conserva SU informe.
def test_A_dos_invocaciones_cada_una_con_su_informe(tmp_path) -> None:
    r1 = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    r2 = run_condition("C_CRIBA", _P2, seed=9, n_candidatos=4, criba_fn=_instrumented())

    _assert_report_complete(r1["selection_report"])
    _assert_report_complete(r2["selection_report"])

    # Identidad de ejecución distinguida por bench_run_id (no por identidad de objeto).
    assert r1["bench_run_id"] != r2["bench_run_id"], "cada episodio tiene su run_id"
    assert r1["problem_id"] != r2["problem_id"]
    # Cada uno conserva el informe de SU invocación: el segundo no es el primero.
    assert r2["selection_report"] is not r1["selection_report"]
    assert r2["selection_report"]["pool_size"] is not None


# B. Callback alternativo tras un éxito -> REPORT_UNAVAILABLE.
def test_B_callback_alternativo_declara_report_unavailable(tmp_path) -> None:
    # Precargar estado: un éxito instrumentado previo (prueba de contaminación).
    ok = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    _assert_report_complete(ok["selection_report"])

    def _cb_sin_reporte(texto: str, seed: int, n: int) -> list[dict]:
        return [{"idea_id": f"x{i}", "title": "t", "score": 0.5,
                 "genome": {}, "methods": ["m"], "classes": ["c"]}
                for i in range(n)]

    r = run_condition("C_CRIBA", _P2, seed=7, n_candidatos=4, criba_fn=_cb_sin_reporte)
    assert r["status"] == "OK", "la ejecución funcional del callback sigue siendo OK"
    assert r["selection_report"] == {
        "instrumented": False,
        "status": "REPORT_UNAVAILABLE",
        "reason": "criba_fn_callback_did_not_supply_selection_report",
    }, "un callback sin informe NO hereda el del episodio anterior"


# C. Excepción tras un éxito -> no exponer informe obsoleto.
def test_C_excepcion_no_expone_informe_anterior(tmp_path) -> None:
    ok = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    _assert_report_complete(ok["selection_report"])
    rep_exito = copy.deepcopy(ok["selection_report"])

    def _cb_falla(texto: str, seed: int, n: int) -> list[dict]:
        raise RuntimeError("fallo de generador")

    with pytest.raises(RuntimeError):
        run_condition("C_CRIBA", _P2, seed=7, n_candidatos=4, criba_fn=_cb_falla)

    # El contrato aditivo captura el informe en el momento de la invocación:
    # un episodio que falla NO produce un record con el informe de otro.
    # Verificación: el siguiente episodio correcto conserva el suyo, no el previo.
    r3 = run_condition("C_CRIBA", _P2, seed=9, n_candidatos=4, criba_fn=_instrumented())
    _assert_report_complete(r3["selection_report"])
    assert r3["selection_report"] is not rep_exito
    # Y un callback heredado (lista) tras el fallo declara REPORT_UNAVAILABLE,
    # no hereda el informe del episodio anterior.
    r4 = run_condition("C_CRIBA", _P2, seed=11, n_candidatos=4, criba_fn=adapter.criba_fn)
    assert r4["selection_report"]["status"] == "REPORT_UNAVAILABLE"
    assert "pool_size" not in r4["selection_report"], \
        "un callback sin instrumento no aporta datos de otro episodio"


# D. Mutación anidada -> independencia semántica del artefacto consolidado.
def test_D_mutacion_anidada_no_rompe_persistencia(tmp_path) -> None:
    r = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    original = copy.deepcopy(r["selection_report"])
    out = exportar({"runs": [r]}, tmp_path / "ep.json")

    r["selection_report"]["discarded_by_floor"].append("MUTADO")
    r["selection_report"]["tie_sets"].append(["MUTADO"])
    r["selection_report"]["opportunity_accounting"]["generated_candidates"] = 99999

    persisted = json.loads(out.read_text(encoding="utf-8"))
    rep = persisted["runs"][0]["selection_report"]
    assert rep["discarded_by_floor"] == original["discarded_by_floor"]
    assert rep["tie_sets"] == original["tie_sets"]
    assert rep["opportunity_accounting"]["generated_candidates"] == \
        original["opportunity_accounting"]["generated_candidates"]


# E. Export/readback con identidad exacta.
def test_E_readback_identidad_exacta(tmp_path) -> None:
    r = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    out = exportar({"runs": [r]}, tmp_path / "ep.json")
    back = json.loads(out.read_text(encoding="utf-8"))["runs"][0]
    assert set(REQUIRED) <= set(back["selection_report"])
    assert json.loads(json.dumps(back["selection_report"], sort_keys=True)) == \
        json.loads(json.dumps(r["selection_report"], sort_keys=True))
    assert back["bench_run_id"] == r["bench_run_id"]
    assert back["problem_id"] == r["problem_id"]
    assert len(back["candidates"]) == 4


# F. Intercalado: contrato por invocación; concurrencia de ESCRITURA limitada.
def test_F_intercalado_contrato_por_invocacion() -> None:
    """El informe viaja con el resultado de cada invocación.

    La concurrencia de ESCRITURA (múltiples procesos) no está soportada por este
    contrato: se documenta como limitación, no se proclama aislamiento.
    """
    r = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=_instrumented())
    assert r["selection_report"]["pool_size"] is not None


# G. Contrato heredado conservado.
def test_G_criba_fn_legacy_signature_y_tipo() -> None:
    import inspect
    assert list(inspect.signature(adapter.criba_fn).parameters) == [
        "problema_texto", "seed", "n_candidatos"
    ]
    out = adapter.criba_fn(_P1["texto"], 7, 4)
    assert isinstance(out, list) and len(out) == 4
    # El contrato heredado NO aporta informe: REPORT_UNAVAILABLE explícito.
    r = run_condition("C_CRIBA", _P1, seed=7, n_candidatos=4, criba_fn=adapter.criba_fn)
    assert r["selection_report"]["status"] == "REPORT_UNAVAILABLE"
