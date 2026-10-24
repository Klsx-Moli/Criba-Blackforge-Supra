# Propuesta de Orden de Integración

- TARGET_MAIN: 15bc237
- TIMESTAMP_UTC: 2026-10-08
- AUTOR: Hermes (writer)

## Estrategia elegida

E. OTRA (basada en evidencia): integrar BLACKFORGE puro (PR8 -> PR9 -> PR11) como
línea independiente sobre main, y SEPARAR PR10/PR12 como línea de intérprete que
requiere split antes de rebase. No se elige A ni B ciegamente porque PR8 y PR11 no
son mutuamente excluyentes (COMPLEMENTARY_WITH_BOUNDARY, ver pr8-pr11-authz-semantic-audit.md);
el orden entre ellos importa menos que documentar la frontera authz y rebasear PR10.

Motivo: PR8/9/11 son BLACKFORGE y parten de main (o main previo en PR8); PR10 parte de
shadow-supra y arrastra 122 archivos. Mezclarlos en un solo merge es riesgo innecesario.

## Tabla por unidad

| Unidad | Base actual | Riesgo | Precondiciones | Acción siguiente | Motivo |
|--------|-------------|--------|----------------|-----------------|--------|
| PR8 safety/authz | dfca79f (main previo) | GREEN | rebase a 15bc237; tests verdes | merge a main tras rebase | independiente en archivos; fail-closed puro |
| PR9 persistence | 15bc237 (main) | YELLOW | correr suite en worktree aislado; ver legacy | merge a main | READY_AFTER_TESTS_ONLY; sin colisión |
| PR11 broker/case | 15bc237 (main) | YELLOW | diff semántico authz vs PR8 (hecho: COMPLEMENTARY_WITH_BOUNDARY); tests verdes | merge a main tras PR8 | authz distinto dominio; documentar frontera |
| PR10 intérprete | shadow-supra b91e43c | ORANGE | SPLIT: extraer docs/contract/tests portables; revisar solapamiento src/ con main | split en N PRs sobre main | 122 archivos vs main; no rebaseable entero |
| PR12 continuity docs | PR10 2dc0094 | GREEN | decidir PR10 primero | mantener DRAFT; no usarlo como verdad | docs-only; CORPUS_INCOMPLETE |

## Precondiciones detalladas

PR8:
- rebase --onto 15bc237 dfca79f 65a58e5 en worktree aislado.
- `gh pr checks 8` ya PASS; suite CRIBA/BLACKFORGE local debe seguir verde.
- Riesgo: bajo (2 archivos, test-only + safety).

PR9:
- ejecutar tests de PR9 en worktree aislado sobre main.
- verificar que BD legacy (si existe) carga o falla con diagnóstico.
- Riesgo: medio (persistencia; schema user_version solo sube, no altera columnas).

PR11:
- frontera authz documentada (CBS-K1 usa pr8-pr11-authz-semantic-audit.md).
- tests negative10 + mutations (REPORTED) deben pasar en main.
- Riesgo: medio (836+1026 líneas nuevas; broker SQLite durable).

PR10:
- NO merge directo. Split en: (1) INTERPRETER_CONTRACT.md + contracts json;
  (2) scripts/check_interpreter.py; (3) tests portables; (4) módulos interprete/intelligence
  tras verificar existencia en main.
- Riesgo: alto (acoplamiento shadow-supra).

PR12:
- queda DRAFT; no merge hasta PR10.
- Riesgo: bajo.

## Decisiones de no-integración

- No fusionar nada a main en esta fase (regla dura de la misión).
- No rebasear PRs existentes (prohibido en esta misión).
- La rama de integración real (cherry-pick) se difiere a CBS-K3 (futura, fuera de esta
  misión documental).

## UNVERIFIED
- Orden de PR8 vs PR9 vs PR11 no validado por merge real (no ejecutado).
- Split de PR10 no delineado módulo a módulo (requiere inspección adicional).
