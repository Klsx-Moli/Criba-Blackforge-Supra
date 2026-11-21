"""Canario BANCO-TRACE-04A: ¿la grammar se aplica de verdad en este llama-server?

Envía el schema REAL con un prompt irrelevante ("responde") y comprueba que la
salida contiene TODAS las claves required y finish_reason=stop. Si no, la
grammar no se aplicó (fallback silencioso) y hay que mirar el log del server.

Prueba las dos formas de response_format:
  (A) json_schema anidado  {"type":"json_schema","json_schema":{"name":...,"schema":...}}
  (B) json_object + schema suelto  {"type":"json_object","schema":...}
"""

from __future__ import annotations

import json
import sys

import httpx

BASE = "http://127.0.0.1:8080/v1"

from criba.interprete.contrato import schema_propuesta  # noqa: E402

IDEA = {"method1": "Poka-Yoke", "method2": "Retroalimentación", "title": "t"}
EVIDENCIA = [{"title": "Registro", "abstract": "30 de 100 se repiten."}]
SCHEMA = schema_propuesta(IDEA, EVIDENCIA)
REQUIRED = [
    "pertinencia",
    "hipotesis",
    "cadena_causal",
    "mecanismo",
    "aportacion_por_tecnica",
    "supuestos",
    "evidencia_citada",
    "conocimiento_previo",
    "incertidumbre",
    "novedad",
    "prueba_concreta",
    "prueba",
    "comprobacion_restricciones",
]


def _probar(nombre: str, response_format: dict) -> dict:
    payload = {
        "model": "criba-local",
        "messages": [
            {"role": "system", "content": "Responde solo JSON."},
            {"role": "user", "content": "responde"},
        ],
        "temperature": 0.2,
        "max_tokens": 2600,
        "response_format": response_format,
    }
    try:
        with httpx.Client(timeout=180.0) as client:
            r = client.post(f"{BASE}/chat/completions", json=payload)
        if r.status_code != 200:
            return {"forma": nombre, "http": r.status_code, "error": r.text[:200]}
        b = r.json()
        content = b["choices"][0]["message"]["content"]
        finish = b["choices"][0].get("finish_reason")
        try:
            parsed = json.loads(content)
        except Exception:
            parsed = None
        claves = set(parsed.keys()) if isinstance(parsed, dict) else set()
        return {
            "forma": nombre,
            "http": 200,
            "finish_reason": finish,
            "parsea": parsed is not None,
            "claves_presentes": sorted(claves),
            "required_completas": REQUIRED_SET.issubset(claves),
            "tokens": b.get("usage", {}).get("completion_tokens"),
            "raw_len": len(content),
        }
    except Exception as exc:
        return {"forma": nombre, "exc": f"{type(exc).__name__}: {exc}"}


REQUIRED_SET = set(REQUIRED)

if __name__ == "__main__":
    resultados = [
        _probar(
            "A_json_schema_anidado",
            {"type": "json_schema", "json_schema": {"name": "propuesta", "schema": SCHEMA}},
        ),
        _probar(
            "B_json_object_con_schema",
            {"type": "json_object", "schema": SCHEMA},
        ),
    ]
    print(json.dumps(resultados, ensure_ascii=False, indent=2))
    for r in resultados:
        print(f"\n{r['forma']}: finish={r.get('finish_reason')} "
              f"required_completas={r.get('required_completas')} "
              f"tokens={r.get('tokens')} parsea={r.get('parsea')}")
