"""Comparativa de catalogos free: ruta A (proxy OAuth Nous) vs ruta B
(OpenRouter directo con API key del entorno de Hermes).

Solo LEE catalogos (/models). No genera texto. No imprime credenciales:
la API key se pasa por variable de entorno y jamas se escribe en la salida.

Salida: por cada ruta, cuantos modelos tool-capable con contexto >= 64K y
razonamiento NO mandatorio, y los :free con esfuerzo "none" soportado.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import httpx

# Ruta A: proxy local OAuth (Hermes adjunta credencial; bearer "local").
PROXY_BASE = "http://127.0.0.1:8645/v1"

# Ruta B: OpenRouter directo. La key se lee del .env de Hermes SIN imprimirla.
ENV_FILE = Path(os.environ["HERMES_HOME"]) / ".env"
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _load_openrouter_key() -> str:
    if not ENV_FILE.exists():
        return ""
    for line in ENV_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("OPENROUTER_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def _tools_capable(m: dict) -> bool:
    sp = m.get("supported_parameters") or []
    return any("tool" in str(p).lower() for p in sp)


def _reasoning_mandatory(m: dict) -> bool:
    r = m.get("reasoning")
    return isinstance(r, dict) and r.get("mandatory") is True


def _supports_none_effort(m: dict) -> bool:
    r = m.get("reasoning")
    if not isinstance(r, dict):
        return False
    efforts = r.get("supported_efforts") or []
    return "none" in efforts


def analyze(label: str, models: list[dict]) -> None:
    print(f"=== {label} ===")
    print("total_models:", len(models))
    tc = [m for m in models if _tools_capable(m) and (m.get("context_length") or 0) >= 65536]
    print("tool_capable>=64K:", len(tc))
    no_mand = [m for m in tc if not _reasoning_mandatory(m)]
    print("sin_reasoning_mandatorio:", len(no_mand))
    free = [m for m in tc if str(m.get("id", "")).endswith(":free")]
    print("free_tool_capable:", len(free))
    free_no_mand = [m for m in free if not _reasoning_mandatory(m)]
    print("free_sin_reasoning_mandatorio:", len(free_no_mand))
    none_ok = [m for m in free_no_mand if _supports_none_effort(m)]
    print("free_con_esfuerzo_none:", len(none_ok))
    for m in free_no_mand[:15]:
        r = m.get("reasoning")
        print(
            f"  {m['id']:42s} ctx={m.get('context_length'):>8} "
            f"reasoning={r} none_effort={_supports_none_effort(m)}"
        )
    print()


def fetch_proxy() -> list[dict]:
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(f"{PROXY_BASE}/models", headers={"Authorization": "Bearer local"})
    resp.raise_for_status()
    return resp.json().get("data", [])


def fetch_openrouter() -> list[dict]:
    key = _load_openrouter_key()
    if not key:
        print("RUTA_B: OPENROUTER_API_KEY ausente en .env de Hermes")
        return []
    with httpx.Client(timeout=30.0) as client:
        resp = client.get(
            f"{OPENROUTER_BASE}/models",
            headers={"Authorization": f"Bearer {key}"},
        )
    resp.raise_for_status()
    return resp.json().get("data", [])


def main() -> None:
    # Ruta A
    try:
        proxy_models = fetch_proxy()
        analyze("RUTA_A proxy OAuth Nous (catalogo real)", proxy_models)
    except Exception as exc:  # noqa: BLE001
        print(f"RUTA_A fallo: {type(exc).__name__}")

    # Ruta B
    try:
        or_models = fetch_openrouter()
        analyze("RUTA_B OpenRouter directo (API key .env Hermes)", or_models)
    except Exception as exc:  # noqa: BLE001
        print(f"RUTA_B fallo: {type(exc).__name__}")


if __name__ == "__main__":
    main()
