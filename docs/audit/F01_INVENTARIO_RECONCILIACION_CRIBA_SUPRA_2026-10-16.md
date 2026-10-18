# F01 — Inventario, Continuidad y Reconciliación de CRIBA · BLACKFORGE · SUPRA

**Fecha de auditoría:** 2026-10-16 (hora local UTC+2)  
**Tipo:** Auditoría de solo lectura  
**Repositorio canónico:** `Klsx-Moli/Criba-Blackforge-Supra`  
**BLACKFORGE:** `HARD_PAUSE` — fuera del alcance funcional  

---

## 1. Resumen Ejecutivo

El repositorio canónico tiene su rama `main` en el SHA `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` (merge PR #22, 2026-10-13). CI verde en ese SHA (run #85, success). No existen releases ni etiquetas.

El checkout local activo (`C:\ASTRA_WORK\Criba-Blackforge-Supra`) está en la rama `hermes/cloud-provider-layer-20261013` (HEAD `3f20e5c`), **23 commits por delante de `origin/main`**, con 24 ficheros modificados (+2604/-23 líneas). El árbol de trabajo está limpio (solo ficheros no rastreados).

Existen **6 PR abiertas**: #21 (procedencia banco), #8/#9/#11 (BLACKFORGE — pausadas), #10 (intérprete + SUPRA + Shadow), #12 (documentación continuidad). Ninguna está fusionada.

El tablero Kanban `astra` contiene **57 tarjetas**: 33 todo, 13 blocked, 10 done, 1 ready. Muchas tarjetas bloqueadas están en realidad **deferred/superseded** por el board de hitos producto-first.

**Hallazgo crítico:** El checkout local no está en `main` sino en una rama de trabajo con 23 commits no integrados. Cualquier trabajo futuro debe decidir si parte de `main` o de esta rama.

---

## 2. Alcance, Fuentes y Limitaciones

### Fuentes consultadas
- API GitHub (commits, PRs, branches, CI runs, tree, releases, tags)
- Git local (worktrees, branches, log, status, diff)
- Hermes Kanban CLI (board `astra`, 57 tarjetas)
- Informes locales en `docs/audit/` y `C:\ASTRA_WORK\`

### Limitaciones
- **NOT_EXECUTED:** No se lanzaron suites de pruebas, benchmarks ni modelos.
- **NOT_EXECUTED:** No se ejecutaron builds ni smoke tests.
- **NOT_ACCESSIBLE:** No se inspeccionaron worktrees de otros agentes (si existen fuera de `C:\ASTRA_WORK\`).
- **NOT_VERIFIED:** Las afirmaciones de informes históricos (CB-00, CB-VERIFICATION_SUMMARY, etc.) no se reproducen; se citan como `REPORTED_LOCAL`.
- **NOT_VERIFIED:** El estado de las PR #13, #14, #15 (citadas históricamente) no se verificó individualmente — no aparecen en la lista de abiertas, lo que sugiere que están cerradas o fusionadas.

---

## 3. SHA Actual de `main` y Evidencia CI

| Campo | Valor | Fuente |
|---|---|---|
| SHA `main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` | API GitHub |
| Mensaje | `Merge pull request #22 from Klsx-Moli/audit/fase0-fase1` | API GitHub |
| Fecha commit | 2026-10-13T20:49:46Z | API GitHub |
| Autor | Klsx-Moli (moliklsx@gmail.com) | API GitHub |
| CI run | #85, `Monorepo CI`, success | API GitHub |
| CI fecha | 2026-10-13T20:49:49Z → 20:53:31Z | API GitHub |
| CI URL | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/actions/runs/38465911526 | API GitHub |
| Releases | 0 | API GitHub |
| Tags | 0 | API GitHub |

### Commits recientes de `main` (últimos 10)
```
defd0fd Merge pull request #22 (Fase 0+1: parches de auditoría)
5472cfe test(local-llm): herramientas reproducibles de evaluacion vs banco CRIBA
a6da00c docs(audit): build Windows CribaShadow + barrido 16 GGUF
6bca989 test(golden): ratificar salida del generador tras auditoría
68419fd merge origin/main: resolver openai_compatible.py
a9d4605 fix(engine): tokenizado, dominio por palabra, genoma, base dinámica
33877fa ci: ruff de corrección + job Linux informativo
```

---

## 4. Estado Local, Ramas y Worktrees

### Checkout principal
| Campo | Valor |
|---|---|
| Ruta | `C:\ASTRA_WORK\Criba-Blackforge-Supra` |
| Rama | `hermes/cloud-provider-layer-20261013` |
| HEAD | `3f20e5c0f4bb909fdba07d23178d84bb841b203e` |
| Estado | Limpio (6 ficheros no rastreados) |
| Relación con main | Descendiente (23 commits ahead, 0 behind) |
| Diff vs main | 24 ficheros, +2604/-23 líneas |

### Worktrees identificados (9)

| # | Ruta | Rama | HEAD | Estado | Relación con main |
|---|---|---|---|---|---|
| 1 | `C:\ASTRA_WORK\Criba-Blackforge-Supra` | `hermes/cloud-provider-layer-20261013` | `3f20e5c` | Limpio | Ahead 23 |
| 2 | `C:\ASTRA_WORK\Criba-Blackforge-Supra-main-baseline` | `hermes/local-snapshot-20261009-main-baseline` | `b845aeb` | Limpio | Snapshot histórico |
| 3 | `C:\ASTRA_WORK\iso-deep-execution-20261005` | `hermes/deep-execution-20261005` | `2f534f9` | Limpio | Rama aislada |
| 4 | `C:\ASTRA_WORK\iso-dossier` | `hermes/local-snapshot-20261009-dossier` | `cfe60fa` | Limpio | Snapshot histórico |
| 5 | `C:\ASTRA_WORK\iso-main-4332ff1` | `hermes/mono03-supra-license` | `ca5bb59` | Limpio | Snapshot histórico |
| 6 | `C:\ASTRA_WORK\iso-pr8-safety` | `astra/blackforge-safety/dfca79-auth-state-failclosed` | `65a58e5` | Limpio | PR #8 head |
| 7 | `C:\ASTRA_WORK\iso-pr9-persistence` | `hermes/local-snapshot-20261009-pr9-persistence` | `5e9ee71` | Limpio | Snapshot histórico |
| 8 | `C:\ASTRA_WORK\iso-valida-17` | (detached HEAD) | `9a8af79` | Limpio | Snapshot histórico |
| 9 | `C:\ASTRA_WORK\kint04-cbs-worktree` | `k-int-04-cbs-docs` | `0c289fd` | Limpio | Ahead 4 de origin/main |

### Ficheros no rastreados en checkout principal
```
.aider.chat-history.md
.aider.input.history
.aider.tags.cache.v4/
e2e_recorrido/
scratch_shadow_test/
shadow_test_freemodels/
smoke_exe_test/
```

### Ramas remotas con trabajo potencialmente importante
- `astra/blackforge-dossier-20261005` — BLACKFORGE (HARD_PAUSE)
- `astra/blackforge-persistence/15bc23-durable-agentic-audit` — BLACKFORGE (HARD_PAUSE)
- `astra/blackforge-safety/dfca79-auth-state-failclosed` — BLACKFORGE (HARD_PAUSE)
- `astra/criba-core/22813e65-lottery-storage-integrity` — CRIBA tests
- `astra/criba-outcome/edd50814-aware-timestamps` — CRIBA tests
- `astra/supra-state/*` (4 ramas) — SUPRA tests
- `cb01-bank-provenance` — PR #21 head
- `codex/interpreter-hardening-20261004` — PR #10 head
- `hermes/cloud-provider-layer-20261013` — rama del checkout local
- `hermes/cbs-continuity-memory-20261005` — PR #12 head

---

## 5. Inventario del Kanban y de la Concurrencia

### Board `astra` (activo)
- **Total tarjetas:** 57
- **Por estado:** todo=33, blocked=13, done=10, ready=1
- **Por asignado:** default=21 (blocked=5, done=6, todo=10), unassigned=36
- **Running:** 0
- **Ready:** 1 (`t_d4cf1f1c` — P17 SHADOW GUI REDISEÑO)

### Board `default` (inactivo)
- Vacío

### Tarjetas done (10) — trabajo completado y preservado
| ID | Título | Evidencia |
|---|---|---|
| `t_00afbdfc` | ASTRA P1: acreditar diagnostico barrera multiproceso | done |
| `t_e54a766c` | ASTRA P0: persistir evidencia acreditacion sentinels | done |
| `t_98411b3c` | ASTRA P1: recorrido CRIBASUPRA end-to-end | done |
| `t_d032e66e` | ASTRA REVIEW: contrato identidad y demarca evidencia | done |
| `t_1a76292e` | SHADOW-00: Shadow UI no existe en monorepo (decisión) | done — ALREADY-DONE |
| `t_aeffc8b7` | K0 BASELINE-SYNC-GUARD | done |
| `t_027217a5` | K1 B03 RESTART / REPLAY / RETRY | done |
| `t_30299455` | K2 BLACKFORGE ISOLATION GATE | done |
| `t_9fc57da5` | P0 M1 SHADOW LAUNCHABLE | done |
| `t_84ce5ac2` | P1 M2 FIRST REAL VERTICAL SLICE | done |

### Tarjetas blocked (13) — diagnóstico
| ID | Título | Diagnóstico |
|---|---|---|
| `t_cb25d2f3` | ASTRA P0: inventariar cambios locales integridad | REVIEW_REQUIRED |
| `t_b703cc30` | MONO-01 Canonical repository identity | STALE — resuelto por integración |
| `t_11068e37` | MONO-03 SUPRA license integrity | BLOCKED_REAL — necesita decisión owner |
| `t_d7ed623a` | SCORING-01 Information theory single source of truth | REVIEW_REQUIRED |
| `t_6143a46a` | SHADOW-MIGRATE-01 verificacion integracion canonica | STALE — ALREADY-DONE |
| `t_2a1adba0` | K3 SHADOW CONTRACT READINESS | STALE — cubierto por integración |
| `t_1bbe9070` | K4 SHADOW-MIGRATE-01 / REAL WIRING | STALE — cubierto por M2 |
| `t_577da5bf` | K5 FIRST REAL VERTICAL SLICE | STALE — absorbido por M2 |
| `t_8f00aa4a` | K6 ROBUSTNESS / ERROR STATES | STALE — absorbido por M3 |
| `t_59c1475c` | K7 WINDOWS APPLICATION READINESS | STALE — absorbido por M4 |
| `t_2dcb8513` | K8 FINAL RECONCILIATION | STALE — absorbido por M5 |
| `t_30266103` | P7 M3 RESTART REPLAY E2E DESDE SHADOW | STALE — absorbido por M3 |
| `t_790aeb39` | P23 OPTIONAL CODING SCOUTS | BLOCKED_REAL — solo read-only |

### Tarjetas ready (1)
| ID | Título | Notas |
|---|---|---|
| `t_d4cf1f1c` | P17 SHADOW GUI REDISEÑO (referencias operador) | Sin asignar, edad 504967s (~5.8 días) |

### Configuración de concurrencia
- `kanban.max_in_progress`: no verificado en esta sesión
- `kanban.dispatch_in_gateway`: no verificado en esta sesión
- Escritores activos: 0 (running=0)

---

## 6. Matriz de PR y Commits No Integrados

### PR abiertas (6)

| PR | Título | Estado | Base | Head SHA | Commits | Archivos | Draft | Recomendación |
|---|---|---|---|---|---|---|---|---|
| #21 | CB-01: procedencia obligatoria en artefactos del banco | open | main | `0344089` | 1 | 3 | No | **INTEGRAR_CANDIDATA** — aditivo, bajo riesgo |
| #8 | BLACKFORGE: deny expired/denied authorization | open | main | `65a58e5` | 6 | 2 | Sí | **MANTENER_PAUSADA** — BLACKFORGE HARD_PAUSE |
| #9 | BLACKFORGE: make agentic audit persistence durable | open | main | `1a98b7e` | 17 | 6 | Sí | **MANTENER_PAUSADA** — BLACKFORGE HARD_PAUSE |
| #10 | Require causal interpreter proposals + preserve CRIBA–SUPRA diagnostics | open | main | `2dc0094` | 7 | 73 | Sí | **PORTAR_SELECTIVAMENTE** — grande, necesita revisión |
| #11 | BLACKFORGE v1: canonical DefensiveCase, execution broker | open | main | `15bc237` | 2 | 6 | Sí | **MANTENER_PAUSADA** — BLACKFORGE HARD_PAUSE |
| #12 | docs(continuity): paquete CBS y límites de evidencia | open | `codex/interpreter-hardening-20261004` | `8b1ba5b` | 4 | 12 | Sí | **CONSERVAR_PARA_DOCUMENTACIÓN** — solo docs |

### PR históricas no verificadas individualmente
- #13, #14, #15: No aparecen en la lista de abiertas. Estado **NOT_VERIFIED** (probablemente cerradas/fusionadas).

### Commits exclusivos del checkout local (rama `hermes/cloud-provider-layer-20261013`)
23 commits ahead de `origin/main`. Ficheros principales afectados:
- `.autoregen/cloud/modal_runner.py` (+211 líneas)
- `criba-blackforge/shadow_ui/shadow_window.py` (+9)
- `criba-blackforge/src/criba/cli.py` (+4/-1)
- `criba-blackforge/src/criba/interprete/seleccion.py` (+28/-1)
- `criba-blackforge/src/criba/ui/actions.py` (+30/-1)
- `supra/src/supra_agentic/cloud_provider_layer.py` (+442)
- `supra/tests/test_cloud_provider_layer.py` (+280)
- 5 scripts de smoke/diag en `supra/scripts/`
- 6 documentos en `docs/audit/`
- 5 ficheros de tests

---

## 7. Estado Técnico de CRIBA, Intérprete, SUPRA, Shadow UI y BLACKFORGE

### 7.1. CRIBA

**Motor y contratos en `main`:**
- Motor de interpretación con contratos de propuesta causal (PR #10 describe el contrato pero no está fusionado)
- Selección de modelos con seed fija y evidencia n3/control (commit `e908f15`)
- Tokenizado, dominio por palabra, genoma, base dinámica y dedup (commit `a9d4605`)
- CI: ruff de corrección + job Linux informativo (commit `33877fa`)

**Capacidades con tests:**
- Suite completa en `main` (tamaño exacto no verificado en esta sesión)
- Tests de golden output, banco-trace, persistencia SUPRA

**Capacidades solo describas (sin tests ejecutados en esta sesión):**
- D3/D4/D6/D8 — NOT_VERIFIED
- T001-T130 — NO_ENCONTRADO (según CB-VERIFICATION)

**Hallazgos abiertos:**
- PR #10 (6188 adiciones) no está fusionado — el contrato del intérprete sigue sin integrar
- PR #21 (procedencia) no está fusionado

### 7.2. Intérprete y Proveedores

**Contrato:** `docs/INTERPRETER_CONTRACT.md` existe en `main` (7224 bytes).

**Informe `CB-LOCAL-LLM-SWEEP_2026-10-13.md`:** Existe en `main` (3835 bytes). No se reprodujo su contenido en esta sesión.

**Distinción de estados del intérprete (según contrato):**
- Error HTTP / conexión
- Timeout
- Modelo inexistente / endpoint no disponible
- Salida truncada
- JSON / esquema inválido
- Abstención correcta
- Rechazo del banco
- Propuesta pertinente que cumple el contrato
- Interpretación completada
- Validación científica independiente

**NOT_EXECUTED:** No se verificó el informe de barrido 16 GGUF ni se reprodujo.

### 7.3. SUPRA y Persistencia

**Contratos y pruebas en `main`:**
- `supra/tests/test_state.py` (51905 bytes)
- `supra/tests/test_state_persistence_atomicity.py` (10707 bytes)
- `supra/tests/test_state_storage.py` (1418 bytes)
- `supra/tests/test_service.py` (26095 bytes)
- `supra/tests/test_service_hardening.py` (10305 bytes)
- `supra/tests/astra_canon/test_astra_persistence_encoding.py`

**Capacidades documentadas:**
- Recepción de dossiers
- Estados y procedencia
- Persistencia en disco (UTF-8 locale-independente, commit `6cd67f7`)
- Recuperación tras reinicio
- Backend no disponible (fail-closed)
- Aislamiento entre proyectos
- Concurrencia (file lock con `msvcrt`/`fcntl`)

**NOT_EXECUTED:** No se lanzaron suites de pruebas.

### 7.4. Shadow UI y Ejecutable Windows

**Entry point:** `criba-blackforge/shadow_ui/entrypoint.py` (en main)
**Launcher:** `criba-blackforge/criba_shadow_main.py` (raíz criba-blackforge, en main)
**Spec:** `criba-blackforge/CribaShadow.spec` (en main)

**Informe `CB-BUILD-WINDOWS_2026-10-13.md`:** Existe en `main` (2996 bytes). No se reprodujo.

**Estado:**
- Shadow UI está integrado y trackeado en el monorepo canónico (29 ficheros)
- Suite verde reportada históricamente: 1832 passed (base `4332ff1`)
- Aceptación visual humana: **NO ACREDITADO** (solo pruebas automatizadas/offscreen)
- Distribución instalada en entorno limpio: **NOT_VERIFIED**

### 7.5. BLACKFORGE

**Estado:** `HARD_PAUSE` confirmado.

**PRs abiertas:** #8, #9, #11 — todas draft, todas pausadas.

**Dependencias que podrían impedir CRIBA + SUPRA independientes:**
- K2 (BLACKFORGE ISOLATION GATE) está done — verificó que BLACKFORGE no es dependencia
- Shadow UI no requiere BLACKFORGE para arrancar (verificado en K3)
- No se identificaron dependencias operativas de BLACKFORGE en CRIBA/SUPRA

---

## 8. Matriz de Evidencia por Capacidad

| Capacidad | Código presente | Test existente | Test ejecutado | CI verde | Build creado | E2E verificado | Aceptación humana | Proveedor real | Distribución | Validación científica |
|---|---|---|---|---|---|---|---|---|---|---|
| CRIBA core | SÍ (main) | SÍ | NOT_EXECUTED | SÍ (run #85) | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_VERIFIED |
| Intérprete | SÍ (main) | SÍ | NOT_EXECUTED | SÍ | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_VERIFIED |
| SUPRA persistencia | SÍ (main) | SÍ | NOT_EXECUTED | SÍ | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_VERIFIED |
| Shadow UI | SÍ (main) | SÍ | NOT_EXECUTED | SÍ | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | N/A | NOT_EXECUTED | N/A |
| BLACKFORGE | SÍ (main) | SÍ | NOT_EXECUTED | SÍ | N/A | N/A | N/A | N/A | N/A | N/A |
| Cloud provider layer | SÍ (rama local) | SÍ (rama local) | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_VERIFIED |
| Windows EXE | SÍ (spec) | SÍ (smoke) | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | NOT_EXECUTED | N/A | NOT_EXECUTED | N/A |

---

## 9. Contradicciones y Datos No Accesibles

### Contradicciones
1. **Checkout local vs main:** El checkout activo está 23 commits por delante de `main` en una rama de trabajo. Los informes históricos (CB-00, CB-VERIFICATION) se refieren a SHAs anteriores. No son contradicciones directas, pero los datos históricos no reflejan el estado actual del checkout.

2. **PR #10 descripción vs tamaño:** La PR #10 reporta "1698 passed, 3 skipped" para CRIBA y "298 passed" para SUPRA, pero estos son resultados históricos no reproducidos en esta sesión.

3. **Kanban blocked vs realidad:** 13 tarjetas blocked, pero al menos 7 están en realidad deferred/superseded por el board producto-first. No son bloqueos reales.

### Datos no accesibles
- Worktrees de otros agentes fuera de `C:\ASTRA_WORK\`
- Contenido completo de informes históricos (no se reprodujeron)
- Estado de PR #13, #14, #15 (no verificadas individualmente)
- Configuración de concurrencia de Hermes (`max_in_progress`, `dispatch_in_gateway`)

---

## 10. Inventario de Trabajo Pendiente

### P0 — Riesgo de pérdida de trabajo, integridad o base fiable
| ID propuesto | Problema | Evidencia | Estado | Dependencias | Archivos afectados | Cambio mínimo | Pruebas necesarias | Criterio aceptación | Riesgo | Esfuerzo | Bloqueos | Condición DONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F02-P0-01 | Checkout local en rama de trabajo, no en main | 23 commits ahead, 24 ficheros | Activo | Ninguno | Todos los ficheros del diff | Decidir: integrar a main o crear rama desde main | git diff --check, suite completa | Decisión documentada y ejecutada | Bajo | 1-2h | Ninguno | Decisión tomada y ejecutada |
| F02-P0-02 | PR #10 no fusionado (6188 adiciones) | PR #10 open, 73 ficheros | Abierto | F02-P0-01 | criba-blackforge/src/, supra/src/ | Revisar y fusionar selectivamente | Suite completa + mypy + ruff | CI verde post-merge | Medio | 4-8h | Ninguno | PR fusionado con CI verde |

### P1 — Bloqueos del recorrido funcional CRIBA + Shadow + SUPRA
| ID propuesto | Problema | Evidencia | Estado | Dependencias | Archivos afectados | Cambio mínimo | Pruebas necesarias | Criterio aceptación | Riesgo | Esfuerzo | Bloqueos | Condición DONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F03-P1-01 | Aceptación visual humana de Shadow UI no acreditada | Solo pruebas offscreen | Pendiente | F02-P0-01 | Ninguno (verificación) | Abrir Shadow UI en Windows y verificar visualmente | Recorrido manual por operador | Operador confirma que la UI es usable | Bajo | 1-2h | Ninguno | Aceptación documentada |
| F03-P1-02 | E2E desde Shadow no verificado en main actual | K5 absorbido por M2, no re-ejecutado | Pendiente | F02-P0-01 | tests/integration/ | Ejecutar suite E2E | test_m2_vertical_slice_e2e.py | 20 passed | Bajo | 2-4h | Ninguno | Suite E2E verde |

### P2 — Empaquetado, instalación, documentación y distribución
| ID propuesto | Problema | Evidencia | Estado | Dependencias | Archivos afectados | Cambio mínimo | Pruebas necesarias | Criterio aceptación | Riesgo | Esfuerzo | Bloqueos | Condición DONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F04-P2-01 | Windows EXE no verificado en entorno limpio | CB-BUILD-WINDOWS no reproducido | Pendiente | F03-P1-01 | CribaShadow.spec | Build + smoke test en entorno limpio | Smoke test + journey E2E | EXE arranca y completa journey | Medio | 4-8h | Ninguno | EXE verificado |
| F04-P2-02 | PR #21 (procedencia) no fusionado | PR #21 open, 1 commit, 3 ficheros | Abierto | F02-P0-01 | verification/_provenance.py | Revisar y fusionar | 12 tests | CI verde post-merge | Bajo | 1-2h | Ninguno | PR fusionado |

### P3 — Mejora de calidad, rendimiento o usabilidad
| ID propuesto | Problema | Evidencia | Estado | Dependencias | Archivos afectados | Cambio mínimo | Pruebas necesarias | Criterio aceptación | Riesgo | Esfuerzo | Bloqueos | Condición DONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F05-P3-01 | 33 tarjetas todo sin asignar | Kanban astra | Pendiente | Ninguno | Ninguno | Asignar y priorizar | N/A | Todas las tarjetas tienen asignado | Bajo | 2-4h | Ninguno | Board actualizado |

### RESEARCH — Investigación científica
| ID propuesto | Problema | Evidencia | Estado | Dependencias | Archivos afectados | Cambio mínimo | Pruebas necesarias | Criterio aceptación | Riesgo | Esfuerzo | Bloqueos | Condición DONE |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F06-R-01 | Validación científica independiente de novedad/causalidad | D3/D4/D6/D8 NOT_VERIFIED | Pendiente | F03-P1-01 | N/A | Experimento controlado | Evaluación independiente | Resultados publicados | Alto | 40h+ | Recursos | Validación completa |

---

## 11. Propuesta de Dependencias y Prioridades

```
F02-P0-01 (decisión base)
  ├── F02-P0-02 (PR #10)
  │     ├── F03-P1-01 (aceptación visual)
  │     │     ├── F03-P1-02 (E2E)
  │     │     │     ├── F04-P2-01 (EXE)
  │     │     │     │     └── F04-P2-02 (PR #21)
  │     │     │     │           └── F05-P3-01 (board)
  │     │     │     │                 └── F06-R-01 (research)
```

---

## 12. Ruta Rápida del MVP

1. **F02-P0-01:** Decidir base de trabajo (main vs rama local)
2. **F02-P0-02:** Fusionar PR #10 selectivamente
3. **F03-P1-01:** Aceptación visual humana de Shadow UI
4. **F03-P1-02:** Verificar E2E desde Shadow

**Total estimado:** 8-16 horas

---

## 13. Ruta de Versión Distribuible

1. Ruta rápida del MVP
2. **F04-P2-01:** Build y verificación del EXE en entorno limpio
3. **F04-P2-02:** Fusionar PR #21 (procedencia)
4. **F05-P3-01:** Actualizar Kanban
5. **F06-R-01:** Validación científica (puede continuar post-MVP)

**Total estimado:** 16-32 horas (sin research)

---

## 14. Riesgos Principales

1. **Pérdida de trabajo:** 23 commits en rama local no integrados a main. Si se pierde el checkout, se pierde el trabajo.
2. **Duplicación:** Las tarjetas blocked del Kanban que están en realidad deferred podrían re-trabajarse.
3. **Regresión:** Fusionar PR #10 (6188 adiciones) sin verificación completa podría romper contratos.
4. **Aceptación falsa:** Declarar el producto terminado sin aceptación visual humana ni E2E verificado.

---

## 15. Lista Explícita de Acciones NO Ejecutadas

- NO se modificó código, tests, configuraciones ni documentación
- NO se hicieron commits, merges, cherry-picks, rebase, reset, revert, stash ni force-push
- NO se ejecutaron `git pull`, `git fetch` ni operaciones que actualicen referencias
- NO se crearon ramas, worktrees, entornos virtuales, builds ni ejecutables
- NO se lanzaron suites de pruebas, benchmarks ni modelos
- NO se iniciaron, cancelaron ni reconfiguraron otros trabajos de Hermes
- NO se cambió la configuración global de Hermes
- NO se eliminaron archivos, artefactos, cachés ni informes
- NO se publicaron comentarios, PRs ni se modificaron estados
- NO se mostraron secretos, claves, tokens ni credenciales

---

## 16. Criterios de Aceptación de F01

- [x] SHA de `main` verificado y documentado
- [x] Estado CI verificado
- [x] Estado local, ramas y worktrees documentados
- [x] Inventario del Kanban completo
- [x] Matriz de PR y commits no integrados
- [x] Estado técnico de CRIBA, intérprete, SUPRA, Shadow UI y BLACKFORGE
- [x] Matriz de evidencia por capacidad
- [x] Contradicciones y datos no accesibles documentados
- [x] Inventario de trabajo pendiente con prioridades
- [x] Propuesta de dependencias y prioridades
- [x] Ruta rápida del MVP
- [x] Ruta de versión distribuible
- [x] Riesgos principales identificados
- [x] Lista de acciones NO ejecutadas
- [x] Fuentes con URLs, SHA y fechas

---

## 17. Fuentes con URLs, SHA y Fechas

| Fuente | URL | SHA | Fecha |
|---|---|---|---|
| GitHub main commit | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/commit/defd0fd9955c5aaf3f7ff8b23fdf016639ed062b | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` | 2026-10-13 |
| CI run #85 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/actions/runs/38465911526 | `defd0fd` | 2026-10-13 |
| PR #21 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/21 | `0344089` | 2026-10-11 |
| PR #8 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/8 | `65a58e5` | 2026-10-01 |
| PR #9 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/9 | `1a98b7e` | 2026-10-01 |
| PR #10 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/10 | `2dc0094` | 2026-10-05 |
| PR #11 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/11 | `15bc237` | 2026-10-05 |
| PR #12 | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/pull/12 | `8b1ba5b` | 2026-10-05 |
| CB-00 Inventario | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/blob/main/docs/audit/CB-00_INVENTARIO_HERMES_2026-10-11.md | — | 2026-10-11 |
| CB-BUILD-WINDOWS | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/blob/main/docs/audit/CB-BUILD-WINDOWS_2026-10-13.md | — | 2026-10-13 |
| CB-LOCAL-LLM-SWEEP | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/blob/main/docs/audit/CB-LOCAL-LLM-SWEEP_2026-10-13.md | — | 2026-10-13 |
| INTERPRETER_CONTRACT | https://github.com/Klsx-Moli/Criba-Blackforge-Supra/blob/main/docs/INTERPRETER_CONTRACT.md | — | — |
| Local checkout | `C:\ASTRA_WORK\Criba-Blackforge-Supra` | `3f20e5c` | 2026-10-16 |

---

## 18. Fecha y Hora de la Auditoría

**Fecha:** 2026-10-16  
**Zona horaria:** UTC+2 (hora de verano romance)  
**Hora aproximada:** 23:15 (hora local)
