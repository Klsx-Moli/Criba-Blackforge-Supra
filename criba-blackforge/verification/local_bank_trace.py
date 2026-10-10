"""PASO 3 BANCO-TRACE-01 — Diagnóstico discriminatorio del banco real
contra llama-server (127.0.0.1:8080, Llama 3.1 8B Q4_K_M).

NO cambia el modelo. NO baja umbrales. NO relaja schema.
Guarda por intento: case_id, prompt, raw_output, finish_reason, tokens,
technical_error, derived_error, latencia.
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
    t0 = time.monotonic()
    report = evaluar_banco(
        lambda q, i, d, e: OpenAICompatibleInterpreter.proponer(local, q, i, d, e),
        repeticiones=2,
    )
    elapsed = time.monotonic() - t0

    diagnostic: dict = {
        "model": local.model,
        "endpoint": local.base,
        "elapsed_s": round(elapsed, 2),
        "report_summary": {
            "passed": report["passed"],
            "completed_attempts": report["completed_attempts"],
            "total_attempts": report["total_attempts"],
            "schema_response_rate": report["schema_response_rate"],
        },
        "attempts": [],
    }

    casos_por_id = {c["id"]: c for c in CASOS}
    for caso in report["cases"]:
        fuente = casos_por_id[caso["id"]]
        for intento, attempt in enumerate(caso["attempts"]):
            diagnostic["attempts"].append(
                {
                    "case_id": attempt.get("case_id", caso["id"]),
                    "attempt": intento + 1,
                    "expected": caso["expected"],
                    "estado": caso["estados"][intento],
                    "result": attempt.get("result"),
                    "technical_error": attempt.get("technical_error"),
                    "derived_error": attempt.get("derived_error"),
                    "raw_output": (attempt.get("raw_output") or "")[:2000],
                    "finish_reason": attempt.get("finish_reason"),
                    "completion_tokens": attempt.get("completion_tokens"),
                    "reasoning_tokens": attempt.get("reasoning_tokens"),
                    "latency_s": attempt.get("latency_s"),
                    "model_requests": attempt.get("model_requests"),
                    "error": attempt.get("resultado", {}).get("error"),
                    "prompt": f"{fuente['query'][:100]} | idea: {fuente['idea'].get('method1', '')}",
                }
            )

    out = Path("verification/local_bank_diagnostic.json")
    out.write_text(json.dumps(diagnostic, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(diagnostic["report_summary"], ensure_ascii=False, indent=2))
    for a in diagnostic["attempts"]:
        print(
            f"{a['case_id']:14s} i{a['attempt']} "
            f"tech={a['technical_error']} "
            f"derived={a['derived_error']} "
            f"err={(a['error'] or '')[:60]}"
        )
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
