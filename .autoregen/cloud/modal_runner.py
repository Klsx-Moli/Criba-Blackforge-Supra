"""Runner Modal mínimo para CRIBA/BLACKFORGE/SUPRA.

Offload de verificación pesada (pytest/mypy) a la nube para no cargar la
máquina local. Escrito para Windows (host) + Linux (container).

Reglas que este runner respeta (lecciones del host Windows):
- Rutas literales "/workspace" y "/artifacts" en toda llamada Modal
  (str(Path("/workspace")) normaliza a \\workspace en Windows y Modal lo rechaza).
- add_local_dir es la ÚLTIMA operación de la imagen.
- Split HOST_ROOT / REMOTE_ROOT por modal.is_local(); nunca parents[N] en worker.
- Un @app.function por gate; lanzar UN gate a la vez.

Entrypoints:
  probe_paths        — solo rutas, sin tests (primer lanzamiento autorizado).
  pytest_full        — suite completa -q.
  mypy_scoped        — mypy con la config del proyecto (pyproject).
  pytest_file        — un archivo de test (--path, repetible).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import modal

app = modal.App("criba-verify")

# Rutas literales: NO usar str(Path("/workspace")) (rompe en Windows).
REMOTE_ROOT = "/workspace"
ARTIFACT_ROOT = "/artifacts"

if modal.is_local():
    HOST_ROOT = str(Path(__file__).resolve().parents[2])  # raíz del repo (runner en .autoregen/cloud/)
else:
    HOST_ROOT = REMOTE_ROOT  # en worker, nunca parents[2]

image = (
    modal.Image.debian_slim(python_version="3.11")
    .uv_pip_install(
        "pytest>=9",
        "pytest-xdist",
        "pytest-randomly",
        "mypy",
        "types-PyYAML",
        "PySide6",
        "httpx",
        "pydantic",
        "fastapi",
    )
    .env({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    .workdir(REMOTE_ROOT)
    .add_local_dir(HOST_ROOT, REMOTE_ROOT)
)


@app.function(image=image, timeout=1800)
def probe_paths() -> dict:
    """Sondeo de rutas: confirma que la imagen monta el repo donde debe.
    Primer lanzamiento autorizado. No ejecuta tests."""
    from pathlib import Path

    ws = Path(REMOTE_ROOT)
    return {
        "modal_is_local": modal.is_local(),
        "cwd_is_workspace": str(Path.cwd()) == REMOTE_ROOT,
        "workspace_exists": ws.is_dir(),
        "criba_src_exists": (ws / "criba-blackforge" / "src" / "criba").is_dir(),
        "supra_src_exists": (ws / "supra" / "src" / "supra_agentic").is_dir(),
        "pyproject_criba_exists": (ws / "criba-blackforge" / "pyproject.toml").is_file(),
    }


def _run(cmd: list[str], cwd: str) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-3000:],
    }


@app.function(image=image, timeout=2400)
def pytest_full() -> dict:
    """Suite CRIBA completa (-q, sin cacheprovider)."""
    return _run(
        ["python", "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider"],
        f"{REMOTE_ROOT}/criba-blackforge",
    )


@app.function(image=image, timeout=1200)
def mypy_scoped() -> dict:
    """mypy con la config del proyecto (descubre pyproject [tool.mypy])."""
    return _run(["python", "-m", "mypy", "src/"], f"{REMOTE_ROOT}/criba-blackforge")


@app.function(image=image, timeout=1800)
def pytest_file(path: str) -> dict:
    """Un archivo de test específico."""
    return _run(
        ["python", "-m", "pytest", path, "-q", "-p", "no:cacheprovider"],
        f"{REMOTE_ROOT}/criba-blackforge",
    )


@app.local_entrypoint()
def main(
    gate: str = "probe_paths",
    path: str = "tests/unit/test_cli.py",
) -> None:
    if gate == "probe_paths":
        print(probe_paths.remote())
    elif gate == "pytest_full":
        print(pytest_full.remote())
    elif gate == "mypy_scoped":
        print(mypy_scoped.remote())
    elif gate == "pytest_file":
        print(pytest_file.remote(path))
    else:
        raise SystemExit(f"gate desconocido: {gate}")
