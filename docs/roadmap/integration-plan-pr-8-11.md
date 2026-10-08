# Plan de Integración PR #8–#11 (Basado en realidad verificada)

- TARGET_MAIN_SHA: 15bc237be5555fcc38bc8a25f80724473c13435b
- BRANCH_AUDIT: hermes/cbs-pr8-11-convergence-audit @ 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer)

## Estrategia canónica recomendada

Dada la evidencia (gh pr view) y SC-01: los PR #8–#11 NO son variantes de una
misma capacidad (no hay consenso/replay/reliability/VOI que reconciliar). Son
cuatro líneas de trabajo distintas sobre BLACKFORGE/intérprete. Por tanto la
"estrategia de integración" no es elegir una variante sobre otra, sino un ORDEN
de integración seguro a main, verificando solapamientos reales.

Recomendación: ESTRATEGIA B modificada — rama de integración limpia desde main
para portar selectivamente, NO merge ciego de PRs. No se fusiona nada a main en
esta fase (regla dura). La rama de auditoría actual SOLO contiene documentación.

## Pasos pequeños (cada uno con rollback)

Paso 1 — Rebasear PR8 a main 15bc237 (su base es dfca79f, main previo).
- Comando (a ejecutar por operador, NO aquí): en worktree aislado,
  `git rebase --onto 15bc237 dfca79f4 65a58e5` sobre rama de PR8.
- Verificación: `gh pr checks 8` y suite CRIBA/BLACKFORGE local verde.
- Rollback: `git rebase --abort` o restaurar ref de la rama de PR8.

Paso 2 — Verificar solapamiento authz PR8 vs PR11 (ambos authorization).
- Comando: diff semántico de `blackforge_safety.py` (PR8) vs
  `blackforge_broker.py`/`blackforge_case.py` authorization (PR11).
- Decisión: si hay duplicación de lógica authz, unificar en un módulo; si son
  dominios distintos (safety vs broker), documentar frontera.
- Rollback: no aplicar port hasta decidir; rama de integración queda sin cambios.

Paso 3 — Integrar PR9 (persistence) tras PR8.
- Verificar que storage.py (blackforge) no choca con intelligence/storage/store.py
  (PR10, aún no integrado). No integra PR10 aquí.
- Rollback: `git revert` del merge por commit o branch por paso.

Paso 4 — PR11 sobre main tras verificar Paso 2.
- Rollback: branch por paso; PR11 NO es draft, pero no se mergea sin revisión.

Paso 5 — PR10: requiere rebase a main (base actual shadow-supra b91e43c).
- ANTES de integrar, rebasear PR10 a 15bc237 en worktree aislado y ejecutar suite
  completa (CRIBA/BLACKFORGE/SUPRA). Solo entonces ordenarlo.
- Rollback: rebase --abort.

Paso 6 — PR12 (docs) tras decidir integración de PR10; nunca como fuente de
  verdad de comportamiento.

## Trazabilidad de pruebas (REPORTED_BY_PR, no reproducido)

- PR8: suite dirigida 188 passed (commit 65a58e5); CRIBA/BLACKFORGE 1508 passed.
- PR9: tests storage/agentic/pipeline (conteos no desglosados en metadata).
- PR10: 174 passed (combined gate, commit 2dc0094); 480 passed (sources/intelligence).
- PR11: 1545 passed full suite; 41 negative+mutation; round-trip JSON idéntico.
- PR12: ningún test (docs).

## Qué NO está verificado
- Ningún test reproducido en esta sesión (working tree de auditoría no ejecutó suite).
- Semántica interna de authz PR8 vs PR11 no comparada línea a línea.
- Base remota de PR10 (b91e43c) no presente localmente.
- Compatibilidad legacy/migración de PR9 no probada con datos reales.

## Límites de acceso
- No se hizo push, merge, rebase ni ejecución de BLACKFORGE.
- HARD_PAUSE vigente; ninguna acción real de BLACKFORGE habilitada.
