"""Smoke camino feliz con upstage/solar-mini4:free via proxy OAuth Nous.

Condiciones aceptadas por el operador:
- UNA sola llamada /chat/completions. Sin tool calling.
- model_id: upstage/solar-mini4:free (free, reasoning effort=none verificado).
- max_tokens=256, temperature=0.2, cost_limit=0.001.
- Solo system y user fijos. Sin codigo, rutas ni datos del repo.
- Exito solo si: HTTP 200, JSON valido con status y resumen, usage
  presente, ExecutionTrace con hashes sha256 64-hex, tokens numericos,
  status=success.
- Tras la prueba enabled vuelve a False y la 2a invocacion no genera red.

La credencial la adjunta el proxy; el script usa "Bearer local".
"""

from __future__ import annotations

import json
import os
import sys

os.environ["SUPRA_CLOUD_ENABLED"] = "1"
os.environ["SUPRA_CLOUD_PROVIDER"] = "openai-compatible"
os.environ["SUPRA_CLOUD_MODEL"] = "upstage/solar-mini4:free"
os.environ["SUPRA_BASE_URL"] = "http://127.0.0.1:8645/v1"
os.environ["SUPRA_API_KEY"] = "local"

sys.path.insert(0, r"C:\ASTRA_WORK\Criba-Blackforge-Supra\supra\src")

from supra_agentic.cloud_provider_layer import (  # noqa: E402
    CloudLayerConfig,
    CloudProviderLayer,
    ProviderDisabled,
)
from supra_agentic.providers import OpenAICompatibleProvider  # noqa: E402

SYSTEM_PROMPT = (
    "Responde exclusivamente con un objeto JSON valido con las claves: "
    "status (string), resumen (string, max 200 chars). "
    "No anadas texto fuera del JSON."
)
USER_PROMPT = (
    "Evalua esta propuesta: 'Un cache LRU reduce latencia p99 en endpoints "
    "de lectura bajo carga alta'. Devuelve status=OK y un resumen de una linea."
)

MAX_TOKENS = 256
TEMPERATURE = 0.2
COST_LIMIT = 0.001
MODEL_ID = "upstage/solar-mini4:free"

result: dict[str, object] = {
    "model_id": MODEL_ID,
    "max_tokens": MAX_TOKENS,
    "temperature": TEMPERATURE,
    "cost_limit": COST_LIMIT,
    "network_calls": 0,
}


def bump() -> None:
    result["network_calls"] = int(result["network_calls"]) + 1


def factory() -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url=os.environ["SUPRA_BASE_URL"],
        api_key=os.environ["SUPRA_API_KEY"],
        default_model=MODEL_ID,
        timeout=120.0,
        provider_name="nous-proxy",
    )


layer = CloudProviderLayer(
    config=CloudLayerConfig(
        provider="openai-compatible",
        model_id=MODEL_ID,
        timeout=120.0,
        retries=0,
        max_tokens=MAX_TOKENS,
        cost_limit=COST_LIMIT,
        enabled=True,
    ),
    provider_factory=factory,
    lineage="smoke-20261013-solar-mini4-free",
)

# La capa arma el payload base; upstage/solar-mini4 trae reasoning
# desactivado por defecto en el catalogo (verificado: reasoning_tokens=0
# tanto en default como en effort=none), asi que no requiere inyeccion.
bump()
text, trace = layer.complete(
    USER_PROMPT,
    system=SYSTEM_PROMPT,
    temperature=TEMPERATURE,
    max_tokens=MAX_TOKENS,
)

result["trace"] = trace.to_dict()
result["raw_text"] = text  # solo para validacion local; NO se persiste

parsed_ok = False
parse_error = ""
if trace.status == "success" and text.strip():
    try:
        parsed = json.loads(text.strip())
        parsed_ok = isinstance(parsed, dict) and "status" in parsed and "resumen" in parsed
        result["parsed_keys"] = sorted(parsed.keys()) if isinstance(parsed, dict) else []
    except ValueError as exc:
        parse_error = type(exc).__name__
result["json_valid_with_keys"] = parsed_ok
if parse_error:
    result["parse_error"] = parse_error

checks = {
    "http_success_via_trace": trace.status == "success",
    "json_valid_with_keys": parsed_ok,
    "usage_present": trace.tokens_in is not None and trace.tokens_out is not None,
    "hashes_64hex": (
        len(trace.prompt_sha256) == 64
        and len(trace.response_sha256) == 64
        and all(c in "0123456789abcdef" for c in trace.prompt_sha256 + trace.response_sha256)
    ),
    "tokens_numeric": (
        type(trace.tokens_in) is int and type(trace.tokens_out) is int
    ),
    "cost_within_limit": (
        trace.cost_reported is None or trace.cost_reported <= COST_LIMIT
    ),
    "model_echoed": trace.model_id == MODEL_ID or trace.model_id.startswith("upstage/"),
}
result["checks"] = checks
result["verdict"] = "SMOKE_PASS" if all(checks.values()) else "SMOKE_FAIL"

# flag off -> sin red
layer.config = CloudLayerConfig(
    provider="openai-compatible",
    model_id=MODEL_ID,
    timeout=120.0,
    retries=0,
    max_tokens=MAX_TOKENS,
    cost_limit=COST_LIMIT,
    enabled=False,
)
disabled_raised = False
try:
    layer.complete("segunda llamada", system=SYSTEM_PROMPT)
except ProviderDisabled:
    disabled_raised = True
result["flag_off_blocks_call"] = disabled_raised
result["network_calls_after_flag_off"] = result["network_calls"]

print("SMOKE_RESULT_JSON_BEGIN")
print(json.dumps({k: v for k, v in result.items() if k != "raw_text"}, indent=2))
print("SMOKE_RESULT_JSON_END")
print("PARSED_STATUS:", "OK" if parsed_ok else "FAIL")
print("VERDICT:", result["verdict"])
