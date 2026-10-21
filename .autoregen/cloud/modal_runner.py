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

import json
import os
import subprocess
import xml.etree.ElementTree as ET
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
    .apt_install(
        "libgl1",
        "libegl1",
        "libxkbcommon0",
        "libdbus-1-3",
        "libglib2.0-0",
        "libfontconfig1",
        "mesa-vulkan-drivers",
        "git",
    )
    .uv_pip_install(
        "pytest>=9",
        "pytest-xdist",
        "pytest-randomly",
        "pytest-qt",
        "pytest-timeout>=2.4",
        "pytest-cov>=7.0",
        "mypy",
        "types-PyYAML",
        "PySide6",
        "httpx",
        "pydantic",
        "fastapi",
        "uvicorn>=0.30",
        "PyYAML>=6.0",
        "hypothesis>=6.0",
        "mutmut>=3.6",
        "jsonschema",
    )
    # El paquete debe estar INSTALADO: los tests lanzan subprocesos con
    # sys.executable que no heredan el pythonpath de pytest, y sin install
    # fallan con ModuleNotFoundError: criba.
    # OJO: add_local_dir es la ÚLTIMA operación de la imagen, así que el install
    # editable se hace EN RUNTIME (pytest_file gate lo hace antes de correr),
    # no en la imagen: en build-time /workspace aún no existe.
    .env({"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"})
    .workdir(REMOTE_ROOT)
    .add_local_dir(HOST_ROOT, REMOTE_ROOT)
)


def _ensure_installed(env: dict[str, str]) -> dict:
    """pip install -e en runtime (no en build: el mount aún no existe)."""
    return _run(
        [
            "python", "-m", "pip", "install", "--quiet",
            "-e", "/workspace/criba-blackforge",
        ],
        REMOTE_ROOT,
        env=env,
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


def _run(cmd: list[str], cwd: str, env: dict[str, str] | None = None) -> dict:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)
    return {
        "cmd": " ".join(cmd),
        "rc": proc.returncode,
        "stdout_tail": proc.stdout[-6000:],
        "stderr_tail": proc.stderr[-3000:],
    }


@app.function(image=image, timeout=2400)
def pytest_full(seed: int | None = None) -> dict:
    """Suite CRIBA completa (-q, sin cacheprovider). Seed fija = determinismo."""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    install = _ensure_installed(env)
    if install.get("rc") != 0:
        return {
            "summary": {"rc": install["rc"], "cmd": install["cmd"],
                        "stderr_tail": install["stderr_tail"]},
            "failures": [],
        }
    args = [
        "python", "-m", "pytest", "tests/", "-q", "-p", "no:cacheprovider",
        "--tb=line", "-rf", "--color=no",
        "--junitxml=/tmp/report.xml",
    ]
    if seed is not None:
        args.append(f"--randomly-seed={seed}")
    result = _run(args, f"{REMOTE_ROOT}/criba-blackforge", env=env)
    # Fallos reales por test, parseados del JUnit XML: evidencia para el informe
    # de 4b (test_id + mensaje observado), no hipótesis.
    failures: list[dict] = []
    try:
        for case in ET.parse("/tmp/report.xml").getroot().iter("testcase"):
            for kind in ("failure", "error"):
                node = case.find(kind)
                if node is not None:
                    failures.append({
                        "test_id": f'{case.get("classname")}::{case.get("name")}',
                        "kind": kind,
                        "message": (node.get("message") or "")[:300],
                    })
    except Exception as exc:  # noqa: BLE001 - el runner no debe morir por el parseo
        result["junit_parse_error"] = str(exc)
    return {"summary": _summary(result), "failures": failures}


def _summary(result: dict) -> dict:
    """Solo cabeceras + últimas líneas: el stdout de pytest con fallos no cabe
    en stdout_tail=[-6000:] y su cola aplasta el resumen."""
    stdout = result.get("stdout_tail", "")
    header = stdout[:400]
    tail_lines = [l for l in stdout.splitlines() if l.strip()][-40:]
    return {
        "cmd": result["cmd"],
        "rc": result["rc"],
        "stdout_head": header,
        "stdout_tail40": tail_lines,
        "stderr_tail": result.get("stderr_tail", ""),
        "junit_parse_error": result.get("junit_parse_error"),
    }


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
    seed: int | None = None,
) -> None:
    if gate == "probe_paths":
        print(probe_paths.remote())
    elif gate == "pytest_full":
        out = pytest_full.remote(seed)
        print(json.dumps({
            "rc": out["summary"]["rc"],
            "cmd": out["summary"]["cmd"],
            "failures": out["failures"],
        }, ensure_ascii=False, indent=2))
    elif gate == "mypy_scoped":
        print(mypy_scoped.remote())
    elif gate == "pytest_file":
        print(pytest_file.remote(path))
    else:
        raise SystemExit(f"gate desconocido: {gate}")
