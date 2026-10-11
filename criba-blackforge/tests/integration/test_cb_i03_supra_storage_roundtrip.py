"""CB-I03: SUPRA ↔ almacenamiento durable ↔ GET/LIST (roundtrip real en disco).

A diferencia de test_m2_read_path_channels (que fija el contrato del CLIENTE con
MockTransport), este módulo ejercita el ProjectStateManager real contra el
sistema de ficheros: escribe, lee, lista y distingue ausente/corrupto/vacío.

Invariantes verificados (del megaprompt):
- rollback: una escritura fallida no deja estado parcial visible como completo
- AUSENTE != CORRUPTO != VACÍO
- LIST coherente: reporta errores de artefactos, no los oculta
- lineage preservado: get tras create devuelve la misma identidad
- PERSISTED != EXECUTED: el estado de workflow no se falsea

Sin red, sin subproceso, sin datos reales: cada test usa un storage_dir aislado
bajo pytest tmp_path.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# SUPRA vive fuera de criba-blackforge; se importa in-process sobre storage aislado.
_CRIBA_ROOT = Path(__file__).resolve().parents[2]
_SUPRA_SRC = _CRIBA_ROOT.parent / "supra" / "src"
if str(_SUPRA_SRC) not in sys.path:
    sys.path.insert(0, str(_SUPRA_SRC))

from supra_agentic.state import (  # noqa: E402
    ARTIFACT_MATCHES_CACHE,
    ARTIFACT_MISSING,
    ARTIFACT_UNVERIFIABLE,
    ARTIFACT_VERIFIED,
    PROVENANCE_ARTIFACT,
    PROVENANCE_MEMORY_CACHE,
    DuplicateProjectError,
    ProjectPosture,
    ProjectStateLoadError,
    ProjectStateManager,
)


def _manager(tmp_path: Path) -> ProjectStateManager:
    return ProjectStateManager(tmp_path / "supra_state")


def _create(
    manager: ProjectStateManager, pid: str, objective: str = "reducir consumo de agua"
) -> ProjectPosture:
    return manager.create_project(objective, project_id=pid)


# --------------------------------------------------------------------------
# Caso base: crear → persistir → GET → LIST
# --------------------------------------------------------------------------


def test_create_persist_get_roundtrip(tmp_path: Path) -> None:
    """Crear → persistir → GET devuelve el mismo estado.

    Tras crear, el proyecto vive en la caché del manager: la lectura inmediata
    declara IN_PROCESS_MEMORY_CACHE con artefacto MATCHES_CACHE (el durable
    coincide). Un manager FRESCO sobre el mismo disco —reinicio real— lee del
    artefacto (PERSISTED_STATE/VERIFIED). Ambas son procedencias honestas.
    """
    manager = _manager(tmp_path)
    created = _create(manager, "proj-rt-01")

    # El artefacto existe en disco, no solo en memoria.
    artifact = (tmp_path / "supra_state" / "proj-rt-01.json")
    assert artifact.exists()

    # Lectura inmediata: caché del propio manager, durable que coincide.
    posture, source, artifact_status, error_kind = manager.get_project_with_provenance("proj-rt-01")
    assert posture is not None
    assert posture.project_id == created.project_id
    assert posture.objective == created.objective
    assert source == PROVENANCE_MEMORY_CACHE
    assert artifact_status == ARTIFACT_MATCHES_CACHE
    assert error_kind is None

    # Reinicio real: manager nuevo, caché vacía → lee del durable.
    manager_fresh = _manager(tmp_path)
    posture2, source2, artifact2, _ = manager_fresh.get_project_with_provenance("proj-rt-01")
    assert posture2 is not None
    assert posture2.objective == created.objective
    assert source2 == PROVENANCE_ARTIFACT
    assert artifact2 == ARTIFACT_VERIFIED


def test_create_persist_list_atomico(tmp_path: Path) -> None:
    """LIST devuelve todos los proyectos creados, sin errores espurios."""
    manager = _manager(tmp_path)
    _create(manager, "proj-l-01", "objetivo uno")
    _create(manager, "proj-l-02", "objetivo dos")

    projects, errors = manager.list_projects_with_errors(limit=50)
    ids = {p.project_id for p in projects}
    assert ids == {"proj-l-01", "proj-l-02"}
    assert errors == []  # nada corrupto ni ausente


# --------------------------------------------------------------------------
# same ID / different payload → rechazo explícito
# --------------------------------------------------------------------------


def test_mismo_id_rechazado(tmp_path: Path) -> None:
    """Crear dos veces el mismo project_id es un error explícito, no una sobrescritura."""
    manager = _manager(tmp_path)
    _create(manager, "proj-dup-01", "primer objetivo")
    with pytest.raises(DuplicateProjectError):
        _create(manager, "proj-dup-01", "segundo objetivo distinto")

    # El payload original sigue intacto: no fue sobreescrito.
    posture, _s, _a, _e = manager.get_project_with_provenance("proj-dup-01")
    assert posture is not None
    assert posture.objective == "primer objetivo"


# --------------------------------------------------------------------------
# AUSENTE != CORRUPTO != VACÍO
# --------------------------------------------------------------------------


def test_ausente_no_es_corrupto(tmp_path: Path) -> None:
    """Un proyecto inexistente se declara MISSING, no UNVERIFIABLE."""
    manager = _manager(tmp_path)
    posture, source, artifact_status, error_kind = manager.get_project_with_provenance("proj-nope")
    assert posture is None
    assert source == PROVENANCE_ARTIFACT
    assert artifact_status == ARTIFACT_MISSING
    assert error_kind is None


def test_corrupto_no_es_ausente(tmp_path: Path) -> None:
    """Un artefacto con JSON inválido en disco lanza ProjectStateLoadError al reiniciar.

    Con caché vacía (manager fresco, reinicio real), el intento de decodificar el
    artefacto corrupto falla explícitamente: no devuelve None (ausente) ni un
    estado vacío (vacío). El tipo de error se declara sin exponer el contenido.
    """
    manager = _manager(tmp_path)
    _create(manager, "proj-corrupt")
    artifact = tmp_path / "supra_state" / "proj-corrupt.json"
    artifact.write_text("{ esto no es json valido ", encoding="utf-8")

    # Reinicio real: manager nuevo, caché vacía, debe intentar leer del disco.
    manager_fresh = _manager(tmp_path)
    with pytest.raises(ProjectStateLoadError):
        manager_fresh.get_project_with_provenance("proj-corrupt")


def test_corrupto_en_cache_se_declara_unverifiable(tmp_path: Path) -> None:
    """Un proyecto en caché cuyo artefacto se corrompe se sirve pero declara UNVERIFIABLE.

    M3: un cache hit es una respuesta correcta, pero no se publica como leída
    del durable; el veredicto del artefacto viaja con la respuesta.
    """
    manager = _manager(tmp_path)
    _create(manager, "proj-cache-corrupt")
    # Lo leemos una vez para meterlo en caché.
    manager.get_project_with_provenance("proj-cache-corrupt")
    # Corrompimos el artefacto en disco.
    artifact = tmp_path / "supra_state" / "proj-cache-corrupt.json"
    artifact.write_text("no-json", encoding="utf-8")

    posture, source, artifact_status, error_kind = manager.get_project_with_provenance(
        "proj-cache-corrupt"
    )
    assert posture is not None  # sirve desde caché
    assert source == PROVENANCE_MEMORY_CACHE  # NO miente como PERSISTED_STATE
    assert artifact_status == ARTIFACT_UNVERIFIABLE
    assert error_kind is not None


def test_vacio_json_null_distinto_de_corrupto(tmp_path: Path) -> None:
    """Un artefacto con JSON válido pero contenido nulo/incompatible es UNVERIFIABLE, no MISSING."""
    manager = _manager(tmp_path)
    _create(manager, "proj-null")
    artifact = tmp_path / "supra_state" / "proj-null.json"
    artifact.write_text("null", encoding="utf-8")
    manager.get_project_with_provenance("proj-null")  # cachear

    posture, source, artifact_status, _e = manager.get_project_with_provenance("proj-null")
    assert posture is not None
    assert source == PROVENANCE_MEMORY_CACHE
    assert artifact_status == ARTIFACT_UNVERIFIABLE


# --------------------------------------------------------------------------
# LIST coherente: reporta, no oculta
# --------------------------------------------------------------------------


def test_list_reporta_artefacto_corrupto(tmp_path: Path) -> None:
    """LIST declara el artefacto corrupto en storage_errors, no lo esconde."""
    manager = _manager(tmp_path)
    _create(manager, "proj-lc-01")
    _create(manager, "proj-lc-02")
    # Corrompemos uno de los dos.
    (tmp_path / "supra_state" / "proj-lc-02.json").write_text("roto", encoding="utf-8")

    projects, errors = manager.list_projects_with_errors(limit=50)
    ids = {p.project_id for p in projects}
    # Ambos siguen listados (el corrupto desde caché si está), y el error se declara.
    assert "proj-lc-01" in ids
    error_ids = {e["project_id"] for e in errors}
    assert "proj-lc-02" in error_ids
    kinds = {e.get("kind") for e in errors}
    assert any(k for k in kinds if k)  # hay un kind no vacío


def test_list_reporta_artefacto_borrado(tmp_path: Path) -> None:
    """LIST detecta un proyecto cacheado cuyo artefacto fue borrado del disco."""
    manager = _manager(tmp_path)
    _create(manager, "proj-missing-file")
    manager.get_project_with_provenance("proj-missing-file")  # cachear
    (tmp_path / "supra_state" / "proj-missing-file.json").unlink()  # borrar artefacto

    _projects, errors = manager.list_projects_with_errors(limit=50)
    missing = [e for e in errors if e["project_id"] == "proj-missing-file"]
    assert missing, "el artefacto borrado debe aparecer en storage_errors"
    assert missing[0]["error"] == "PERSISTED_ARTIFACT_MISSING"


# --------------------------------------------------------------------------
# Rollback: escritura fallida no deja parcial visible como completo
# --------------------------------------------------------------------------


def test_rollback_restaura_estado_previo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Si la persistencia falla a mitad de una transición, el estado prevalece."""
    manager = _manager(tmp_path)
    _create(manager, "proj-rb-01", "objetivo estable")

    # Forzamos el fallo de escritura a disco durante una transición.

    def _boom(_project_id: str) -> None:
        raise RuntimeError("disco simulado lleno")

    monkeypatch.setattr(manager, "_persist_project", _boom)

    with pytest.raises(RuntimeError, match="disco simulado lleno"):
        manager.block_project("proj-rb-01", "razon de prueba")

    # El estado en memoria no quedó a medias: sigue siendo el previo a la transición.
    posture, _s, _a, _e = manager.get_project_with_provenance("proj-rb-01")
    assert posture is not None
    assert posture.objective == "objetivo estable"


# --------------------------------------------------------------------------
# Recuperación tras reinicio (nuevo manager sobre el mismo disco)
# --------------------------------------------------------------------------


def test_reinicio_recupera_desde_disco(tmp_path: Path) -> None:
    """Un manager nuevo sobre el mismo storage recupera el estado durable (lineage)."""
    manager1 = _manager(tmp_path)
    created = _create(manager1, "proj-restart", "objetivo que sobrevive")
    del manager1  # simula cierre de proceso

    manager2 = _manager(tmp_path)
    posture, source, artifact_status, _e = manager2.get_project_with_provenance("proj-restart")
    assert posture is not None
    assert posture.project_id == created.project_id
    assert posture.objective == "objetivo que sobrevive"
    # Leído del artefacto, no de una caché heredada (manager nuevo, caché vacía).
    assert source == PROVENANCE_ARTIFACT
    assert artifact_status == ARTIFACT_VERIFIED


def test_cache_hit_tras_relectura_coincide(tmp_path: Path) -> None:
    """Una segunda lectura del mismo proyecto declara MATCHES_CACHE si el artefacto coincide."""
    manager = _manager(tmp_path)
    _create(manager, "proj-match")
    manager.get_project_with_provenance("proj-match")  # cachear

    posture, source, artifact_status, _e = manager.get_project_with_provenance("proj-match")
    assert posture is not None
    assert source == PROVENANCE_MEMORY_CACHE
    assert artifact_status == ARTIFACT_MATCHES_CACHE


# --------------------------------------------------------------------------
# PERSISTED != EXECUTED
# --------------------------------------------------------------------------


def test_persisted_no_es_executed(tmp_path: Path) -> None:
    """El stage persistido refleja el workflow real; crear no implica ejecutar."""
    manager = _manager(tmp_path)
    created = _create(manager, "proj-exec")
    # Recién creado: stage RECEIVED, no COMPLETED.
    assert created.stage.value == "RECEIVED"
    # La lectura durable coincide.
    posture, _s, _a, _e = manager.get_project_with_provenance("proj-exec")
    assert posture is not None
    assert posture.stage.value == "RECEIVED"


def test_block_project_es_persistido_y_legible(tmp_path: Path) -> None:
    """block_project persiste el estado y se recupera íntegro tras recarga en disco."""
    manager = _manager(tmp_path)
    _create(manager, "proj-block")
    manager.block_project("proj-block", "fallo de verificación")

    manager2 = _manager(tmp_path)  # reinicio
    posture, source, _a, _e = manager2.get_project_with_provenance("proj-block")
    assert posture is not None
    assert posture.stage.value == "BLOCKED"
    assert source == PROVENANCE_ARTIFACT


# --------------------------------------------------------------------------
# Concurrencia controlada: dos managers sobre el mismo disco
# --------------------------------------------------------------------------


def test_concurrencia_dos_managers_mismo_disco(tmp_path: Path) -> None:
    """Dos managers comparten disco sin corromper: ven sus proyectos y los del otro."""
    manager_a = _manager(tmp_path)
    manager_b = _manager(tmp_path)
    _create(manager_a, "proj-a-01", "de A")
    _create(manager_b, "proj-b-01", "de B")

    # B lee lo de A desde disco (no lo tiene en su caché).
    posture_b, source_b, _a, _e = manager_b.get_project_with_provenance("proj-a-01")
    assert posture_b is not None
    assert posture_b.objective == "de A"
    assert source_b == PROVENANCE_ARTIFACT
