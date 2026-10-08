# Matriz de Convergencia PR #8–#12 (Real — Checkout + GitHub)

- TARGET_MAIN_SHA / REMOTE_MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- BRANCH_AUDIT: hermes/cbs-pr8-11-convergence-audit @ 15bc237
- CANONICAL_REMOTE_MAIN: origin/main
- TIMESTAMP_UTC: 2026-10-08 (sesión)
- AUTOR: Hermes (writer; NO verificador independiente)

## SC-01 — Conflicto de fuentes

- Fuente externa: informe adjunto / Kanban que describe PR #8–#11 como
  CONSENSUS / EVIDENCE_CONFIGURATION / RELIABILITY / EPISODIC_MEMORY /
  RETRIEVAL / DIVERSITY_TOP_K / VOI / REGRET / SHADOW_PRICING / PROVIDER_MODEL_KWARGS.
- Observación primaria: checkout local + metadatos GitHub/gh actuales.
- Conflicto: identidad, objetivo y alcance de PR #8–#12. Los diffs reales NO
  contienen esas capacidades.
- Resolución: Git remoto y diffs GitHub son autoritativos para la decisión
  presente. El informe externo queda como HISTORICAL_UNVERIFIED.
- Impacto: se INVALIDA la matriz propuesta para consenso/evidence/reliability/
  episodic replay/VOI/shadow pricing hasta que exista evidencia actual de
  tales ramas/PR. No se inventan contratos ausentes.

## PR_REALITY_MATRIX (datos de gh pr view; REPORTED_BY_PR salvo donde se diga)

| PR | Base Ref | Base SHA | Head Ref | Head SHA | Área real | Estado | Dependencias | Solapamientos | Riesgo | Decisión |
|----|----------|----------|----------|----------|-----------|--------|--------------|---------------|--------|----------|
| 8 | main | dfca79f4ea4a9ddd2bb99a9be2f3b9f4caaf39c0 | astra/blackforge-safety/dfca79-auth-state-failclosed | 65a58e565d58ad793272388653f35afc2dc9d1ed | BLACKFORGE safety / authz fail-closed | OPEN, DRAFT, mergeState CLEAN, checks PASS | main (base previa) | ninguno con 9/11 (módulo distinto) | GREEN | CONSERVAR |
| 9 | main | 15bc237be5555fcc38bc8a25f80724473c13435b | astra/blackforge-persistence/15bc23-durable-agentic-audit | 1a98b7e26953c3f8642e40e8905cab7ef7e9a55a | BLACKFORGE persistencia / auditabilidad | OPEN, DRAFT, CLEAN, PASS | main | storage.py vs PR11 (distinto módulo) | YELLOW | CONSERVAR, verificar round-trip |
| 10 | hermes/astra/shadow-supra-20261002 | b91e43c1a6261e6a7c7583460478fd87a3367c1f | codex/interpreter-hardening-20261004 | 2dc009485848b55ada5009986fe7e78d67c31ade | intérprete causal / contrato / evidence_context / UI | OPEN, DRAFT, CLEAN, PASS | NO es main (base shadow-supra) | PR12 descansa sobre este HEAD | ORANGE | REVISAR base; requiere rebase a main |
| 11 | main | 15bc237be5555fcc38bc8a25f80724473c13435b | astra/blackforge-dossier-20261005 | 3244879e7b2a2b4510dd997f4a343e26b1811b1b | BLACKFORGE v1 broker / DefensiveCase / slice authz | OPEN, NO draft, CLEAN, PASS | main | authz puede solaparse con PR8 | YELLOW | CONSERVAR, verificar solapamiento authz con PR8 |
| 12 | codex/interpreter-hardening-20261004 | 2dc009485848b55ada5009986fe7e78d67c31ade | hermes/cbs-continuity-memory-20261005 | 8b1ba5be80051dff197d82eba1a844ed5961da77 | continuidad / documentación / handoff | OPEN, DRAFT, CLEAN, PASS | PR10 (2dc0094) | sólo docs; CORPUS_INTEGRITY=INCOMPLETE | GREEN | POSPONER hasta decidir integración |

## Relaciones determinadas (no por número de PR)

- PR8 base dfca79f (main antiguo) -> HEAD 65a58e5. PR9/11 base 15bc237 (main actual).
  PR8 debe rebasear a 15bc237 antes de integración (su base es main previo).
- PR10 NO parte de main: base b91e43c (shadow-supra-20261002). No es
  acumulable con 8/9/11 sin rebase explícito a main. PR12 descansa sobre PR10.
- PR8 y PR11 tocan authorization: PR8 = fail-closed en safety; PR11 =
  authorization record en broker/case. Mismo dominio (authz) pero módulos
  distintos. Riesgo de semántica duplicada/conflicto: requiere diff semántico
  antes de portar. NO asumido compatible.
- PR9 storage.py (blackforge) vs PR10 intelligence/storage/store.py: módulos
  distintos, no confirmado solapamiento.

## INTEGRATION_ORDER_CANDIDATE (no ejecutado; propuesta de análisis)

1. PR8 (safety/authz) + PR9 (persistence) sobre main 15bc237 — independientes
   en archivos, ambos CLEAN/PASS.
2. PR11 (broker/case) sobre main 15bc237 — verificar solapamiento authz con PR8.
3. PR10 requiere rebase a main (base shadow-supra) ANTES de cualquier orden.
4. PR12 es documentation-only sobre PR10; decide tras PR10.

NO_SAFE_ORDER_DETERMINED para PR10 integrado a main sin rebase previo y sin
verificar semántica vs 8/9/11.

## DO_NOT_TOUCH
- main (protegido; no merge, no push --force).
- Cualquier ejecución BLACKFORGE real (HARD_PAUSE vigente).
- Permisos/secretos/protección de rama de GitHub.
- Borrar ramas, PR, worktrees, ficheros o historial.

## UNVERIFIED
- Conteos de tests son REPORTED_BY_PR (commit bodies), no reproducidos en esta
  sesión. No se ejecutó suite para no contaminar working tree.
- Semántica interna de símbolos más allá de nombres de archivo no inspeccionada.
- Base remota de PR10 (b91e43c) no presente localmente en esta rama de auditoría.
