"""Prueba de aceptación de json_schema en el build local de llama-server.

Comprueba anyOf, minItems, minimum, enum y const — los operadores que usa el
schema derivado del contrato real. NO cambia el banco.
"""

from __future__ import annotations

import json

import httpx

BASE = "http://127.0.0.1:8080/v1"

SCHEMA = {
    "anyOf": [
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["pertinencia", "motivo_abstencion"],
            "properties": {
                "pertinencia": {"const": "ABSTENER"},
                "motivo_abstencion": {"type": "string", "minLength": 1},
            },
        },
        {
            "type": "object",
            "additionalProperties": False,
            "required": ["pertinencia", "cadena_causal", "evidencia_citada", "estado"],
            "properties": {
                "pertinencia": {"const": "PERTINENTE"},
                "cadena_causal": {"type": "array", "items": {"type": "string"}, "minItems": 2},
                "evidencia_citada": {
                    "type": "array",
                    "maxItems": 1,
                    "items": {"type": "integer", "minimum": 1, "maximum": 1},
                },
                "estado": {"enum": ["CUMPLE", "VIOLA", "NO_VERIFICADO"]},
            },
        },
    ]
}

payload = {
    "model": "criba-local",
    "messages": [
        {"role": "system", "content": "Responde solo JSON conforme al esquema."},
        {"role": "user", "content": "Caso: reducir la cola con Poka-Yoke. Responde PERTINENTE."},
    ],
    "temperature": 0.2,
    "max_tokens": 300,
    "response_format": {
        "type": "json_schema",
        "json_schema": {"name": "propuesta", "schema": SCHEMA},
    },
}

try:
    with httpx.Client(timeout=120.0) as client:
        r = client.post(f"{BASE}/chat/completions", json=payload)
    print("HTTP", r.status_code)
    body = r.json()
    if r.status_code == 200:
        content = body["choices"][0]["message"]["content"]
        print("finish_reason:", body["choices"][0].get("finish_reason"))
        print("usage:", body.get("usage"))
        print("CONTENT:", content[:600])
        try:
            parsed = json.loads(content)
            print("PARSEA OK, keys:", list(parsed.keys()))
        except Exception as exc:
            print("NO PARSEA:", exc)
    else:
        print("ERROR BODY:", json.dumps(body, ensure_ascii=False)[:800])
except Exception as exc:
    print("EXC", type(exc).__name__, exc)
