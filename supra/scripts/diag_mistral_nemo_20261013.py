"""Diagnóstico: por qué mistral-nemo devolvió model_unavailable.

Misma petición mínima, pero capturando el código HTTP y el cuerpo del
proveedor para clasificar la causa real (404 vs 429 vs otro). No es parte
del smoke aprobado: es una llamada de diagnóstico con el mismo modelo.
"""

from __future__ import annotations

import json
import os

os.environ["SUPRA_BASE_URL"] = "http://127.0.0.1:8645/v1"
os.environ["SUPRA_API_KEY"] = "local"

import httpx

MODEL_ID = "mistralai/mistral-nemo"
payload = {
    "model": MODEL_ID,
    "messages": [
        {"role": "system", "content": "Responde solo JSON con claves status y resumen."},
        {"role": "user", "content": "Di OK."},
    ],
    "temperature": 0.2,
    "max_tokens": 64,
}

with httpx.Client(timeout=120.0) as client:
    resp = client.post(
        f"{os.environ['SUPRA_BASE_URL']}/chat/completions",
        json=payload,
        headers={"Authorization": "Bearer local", "Content-Type": "application/json"},
    )

print("HTTP_STATUS:", resp.status_code)
body = resp.text
print("BODY_LEN:", len(body))
print("BODY_HEAD:", body[:600])
