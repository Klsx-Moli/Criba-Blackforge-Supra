"""CB-L03: carga de SUPRA y almacenamiento durable — volumen sin corrupción.

Contra ProjectStateManager real (disco, no red): crear muchos proyectos,
persistir, listar masivamente y recuperar cada uno. Verifica que el volumen
no degrada la integridad ni mezcla payloads.

Invariantes (del megaprompt):
- sin parcial visible como completo
- lineage preservado: cada proyecto recupera su propio estado
- LIST coherente bajo carga
- PERSISTED != EXECUTED

Volumen moderado (100 proyectos) dentro del presupuesto del entorno; el
megaprompt permite abortar si disco/RAM se exceden (aquí son payloads pequeños).

Sin red, sin subproceso: storage_dir aislado bajo tmp_path.
"""
from __future__ import annotations

import sys
from pathlib import Path

_CRIBA_ROOT = Path(__file__).resolve().parents[2]
_SUPRA_SRC = _CRIBA_ROOT.parent / "supra" / "src"
if str(_SUPRA_SRC) not in sys.path:
    sys.path.insert(0, str(_SUPRA_SRC))

from supra_agentic.state import (  # noqa: E402
    PROVENANCE_ARTIFACT,
    ProjectStateManager,
)


def _manager(tmp_path: Path) -> ProjectStateManager:
    return ProjectStateManager(tmp_path / "supra_state")


# --------------------------------------------------------------------------
# Volumen: crear N proyectos, persistir, verificar integridad
# --------------------------------------------------------------------------


def test_crear_100_proyectos_integridad(tmp_path: Path) -> None:
    """100 proyectos creados y persistidos: cada uno recupera su propio objetivo."""
    manager = _manager(tmp_path)
    n = 100
    for i in range(n):
        manager.create_project(f"objetivo numero {i}", project_id=f"proj-{i:04d}")

    # Cada uno recupera su objetivo exacto desde disco (lineage preservado).
    for i in range(n):
        posture, source, _a, _e = manager.get_project_with_provenance(f"proj-{i:04d}")
        assert posture is not None
        assert posture.objective == f"objetivo numero {i}"


def test_list_masivo_coherente(tmp_path: Path) -> None:
    """LIST sobre 100 proyectos devuelve todos sin errores espurios."""
    manager = _manager(tmp_path)
    for i in range(100):
        manager.create_project(f"obj {i}", project_id=f"proj-{i:04d}")

    projects, errors = manager.list_projects_with_errors(limit=200)
    ids = {p.project_id for p in projects}
    assert len(ids) == 100
    assert errors == []


def test_list_limit_respetado(tmp_path: Path) -> None:
    """El limit de LIST se respeta: no devuelve más de lo pedido."""
    manager = _manager(tmp_path)
    for i in range(100):
        manager.create_project(f"obj {i}", project_id=f"proj-{i:04d}")

    projects, _errors = manager.list_projects_with_errors(limit=10)
    assert len(projects) == 10


def test_recuperacion_masiva_tras_reinicio(tmp_path: Path) -> None:
    """Un manager fresco recupera los 100 proyectos desde disco sin pérdida."""
    manager1 = _manager(tmp_path)
    for i in range(100):
        manager1.create_project(f"objetivo {i}", project_id=f"proj-{i:04d}")
    del manager1

    manager2 = _manager(tmp_path)  # reinicio, caché vacía
    perdidos = []
    for i in range(100):
        posture, source, _a, _e = manager2.get_project_with_provenance(f"proj-{i:04d}")
        if posture is None or posture.objective != f"objetivo {i}":
            perdidos.append(i)
    assert not perdidos, f"proyectos perdidos/corruptos tras reinicio: {perdidos[:10]}"


def test_sin_mezcla_de_payloads(tmp_path: Path) -> None:
    """Bajo carga, ningún proyecto recupera el objetivo de otro (sin mezcla)."""
    manager = _manager(tmp_path)
    objetivos = {f"proj-{i:04d}": f"objetivo-unico-{i}" for i in range(50)}
    for pid, obj in objetivos.items():
        manager.create_project(obj, project_id=pid)

    for pid, obj in objetivos.items():
        posture, _s, _a, _e = manager.get_project_with_provenance(pid)
        assert posture is not None
        assert posture.objective == obj, f"{pid} recuperó el payload equivocado"


# --------------------------------------------------------------------------
# Payload grande: un objetivo largo no corrompe
# --------------------------------------------------------------------------


def test_objetivo_largo_no_corrompe(tmp_path: Path) -> None:
    """Un objetivo cercano al límite se persiste y recupera íntegro.

    create_project normaliza con .strip() (espacios exteriores); el contenido
    interior se conserva byte a byte. No es corrupción: es la normalización
    declarada del almacenamiento.
    """
    manager = _manager(tmp_path)
    largo = ("optimizar " + "el proceso de aprobacion documental " * 40).strip()  # ~1400 chars
    manager.create_project(largo, project_id="proj-largo")

    manager2 = _manager(tmp_path)  # reinicio
    posture, source, _a, _e = manager2.get_project_with_provenance("proj-largo")
    assert posture is not None
    assert posture.objective == largo
    assert source == PROVENANCE_ARTIFACT


# --------------------------------------------------------------------------
# PERSISTED != EXECUTED bajo carga
# --------------------------------------------------------------------------


def test_todos_recieved_no_ejecutados(tmp_path: Path) -> None:
    """Tras crear 100 proyectos, todos están en RECEIVED, ninguno ejecutado."""
    manager = _manager(tmp_path)
    for i in range(100):
        manager.create_project(f"obj {i}", project_id=f"proj-{i:04d}")

    manager2 = _manager(tmp_path)
    ejecutados = []
    for i in range(100):
        posture, _s, _a, _e = manager2.get_project_with_provenance(f"proj-{i:04d}")
        if posture is not None and posture.stage.value != "RECEIVED":
            ejecutados.append(i)
    assert not ejecutados, f"proyectos no-RECEIVED inesperados: {ejecutados[:10]}"


# --------------------------------------------------------------------------
# LIST bajo un disco con un artefacto corrupto entre muchos válidos
# --------------------------------------------------------------------------


def test_list_con_un_corrupto_entre_muchos(tmp_path: Path) -> None:
    """Un artefacto corrupto entre 50 válidos se reporta sin ocultar los válidos."""
    manager = _manager(tmp_path)
    for i in range(50):
        manager.create_project(f"obj {i}", project_id=f"proj-{i:04d}")
    # Corrompemos uno.
    (tmp_path / "supra_state" / "proj-0025.json").write_text("roto", encoding="utf-8")

    projects, errors = manager.list_projects_with_errors(limit=200)
    ids = {p.project_id for p in projects}
    # Los válidos siguen presentes (49 o 50 según caché).
    assert "proj-0000" in ids
    assert "proj-0049" in ids
    # El corrupto se declara.
    error_ids = {e["project_id"] for e in errors}
    assert "proj-0025" in error_ids
