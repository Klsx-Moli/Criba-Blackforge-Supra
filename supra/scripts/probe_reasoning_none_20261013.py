"""Prueba de esfuerzo de razonamiento con upstage/solar-mini4:free.

El catalogo declara supported_efforts=[..., 'none']. Verificamos con una
inferencia REAL (2 llamadas cortas: una con reasoning.effort=none y otra
con default) si el proveedor honra el esfuerzo 'none'. Esto importa para el
banco CRIBA: el barrido del 2026-10-13 demostro que las plantillas fuerzan
thinking -> timeout; necesitamos esfuerzo real 'none'.

NO imprime credenciales: ruta A usa el proxy OAuth (bearer "local").
"""

from __future__ import annotations

import json
import time

import httpx

PROXY_BASE = "http://127.0.0.1:8645/v1"
MODEL = "upstage/solar-mini4:free"

MESSAGES = [
    {"role": "system", "content": "Responde solo JSON: {status, resumen}."},
    {"role": "user", "content": "Di OK en una linea."},
]


def call(label: str, payload: dict) -> dict:
    inicio = time.monotonic()
    with httpx.Client(timeout=90.0) as client:
        resp = client.post(
            f"{PROXY_BASE}/chat/completions",
            json={"model": MODEL, "messages": MESSAGES, "max_tokens": 128, **payload},
            headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
        )
    latency = int((time.monotonic() - inicio) * 1000)
    body = resp.text
    result = {
        "label": label,
        "http": resp.status_code,
        "latency_ms": latency,
    }
    if resp.status_code == 200:
        data = resp.json()
        msg = (data.get("choices") or [{}])[0].get("message") or {}
        result["content_head"] = (msg.get("content") or "")[:120]
        result["reasoning_head"] = (msg.get("reasoning") or "")[:120]
        result["finish_reason"] = (data.get("choices") or [{}])[0].get("finish_reason")
        usage = data.get("usage") or {}
        result["completion_tokens"] = usage.get("completion_tokens")
        result["reasoning_tokens"] = (
            (usage.get("completion_tokens_details") or {}).get("reasoning_tokens")
        )
    else:
        result["error_head"] = body[:200]
    return result


def main() -> None:
    print("MODEL:", MODEL)
    # 1) esfuerzo none explicito
    r1 = call("effort_none", {"reasoning": {"effort": "none"}})
    print(json.dumps(r1, indent=1))
    # 2) sin esfuerzo (default del catalogo es 'medium')
    r2 = call("default", {})
    print(json.dumps(r2, indent=1))

    # conclusion
    none_ok = r1.get("http") == 200 and (r1.get("reasoning_tokens") or 0) == 0
    print("CONCLUSION_none_effort_honored:", none_ok)


if __name__ == "__main__":
    main()
