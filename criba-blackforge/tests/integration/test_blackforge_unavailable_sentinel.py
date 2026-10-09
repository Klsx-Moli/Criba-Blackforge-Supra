"""
P0 Sentinel: BLACKFORGE unavailable must not block CRIBA+SUPRA.

Each test runs in a subprocess with BLACKFORGE modules blocked in sys.modules
to prove real independence, not just absence of import errors.
"""
import subprocess
import sys
from pathlib import Path

import pytest

# Resolve paths relative to this file (tests/integration/)
CRIBA_BLACKFORGE_DIR = Path(__file__).parent.parent.parent  # criba-blackforge/
SHADOW_UI_DIR = CRIBA_BLACKFORGE_DIR / "shadow_ui"
SUPRA_DIR = CRIBA_BLACKFORGE_DIR.parent / "supra"


def _criba_python():
    return CRIBA_BLACKFORGE_DIR / ".venv" / "Scripts" / "python.exe"


def _supra_python():
    """Resolve SUPRA interpreter: env var or venv path."""
    import os
    env_py = os.environ.get("SUPRA_PYTHON")
    if env_py:
        return Path(env_py)
    return SUPRA_DIR / ".venv" / "Scripts" / "python.exe"


def _block_blackforge_and_run(code: str, extra_path: str = ""):
    """Run code in a subprocess with all BLACKFORGE modules blocked."""
    block_code = "import sys\n"
    block_code += "for mod in list(sys.modules):\n"
    block_code += "    if mod.startswith('criba.blackforge') or mod.startswith('criba.ui.blackforge'):\n"
    block_code += "        sys.modules[mod] = None\n"
    # Block all known BLACKFORGE package names
    for pkg in [
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
    ]:
        block_code += f"sys.modules['{pkg}'] = None\n"
    if extra_path:
        block_code += f"sys.path.insert(0, {extra_path!r})\n"
    block_code += code
    return block_code


def test_criba_imports_without_blackforge():
    """CRIBA must import without BLACKFORGE."""
    code = _block_blackforge_and_run("from criba.engine import activate; assert activate is not None")
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=30,
        cwd=str(CRIBA_BLACKFORGE_DIR)
    )
    assert result.returncode == 0, f"CRIBA import failed: {result.stderr}"


def test_supra_imports_without_blackforge():
    """SUPRA must import without BLACKFORGE."""
    supra_py = _supra_python()
    if not supra_py.exists():
        pytest.skip(f"SUPRA interpreter not found: {supra_py}")
    result = subprocess.run(
        [str(supra_py), "-c", "from supra_agentic.service import app; assert app is not None"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"SUPRA import failed: {result.stderr}"


def test_shadow_ui_imports_without_blackforge():
    """Shadow UI must import without BLACKFORGE."""
    criba_py = _criba_python()
    if not criba_py.exists():
        pytest.skip(f"CRIBA interpreter not found: {criba_py}")
    code = _block_blackforge_and_run(
        "from shadow_window import ShadowWindow; assert ShadowWindow is not None",
        extra_path=str(SHADOW_UI_DIR)
    )
    result = subprocess.run(
        [str(criba_py), "-c", code],
        capture_output=True, text=True, timeout=30,
        cwd=str(CRIBA_BLACKFORGE_DIR)
    )
    assert result.returncode == 0, f"Shadow UI import failed: {result.stderr}"


def test_criba_activate_runs_without_blackforge():
    """CRIBA activate() must run without BLACKFORGE key and return ideas."""
    code = _block_blackforge_and_run(
        "from criba.engine import activate; "
        "result = activate('test problem', mode='balanced', supporting_methods=5); "
        "assert result is not None; "
        "assert isinstance(result, dict); "
        "assert 'ideas' in result, f'Expected ideas key, got: {sorted(result.keys())}'"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True, text=True, timeout=60,
        cwd=str(CRIBA_BLACKFORGE_DIR)
    )
    assert result.returncode == 0, f"CRIBA activate failed: {result.stderr}"


def test_supra_service_starts_without_blackforge():
    """SUPRA service must start without BLACKFORGE."""
    supra_py = _supra_python()
    if not supra_py.exists():
        pytest.skip(f"SUPRA interpreter not found: {supra_py}")
    result = subprocess.run(
        [str(supra_py), "-c", "from supra_agentic.service import app; assert app is not None; assert app.title is not None"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"SUPRA service failed: {result.stderr}"


def test_shadow_window_constructs_without_blackforge():
    """ShadowWindow must construct without BLACKFORGE."""
    criba_py = _criba_python()
    if not criba_py.exists():
        pytest.skip(f"CRIBA interpreter not found: {criba_py}")
    code = _block_blackforge_and_run(
        "from shadow_window import ShadowWindow; assert ShadowWindow is not None; assert hasattr(ShadowWindow, '__init__')",
        extra_path=str(SHADOW_UI_DIR)
    )
    result = subprocess.run(
        [str(criba_py), "-c", code],
        capture_output=True, text=True, timeout=30,
        cwd=str(CRIBA_BLACKFORGE_DIR)
    )
    assert result.returncode == 0, f"ShadowWindow construct failed: {result.stderr}"


def test_no_blackforge_qprocess_in_startup():
    """No QProcess BLACKFORGE must be launched during startup (init/show)."""
    shadow_ui_path = CRIBA_BLACKFORGE_DIR / "shadow_ui"
    py_files = list(shadow_ui_path.glob("*.py"))
    assert len(py_files) > 0, f"No .py files found in {shadow_ui_path}"
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8")
        # Check that QProcess.start() is NOT called in __init__ or showEvent
        # (which run at startup). show_blackforge_page is user-triggered (click).
        lines = content.split("\n")
        in_init = False
        in_show = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("def __init__"):
                in_init = True
                in_show = False
            elif stripped.startswith("def showEvent"):
                in_show = True
                in_init = False
            elif stripped.startswith("def ") and not stripped.startswith("def __init__") and not stripped.startswith("def showEvent"):
                in_init = False
                in_show = False
            if (in_init or in_show) and "QProcess" in line and "start" in line:
                pytest.fail(f"Found QProcess.start() in startup method at {py_file.name}:{i+1}")


def test_shadow_window_independent_of_blackforge():
    """ShadowWindow must import even when BLACKFORGE modules are blocked (RED proof)."""
    criba_py = _criba_python()
    if not criba_py.exists():
        pytest.skip(f"CRIBA interpreter not found: {criba_py}")
    code = _block_blackforge_and_run(
        "from shadow_window import ShadowWindow; assert ShadowWindow is not None",
        extra_path=str(SHADOW_UI_DIR)
    )
    result = subprocess.run(
        [str(criba_py), "-c", code],
        capture_output=True, text=True, timeout=30,
        cwd=str(CRIBA_BLACKFORGE_DIR)
    )
    assert result.returncode == 0, (
        f"ShadowWindow import failed with BLACKFORGE blocked: {result.stderr}\n"
        "This proves ShadowWindow depends on BLACKFORGE — must be decoupled."
    )
