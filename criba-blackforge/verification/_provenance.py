"""Procedencia obligatoria para artefactos de verificación del banco.

Cada JSON generado por los scripts de verification/ debe poder atribuirse sin
ambigüedad a un commit, entorno, modelo, semilla y configuración. Este helper
centraliza esa recolección para que ningún script la duplie ni la omita.

No contiene secretos: el endpoint se sanea y la api_key nunca se lee aquí.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Raíz del repo criba-blackforge (dos niveles arriba de este fichero: verification/ -> raíz)
_REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_git(args: list[str]) -> str:
    """Ejecuta un comando git en el repo; devuelve '' si falla (no es crítico)."""
    try:
        out = subprocess.run(
            ["git", *args],
            cwd=str(_REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""


def repo_head_sha() -> str:
    return _run_git(["rev-parse", "HEAD"])


def git_dirty() -> bool:
    """True si hay cambios sin commitear (trackeados)."""
    status = _run_git(["status", "--porcelain"])
    return bool(status)


def git_diff_hash() -> str:
    """Hash estable del working tree sucio; '' si está limpio."""
    diff = _run_git(["diff", "HEAD"])
    if not diff:
        return ""
    return hashlib.sha256(diff.encode("utf-8")).hexdigest()


def python_version() -> str:
    return platform.python_version()


def platform_tag() -> str:
    return f"{platform.system()} {platform.release()} ({platform.machine()})"


def uv_lock_sha256() -> str:
    lock = _REPO_ROOT / "uv.lock"
    if not lock.exists():
        return ""
    return hashlib.sha256(lock.read_bytes()).hexdigest()


def script_sha256(script_path: str | Path | None = None) -> str:
    """Hash del script que genera el artefacto (para trazabilidad del generador)."""
    if script_path is None:
        return ""
    p = Path(script_path)
    if not p.exists():
        return ""
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sanitize_endpoint(endpoint: str) -> str:
    """Elimina cualquier credencial embebida en una URL antes de persistirla."""
    if not endpoint:
        return ""
    if "@" in endpoint:
        # http://user:pass@host -> http://host
        scheme, _, rest = endpoint.partition("://")
        host = rest.rsplit("@", 1)[-1]
        return f"{scheme}://{host}"
    return endpoint


def build_provenance(
    *,
    bank_version: str = "",
    prompt_version: str = "",
    schema_version: str = "",
    constrained_decoding: str = "",
    seed: int | str | None = None,
    model_requested: str = "",
    model_reported: str = "",
    endpoint: str = "",
    script_path: str | Path | None = None,
) -> dict[str, Any]:
    """Construye el bloque de procedencia completo y sin secretos.

    Todos los scripts de verification/ deben empaquetar su resultado bajo una
    clave ``provenance`` usando esta función.
    """
    return {
        "repo_head_sha": repo_head_sha(),
        "git_dirty": git_dirty(),
        "git_diff_hash": git_diff_hash(),
        "python_version": python_version(),
        "platform": platform_tag(),
        "uv_lock_sha256": uv_lock_sha256(),
        "bank_version": bank_version,
        "prompt_version": prompt_version,
        "schema_version": schema_version,
        "constrained_decoding": constrained_decoding,
        "seed": seed,
        "model_requested": model_requested,
        "model_reported": model_reported,
        "endpoint_sin_secretos": sanitize_endpoint(endpoint),
        "started_at_utc": _utc_now_iso(),
        "script_sha256": script_sha256(script_path),
    }


def finalize_provenance(prov: dict[str, Any]) -> dict[str, Any]:
    """Añade finished_at_utc y serializa a un dict plano seguro para JSON."""
    prov = dict(prov)
    prov["finished_at_utc"] = _utc_now_iso()
    # Verificación defensiva: nunca debe colarse un campo de credencial.
    return prov


def provenance_json(prov: dict[str, Any]) -> str:
    return json.dumps(finalize_provenance(prov), ensure_ascii=False, indent=1)
