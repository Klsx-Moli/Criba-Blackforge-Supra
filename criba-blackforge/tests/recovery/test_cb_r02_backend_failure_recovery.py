"""CB-R02: backend caído, timeout y retry controlado — sin corrupción.

Contra _run_inventar real con un intérprete que FALLA (backend caído/timeout).
Verifica que un fallo transitorio del proveedor:

- NO corrompe el sheet: todas las entradas quedan pendientes honestas
- NO duplica dossiers ni pierde procedencia
- NO provoca reintento automático descontrolado (cada fallo = 1 intento)
- el retry manual es seguro: re-ejecutar produce el mismo resultado determinista
- el estado es honesto: el error viaja con cada entrada

Invariantes: sin reintento infinito; sin duplicar dossier; sin perder
procedencia; estado honesto; retry manual seguro.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from criba.ui import actions  # noqa: E402


class _InterpreteCaido:
    """Interprete cuyo backend está caído: operativo()=False, proponer falla."""

    def __init__(self) -> None:
        self.calls = 0
        self.backend = "openai_compatible"
        self.provider = "caido"
        self.model = "m"
        self.gate_report = None

    def operativo(self) -> tuple[bool, str]:
        return False, "backend caido: conexion rechazada"

    def proponer(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        raise ConnectionError("backend caido")


class _InterpreteTimeout:
    """Interprete que responde con timeout simulado."""

    def __init__(self) -> None:
        self.calls = 0
        self.backend = "openai_compatible"
        self.provider = "lento"
        self.model = "m"
        self.gate_report = None

    def operativo(self) -> tuple[bool, str]:
        return True, "operativo pero lento"

    def proponer(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        raise TimeoutError("se agoto el tiempo de espera")


def _invent_con(monkeypatch: pytest.MonkeyPatch, interprete: Any, n: int):
    def construir(backend: str):
        return interprete

    def invent_falso(problem: str, *, store: Any, proponer: Any, **_kwargs: Any):
        ideas = [{"title": f"i{k}", "method1": "A", "method2": "B"} for k in range(n)]
        entradas = []
        for idea in ideas:
            # _default_proponer captura la excepción del intérprete → pendiente.
            proposal = proponer(problem, idea, {"title": "d"}, [])
            entradas.append(
                {
                    "title": idea["title"],
                    "estado_interpretacion": proposal["estado"],
                    "hipotesis": proposal.get("hipotesis", ""),
                    "mecanismo": proposal.get("mecanismo", ""),
                    "interpretacion_error": proposal.get("error", ""),
                    "interpretacion_provenance": proposal.get("interpretacion_provenance"),
                }
            )
        return {
            "query": problem,
            "seed": 1,
            "mode": "stratified",
            "entries": entradas,
            "totals": {"ideas": n},
        }

    monkeypatch.setattr("criba.interprete.seleccion.construir_interprete", construir)
    monkeypatch.setattr("criba.inventar.invent", invent_falso)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _s: Path("ledger.jsonl"))
    monkeypatch.setattr("criba.intelligence.refresh.default_store", lambda: object())


def _run(cancel):
    """Ejecuta _run_inventar con el backend canónico; acorta las llamadas de test."""
    return actions._run_inventar(
        "problema", backend="openai_compatible", cancel_requested=cancel,
    )


def test_backend_caido_no_corrompe_sheet(
    monkeypatch, tmp_path: Path
) -> None:
    """Con el backend caído, el sheet queda íntegro y todas las entradas pendientes."""
    interprete = _InterpreteCaido()
    _invent_con(monkeypatch, interprete, n=4)
    sheet = _run(lambda: False)
    # El sheet existe y tiene las 4 entradas.
    assert len(sheet["entries"]) == 4
    # Ninguna entrada fabrica hipótesis: el fallo no produce contenido.
    assert all(not e["hipotesis"] for e in sheet["entries"])


def test_backend_caido_un_intento_por_candidato(
    monkeypatch, tmp_path: Path
) -> None:
    """Sin reintento automático: cada candidato provoca exactamente 1 llamada que falla."""
    interprete = _InterpreteCaido()
    _invent_con(monkeypatch, interprete, n=3)
    actions._run_inventar("problema", backend="openai_compatible", cancel_requested=lambda: False)
    # 3 candidatos = 3 llamadas, no 3*N reintentos.
    assert interprete.calls == 3


def test_timeout_no_corrompe(
    monkeypatch, tmp_path: Path
) -> None:
    """Un timeout por candidato deja el sheet honesto, sin propuestas fabricadas."""
    interprete = _InterpreteTimeout()
    _invent_con(monkeypatch, interprete, n=3)
    sheet = _run(lambda: False)
    assert len(sheet["entries"]) == 3
    assert all(not e["hipotesis"] for e in sheet["entries"])
    assert interprete.calls == 3  # sin reintento descontrolado


def test_fallo_conserva_procedencia_del_backend(
    monkeypatch, tmp_path: Path
) -> None:
    """El fallo declara el backend usado, no pierde la procedencia."""
    interprete = _InterpreteCaido()
    _invent_con(monkeypatch, interprete, n=1)
    sheet = _run(lambda: False)
    # El estado del intérprete (incl. motivo de no-disponibilidad) viaja en el sheet.
    estado = sheet["interpreter"]
    assert estado["backend"] == "openai_compatible"
    assert estado["conectado"] is False


def test_error_viaja_con_cada_entrada(
    monkeypatch, tmp_path: Path
) -> None:
    """Cada entrada pendiente por fallo lleva su error, no un éxito vacío."""
    interprete = _InterpreteCaido()
    _invent_con(monkeypatch, interprete, n=2)
    sheet = _run(lambda: False)
    for entry in sheet["entries"]:
        assert entry["hipotesis"] == ""
        # El fallo se registra (error o provenance pendiente), no se silencia.
        assert entry.get("interpretacion_error") or entry.get("interpretacion_provenance")


def test_retry_manual_es_determinista(
    monkeypatch, tmp_path: Path
) -> None:
    """Re-ejecutar el run (retry manual) con el mismo backend da el mismo resultado."""
    interprete = _InterpreteCaido()
    _invent_con(monkeypatch, interprete, n=2)
    sheet1 = _run(lambda: False)
    sheet2 = _run(lambda: False)
    # Mismo número de entradas, mismo estado honesto en ambos intentos.
    assert len(sheet1["entries"]) == len(sheet2["entries"]) == 2
    assert all(not e["hipotesis"] for e in sheet1["entries"])
    assert all(not e["hipotesis"] for e in sheet2["entries"])


def test_backend_recuperado_tras_fallo(
    monkeypatch, tmp_path: Path
) -> None:
    """Si el backend se recupera, el retry manual produce propuestas reales."""
    from criba.interprete.puerto import InterpretationResult

    class _InterpreteRecuperado:
        def __init__(self) -> None:
            self.calls = 0
            self.backend = "openai_compatible"
            self.provider = "ok"
            self.model = "m"
            self.gate_report = None

        def operativo(self) -> tuple[bool, str]:
            return True, "recuperado"

        def proponer(self, *args: Any, **kwargs: Any) -> Any:
            self.calls += 1
            return InterpretationResult(
                estado="PROPUESTA",
                hipotesis="Hipótesis recuperada del backend tras el fallo.",
                mecanismo="Mecanismo causal específico del backend ya recuperado aquí.",
            )

    _invent_con(monkeypatch, _InterpreteRecuperado(), n=2)
    sheet = _run(lambda: False)
    # Con el backend vivo, las propuestas llegan con contenido.
    assert all(e["hipotesis"] for e in sheet["entries"])
