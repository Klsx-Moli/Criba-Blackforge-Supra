# F02 — Preservación Forense y Preparación de Base Segura de Integración

**Fecha:** 2026-10-16 (hora local UTC+2)  
**Tipo:** Preservación de solo lectura + preparación de integración  
**Repositorio:** `Klsx-Moli/Criba-Blackforge-Supra`  
**Rama local:** `hermes/cloud-provider-layer-20261013`  
**Base main:** `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b`  

---

## 1. Estado Actual Verificado de Rama, SHA y Working Tree

| Campo | Valor | Etiqueta |
|---|---|---|
| Ruta real | `C:/ASTRA_WORK/Criba-Blackforge-Supra` | FACT |
| Rama activa | `hermes/cloud-provider-layer-20261013` | FACT |
| SHA HEAD | `3f20e5c0f4bb909fdba07d23178d84bb841b203e` | FACT |
| SHA origin/main | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` | FACT |
| Ahead/Behind | 23 ahead, 0 behind | FACT |
| Staged changes | Ninguno | FACT |
| Unstaged changes | Ninguno | FACT |
| Untracked files | 11 (ver sección 2) | FACT |
| Submódulos | No existen | FACT |
| Git LFS | No existe | FACT |
| Stashes | Ninguno | FACT |
| Worktrees | 9 (todos contabilizados) | FACT |

**VERIFIED_BY_EXECUTION:** `git rev-parse HEAD` → `3f20e5c0f4bb909fdba07d23178d84bb841b203e`  
**VERIFIED_BY_EXECUTION:** `git rev-list --left-right --count origin/main...HEAD` → `0 23`

---

## 2. Inventario de Commits y Cambios Sin Commit

### 2.1. Commits exclusivos de la rama local (23)

| # | SHA | Mensaje | Archivos | Clasificación |
|---|---|---|---|---|
| 1 | `bd530b3` | feat(supra): capa opcional de proveedores en la nube (flag OFF) | `supra/src/supra_agentic/cloud_provider_layer.py`, `supra/tests/test_cloud_provider_layer.py` | **Necesaria para MVP** — capa cloud provider |
| 2 | `156f1a4` | fix(cloud-layer): clasificar 404 por credito/saldo como auth_required | `supra/src/supra_agentic/cloud_provider_layer.py`, `supra/tests/test_cloud_provider_layer.py`, 2 scripts | **Necesaria para MVP** — fix auth |
| 3 | `d89e0c1` | scripts: comparativa catalogos free + prueba esfuerzo none | `supra/scripts/catalog_compare_20261013.py`, `supra/scripts/probe_reasoning_none_20261013.py` | **Documentación/evidencia** — scripts de diagnóstico |
| 4 | `09ce339` | scripts: smoke camino feliz con upstage/solar-mini4:free | `supra/scripts/smoke_cloud_provider_solar_20261013.py` | **Documentación/evidencia** — script smoke |
| 5 | `cc3b97d` | docs(audit): F0 linea base | `docs/audit/BASELINE.md` | **Documentación** |
| 6 | `57f0ae7` | test(criba): aislar storage y arreglar espera Qt cross-thread | `criba-blackforge/tests/unit/test_gui_inventar.py`, `criba-blackforge/tests/unit/test_hybrid.py` | **Necesaria para MVP** — fix tests |
| 7 | `4e47ea7` | chore(g1): retirar opcion --llm nebius (muerta) de la CLI | `criba-blackforge/src/criba/cli.py`, `docs/audit/CLEANUP_REPORT.md` | **Necesaria para MVP** — limpieza CLI |
| 8 | `72a2155` | feat(modal): runner minimo de verificacion en la nube | `.autoregen/cloud/modal_runner.py` | **Experimental** — runner cloud |
| 9 | `e735f10` | docs: HANDOFF checkpoint | `docs/audit/HANDOFF.md` | **Documentación** |
| 10 | `106b546` | fix(modal): añadir types-PyYAML a la imagen del runner | `.autoregen/cloud/modal_runner.py`, `docs/audit/HANDOFF.md` | **Experimental** — fix runner |
| 11 | `eb24690` | test(modal): gate Linux NO verde; runner robusto + informe 25 fallos | `.autoregen/cloud/modal_runner.py`, `docs/audit/HANDOFF.md`, `docs/audit/MODAL_LINUX_GATE_REPORT.json`, `docs/audit/MODAL_LINUX_GATE_REPORT.md` | **Experimental** — gate Linux |
| 12 | `5d1cabd` | docs(audit): verificacion board — premisa shadow_ui caducada | `docs/audit/HANDOFF.md` | **Documentación** |
| 13 | `faed270` | docs(audit): reconciliar HANDOFF; cierre SHADOW-00 | `docs/audit/HANDOFF.md` | **Documentación** |
| 14 | `cc5fae8` | docs(audit): fijar COMMIT_DOCUMENTAL_FINAL=faed270 | `docs/audit/HANDOFF.md` | **Documentación** |
| 15 | `4e93e3f` | docs(audit): HEAD publicado cc5fae8 | `docs/audit/HANDOFF.md` | **Documentación** |
| 16 | `4a290d5` | test(shadow): probe arranque K3 — ShadowWindow sin BLACKFORGE | `criba-blackforge/shadow_ui/_k3_launch_probe.py` | **Necesaria para MVP** — probe arranque |
| 17 | `4f2c8c1` | docs(audit): evidencia K3/MIGRATE ejecutada | `docs/audit/HANDOFF.md` | **Documentación** |
| 18 | `f05de79` | docs(audit): STATE.md canonico + kanban integracion | `docs/architecture/KANBAN_INTEGRACION_RAMAS_20261014.md`, `docs/audit/STATE.md` | **Documentación** |
| 19 | `0394e87` | docs(audit): STATE.md sec.9 campana 01:20 + H-CAMP-04 | `docs/audit/STATE.md` | **Documentación** |
| 20 | `61c8c09` | docs(arch): kanban + H-CAMP-04 (6 ramas astra/* no integrar) | `docs/architecture/KANBAN_INTEGRACION_RAMAS_20261014.md` | **Documentación** |
| 21 | `c4df938` | docs(arch): kanban sin trailing whitespace | `docs/architecture/KANBAN_INTEGRACION_RAMAS_20261014.md` | **Documentación** |
| 22 | `dc86b65` | feat(shadow-ui): selector de modelos gratuitos del proxy Hermes | `criba-blackforge/shadow_ui/shadow_window.py`, `criba-blackforge/src/criba/interprete/seleccion.py`, `criba-blackforge/src/criba/ui/actions.py`, 2 tests | **Necesaria para MVP** — UI selector modelos |
| 23 | `3f20e5c` | docs(kanban): cierre K-FUNC-01/02/03 con evidencia real | `docs/architecture/KANBAN_INTEGRACION_RAMAS_20261014.md` | **Documentación** |

### 2.2. Archivos modificados (24 ficheros, +2604/-23)

| Archivo | Status | Líneas | Clasificación |
|---|---|---|---|
| `.autoregen/cloud/modal_runner.py` | A | +211 | Experimental (runner cloud) |
| `criba-blackforge/shadow_ui/_k3_launch_probe.py` | A | +34 | Necesaria (probe arranque) |
| `criba-blackforge/shadow_ui/shadow_window.py` | M | +9 | Necesaria (selector modelos) |
| `criba-blackforge/src/criba/cli.py` | M | +4/-1 | Necesaria (limpieza CLI) |
| `criba-blackforge/src/criba/interprete/seleccion.py` | M | +28/-1 | Necesaria (selector modelos) |
| `criba-blackforge/src/criba/ui/actions.py` | M | +30/-1 | Necesaria (selector modelos) |
| `criba-blackforge/tests/unit/test_gui_inventar.py` | M | +56/-1 | Necesaria (fix tests) |
| `criba-blackforge/tests/unit/test_hybrid.py` | M | +22 | Necesaria (fix tests) |
| `criba-blackforge/tests/unit/test_interpreter_selector_startup.py` | M | +8/-1 | Necesaria (selector modelos) |
| `criba-blackforge/tests/unit/test_shadow_interpreter_journey.py` | M | +27/-1 | Necesaria (selector modelos) |
| `docs/architecture/KANBAN_INTEGRACION_RAMAS_20261014.md` | A | +326 | Documentación |
| `docs/audit/BASELINE.md` | A | +100 | Documentación |
| `docs/audit/CLEANUP_REPORT.md` | A | +49 | Documentación |
| `docs/audit/HANDOFF.md` | A | +144 | Documentación |
| `docs/audit/MODAL_LINUX_GATE_REPORT.json` | A | +81 | Evidencia experimental |
| `docs/audit/MODAL_LINUX_GATE_REPORT.md` | A | +68 | Evidencia experimental |
| `docs/audit/STATE.md` | A | +160 | Documentación |
| `supra/scripts/catalog_compare_20261013.py` | A | +114 | Evidencia (script diagnóstico) |
| `supra/scripts/diag_mistral_nemo_20261013.py` | A | +39 | Evidencia (script diagnóstico) |
| `supra/scripts/probe_reasoning_none_20261013.py` | A | +75 | Evidencia (script diagnóstico) |
| `supra/scripts/smoke_cloud_provider_20261013.py` | A | +162 | Evidencia (script smoke) |
| `supra/scripts/smoke_cloud_provider_solar_20261013.py` | A | +158 | Evidencia (script smoke) |
| `supra/src/supra_agentic/cloud_provider_layer.py` | A | +442 | Necesaria (cloud provider) |
| `supra/tests/test_cloud_provider_layer.py` | A | +280 | Necesaria (cloud provider tests) |

### 2.3. Ficheros no versionados (11)

| Fichero | Tamaño | ¿Relevante? | Etiqueta |
|---|---|---|---|
| `.aider.chat.history.md` | 8387 bytes | No (cache aider) | FACT |
| `.aider.input.history` | 591 bytes | No (cache aider) | FACT |
| `.aider.tags.cache.v4/cache.db-shm` | 32768 bytes | No (cache aider) | FACT |
| `.aider.tags.cache.v4/cache.db-wal` | 4148872 bytes | No (cache aider) | FACT |
| `docs/audit/F01_INVENTARIO...md` | 25012 bytes | **Sí** (informe F01) | FACT |
| `e2e_recorrido/` | ~57KB | **Sí** (evidencia E2E) | FACT |
| `scratch_shadow_test/` | ~58KB | **Sí** (evidencia smoke) | FACT |
| `shadow_test_freemodels/` | ~57KB | **Sí** (evidencia smoke) | FACT |
| `smoke_exe_test/` | ~57KB | **Sí** (evidencia smoke) | FACT |

---

## 3. Ubicación de la Copia de Seguridad y Pruebas de Integridad

### 3.1. Copias creadas

| Copia | Ruta | Tamaño | Estado |
|---|---|---|---|
| Git bundle (todas las ramas) | `C:/ASTRA_WORK/BACKUPS_F02/rama-local-3f20e5c.bundle` | 14,154,265 bytes | VERIFICADO |
| Tar (ficheros no versionados) | `C:/ASTRA_WORK/BACKUPS_F02/untracked-relevantes-3f20e5c.tar.gz` | 17,030 bytes | VERIFICADO |
| Patch (diff vs main) | `C:/ASTRA_WORK/BACKUPS_F02/diff-rama-local-vs-main.patch` | 135,074 bytes | VERIFICADO |

### 3.2. Pruebas de integridad realizadas

**VERIFIED_BY_EXECUTION:** `git bundle verify` → "The bundle records a complete history. The bundle uses this hash algorithm: sha1" — 75 refs, incluye HEAD `3f20e5c` y main `defd0fd`.

**VERIFIED_BY_EXECUTION:** `tar -tzf` → Lista 30+ ficheros, incluye `.aider.chat.history.md`, `docs/audit/F01_INVENTARIO...md`, `e2e_recorrido/`, `scratch_shadow_test/`, `shadow_test_freemodels/`, `smoke_exe_test/`.

### 3.3. Elementos cuya recuperación se ha verificado

- [x] Los 23 commits de la rama local (en el bundle)
- [x] Todas las ramas del repositorio (75 refs en el bundle)
- [x] Los ficheros no versionados relevantes (en el tar)
- [x] El diff completo vs main (en el patch)

### 3.4. Elementos que siguen sin verificar

- [ ] Recuperación del bundle en un directorio limpio (no ejecutado — requeriría crear un clon de prueba)
- [ ] Recuperación del tar en un directorio limpio (no ejecutado)
- [ ] Los ficheros de cache de `.aider.tags.cache.v4/` (4MB) no se incluyeron en el tar por ser cache no relevante

---

## 4. Diferencias Entre `main` y la Rama Local

### 4.1. Resumen

| Métrica | Valor |
|---|---|
| Commits de diferencia | 23 |
| Ficheros modificados | 24 |
| Líneas añadidas | +2604 |
| Líneas eliminadas | -23 |
| Ficheros añadidos (nuevos) | 18 |
| Ficheros modificados | 6 |

### 4.2. Diferencias por componente

| Componente | Ficheros | Líneas | Impacto MVP |
|---|---|---|---|
| `criba-blackforge/shadow_ui/` | 2 | +43 | **ALTO** — selector modelos, probe arranque |
| `criba-blackforge/src/criba/` | 3 | +61/-3 | **ALTO** — CLI, selector, actions |
| `criba-blackforge/tests/` | 4 | +113/-3 | **ALTO** — tests actualizados |
| `supra/src/` | 1 | +442 | **ALTO** — cloud provider layer |
| `supra/tests/` | 1 | +280 | **ALTO** — cloud provider tests |
| `supra/scripts/` | 5 | +548 | **MEDIO** — scripts diagnóstico/smoke |
| `.autoregen/cloud/` | 1 | +211 | **BAJO** — runner cloud experimental |
| `docs/` | 8 | +1076 | **BAJO** — documentación |

### 4.3. Contratos afectados

| Contrato | ¿Modificado? | Commit(s) | Riesgo |
|---|---|---|---|
| CLI (`criba/cli.py`) | Sí | `4e47ea7` | Bajo — retirar opción muerta |
| Selector interprete (`interprete/seleccion.py`) | Sí | `dc86b65` | Medio — nueva funcionalidad |
| UI actions (`ui/actions.py`) | Sí | `dc86b65` | Medio — wiring selector |
| Cloud provider (`supra_agentic/cloud_provider_layer.py`) | Sí | `bd530b3`, `156f1a4` | Medio — capa nueva |
| Shadow window (`shadow_ui/shadow_window.py`) | Sí | `dc86b65` | Medio — selector modelos |
| Tests GUI (`test_gui_inventar.py`, `test_hybrid.py`) | Sí | `57f0ae7` | Bajo — fix tests |

---

## 5. Riesgos, Dependencias y Conflictos

### 5.1. Riesgos

| Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|
| Pérdida de la rama local | ALTO | Baja | Bundle verificado en `BACKUPS_F02` |
| Conflicto al integrar `dc86b65` (selector modelos) con PR #10 | MEDIO | Media | Revisar antes de integrar |
| Conflicto al integrar `57f0ae7` (fix tests) con PR #10 | MEDIO | Media | Revisar antes de integrar |
| El runner cloud (`.autoregen/`) no es necesario para MVP | BAJO | N/A | Integrar después o no integrar |
| Los scripts de diagnóstico son evidencia, no código funcional | BAJO | N/A | Integrar como documentación |

### 5.2. Dependencias entre commits

```
bd530b3 (cloud provider) ← 156f1a4 (fix auth) ← d89e0c1 (scripts diag) ← 09ce339 (script smoke)
                                                                      ↓
57f0ae7 (fix tests) ← 4e47ea7 (cli cleanup) ← cc3b97d (baseline docs)
                                                                      ↓
dc86b65 (selector modelos) ← 4a290d5 (probe arranque)
                                                                      ↓
72a2155 (runner cloud) ← 106b546 (fix runner) ← eb24690 (gate Linux)
```

### 5.3. Conflictos previsibles con PR #10

| Archivo | Conflicto probable | Razón |
|---|---|---|
| `criba-blackforge/src/criba/interprete/seleccion.py` | **SÍ** — PR #10 modifica el selector | Ambos tocan la selección de modelos |
| `criba-blackforge/src/criba/ui/actions.py` | **SÍ** — PR #10 modifica actions | Ambos tocan las acciones de UI |
| `criba-blackforge/tests/unit/test_shadow_interpreter_journey.py` | **SÍ** — PR #10 modifica tests | Ambos tocan tests del journey |
| `criba-blackforge/shadow_ui/shadow_window.py` | **POSIBLE** — PR #10 puede tocar shadow_window | Ambos tocan la ventana Shadow |

---

## 6. Propuesta de Integración Selectiva por Orden de Prioridad

### Grupo 1 — Necesarias para MVP (integración prioritaria)

| Orden | Commit | Descripción | Archivos | Dependencias | Criterio de aceptación |
|---|---|---|---|---|---|
| 1 | `bd530b3` | Capa cloud provider (flag OFF) | `supra/src/.../cloud_provider_layer.py`, `supra/tests/.../test_cloud_provider_layer.py` | Ninguna | Tests del cloud provider pasan |
| 2 | `156f1a4` | Fix auth 404 en cloud provider | `supra/src/.../cloud_provider_layer.py`, 2 scripts | #1 | Tests auth pasan |
| 3 | `57f0ae7` | Fix tests GUI (storage + Qt cross-thread) | `criba-blackforge/tests/unit/test_gui_inventar.py`, `test_hybrid.py` | Ninguna | Tests GUI pasan |
| 4 | `4e47ea7` | Retirar opción --llm nebius muerta | `criba-blackforge/src/criba/cli.py` | Ninguna | CLI arranca sin la opción |
| 5 | `4a290d5` | Probe arranque K3 (ShadowWindow sin BLACKFORGE) | `criba-blackforge/shadow_ui/_k3_launch_probe.py` | Ninguna | Probe arranca |
| 6 | `dc86b65` | Selector modelos gratuitos proxy Hermes | `shadow_window.py`, `seleccion.py`, `actions.py`, 2 tests | #3, #4 | Tests selector pasan |

### Grupo 2 — Documentación y evidencia (integración secundaria)

| Orden | Commit | Descripción | Criterio de aceptación |
|---|---|---|---|
| 7 | `cc3b97d` | F0 línea base | Documento presente |
| 8 | `f05de79` | STATE.md canónico + kanban integración | Documento presente |
| 9 | `0394e87` | STATE.md sec.9 | Documento presente |
| 10 | `61c8c09` | Kanban + H-CAMP-04 | Documento presente |
| 11 | `c4df938` | Kanban sin trailing whitespace | `git diff --check` limpio |
| 12 | `3f20e5c` | Cierre K-FUNC-01/02/03 | Documento presente |
| 13 | `4f2c8c1` | Evidencia K3/MIGRATE | Documento presente |
| 14 | `faed270` | Reconciliar HANDOFF | Documento presente |
| 15 | `cc5fae8` | Fijar COMMIT_DOCUMENTAL_FINAL | Documento presente |
| 16 | `4e93e3f` | HEAD publicado cc5fae8 | Documento presente |
| 17 | `5d1cabd` | Verificacion board | Documento presente |
| 18 | `e735f10` | HANDOFF checkpoint | Documento presente |

### Grupo 3 — Evidencia experimental (integración opcional)

| Orden | Commit | Descripción | Criterio de aceptación |
|---|---|---|---|
| 19 | `d89e0c1` | Scripts comparativa catalogos | Scripts presentes |
| 20 | `09ce339` | Script smoke solar | Script presente |
| 21 | `72a2155` | Runner cloud mínimo | Runner presente |
| 22 | `106b546` | Fix types-PyYAML runner | Fix presente |
| 23 | `eb24690` | Gate Linux NO verde + informe | Informe presente |

### Grupo 4 — No integrar (mantener en rama local)

| Commit | Razón |
|---|---| Ninguno — todos los commits son integrables |

---

## 7. Preparación de Integración Aislada (Fase D)

### 7.1. Worktree de integración

**No existe un worktree de integración seguro preexistente.** Los 9 worktrees existentes son:
- 1 checkout principal (rama local)
- 8 worktrees aislados (snapshots históricos y ramas de auditoría)

**Propuesta para crear worktree de integración:**

```bash
# Desde el checkout principal (NO ejecutar sin autorización)
git worktree add C:/ASTRA_WORK/integracion-f02 -b integracion/f02 origin/main
```

Este worktree:
- Se basa en `origin/main` (`defd0fd`) verificado
- No interfiere con el checkout principal ni con otros worktrees
- Permite integrar selectivamente los commits de la rama local
- Puede eliminarse después de la integración

### 7.2. Procedimiento de integración propuesto

1. Crear worktree de integración desde `origin/main`
2. Integrar Grupo 1 (commits necesarios para MVP) en orden
3. Ejecutar tests después de cada commit
4. Integrar Grupo 2 (documentación)
5. Integrar Grupo 3 (evidencia experimental)
6. Verificar CI verde
7. Proponer merge a main (requiere autorización del usuario)

---

## 8. Acciones NO Ejecutadas

- NO se modificó código, tests, configuraciones ni documentación
- NO se hicieron commits, merges, cherry-picks, rebase, reset, revert, stash ni force-push
- NO se ejecutaron `git pull`, `git fetch` ni operaciones que actualicen referencias
- NO se crearon ramas, worktrees ni entornos virtuales
- NO se lanzaron suites de pruebas, benchmarks ni modelos
- NO se iniciaron, cancelaron ni reconfiguraron otros trabajos de Hermes
- NO se cambió la configuración global de Hermes
- NO se eliminaron archivos, artefactos, cachés ni informes
- NO se publicaron comentarios, PRs ni se modificaron estados
- NO se mostraron secretos, claves, tokens ni credenciales
- NO se creó el worktree de integración (requiere autorización)

---

## 9. Decisiones que Requieren Autorización del Usuario

1. **¿Crear el worktree de integración en `C:/ASTRA_WORK/integracion-f02`?** — Necesario para ejecutar la integración selectiva sin modificar el checkout original.

2. **¿Integrar los 6 commits del Grupo 1 (necesarios para MVP) en el worktree de integración?** — Esto es el primer paso de F03, no de F02. F02 solo prepara la base.

3. **¿Los scripts de diagnóstico del Grupo 3 se integran o se mantienen solo en la rama local?** — Son evidencia, no código funcional. No bloquea el MVP.

---

## 10. Criterios de Aceptación de F02

- [x] Estado actual verificado (rama, SHA, working tree)
- [x] Inventario de commits y cambios sin commit completo
- [x] Copia de seguridad creada y verificada
- [x] Diferencias entre main y rama local documentadas
- [x] Riesgos, dependencias y conflictos identificados
- [x] Propuesta de integración selectiva por orden de prioridad
- [x] Acciones no ejecutadas documentadas
- [x] Decisiones que requieren autorización identificadas

---

## 11. Fecha y Hora

**Fecha:** 2026-10-16  
**Zona horaria:** UTC+2 (hora de verano romance)  
**Hora aproximada:** 23:55 (hora local)
