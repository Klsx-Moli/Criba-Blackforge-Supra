"""Barrido del banco de admision CRIBA sobre los 16 GGUF locales.

Secuencial, un modelo a la vez, contra el motor Vulkan propio
(E:\\AI\\llama.cpp-vulkan\\bin\\llama-server.exe). Cada modelo:
  1. arranca llama-server (loopback 127.0.0.1) con alias criba-eval
  2. espera readiness (/v1/models)
  3. corre el banco REAL de CRIBA (evaluar_banco via LocalLlamaInterpreter,
     constrained decoding json_schema) SIN modificar umbrales ni schema
  4. registra passed + tasas por modelo
  5. mata el server y libera VRAM antes del siguiente

Los 2 modelos de cuarentena van incluidos por autorizacion explicita del
usuario (-AllowUnsafeModel); se marcan quarantined=True en el registro.

NO toca CRIBA. NO cambia golden/umbrales/schema. Reporta solo.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

SERVER = "E:/AI/llama.cpp-vulkan/bin/llama-server.exe"
PORT = 8080
BASE = f"http://127.0.0.1:{PORT}/v1"
ALIAS = "criba-eval"

MODELS = [
    ("gemma4_e2b_qat", False, "E:/AI/MODELOS_HF_MODIFICADOS/01_QAT_Y_CUANTIZACION_MEJORADA/google--gemma-4-E2B-it-qat-q4_0-gguf/gemma-4-E2B_q4_0-it.gguf"),
    ("qwen35_4b_qat", False, "E:/AI/MODELOS_HF_MODIFICADOS/01_QAT_Y_CUANTIZACION_MEJORADA/YoozLabs--Qwen3.5-4B-qat-GGUF/Qwen3.5-4B-qat-Q4_0.gguf"),
    ("gemma4_e4b_qat", False, "E:/AI/MODELOS_HF_MODIFICADOS/01_QAT_Y_CUANTIZACION_MEJORADA/google--gemma-4-E4B-it-qat-q4_0-gguf/gemma-4-E4B_q4_0-it.gguf"),
    ("qwen35_base_control", False, "E:/AI/MODELOS_HF_MODIFICADOS/00_CONTROL_OFICIAL/bartowski--Qwen_Qwen3.5-4B-GGUF/Qwen_Qwen3.5-4B-Q4_K_M.gguf"),
    ("qwen35_4b_neo", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/Jackrong--Qwen3.5-4B-Neo-GGUF/Qwen3.5-4B.Q4_K_M.gguf"),
    ("qwopus35_4b_v3", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/Jackrong--Qwopus3.5-4B-v3-GGUF/Qwen3.5-4B.Q4_K_M.gguf"),
    ("qwen35_4b_claude_opus_v2", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/Jackrong--Qwen3.5-4B-Claude-4.6-Opus-Reasoning-Distilled-v2-GGUF/Qwen3.5-4B.Q4_K_M.gguf"),
    ("adi_qwen35_4b_glm52", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/AdvancedDataIntelligence--adi-qwen3.5-4b-glm5.2-general-GGUF/adi-qwen3.5-4b-glm5.2-general-q4_k_m.gguf"),
    ("qwen35_9b_deepseek_v4_flash", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/Jackrong--Qwen3.5-9B-DeepSeek-V4-Flash-GGUF/Qwen3.5-9B-DeepSeek-V4-Flash-Q4_K_M.gguf"),
    ("qwopus35_9b_v3", False, "E:/AI/MODELOS_HF_MODIFICADOS/02_RAZONAMIENTO_GENERAL/Jackrong--Qwopus3.5-9B-v3-GGUF/Qwopus3.5-9B-v3.Q4_K_M.gguf"),
    ("qwopus35_9b_coder", False, "E:/AI/MODELOS_HF_MODIFICADOS/03_PROGRAMACION/Jackrong--Qwopus3.5-9B-Coder-GGUF/Qwopus3.5-9B-coder-Exp-Q4_K_M.gguf"),
    ("qwen35_4b_super_coder", False, "E:/AI/MODELOS_HF_MODIFICADOS/90_EXPERIMENTALES/jica98--qwen3.5-4B-super-coder/qwen3.5-4B-super-coder.Q4_0.gguf"),
    ("qwen35_4b_agenttools", False, "E:/AI/MODELOS_HF_MODIFICADOS/04_AGENTES_Y_HERRAMIENTAS/limnmn--Qwen3.5-4B-AgentTools-GGUF/Qwen3.5-4B-AgentTools-v0.8-Q4_K_M.gguf"),
    ("lfm25_8b_a1b", False, "E:/AI/MODELOS_HF_MODIFICADOS/05_MODELOS_ALTERNATIVOS/LiquidAI--LFM2.5-8B-A1B-GGUF/LFM2.5-8B-A1B-Q4_K_M.gguf"),
    ("qwen35_9b_abliterated", True, "E:/AI/MODELOS_HF_MODIFICADOS/99_CUARENTENA_UNCENSORED/lukey03--Qwen3.5-9B-abliterated-GGUF/Qwen3.5-9B-abliterated-Q4_K_M.gguf"),
    ("qwen35_9b_defiant", True, "E:/AI/MODELOS_HF_MODIFICADOS/99_CUARENTENA_UNCENSORED/DavidAU--Qwen3.5-9B-The-Defiant-Fable-Uncensored-Heretic-NEO-IMATRIX-MAX-MTP-GGUF/Qwen3.5-9B-The-Defiant-Fable-Uncnr-Heretic-NEO-MAX-Q4_K_M.gguf"),
]

OUT = "C:/Users/KLSX/AppData/Local/hermes/cache/scratch/barrido_banco.json"


def start_server(gguf: str) -> subprocess.Popen:
    proc = subprocess.Popen(
        [SERVER, "-m", gguf, "--alias", ALIAS, "--device", "Vulkan0",
         "--gpu-layers", "999", "--host", "127.0.0.1", "--port", str(PORT),
         "--ctx-size", "4096", "--jinja"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return proc


def wait_ready(timeout: float = 120.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{BASE}/models", timeout=4) as r:
                if r.status == 200:
                    ids = json.load(r).get("data", [])
                    if any(m.get("id") == ALIAS for m in ids):
                        return True
        except Exception:
            pass
        time.sleep(2)
    return False


def kill_server(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
        proc.wait(timeout=15)
    except Exception:
        try:
            proc.kill()
            proc.wait(timeout=8)
        except Exception:
            pass


def run_bank(model_id: str) -> dict:
    os.environ["CRIBA_CONSTRAINED_DECODING"] = "json_schema"
    os.environ["CRIBA_LOCAL_BASE"] = BASE
    os.environ["CRIBA_LOCAL_MODEL"] = ALIAS
    for m in [k for k in sys.modules if k.startswith("criba")]:
        del sys.modules[m]
    sys.path.insert(0, "C:/ASTRA_WORK/Criba-Blackforge-Supra/criba-blackforge/src")
    from criba.interprete.seleccion import construir_interprete  # noqa
    interp = construir_interprete("local_llama")
    listo, motivo = interp.operativo()
    rep = interp.gate_report or {}
    resumen = {k: v for k, v in rep.items() if k != "cases"}
    casos = []
    for c in rep.get("cases", []):
        a = c["attempts"][0]
        casos.append({
            "id": c["id"], "expected": c["expected"], "correcto": c["correcto"],
            "consistente": c["consistente"], "estados": c["estados"],
            "technical_error": a.get("technical_error"),
            "finish_reason": a.get("finish_reason"),
            "completion_tokens": a.get("completion_tokens"),
            "error_validacion": a["resultado"].get("error"),
        })
    return {"operativo": listo, "motivo": motivo, "resumen": resumen, "casos": casos}


def main() -> None:
    resultados = []
    for i, (mid, quar, gguf) in enumerate(MODELS, 1):
        if not Path(gguf).is_file():
            resultados.append({"id": mid, "quarantined": quar, "error": "GGUF no encontrado", "path": gguf})
            print(f"[{i}/16] {mid}: GGUF NO ENCONTRADO", flush=True)
            continue
        print(f"[{i}/16] {mid}: arrancando server...", flush=True)
        proc = start_server(gguf)
        try:
            if not wait_ready():
                resultados.append({"id": mid, "quarantined": quar, "error": "server no levanto / no ready"})
                print(f"[{i}/16] {mid}: SERVER NO READY", flush=True)
                continue
            print(f"[{i}/16] {mid}: banco...", flush=True)
            try:
                bank = run_bank(mid)
            except Exception as exc:  # noqa: BLE001
                bank = {"error": f"{type(exc).__name__}: {exc}"}
            r = bank.get("resumen", {}) if isinstance(bank, dict) else {}
            entry = {
                "id": mid, "quarantined": quar,
                "passed": r.get("passed"),
                "schema_response_rate": r.get("schema_response_rate"),
                "correct_abstention_rate": r.get("correct_abstention_rate"),
                "consistency_rate": r.get("consistency_rate"),
                "operativo": bank.get("operativo"), "motivo": bank.get("motivo"),
                "error": bank.get("error"), "casos": bank.get("casos"),
            }
            resultados.append(entry)
            print(f"[{i}/16] {mid}: passed={entry['passed']} "
                  f"schema_rate={entry['schema_response_rate']} "
                  f"abstention={entry['correct_abstention_rate']} "
                  f"consistency={entry['consistency_rate']}", flush=True)
        finally:
            kill_server(proc)
            time.sleep(3)  # liberar VRAM antes del siguiente
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(resultados, f, ensure_ascii=False, indent=1)
    print("GUARDADO:", OUT, flush=True)
    # resumen final
    print("\n==== RESUMEN ====", flush=True)
    for e in resultados:
        tag = " [CUARENTENA]" if e.get("quarantined") else ""
        print(f"  {e['id']:28s} passed={e.get('passed')} "
              f"schema={e.get('schema_response_rate')} "
              f"abst={e.get('correct_abstention_rate')}{tag}", flush=True)


if __name__ == "__main__":
    main()
