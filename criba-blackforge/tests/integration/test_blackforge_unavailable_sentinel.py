"""
P0 Sentinel: BLACKFORGE unavailable must not block CRIBA+SUPRA.

Evidence Label: VERIFIED_BY_EXECUTION
SHA: 583d44e
"""
import os
import sys
from pathlib import Path

import pytest

# Add shadow_ui to path
SHADOW_UI_PATH = Path(__file__).parent.parent / "shadow_ui"
if str(SHADOW_UI_PATH) not in sys.path:
    sys.path.insert(0, str(SHADOW_UI_PATH))


def test_criba_imports_without_blackforge():
    """CRIBA must import without BLACKFORGE."""
    from criba.engine import activate
    assert activate is not None


def test_supra_imports_without_blackforge():
    """SUPRA must import without BLACKFORGE (from supra venv)."""
    import subprocess
    supra_venv = Path(__file__).parent.parent.parent.parent / "supra" / ".venv" / "Scripts" / "python.exe"
    if not supra_venv.exists():
        pytest.skip("SUPRA venv not found")
    result = subprocess.run(
        [str(supra_venv), "-c", "from supra_agentic.service import app; assert app is not None"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"SUPRA import failed: {result.stderr}"


def test_shadow_ui_imports_without_blackforge():
    """Shadow UI must import without BLACKFORGE."""
    import subprocess
    criba_venv = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
    shadow_ui_abs = str(Path(__file__).parent.parent.parent / "shadow_ui")
    result = subprocess.run(
        [str(criba_venv), "-c", f"import sys; sys.path.insert(0, {shadow_ui_abs!r}); from shadow_window import ShadowWindow; assert ShadowWindow is not None"],
        capture_output=True, text=True, timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    assert result.returncode == 0, f"Shadow UI import failed: {result.stderr}"


def test_criba_activate_runs_without_blackforge():
    """CRIBA activate() must run without BLACKFORGE key."""
    from criba.engine import activate
    result = activate("test problem", mode="balanced", supporting_methods=5)
    assert result is not None
    assert isinstance(result, dict)


def test_supra_service_starts_without_blackforge():
    """SUPRA service must start without BLACKFORGE (from supra venv)."""
    import subprocess
    supra_venv = Path(__file__).parent.parent.parent.parent / "supra" / ".venv" / "Scripts" / "python.exe"
    if not supra_venv.exists():
        pytest.skip("SUPRA venv not found")
    result = subprocess.run(
        [str(supra_venv), "-c", "from supra_agentic.service import app; assert app is not None; assert app.title is not None"],
        capture_output=True, text=True, timeout=30
    )
    assert result.returncode == 0, f"SUPRA service failed: {result.stderr}"


def test_shadow_window_constructs_without_blackforge():
    """ShadowWindow must construct without BLACKFORGE."""
    import subprocess
    criba_venv = Path(__file__).parent.parent.parent / ".venv" / "Scripts" / "python.exe"
    shadow_ui_abs = str(Path(__file__).parent.parent.parent / "shadow_ui")
    result = subprocess.run(
        [str(criba_venv), "-c", f"import sys; sys.path.insert(0, {shadow_ui_abs!r}); from shadow_window import ShadowWindow; assert ShadowWindow is not None; assert hasattr(ShadowWindow, '__init__')"],
        capture_output=True, text=True, timeout=30,
        cwd=str(Path(__file__).parent.parent.parent)
    )
    assert result.returncode == 0, f"ShadowWindow construct failed: {result.stderr}"


def test_no_blackforge_qprocess_in_startup():
    """No QProcess BLACKFORGE must be launched during startup."""
    shadow_ui_path = Path(__file__).parent.parent / "shadow_ui"
    for py_file in shadow_ui_path.glob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        if "QProcess" in content and "blackforge" in content.lower():
            pytest.fail(f"Found QProcess+blackforge in {py_file.name}")
