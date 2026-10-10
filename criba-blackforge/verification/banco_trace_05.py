"""BANCO-TRACE-05 paso 2: repetir a) sin grammar y b) con grammar 3 veces.

Seed fija (parámetro de generación registrado en generation_parameters).
Guarda desglose por intento con raw_output, finish_reason, tokens,
error técnico, error derivado, latencia y cap_hit.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

os.environ.setdefault("CRIBA_LOCAL_BASE", "http://127.0.0.1:8080/v1")
os.environ.setdefault("CRIBA_LOCAL_MODEL", "criba-local")

from criba.interprete.banco import CASOS, evaluar_banco
from criba.interprete.openai_compatible import LocalLlamaInterpreter, OpenAICompatibleInterpreter

SEED = 20261011


def una_corrida(restringido: bool) -> dict:
    local = LocalLlamaInterpreter()
    local.max_tokens = 2600
    local.seed = SEED
    t0 = time.monotonic()
    report = evaluar_banco(
        lambda q, i, d, e: OpenAICompatibleInterpreter.proponer(local, q, i, d, e),
        repeticiones=2,
        constrained_decoding="json_schema" if restringido else "",
    )
    elapsed = time.monotonic() - t0
    casos_por_id = {c["id"]: c for c in CASOS}
    attempts = []
    for caso in report["cases"]:
        fuente = casos_por_id[caso["id"]]
        for intento, att in enumerate(caso["attempts"]):
            attempts.append({
                "case_id": caso["id"],
                "attempt": intento + 1,
                "expected": caso["expected"],
                "estado": caso["estados"][intento],
                "result": att.get("result"),
                "technical_error": att.get("technical_error"),
                "derived_error": att.get("derived_error"),
                "raw_output": att.get("raw_output") or "",
                "finish_reason": att.get("finish_reason"),
                "completion_tokens": att.get("completion_tokens"),
                "latency_s": att.get("latency_s"),
                "cap_hit": att.get("cap_hit"),
                "prompt": f"{fuente['query'][:80]} | {fuente['idea'].get('method1','')}",
            })
    return {
        "constrained": "json_schema" if restringido else "",
        "seed": SEED,
        "elapsed_s": round(elapsed, 2),
        "summary": {
            "passed": report["passed"],
            "schema_response_rate": report["schema_response_rate"],
            "correct_abstention_rate": report["correct_abstention_rate"],
            "consistency_rate": report["consistency_rate"],
        },
        "attempts": attempts,
    }


def main() -> None:
    resultados = {"a_nogrammar": [], "b_grammar": []}
    for modo, restringido in [("a_nogrammar", False), ("b_grammar", True)]:
        for n in range(1, 4):
            print(f"=== {modo} corrida {n}/3 ===", flush=True)
            r = una_corrida(restringido)
            resultados[modo].append(r)
            print(f"  passed={r['summary']['passed']} "
                  f"srate={r['summary']['schema_response_rate']:.3f} "
                  f"absten={r['summary']['correct_abstention_rate']:.3f} "
                  f"t={r['elapsed_s']}s", flush=True)
    out = Path("verification/banco_trace_05_n3.json")
    out.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
