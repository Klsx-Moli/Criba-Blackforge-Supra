"""PASO 5: 5 seeds distintas por modo (a sin grammar / b con grammar).

Compara raw_output_sha256 entre modos por intento (mismo seed) para confirmar
que constrained_decoding cambia la salida, y confirma constrained_decoding por
intento en provenance.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path

os.environ.setdefault("CRIBA_LOCAL_BASE", "http://127.0.0.1:8080/v1")
os.environ.setdefault("CRIBA_LOCAL_MODEL", "criba-local")

from criba.interprete.banco import CASOS, evaluar_banco
from criba.interprete.openai_compatible import LocalLlamaInterpreter, OpenAICompatibleInterpreter

SEEDS = [20261011, 20261012, 20261013, 20261014, 20261015]


def una(restringido: bool, seed: int) -> dict:
    local = LocalLlamaInterpreter()
    local.max_tokens = 2600
    local.seed = seed
    t0 = time.monotonic()
    report = evaluar_banco(
        lambda q, i, d, e: OpenAICompatibleInterpreter.proponer(local, q, i, d, e),
        repeticiones=2,
        constrained_decoding="json_schema" if restringido else "",
    )
    elapsed = time.monotonic() - t0
    por_intento = []
    for caso in report["cases"]:
        for n, att in enumerate(caso["attempts"], 1):
            raw = att.get("raw_output") or ""
            prov = att.get("provenance", {})
            por_intento.append({
                "case_id": caso["id"], "attempt": n,
                "raw_sha256": hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16],
                "constrained_decoding": prov.get("generation_parameters", {}).get("constrained_decoding", ""),
                "seed": prov.get("generation_parameters", {}).get("seed"),
                "finish_reason": att.get("finish_reason"),
                "estado": caso["estados"][n-1],
                "campo_truncado": att.get("campo_truncado_por_grammar", []),
            })
    return {
        "constrained": "json_schema" if restringido else "",
        "seed": seed,
        "elapsed_s": round(elapsed, 1),
        "summary": {
            "passed": report["passed"],
            "schema_response_rate": report["schema_response_rate"],
            "correct_abstention_rate": report["correct_abstention_rate"],
        },
        "intentos": por_intento,
    }


def main() -> None:
    resultados = {"a_nogrammar": [], "b_grammar": []}
    for seed in SEEDS:
        print(f"=== seed {seed} ===", flush=True)
        for modo, restr in [("a_nogrammar", False), ("b_grammar", True)]:
            r = una(restr, seed)
            resultados[modo].append(r)
            print(f"  {modo}: passed={r['summary']['passed']} "
                  f"absten={r['summary']['correct_abstention_rate']:.3f} t={r['elapsed_s']}s", flush=True)
    out = Path("verification/banco_05_seeds.json")
    out.write_text(json.dumps(resultados, ensure_ascii=False, indent=1), encoding="utf-8")
    # Comparacion raw_sha256 entre modos por (seed, caso, intento)
    print("\n=== raw_output_sha256 a vs b por intento (seed 20261011) ===")
    a = resultados["a_nogrammar"][0]["intentos"]
    b = resultados["b_grammar"][0]["intentos"]
    difieren = 0
    for xa, xb in zip(a, b):
        misma = xa["raw_sha256"] == xb["raw_sha256"]
        if not misma:
            difieren += 1
        print(f"  {xa['case_id']:13s} i{xa['attempt']} a={xa['raw_sha256']} b={xb['raw_sha256']} {'=' if misma else 'DIFIERE'}")
    print(f"\nintentos que difieren entre modos: {difieren}/{len(a)}")
    # confirmar constrained_decoding por intento
    cdb = set(i["constrained_decoding"] for i in b)
    cda = set(i["constrained_decoding"] for i in a)
    print(f"constrained_decoding en a): {cda} | en b): {cdb}")
    print(f"Saved {out}")


if __name__ == "__main__":
    main()
