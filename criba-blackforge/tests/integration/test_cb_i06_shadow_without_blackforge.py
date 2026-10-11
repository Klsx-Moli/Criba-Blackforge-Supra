"""CB-I06: Shadow ↔ BLACKFORGE sin acoplamiento — aislamiento ante fallo.

Complementa test_blackforge_unavailable_sentinel (que bloquea BLACKFORGE en
sys.modules y prueba imports/arranque). Aquí se añaden los casos de BLACKFORGE
CORRUPTO o que FALLA al importar/inicializar, del megaprompt:

- un módulo BLACKFORGE que lanza al importar no tumba CRIBA
- un módulo BLACKFORGE corrupto (sintaxis inválida) no tumba CRIBA
- CRIBA/SUPRA/Shadow siguen operativos con BLACKFORGE en estado de fallo

Invariante: CRIBA/SUPRA no dependen de BLACKFORGE; un fallo de BLACKFORGE no
corrompe el estado de CRIBA; sin activación accidental.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CRIBA_BLACKFORGE_DIR = Path(__file__).resolve().parents[2]
SHADOW_UI_DIR = CRIBA_BLACKFORGE_DIR / "shadow_ui"

# Módulos BLACKFORGE que se fuerzan a fallar.
_BLACKFORGE_MODS = [
    "criba.blackforge_agentic",
    "criba.blackforge_agentic_security",
    "criba.blackforge_catalog",
    "criba.blackforge_causal",
    "criba.blackforge_gui",
    "criba.blackforge_pipeline",
    "criba.blackforge_safety",
    "criba.blackforge_selector",
    "criba.ui.blackforge_screen",
    "criba.ui.blackforge_window",
]


def _criba_python() -> Path:
    return CRIBA_BLACKFORGE_DIR / ".venv" / "Scripts" / "python.exe"


def _run_with_blackforge_failure(
    failure_code: str, code: str, extra_path: str = ""
) -> subprocess.CompletedProcess:
    """Ejecuta 'code' en un subproceso donde importar BLACKFORGE lanza 'failure_code'.

    Se instala un meta_path finder que, para los módulos BLACKFORGE, devuelve un
    loader cuyo exec_module lanza la excepción indicada. Así se simula un módulo
    corrupto o que falla al inicializar, sin tocar el disco.
    """
    prologue = (
        "import sys, importlib.abc, importlib.util\n"
        "class _FailingLoader(importlib.abc.Loader):\n"
        "    def create_module(self, spec):\n"
        "        return None\n"
        "    def exec_module(self, module):\n"
        f"        raise {failure_code}\n"
        "class _FailingFinder(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if any(name == m or name.startswith(m + '.') for m in "
        f"{_BLACKFORGE_MODS!r}):\n"
        "            return importlib.util.spec_from_loader(name, _FailingLoader())\n"
        "        return None\n"
        "sys.meta_path.insert(0, _FailingFinder())\n"
    )
    if extra_path:
        prologue += f"sys.path.insert(0, {extra_path!r})\n"
    return subprocess.run(
        [str(_criba_python()), "-c", prologue + code],
        capture_output=True, text=True, timeout=60,
        cwd=str(CRIBA_BLACKFORGE_DIR),
    )


@pytest.mark.skipif(not _criba_python().exists(), reason="venv de criba ausente")
def test_blackforge_import_fallo_no_tumba_criba() -> None:
    """Si importar BLACKFORGE lanza RuntimeError, CRIBA sigue importando y operando."""
    result = _run_with_blackforge_failure(
        "RuntimeError('blackforge corrupto')",
        "from criba.engine import activate; "
        "p = activate('reducir consumo de agua'); assert p['ideas']",
    )
    assert result.returncode == 0, f"CRIBA cayó por fallo de BLACKFORGE: {result.stderr}"


@pytest.mark.skipif(not _criba_python().exists(), reason="venv de criba ausente")
def test_blackforge_sintaxis_corrupta_no_tumba_criba() -> None:
    """Un módulo BLACKFORGE con error de sintaxis simulado no tumba CRIBA."""
    result = _run_with_blackforge_failure(
        "SyntaxError('invalid syntax')",
        "from criba.engine import activate; assert activate is not None",
    )
    assert result.returncode == 0, f"CRIBA cayó por BLACKFORGE corrupto: {result.stderr}"


@pytest.mark.skipif(not _criba_python().exists(), reason="venv de criba ausente")
def test_shadow_window_con_blackforge_en_fallo() -> None:
    """ShadowWindow se construye aunque BLACKFORGE falle al importar."""
    result = _run_with_blackforge_failure(
        "ImportError('blackforge init failed')",
        "from shadow_window import ShadowWindow; assert ShadowWindow is not None",
        extra_path=str(SHADOW_UI_DIR),
    )
    assert result.returncode == 0, f"Shadow dependía de BLACKFORGE: {result.stderr}"


@pytest.mark.skipif(not _criba_python().exists(), reason="venv de criba ausente")
def test_supra_importa_con_blackforge_en_fallo() -> None:
    """SUPRA importa aunque BLACKFORGE esté en estado de fallo."""
    supra_src = CRIBA_BLACKFORGE_DIR.parent / "supra" / "src"
    result = _run_with_blackforge_failure(
        "RuntimeError('blackforge caido')",
        "from supra_agentic.service import app; assert app is not None",
        extra_path=str(supra_src),
    )
    assert result.returncode == 0, f"SUPRA cayó por BLACKFORGE: {result.stderr}"
