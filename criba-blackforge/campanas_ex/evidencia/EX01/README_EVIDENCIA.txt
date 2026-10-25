EX01 — Descomponer brechas reales del canon en lotes
====================================================
Fecha: 2026-10-25
Branch: campana/ex-01-descomponer-brechas
Base: EX00 DONE_VERIFIED
Writer: hermes

ACCION: Descomposicion READ-ONLY de las 101 tecnicas PLANNED en 18 lotes por (family, modulo).
Fuente: EX00 clasificacion + K10 audit matrix + technique_registry.yaml.

LOTES (18): 2 especiales (gate owner) + 8 con modulo + 8 sin modulo.
  - L0_SPECIAL_PROMOTION (2): T054,T061 — gate owner (attestation A2)
  - L0_SPECIAL_SHADOW_BYPASS (2): T104,T111 — gate owner (ADR)
  - L_MOD_* (8 lotes, 44 IDs): modulo importa, falta test/consumer
  - L_NOMOD_* (8 lotes, 53 IDs): sin modulo importable, construccion nueva

Horas estimadas totales: 82h IE (planificacion, no medidas).
Estimacion por lote: 0.5h/ID con modulo importable, 1.0h/ID sin modulo, 1.5h/ID special.
No se fabricaron 101 estimaciones individuales: se agrupan por lote.

VERIFICACION (validacion_descomposicion.py):
  - 18 lotes, 101 tecnicas, 0 duplicados, 0 omisiones, 0 solapamiento con IMPLEMENTED
  - familia coherente por lote
  - count coherente por lote
  - horas positivas
  - especiales contienen T054/T061/T104/T111
  - guard trazabilidad: 38 passed (sin cambio de codigo)

NOTA SOBRE OWNERS: 7 lotes mezclan owners dentro de la misma familia (CRIBA/CRIBA_IIE/SUPRA).
Esto es aceptable porque el lote agrupa por familia+modulo, no por owner; el owner canonico
se resuelve por tecnica en el registry. No es un defecto de descomposicion.

HALLAZGO: Los nombres de tests declarados en el canon (tests[]) no coinciden exactamente con
los nombres reales de funciones test_* en tests/. Para 101 planned, 0 coincidencias exactas.
Esto es una deuda de trazabilidad del canon (preexistente, no introducida por EX01).
Las tecnicas con codigo real y tests reales son las 29 IMPLEMENTED (guard pasa).
Las 21 planned mencionadas en tests son referencias parciales, no tests dedicados.

ARCHIVOS:
  - backlog_lotes.json / .csv (18 lotes)
  - backlog_lotes_enriched.json (import_ok, tests, src_mentions por ID)
  - orden_ejecucion.json (orden recomendado)
  - fichas_hijas.md (18 fichas)
  - validacion_descomposicion.py (guard EX01)
  - README_EVIDENCIA.txt

CONCLUSION: EX01 DONE_VERIFIED (descomposicion, sin cambios de codigo de produccion).
Ejecucion total del canon sigue TBD hasta descomposicion y aprobacion por lote.
