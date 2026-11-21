"""Prueba discriminante BANCO-TRACE-01 PASO 5: banco real CON grammar.

Compara el banco contra el mismo llama-server con y sin decodificación
restringida. NO cambia modelo ni umbrales. Guarda diagnóstico por intento.
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


def main() -> None:
    local = LocalLlamaInterpreter()
    local.max_tokens = 2600
    t0 = time.monotonic()
    report = evaluar_banco(
        lambda q, i, d, e: OpenAICompatibleInterpreter.proponer(local, q, i, d, e),
        repeticiones=2,
    )
    elapsed = time.monotonic() - t0

    diagnostic = {
        "model": local.model,
        "endpoint": local.base,
        "constrained_decoding": os.getenv("CRIBA_CONSTRAINED_DECODING", ""),
        "elapsed_s": round(elapsed, 2),
        "report_summary": {
            "passed": report["passed"],
            "completed_attempts": report["completed_attempts"],
            "total_attempts": report["total_attempts"],
            "schema_response_rate": report["schema_response_rate"],
            "correct_abstention_rate": report["correct_abstention_rate"],
        },
        "attempts": [],
    }
    casos_por_id = {c["id"]: c for c in CASOS}
    for caso in report["cases"]:
        fuente = casos_por_id[caso["id"]]
        for intento, attempt in enumerate(caso["attempts"]):
            diagnostic["attempts"].append(
                {
                    "case_id": caso["id"],
                    "attempt": intento + 1,
                    "expected": caso["expected"],
                    "estado": caso["estados"][intento],
                    "result": attempt.get("result"),
                    "technical_error": attempt.get("technical_error"),
                    "derived_error": attempt.get("derived_error"),
                    "raw_output": (attempt.get("raw_output") or "")[:2000],
                    "finish_reason": attempt.get("finish_reason"),
                    "completion_tokens": attempt.get("completion_tokens"),
                    "latency_s": attempt.get("latency_s"),
                    "prompt": f"{fuente['query'][:80]} | {fuente['idea'].get('method1','')}",
                }
            )
    suffix = "grammar" if os.getenv("CRIBA_CONSTRAINED_DECODING") else "nogrammar"
    out = Path(f"verification/local_bank_{suffix}.json")
    out.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(diagnostic["report_summary"], ensure_ascii=False, indent=2))
    for a in diagnostic["attempts"]:
        print(
            f"{a['case_id']:14s} i{a['attempt']} {a['estado']:9s} {str(a.get('result')):8s} "
            f"tok={a.get('completion_tokens')} fin={a.get('finish_reason')} "
            f"te={str(a.get('technical_error'))[:45]}"
        )
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
