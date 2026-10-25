EX01 — Descomponer brechas reales del canon en lotes
====================================================
Fecha: 2026-10-25
Branch: campana/ex-01-descomponer-brechas
Base: EX00 DONE_VERIFIED
Writer: hermes

ACCION: Descomposicion READ-ONLY de las 101 tecnicas PLANNED en 18 lotes por (family, modulo).
Fuente: EX00 clasificacion + K10 audit matrix + technique_registry.yaml.

LOTES (18):
  L0_SPECIAL_PROMOTION (2): T054,T061 — gate owner (attestation A2)
  L0_SPECIAL_SHADOW_BYPASS (2): T104,T111 — gate owner (ADR)
  L_MOD_* (9 lotes, 44 IDs): modulo existe, falta test/consumer
  L_NOMOD_* (8 lotes, 53 IDs): sin modulo, construccion nueva

Horas estimadas totales: ~80h IE (planificacion, no medidas).
No se fabricaron 101 estimaciones individuales: se agrupan por lote.

VERIFICACION:
  - total planned = 101 (coincide con canon: 130-29)
  - guard trazabilidad: 38 passed (sin cambio de codigo)
  - recovery baseline: 21 passed

ARCHIVOS:
  - backlog_lotes.json / .csv
  - orden_ejecucion.json
  - fichas_hijas.md
  - README_EVIDENCIA.txt

CONCLUSION: EX01 DONE_VERIFIED (descomposicion, sin cambios de codigo de produccion).
Ejecucion total del canon sigue TBD hasta descomposicion y aprobacion por lote.
