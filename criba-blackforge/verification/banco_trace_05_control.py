"""BANCO-TRACE-05 paso 4: CONTROL (c) con modelo fuerte vía proxy local de Hermes.

Apunta OpenAICompatibleInterpreter al proxy local (http://127.0.0.1:8645/v1),
SIN copiar claves (el proxy local acepta cualquier bearer). Registra modelo,
si acepta json_schema, y los mismos indicadores del banco.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from criba.interprete.banco import CASOS, evaluar_banco
from criba.interprete.openai_compatible import OpenAICompatibleInterpreter

PROXY = "http://127.0.0.1:8645/v1"
MODELO = os.getenv("CRIBA_CONTROL_MODEL", "openai/gpt-6.1-sol")
SEED = 20261011


def sondeo_modelo() -> dict:
    """¿El proxy expone el modelo y acepta json_schema?"""
    i = OpenAICompatibleInterpreter(base_url=PROXY, model=MODELO, api_key="proxy", seed=SEED)
    listo, motivo = i.operativo()
    return {"model": MODELO, "operativo": listo, "motivo": motivo}


def una_corrida(restringido: bool) -> dict:
    i = OpenAICompatibleInterpreter(base_url=PROXY, model=MODELO, api_key="proxy", seed=SEED)
    t0 = time.monotonic()
    report = evaluar_banco(
        lambda q, idea, d, e: i.proponer(q, idea, d, e),
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
                "raw_output": (att.get("raw_output") or "")[:1500],
                "finish_reason": att.get("finish_reason"),
                "completion_tokens": att.get("completion_tokens"),
                "latency_s": att.get("latency_s"),
                "cap_hit": att.get("cap_hit"),
                "prompt": f"{fuente['query'][:80]} | {fuente['idea'].get('method1','')}",
            })
    return {
        "constrained": "json_schema" if restringido else "",
        "seed": SEED,
        "model": MODELO,
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
    print("=== sondeo del proxy ===", flush=True)
    s = sondeo_modelo()
    print(json.dumps(s, ensure_ascii=False), flush=True)
    if not s["operativo"]:
        print("PROXY NO OPERATIVO — abortando control (c)", flush=True)
        Path("verification/banco_trace_05_control.json").write_text(
            json.dumps({"sondeo": s, "error": "proxy no operativo"}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return
    r = una_corrida(restringido=True)
    print(f"control passed={r['summary']['passed']} "
          f"srate={r['summary']['schema_response_rate']:.3f} "
          f"absten={r['summary']['correct_abstention_rate']:.3f} "
          f"t={r['elapsed_s']}s", flush=True)
    out = Path("verification/banco_trace_05_control.json")
    out.write_text(json.dumps({"sondeo": s, "corrida": r}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
