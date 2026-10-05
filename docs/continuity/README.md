# Continuidad CBS — paquete de memoria (CRIBA / BLACKFORGE / SUPRA)

OBSERVED_AT: 2026-10-05 · autor: Hermes (writer) · rama:
`hermes/cbs-continuity-memory-20261005` (base `codex/interpreter-hardening-
20261004` @ 2dc009485848b55ada5009986fe7e78d67c31ade)

Este directorio es un **paquete durable de continuidad**, no una afirmación de
verdad viva. Conserva separados: `proposed` / `accepted_for_design` /
`implemented` / `wired` / `verified` / `retired`.

## Contenido

| fichero | qué es |
|---|---|
| `00_SOURCE_MEGAPROMPT_ASTRA6_literal.md` | FUENTE A literal (mega prompt v2026-10-05) |
| `01_SOURCE_RESPUESTAS_DISENO_literal.md` | FUENTE B literal (RESPUESTA 1 + 2 + síntesis) |
| `02_SOURCE_MANDATO_MAESTRO_v2_literal.md` | FUENTE C literal (mandato maestro v2) |
| `10_INDICE_FUENTES.md` | índice de fuentes, hashes, cobertura y correcciones |
| `30_ESTADO_VERIFICADO.md` | estado observado + pruebas ejecutadas por Hermes |
| `40_REGISTRO_DECISIONES.md` | decisiones D1–D15 con estado y sustitución |
| `50_REGISTRO_CONFLICTOS.md` | conflictos C-01–C-15 y su resolución |
| `60_MEGA_PROMPT_CBS_v3.md` | MEGA PROMPT consolidado + ANEXO literal A/B/C |
| `70_HANDOFF_OPERATIVO.md` | TARGET_SHA, prioridad, evidencia, siguiente acción |
| `80_REGISTRO_EJECUCIONES.md` | registro E-01–E-12 con la plantilla exigida |

## Reglas de uso (no negociables)

1. Este paquete NO acredita implementación ni levanta HARD_PAUSE.
2. Los estados citados son históricos o medidos en una sesión; anclar siempre a
   un SHA antes de actuar.
3. Las pruebas las ejecutó Hermes, que es el writer: son EVIDENCIA REPORTADA,
   no verificación independiente.
4. GUI ejecutada en **offscreen** NO es escritorio Windows verificado.
5. `CORPUS_INTEGRITY = INCOMPLETE`: faltan los originales de SRC-01, SRC-02 y
   SRC-03 (ver `10_INDICE_FUENTES.md`). Ningún resumen los sustituye.

## Invariantes (recordatorio)

    TEST GREEN != CONTRACT PROTECTED
    IMPLEMENTED != WIRED != EXECUTED != TESTED
    UNKNOWN != 0 / PASS / VALIDATED / evidence
    PLANNED != EXECUTED · PERSISTED != EXECUTED
    BLOCKED != SUCCESS · FAILED != SUCCESS
    HTTP 2xx != VALIDATION · DECLARED != OBSERVED · OBSERVED != CAUSAL
