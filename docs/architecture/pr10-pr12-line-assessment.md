# Evaluación de la Línea PR10 + PR12

- PR10 head: 2dc009485848b55ada5009986fe7e78d67c31ade (base: hermes/astra/shadow-supra-20261002 @ b91e43c)
- PR12 head: 8b1ba5be80051dff197d82eba1a844ed5961da77 (base: PR10 2dc0094)
- TARGET_MAIN: 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer; inspección de diffs/metadata)

## 1. Qué aporta PR10 (por diff real, gh pr view)

73 archivos modificados (6.188 add / 1.317 del). Áreas:
- intérprete causal: `interprete/` (adaptador, banco, contrato, juez, openai_compatible,
  pipeline, prefilter, protocolo, puerto, store, ids) — hardening de contrato.
- `intelligence/`: evidence_context.py (ADDED, retrieval acotado con source identity),
  refresh.py (concurrent acquisition + budget), sources/protocol.py, transport.py,
  storage/store.py (MODIFIED).
- UI: shadow_ui/*, ui/actions.py, i18n.py, panels.py, source_progress.py (ADDED).
- model_config.py, model_runtime.py, mcp_server.py, api.py, inventar.py, supra_dossier.py.
- supra/: service.py, state.py (diagnósticos atómicos).
- tests: astra_canon, integration, intelligence, unit (test_interpreter_hardening,
  test_source_evidence_context, test_source_refresh_hardening, etc.).
- docs: INTERPRETER_CONTRACT.md, contracts/criba_supra_envelope_fingerprints.json.
- verification/: interpreter_cases.py, journey_harness.py.

Puntos de entrada: `scripts/check_interpreter.py`, `interprete/` pipeline, `intelligence/refresh`.

Contrato del intérprete: causal interpreter proposals + revalidación de cache contra
evidencia entregada (commit 2dc0094). Coverage UNKNOWN; scientific_validation NOT_VALIDATED
(según propio commit body).

## 2. Dependencia real de su base (shadow-supra b91e43c)

- PR10 NO parte de main. Base = b91e43c (rama hermes/astra/shadow-supra-20261002).
- Diff PR10 head vs main (15bc237): 122 archivos, +16062 / -1332. Es decir, PR10 arrastra
  TODO el árbol shadow-supra que main no tiene, no solo los 73 de su propia descripción.
- Consecuencia: un `git merge` de PR10 a main traería 122 archivos, no 73. Rebase puro es
  enorme y propenso a conflictos en src/ (26 archivos) y shadow_ui.

## 3. Partes portables vs acopladas

- Independientes y portables (candidatas a cherry-pick aislado):
  - `docs/INTERPRETER_CONTRACT.md` + `contracts/*.json` (documentación de contrato).
  - `scripts/check_interpreter.py` (herramienta de verificación).
  - `tests/intelligence/test_source_evidence_context.py`, `test_interpreter_hardening.py`
    (si sus dependencias de módulo existen en main).
- Acopladas al árbol shadow-supra:
  - `shadow_ui/*` (UI específica de Shadow CRIBA/SUPRA).
  - `interprete/*` completo (probablemente no existe en main tal cual).
  - `ui/*` (actions, i18n, panels, source_progress) — posible solapamiento con main.
- Mezcladas con UI: refresh.py, evidence_context.py, source_progress.py.
- Demasiado grandes para un solo rebase: SÍ (122 archivos vs main).

## 4. Qué hace PR12

- Documentation-only: `docs/continuity/` (corpus literal, índice, estado, registro de
  ejecuciones, decisiones D1-D15, conflictos C-01-C15, handoff, MEGA PROMPT).
- `.gitattributes` acotado a 4 paths `-text` del corpus (NO renormalización global).
- CORPUS_INTEGRITY=INCOMPLETE (faltan originales SRC-01/02/03).
- Declara explícitamente: NO acredita implementación, NO levanta HARD_PAUSE, M2_GUI_VISIBLE
  NO ACREDITADO, M3_ACCEPTANCE PENDIENTE.
- NO documenta comportamiento de código como hecho; es handoff operativo + corpus.
- No adelanta capacidades de main (es paquete de continuidad del proyecto).

## 5. Clasificación final

SPLIT_BEFORE_REBASE

PR10 es una línea grande acoplada a shadow-supra (122 archivos vs main). No es un
rebase simple: requiere dividir en (a) contrato/documentación portable, (b) tests
portables, (c) módulos de intérprete/UI que pueden no existir en main o colisionar.
PR12 es DOCS_ONLY_HOLD: debe permanecer bloqueada hasta decidir PR10, pero ya está
correctamente etiquetada como documentation-only y no debe usarse como fuente de
verdad de comportamiento.

## UNVERIFIED
- No se inspeccionó internamente cada uno de los 26 módulos src/ de PR10.
- No se verificó si main ya contiene `interprete/` o `shadow_ui/` (el diff vs main
  sugiere que PR10 los introduce/modifica, pero el estado previo de main no se leyó
  módulo a módulo).
- Tests de PR10 no ejecutados (NOT_RUN).
