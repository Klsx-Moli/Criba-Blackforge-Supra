"""Capa B (v2): banco de admision real de LocalLlamaInterpreter contra Qwen3.

El gate vive dentro de operativo(): corre evaluar_banco una vez y cachea
gate_report. Instanciamos LIMPIO (sin llamar operativo antes) y dejamos que el
propio operativo() ejecute el banco contra el modelo ya corregido. Reporta
passed + tasas. NO toca umbrales.
"""
from __future__ import annotations

import json
import os
import sys

os.environ["CRIBA_CONSTRAINED_DECODING"] = "json_schema"
os.environ["CRIBA_LOCAL_BASE"] = "http://127.0.0.1:8080/v1"
os.environ["CRIBA_LOCAL_MODEL"] = "qwen3"
sys.path.insert(0, "src")

from criba.interprete.seleccion import construir_interprete  # noqa: E402

interp = construir_interprete("local_llama")
print("backend:", interp.backend, "| base:", interp.base, "| model:", interp.model)
print("--- operativo() corre el banco interno contra Qwen3 (8 intentos) ---")
listo, motivo = interp.operativo()
report = interp.gate_report
print("operativo:", listo, "| motivo:", motivo)
if report:
    resumen = {k: v for k, v in report.items() if k != "cases"}
    print(json.dumps(resumen, ensure_ascii=False, indent=1))
    print("--- detalle por caso ---")
    for c in report["cases"]:
        print(f"  {c['id']:14s} expected={c['expected']:9s} correcto={c['correcto']} "
              f"consistente={c['consistente']} estados={c['estados']}")
    # primer attempt con error real
    a0 = report["cases"][0]["attempts"][0]
    print("primer attempt: technical_error=", a0.get("technical_error"),
          "| error=", a0["resultado"].get("error"),
          "| raw(120)=", repr(a0["resultado"].get("raw_output"))[:120])
    out = "C:/Users/KLSX/AppData/Local/hermes/cache/scratch/qwen3_banco_v2.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("GUARDADO:", out)
