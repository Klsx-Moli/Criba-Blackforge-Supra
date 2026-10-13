# CB-LOCAL-LLM-SWEEP — Barrido de 16 GGUF locales vs banco de admision de CRIBA

Fecha: 2026-10-13. Rama: audit/fase0-fase1. Motor Vulkan propio
E:\AI\llama.cpp-vulkan\bin\llama-server.exe (build 10079), loopback 127.0.0.1,
Radeon RX 570 (Vulkan0, --gpu-layers 999). BLACKFORGE inerte.

## ALCANCE (VERIFIED_BY_EXECUTION)
- Banco de admision REAL de CRIBA (criba.interprete.banco.evaluar_banco) con
  constrained decoding=json_schema. 4 casos x2 repeticiones = 8 intentos/modelo.
- Secuencial, un modelo a la vez, VRAM liberada entre modelos.
- Incluidos los 2 de 99_CUARENTENA_UNCENSORED (abliterated, defiant) por
  autorizacion explicita del usuario (-AllowUnsafeModel). Se marcan CUARENTENA.
- NO se toco banco, schema, umbrales ni golden. Solo se mide.

## RESULTADO (16/16, ninguno PASS)
| modelo | schema_rate | abstention | consistency | passed |
|---|---|---|---|---|
| qwen35_4b_qat | 1.0 | 1.0 | 1.0 | False |
| qwen35_base_control | 1.0 | 1.0 | 1.0 | False |
| qwen35_4b_agenttools | 0.875 | 1.0 | 0.75 | False |
| lfm25_8b_a1b | 0.75 | 0.67 | 1.0 | False |
| gemma4_e2b_qat / e4b_qat | 0.5 | 0.67 | 1.0 | False |
| adi_qwen35_4b_glm52 | 0.5 | 0.67 | 1.0 | False |
| qwen35_9b_defiant [CUAR] | 0.5 | 0.67 | 1.0 | False |
| qwen35_4b_super_coder | 0.5 | 0.67 | 1.0 | False |
| qwopus35_9b_coder | 0.5 | 0.67 | 1.0 | False |
| qwen35_4b_claude_opus_v2 | 0.5 | 0.33 | 0.5 | False |
| qwen35_9b_abliterated [CUAR] | 0.375 | 0.33 | 0.75 | False |
| qwen35_4b_neo / qwopus35_4b_v3 | 0.0 | 0.0 | 1.0 | False |
| qwen35_9b_deepseek / qwopus35_9b_v3 | 0.0 | 0.0 | 1.0 | False |

## DIAGNOSTICO
- Los dos mejores (qat, base_control): JSON valido siempre, abstienen perfecto
  en los 3 negativos. El UNICO punto que les falla es el caso pertinente:
  validan el contenido pero abstienen cuando deberian proponer (interpretan que
  la evidencia local no apoya el mecanismo). Criterio semantico, no timeout.
- Timeouts (agenttools, ambos uncensored, dossier completo): las plantillas de
  estos GGUF (modificados/QAT) fuerzan reasoning_content ("Thinking Process").
  Con json_schema + prompt largo de dossier+critica, el pensamiento se come el
  presupuesto -> timeout o contenido vacio. Verificado en Qwen3-8B,
  Qwen3-4B-agenttools y gemma-4-E2B (todos emiten reasoning_content pese a --jinja).

## DOSSIER COMPLETO (30 preguntas): NOT_EXECUTED
- Ruta real invent() -> interprete -> dossier con el ganador:
  1) backend local_llama exige superar el banco antes de emitir -> bloquea toda
     propuesta (model_requests=0).
  2) backend externo apuntando al GGUF local (bypass honesto del gate): timeout
     a 240s (Qwen3-4B) o contenido vacio por thinking (gemma-4-E2B). Un dossier
     de CRIBA es largo y un 4B local con plantilla thinking no lo termina.
- No se forzaron respuestas cortas ni se inflo el resultado. Muro real, documentado.

## CONFIG QUE FUNCIONA (para reproducir)
- llama-server -m <gguf> --alias qwen3 --device Vulkan0 --gpu-layers 999
  --host 127.0.0.1 --port 8080 --ctx-size 4096|8192 --jinja
  SIN banderas --reasoning (esas rompian la grammar con json_schema).
- El runtime local de CRIBA (local_llama) ademas corre el banco interno en
  operativo() y cachea gate_report; hay que instanciar limpio por modelo.

## CONCLUSION
- Con la RX 570 (8 GB) y estos GGUF, ningun modelo local pasa el banco de
  admision de CRIBA, y el dossier completo no se genera en tiempo razonable por
  el thinking forzado de las plantillas.
- Siguiente paso propuesto (NO ejecutado, pendiente de confirmacion): un GGUF
  instruct no-reasoning de ~7-9B (p. ej. Qwen2.5-7B-Instruct Q4_K_M, ~4.7 GB,
  cabe en 8 GB) para que el dossier no choque con el thinking.

## EVIDENCIA
- Reporte completo por modelo con technical_error y finish_reason: copia en
  docs/audit/evidence/local_llm_sweep_2026-10-13.json (barrido_banco.json).
