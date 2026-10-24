"""El registry debe declarar la ruta de implementación que realmente existe.

Hallazgo corregido (2026-10-23): T081 declaraba `criba.intelligence.scoring.novelty`
pero la implementación real vive en `criba.scoring.novelty`. El generador
(`gen_registry.py`) prefijaba `criba.intelligence.` a ciegas, de modo que un módulo
fuera de ese paquete quedaba apuntando a una ruta inexistente.

Este test falla si el desfase se reintroduce, para cualquier técnica cuyo módulo
declarado exista en el árbol fuente.
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from criba.intelligence.registry import TechniqueRegistry

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "intelligence" / "technique_registry.yaml"


def _module_exists(dotted: str) -> bool:
    """True si el módulo punteado COMPLETO es importable.

    Cobertura falsa corregida (2026-10-23): la versión previa devolvía True
    si importaba *cualquier prefijo* del dotted (p.ej. el paquete contenedor
    `criba.intelligence.scoring`), de modo que un módulo declarado que no
    existía como módulo completo (p.ej. `criba.intelligence.scoring.novelty`)
    seguía pasando el test. Aquí se exige importar el módulo declarado entero.
    """
    try:
        importlib.import_module(dotted)
        return True
    except ModuleNotFoundError:
        return False
    except Exception:
        # El módulo existe pero falla al importar por otra causa (dependencia,
        # error de código) — sigue siendo un módulo real, no un camino roto.
        return True


def test_declared_modules_resolve_to_real_imports() -> None:
    """Cada `module` de una técnica IMPLEMENTED debe importar como módulo
    completo; si no, el registro miente sobre la ruta de implementación.

    Restringido a IMPLEMENTED: las técnicas PLANNED declaran rutas de trabajo
    futuro que, por definición, aún no existen en el árbol fuente (son
    objetivos, no afirmaciones de implementación). Verificarlas daría falsos
    positivos legítimos, no un defecto de trazabilidad.
    """
    registry = TechniqueRegistry(REGISTRY_PATH)
    broken: list[str] = []
    for technique in registry.all():
        if getattr(technique, "status", None) != "IMPLEMENTED":
            continue
        for module in technique.module or ():
            if not _module_exists(module):
                broken.append(f"{technique.id}: {module}")
    assert not broken, (
        "El registry declara módulos que no importan:\n  "
        + "\n  ".join(broken)
        + "\nRevisar gen_registry.py (prefijo automático) y reg_parts/*.txt."
    )


def test_t081_points_to_the_real_scoring_module() -> None:
    """Caso concreto del desfase: T081 vive en criba.scoring, no en intelligence."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    technique = registry.get("T081")
    assert technique.module == ("criba.scoring.novelty",), (
        f"T081 debe declarar la ruta real; declaró {technique.module}"
    )
    # Y la ruta corregida importa y expone la función canónica.
    module = importlib.import_module("criba.scoring.novelty")
    assert hasattr(module, "local_novelty"), "criba.scoring.novelty debe exponer local_novelty"


def _t104_t111_module_path(tid: str, expected: str) -> None:
    """Discriminante del desfase T104/T111: ambas funcionan sobre `scoring.evidence`
    (no sobre módulos `scoring.confidence`/`scoring.feasibility` que no existen)."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    technique = registry.get(tid)
    assert technique.module == (expected,), (
        f"{tid} debe declarar el módulo real donde vive su función; declaró {technique.module}"
    )
    module = importlib.import_module(expected)
    fn = "confidence" if tid == "T104" else "feasibility"
    assert hasattr(module, fn), f"{expected} debe exponer {fn}"


def test_t104_points_to_the_real_scoring_module() -> None:
    _t104_t111_module_path("T104", "criba.intelligence.scoring.evidence")


def test_t111_points_to_the_real_scoring_module() -> None:
    _t104_t111_module_path("T111", "criba.intelligence.scoring.evidence")


def test_t104_t111_modules_import_and_expose_functions() -> None:
    """Contrato mínimo: el módulo declarado por T104/T111 importa y expone ambas
    funciones de scoring, cerrando el hueco entre el registry y el consumidor real
    (tests/intelligence/test_t104_t111_scoring.py)."""
    registry = TechniqueRegistry(REGISTRY_PATH)
    for tid, fn in (("T104", "confidence"), ("T111", "feasibility")):
        mod = registry.get(tid).module[0]
        module = importlib.import_module(mod)
        assert hasattr(module, fn), f"{mod} debe exponer {fn}"
