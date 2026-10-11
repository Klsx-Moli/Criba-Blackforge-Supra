"""CB-I02: Shadow ↔ CRIBA ↔ intérprete ↔ cancelación cooperativa.

Complementa test_shadow_interpreter_journey (selector, worker, progreso,
reapertura). Aquí se prueba la cancelación cooperativa real de _run_inventar:

- cancelar antes → todas las propuestas quedan pendientes honestas, sin llamar
  al intérprete remoto
- cancelar a mitad → las ya iniciadas terminan, las siguientes quedan pendientes
- cancelar nunca fabrica un resultado ni promueve PENDIENTE a PROPUESTA
- el run termina sin excepción ni deadlock; el sheet declara cancel_requested

Sin Qt visible: _run_inventar es la capa de acciones real, se ejercita directa
con un intérprete falso y un invent determinista (mismo patrón que el journey).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from criba.ui import actions  # noqa: E402


class _InterpreteFalso:
    """Cuenta llamadas reales al intérprete; implementa InterpreterPort mínimo."""

    def __init__(self) -> None:
        self.calls = 0
        self.backend = "openai_compatible"
        self.provider = "falso"
        self.model = "falso-model"
        self.gate_report = None

    def operativo(self) -> tuple[bool, str]:
        return True, "falso operativo"

    def proponer(self, *args: Any, **kwargs: Any) -> Any:
        from criba.interprete.puerto import InterpretationResult

        self.calls += 1
        return InterpretationResult(
            estado="PROPUESTA",
            hipotesis="Hipótesis del intérprete falso suficientemente larga.",
            mecanismo="Mecanismo causal específico del intérprete falso aquí y allá.",
        )


def _invent_controlado(monkeypatch: pytest.MonkeyPatch, interprete: _InterpreteFalso, n: int):
    """Parchea selección + invent para un run determinista de n candidatos."""
    construcciones: list[str] = []

    def construir(backend: str):
        construcciones.append(backend)
        return interprete

    def invent_falso(problem: str, *, store: Any, proponer: Any, **_kwargs: Any):
        ideas = [{"title": f"i{k}", "method1": "A", "method2": "B"} for k in range(n)]
        entradas = []
        for idea in ideas:
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
            "totals": {"ideas": n, "pending_interpretation": 0, "unresolved": 0},
        }

    monkeypatch.setattr("criba.interprete.seleccion.construir_interprete", construir)
    monkeypatch.setattr("criba.inventar.invent", invent_falso)
    monkeypatch.setattr("criba.inventar.append_ledger", lambda _s: Path("ledger.jsonl"))
    monkeypatch.setattr("criba.intelligence.refresh.default_store", lambda: object())
    return construcciones


def _run(cancel, *, progress=None):
    """Ejecuta _run_inventar con el backend canónico; acorta las llamadas de test."""
    return actions._run_inventar(
        "problema", backend="openai_compatible",
        progress=progress, cancel_requested=cancel,
    )


def test_sin_cancelacion_todas_se_interpretan(monkeypatch, tmp_path: Path) -> None:
    """Control: sin cancelación, el intérprete procesa todos los candidatos."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=3)
    sheet = _run(lambda: False)
    assert interprete.calls == 3
    assert sheet["cancel_requested"] is False
    # Cada entrada lleva la hipótesis que devolvió el intérprete real.
    assert all(e["hipotesis"] for e in sheet["entries"])


def test_cancelar_antes_no_llama_interprete(monkeypatch, tmp_path: Path) -> None:
    """Cancelar desde el inicio: ninguna llamada remota, todo pendiente honesto."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=3)
    sheet = _run(lambda: True)
    # No se llamó al intérprete remoto.
    assert interprete.calls == 0
    assert sheet["cancel_requested"] is True
    # Ninguna propuesta se fabrica: todas sin hipótesis.
    assert all(not e["hipotesis"] for e in sheet["entries"])


def test_cancelar_a_mitad_las_siguientes_quedan_pendientes(
    monkeypatch, tmp_path: Path
) -> None:
    """Cancelar tras 2 candidatos: esos 2 se interpretaron, el resto queda pendiente."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=5)
    # Cancela a partir de la 3ª propuesta (completed >= 2).
    progresos: list[dict[str, Any]] = []
    sheet = actions._run_inventar(
        "problema",
        backend="openai_compatible",
        progress=progresos.append,
        cancel_requested=lambda: len(progresos) >= 2,
    )
    # Exactamente 2 llamadas al intérprete; las 3 restantes canceladas.
    assert interprete.calls == 2
    assert sheet["cancel_requested"] is True
    interpretadas = [e for e in sheet["entries"] if e["hipotesis"]]
    canceladas = [e for e in sheet["entries"] if not e["hipotesis"]]
    assert len(interpretadas) == 2
    assert len(canceladas) == 3
    # Las canceladas no llevan hipótesis fabricada.
    assert all(not e["mecanismo"] for e in canceladas)


def test_cancelacion_no_fabrina_resultado(monkeypatch, tmp_path: Path) -> None:
    """Un candidato cancelado no se promociona con contenido inventado."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=2)
    sheet = _run(lambda: True)
    for entry in sheet["entries"]:
        assert entry["hipotesis"] == ""
        assert entry["mecanismo"] == ""


def test_cancelacion_reporta_motivo(monkeypatch, tmp_path: Path) -> None:
    """La propuesta pendiente por cancelación declara el motivo, no queda vacía sin causa."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=1)
    sheet = _run(lambda: True)
    entry = sheet["entries"][0]
    # No hay hipótesis fabricada, pero el motivo de cancelación viaja en el error.
    assert entry["hipotesis"] == ""
    assert "cancel" in entry.get("interpretacion_error", "").casefold()


def test_run_cancelado_termina_sin_excepcion(monkeypatch, tmp_path: Path) -> None:
    """El run cancelado devuelve el sheet completo, sin lanzar ni colgarse."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=4)
    sheet = _run(lambda: True)
    assert isinstance(sheet, dict)
    assert sheet["query"] == "problema"
    assert len(sheet["entries"]) == 4


def test_cancel_requested_none_no_rompe(monkeypatch, tmp_path: Path) -> None:
    """Sin callback de cancelación, el run procede normal (retrocompatibilidad)."""
    interprete = _InterpreteFalso()
    _invent_controlado(monkeypatch, interprete, n=2)
    sheet = _run(None)
    assert interprete.calls == 2
    assert sheet["cancel_requested"] is False
