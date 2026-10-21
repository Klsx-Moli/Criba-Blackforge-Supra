# CLASIFICACIÓN FINAL DE RAMAS (2026-10-17)
# Basado en el plano de ramas (37 refs) y el MVA Master Value Archive.

# INTEGRADAS EN integrate/shadow-supra-final (commiteado + push)
✅ fix/offline-test-correction-20261017 — bug interprete corregido
✅ cb01-bank-provenance — procedencia verificación
✅ cb03-journey-e2e — journey end-to-end
✅ hermes/astra/shadow-supra-20261002 — Shadow UI
✅ hermes/cloud-provider-layer-20261013 — cloud_provider_layer.py (17 commits)
✅ k-int-04-cbs-docs — docs CBS canónicos (13 archivos)

# NO INTEGRADAS — JUSTIFICACIÓN

## Riesgo de seguridad (preservar defensas en HEAD)
❌ hermes/banco-grammar-04 (7 commits) — elimina endpoint_problem()
❌ hermes/banco-trace-04a-20261010 (3 commits) — elimina endpoint_problem()

## Diferido (requiere decisión de moli)
❌ hermes/deep-execution-20261005 (9 commits) — divergencia supra_result_status

## Riesgo de regresión (elimina funcionalidad de HEAD)
❌ hermes/astra/p0-state-utf8-persistence (1 commit) — elimina _persisted_error_kind + ProjectStateLoadError
❌ hermes/astra/p1-golden-blob-path (2 commits) — verificar diferencias
❌ astra5-20260930-criba-type-debt (9 commits) — viejo, posible conflicto con typing

## BLACKFORGE HARD_PAUSE
⏸ astra/blackforge-dossier-20261005 (2 commits)
⏸ astra/blackforge-persistence/15bc23-durable-agentic-audit (17 commits)
⏸ astra/blackforge-safety/dfca79-auth-state-failclosed (6 commits)

## Alto riesgo de scope
❌ chatgpt/forensic-all-fixes-20261001 (27 commits) — lote masivo antiguo

## Snapshots preservados como artefactos (NO borrados)
✅ hermes/audit-snapshot-20261009 (1)
✅ hermes/local-snapshot-20261009-convergence-audit (1)
✅ hermes/local-snapshot-20261009-dossier (3)
✅ hermes/local-snapshot-20261009-main-baseline (1)
✅ hermes/local-snapshot-20261009-pr9-persistence (18 — riesgo alto, preservado)
✅ hermes/cbs-continuity-memory-20261005 (4) — docs

## Absorbidos en HEAD (no hacen falta merge)
✅ hermes/cbs-pr8-11-convergence-audit — 0 commits únicos
✅ chatgpt/shadow-exe-journey-20261008 — 0 commits únicos
✅ chatgpt/shadow-supra-reliability-20261008 — 0 commits únicos
✅ chatgpt/reconcile-hermes-deep-20261009 — 0 commits únicos

# RESUMEN
37 refs: 6 integradas + 3 absorbidas + 5 snapshots preservados + 22 diferidas/no integradas
BLACKFORGE: 3 ramas en HARD_PAUSE
