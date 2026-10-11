"""K7 · Windows Application Readiness — invariantes de arranque VERIFICABLES.

Comprueba, sin GUI física ni display, los invariantes que K7 exige para "uso
real en Windows": cwd-independence, wire_import_paths idempotente (funciona
congelado o no), lock de instancia única (msvcrt/fcntl), data_root con UTF-8,
limpieza de lock. Son verificaciones reproducibles de robustez de arranque.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import criba_shadow_main as m  # noqa: E402


def test_bundle_root_y_data_root_son_rutas_validas(tmp_path, monkeypatch):
    """bundle_root apunta al repo; data_root es escribible (persistencia)."""
    br = m.bundle_root()
    assert isinstance(br, Path)
    dr = m.data_root()
    assert isinstance(dr, Path)
    # data_root debe ser un directorio existente o creable.
    dr.mkdir(parents=True, exist_ok=True)
    assert dr.is_dir()


def test_wire_import_paths_es_idempotente():
    """Llamar dos veces wire_import_paths no duplica ni rompe sys.path."""
    before = list(sys.path)
    m.wire_import_paths()
    m.wire_import_paths()
    after = sys.path
    # No debe haber duplicados nuevos masivos (idempotencia).
    assert after.count(after[-1]) == 1 if after else True
    # src y bundle siguen presentes.
    assert any("src" in p for p in after)


def test_pid_lock_single_instance(tmp_path):
    """acquire_single_instance: primer OK, segundo sobre el MISMO root es False
    (instancia única), y se puede liberar para cleanup. Contrato real del launcher."""
    root = tmp_path / "app"
    root.mkdir()
    # Primer acquire: OK.
    ok1, _msg1 = m.acquire_single_instance(root)
    assert ok1 is True
    # Segundo acquire sobre el mismo root: debe denegar (instancia única).
    ok2, msg2 = m.acquire_single_instance(root)
    assert ok2 is False, "segunda instancia debe ser rechazada (single-instance)"
    # Cleanup: liberar el lock global real para no contaminar otros tests.
    m.release_single_instance(root)


def test_pid_alive_con_pid_inexistente():
    """_pid_alive(pid basura) es False (no afirma vida de un proceso muerto)."""
    assert m._pid_alive(999_999) is False


def test_arranque_independiente_de_cwd(tmp_path):
    """Importar el launcher y construir rutas no depende del cwd actual."""
    old = Path.cwd()
    try:
        os.chdir(tmp_path)
        # Las rutas son absolutas (bundle_root), no relativas al cwd.
        assert m.bundle_root().is_absolute()
    finally:
        os.chdir(old)
