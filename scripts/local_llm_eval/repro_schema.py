"""Reproducir el fallo de json_schema FUERA del banco, con el schema real de CRIBA.

No toca CRIBA. Solo: (1) construye schema_propuesta real, (2) lo manda al
llama-server con response_format json_schema, (3) imprime status + cuerpo.
Registra el payload exacto para el informe.
"""
from __future__ import annotations

import json
import sys

import httpx

sys.path.insert(0, "src")
from criba.interprete.contrato import schema_propuesta  # noqa: E402
from criba.interprete.banco import CASOS  # noqa: E402

caso = CASOS[0]
schema = schema_propuesta(caso["idea"], caso["evidence"])
print("=== caso del banco:", caso["id"], "expected:", caso["expected"])
print("=== schema_propuesta REAL (tamano chars):", len(json.dumps(schema)))

payload = {
    "model": "qwen3",
    "messages": [
        {"role": "system", "content": "Eres un extractor. Solo JSON."},
        {"role": "user", "content": "Genera una propuesta."},
    ],
    "temperature": 0.25,
    "max_tokens": 200,
    "response_format": {"type": "json_schema", "json_schema": {"name": "propuesta", "schema": schema}},
}
print("=== payload response_format.type:", payload["response_format"]["type"])
try:
    r = httpx.post("http://127.0.0.1:8080/v1/chat/completions", json=payload, timeout=60)
    print("HTTP", r.status_code)
    print(r.text[:500])
except Exception as exc:  # noqa: BLE001
    print("EXCEPCION:", type(exc).__name__, exc)
