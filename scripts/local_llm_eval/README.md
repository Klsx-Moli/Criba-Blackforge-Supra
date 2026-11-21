# Evaluación de LLMs locales contra el banco de admisión de CRIBA

Herramientas para medir un GGUF local (motor llama-server Vulkan, loopback)
contra el **banco de admisión real** de CRIBA (`criba.interprete.banco`).
NO modifican banco, schema, umbrales ni golden. Solo miden y reportan.

Motor usado: `E:\AI\llama.cpp-vulkan\bin\llama-server.exe` (RX 570, Vulkan0).
Config que funciona (ver docs/audit/CB-LOCAL-LLM-SWEEP_2026-10-13.md):

```
llama-server -m <gguf> --alias qwen3 --device Vulkan0 --gpu-layers 999 \
  --host 127.0.0.1 --port 8080 --ctx-size 8192 --jinja
```

Importante: **sin** banderas `--reasoning off` — rompen la grammar `json_schema`.

## Scripts

- `sweep_bank.py` — barre los 16 GGUF de `E:\AI\MODELOS_HF_MODIFICADOS`,
  arranca/apaga el server por modelo y corre el banco de cada uno. Escribe el
  reporte JSON por modelo.
- `bank_single.py` — corre el banco contra UN modelo ya servido (instancia limpia).
- `repro_schema.py` — reproduce `json_schema` fuera del banco con el schema real
  de CRIBA, para diagnosticar HTTP 400 / grammar.
- `run_questions.py` — 30 preguntas por la ruta real `invent()` → intérprete →
  dossier. Requiere el server activo y `CRIBA_*` configuradas.

## Resultado del barrido (2026-10-13)

Ningún modelo local pasó el banco. Detalle y diagnóstico:
`docs/audit/CB-LOCAL-LLM-SWEEP_2026-10-13.md` +
`docs/audit/evidence/local_llm_sweep_2026-10-13.json`.
