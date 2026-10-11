"""PASO 4: capturar la CRITICA completa del caso pertinente (modelo fuerte).

El modelo fuerte devolvió validacion:critica.restricciones_respetadas=False y
critica.objeciones no vacias. Guarda la critica completa para diagnosticar.
max_tokens suficiente para no truncar.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from criba.interprete.banco import CASOS
from criba.interprete.openai_compatible import OpenAICompatibleInterpreter

PROXY = "http://127.0.0.1:8645/v1"
MODELO = os.getenv("CRIBA_CONTROL_MODEL", "stepfun/step-5-preview:free")
SEED = 20261011

caso = next(c for c in CASOS if c["id"] == "pertinente")

i = OpenAICompatibleInterpreter(base_url=PROXY, model=MODELO, api_key="proxy", seed=SEED)
i.max_tokens = 8000  # suficiente para propuesta + critica sin truncar
r = i.proponer(caso["query"], caso["idea"], None, caso["evidence"])

critica = r.critica or {}
salida = {
    "model": MODELO,
    "seed": SEED,
    "estado": r.estado,
    "es_propuesta": r.es_propuesta,
    "error": r.error,
    "pertinencia": r.pertinencia,
    "evaluation_status": critica.get("evaluation_status"),
    "same_model": critica.get("same_model"),
    "finish_reason_propuesta": r.finish_reason,
    "completion_tokens_propuesta": r.completion_tokens,
    "critica_finish_reason": critica.get("finish_reason"),
    "critica_completion_tokens": critica.get("completion_tokens"),
    "critica_respuesta": critica.get("respuesta"),
    "restricciones_obligatorias_del_caso": (
        caso["idea"].get("bloqueo", {}).get("restricciones_obligatorias", [])
        if isinstance(caso["idea"].get("bloqueo"), dict) else []
    ),
}
Path("verification/critica_control_pertinente.json").write_text(
    json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8"
)
print(json.dumps({k: salida[k] for k in [
    "estado", "es_propuesta", "error", "evaluation_status",
    "critica_finish_reason", "critica_completion_tokens",
    "restricciones_obligatorias_del_caso",
]}, ensure_ascii=False, indent=2))
print("--- critica.respuesta ---")
print(json.dumps(critica.get("respuesta"), ensure_ascii=False, indent=2)[:3000])
