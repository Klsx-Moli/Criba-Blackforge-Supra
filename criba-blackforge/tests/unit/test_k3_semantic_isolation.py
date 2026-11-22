"""K3 paso 3 - Aislamiento del laboratorio frente al camino productivo.

El handoff exige que ``invention_service.run_invention`` -> ``inventar``,
el adaptador/pipeline, el scoring/reward y la exportacion/SUPRA NO conviertan
una lectura semantica en evidencia.

Aqui se comprueba, sin proveedor y sin red:
  1. Ningun modulo de produccion importa el laboratorio.
  2. El laboratorio no se usa como fallback de scoring.
  3. Un candidato defendible sigue visible como candidato, no como validado.
"""

from __future__ import annotations

import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SRC = RAIZ / "src"
SHADOW = RAIZ / "shadow_ui"

MODULOS_LAB = ("semantic_lab", "semantic_critic_bridge", "semantic_bridge_test_data")


def _modulos_de_produccion() -> list[Path]:
    ficheros = list(SRC.rglob("*.py")) + list(SHADOW.rglob("*.py"))
    return [f for f in ficheros if f.is_file()]


def _imports_de(path: Path) -> set[str]:
    """Nombres de modulo importados por un fichero, sin ejecutarlo."""
    try:
        arbol = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return set()
    nombres: set[str] = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.Import):
            for alias in nodo.names:
                nombres.add(alias.name)
        elif isinstance(nodo, ast.ImportFrom):
            if nodo.module:
                nombres.add(nodo.module)
    return nombres


def test_ningun_modulo_de_produccion_importa_el_laboratorio() -> None:
    offenders: list[str] = []
    for fichero in _modulos_de_produccion():
        for nombre in _imports_de(fichero):
            if any(nombre.endswith(mod) or nombre == mod for mod in MODULOS_LAB):
                offenders.append(f"{fichero.relative_to(RAIZ)} -> {nombre}")
    assert offenders == [], (
        "El laboratorio se ha colado en produccion: " + "; ".join(offenders)
    )


def test_el_laboratorio_no_es_un_fallback_de_scoring() -> None:
    """El laboratorio no debe alimentar el scoring: cero referencias cruzadas.

    No se prohíbe la palabra "reward" (existe de forma legitima en el
    scoring del proyecto); se comprueba que NINGUN fichero que hable del
    laboratorio lo enlace con scoring.
    """
    for fichero in _modulos_de_produccion():
        texto = fichero.read_text(encoding="utf-8", errors="replace")
        habla_del_lab = any(mod in texto for mod in MODULOS_LAB)
        if not habla_del_lab:
            continue
        # Si un fichero menciona el laboratorio, no debe ademas puntuar.
        for marca in ("epistemic_score", "judge_score"):
            assert marca not in texto, (
                f"{fichero.relative_to(RAIZ)} mezcla laboratorio con {marca}"
            )


def test_el_laboratorio_no_se_importa_a_si_mismo_desde_produccion() -> None:
    """Un test o script de benchmarks si puede importarlo; produccion no."""
    permitidos = ("benchmarks/", "tests/")
    offenders: list[str] = []
    for fichero in _modulos_de_produccion():
        rel = fichero.relative_to(RAIZ).as_posix()
        if any(rel.startswith(p) for p in permitidos):
            continue
        for nombre in _imports_de(fichero):
            if any(nombre.endswith(mod) for mod in MODULOS_LAB):
                offenders.append(rel)
    assert offenders == []


def test_candidato_argumentado_no_es_promocion() -> None:
    """La disposicion dice candidato argumentado, no validado ni PASS."""
    from benchmarks.innovation.semantic_lab import OUTCOMES

    # OUTCOMES son estados de proceso, no de promocion.
    for outcome in OUTCOMES:
        assert "PASS" != outcome
        assert "VALIDATED" != outcome
    assert "CAUSALLY_ARGUED_CANDIDATE" not in OUTCOMES