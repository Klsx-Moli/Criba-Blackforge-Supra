# CBS SPRINT LOCAL — INFORME ÚNICO

**Fecha:** 2026-10-22 · **Checkpoint de entrada:** `docs/audits/PREPLAN_CHECKPOINT.md`
**Estado de cierre:** `CBS_LOCAL_SPRINT_PARTIAL` (ver §12)

Vocabulario: `OBSERVED` (esta sesión), `STATIC_INSPECTION`, `PREVIOUS_REPORT`, `INFERENCE`, `NOT_VERIFIED`.

---

## 1. Baseline y delta

| Campo | Valor |
|---|---|
| Repo | `C:\ASTRA_WORK\Criba-Blackforge-Supra` |
| Rama | `reconcile/candidate-fix-20261020` |
| HEAD | `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` |
| `main` / `origin/main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` |
| PR #23 | OPEN, head `b07147b`, base `main` (sin cambios) |
| Staged | **vacío** (no staging) |
| Unstaged | `criba_adapter.py` (+113/-9), `harness.py` (+18/-9) |
| Untracked | 2 tests F5 + `docs/audits/pilot_ledger_schema.py` + 15 documentos |
| Entorno | Python 3.11.15 (`criba-blackforge/.venv/Scripts/python.exe`) |
| cwd | `C:\ASTRA_WORK\Criba-Blackforge-Supra` |

**SHA256 de cada archivo probado:**
```
4de3d6b82f282141ff59273db5ba276c  criba-blackforge/benchmarks/innovation/criba_adapter.py
204b4c9162a254d50cc305ea71e33948  criba-blackforge/benchmarks/innovation/harness.py
cb918cfd0d19a6377f4b9559347cce81  criba-blackforge/tests/unit/test_selection_report_attribution.py
ebc97d84b3ac748691065be107759fee  criba-blackforge/tests/unit/test_selection_report_persistence.py
14efb76a22d2f251a6eebcaf5cc10cd1  docs/audits/pilot_ledger_schema.py
```
**SHA256 del patch (binario):** `6027dab60d2699daa204d8bd8c70b2f6`
**Copia aislada de mutación:** `/tmp/tmp.*` (temporal, eliminada tras la prueba).

---

## 2. Paquete CBS (continuidad)

**`OBSERVED`:** el ZIP está disponible en `C:\Users\KLSX\Downloads\CBS_INTEGRACION_RECONCILIACION_HERMES_2026-10-22.zip`.
- SHA256: `3d2021b1416134102aabafbb8b6ac6d236c814e8864eb32214dfe33ab45a9f1` — **coincide** con el registro histórico.
- `unzip -t` → `No errors detected`.
- 26+ capítulos + `datos/` + `paquete_original_20261020/` (contiene el canónico PROMPT 10).
- `CBS_GUIA_DE_ENTREGA_Y_ARRANQUE.md` `283d715e…`, `CBS_MASTER_TODO_EN_UNO.md` `f13a8fd3…` (ambos coinciden con el histórico).

**Canónico dentro del ZIP:** `paquete_original_20261020/prompts/PROMPT_10_PILOTO_SELECTOR_CRIBA.md` → SHA256 `c9dcea221ac10edf5f1bed330b12621afec912dfb2ccf6672f03b514914a851c` — **idéntico** al mío.

**Lectura:** solo `00`, `04`, `10`, `16` (capítulos pertinentes), **sin extraer** (solo `unzip -p`/`-l`).

---

## 3. F5 — revisión del delta

**Contrato verificado (`OBSERVED`, 39 passed):**
- `CribaResult` liga candidatos + informe a la **misma invocación**.
- El harness recoge el informe del **objeto devuelto**, no de un getter global.
- Callback sin report → `REPORT_UNAVAILABLE` (`instrumented=false`, motivo concreto) **tras un éxito previo** (test B).
- Excepción → no expone el informe anterior (test C).
- Independencia de estructuras anidadas (test D, `copy.deepcopy`).
- Export/readback conserva identidad, candidatos e informe (test E).
- Contrato legacy `criba_fn` preservado (firma y tipo) → declara `REPORT_UNAVAILABLE` (test G).
- `opportunity_accounting` registra solo lo ocurrido en esta ruta; `budget_complete=False` explícito.
- Consumidores: `harness.py` usa `CribaResult`/`_coerce_result`; los tests usan `run_criba_selection`.

**Mutación detectada (`OBSERVED`):** 10 failed en copia aislada al quitar `CribaResult` (tests y causas corresponden al contrato roto; no import/colección/entorno).

**Límites:** concurrencia de ESCRITURA no soportada (documentado); `F5_STATUS = CORREGIDO_LOCALMENTE` (falta SHA de revisión y evaluación separada; Hermes sigue siendo writer).

**No se reescribió por estética** (el contrato ya se cumple).

---

## 4. Matriz de riesgos reconciliada

**`OBSERVED` — recuento real:**
```
filas de datos: 143
rutas únicas:   143
ids únicos:     143
categorías:     24 GREEN + 112 YELLOW + 7 ORANGE = 143
```

**Corrección del resumen:** el «24 GREEN + 112 YELLOW + 7 ORANGE + **1 RED = 144**» es **incorrecto**. La matriz tiene **143 rutas** y **143 = 24+112+7**. El «1 RED» del resumen es un **término dentro de un texto** (`PR23-F077`: «…restauración byte exacta y **RED** por causa específica»), **no** una categoría. F077 está categorizado **ORANGE**.

**No hay duplicados ni rutas solapadas.** Una categoría exclusiva por ruta.

**Las 5 filas locales nuevas** (§3 del checkpoint) **no** aparecen en la matriz de 143 (que cubre el diff remoto). Se añadieron por separado.

---

## 5. F3 — diagnóstico con traza

**Ruta (`STATIC_INSPECTION` + `OBSERVED`):**
```
catalog.methods → LotteryEngine.from_methods(seed) → run_round(mode="stratified",
batch_size=max(8,2N), query) → get_top_ideas(max(4N,8)) → select_finalists → proyección
```

**Entradas que recibe `select_finalists` (`OBSERVED`):**
```
pool[0]: score=0.349 | genome=None | family=None | idea_id=None
         family1='estrategia' | family2='ruptura_marco'   ← disponibles pero NO consumidas
```

**Fórmula/componentes (`OBSERVED`, `criba/engine.py:_evaluate_idea`):**
```
evidence  = 0.3 + 0.7 * (ejes_concretos / 15)     → 0.3467 con 1 eje
novelty   = min(1, (moved_axes/15)*0.5 + fam_diversity + 0.2) → 0.4333
cost      = 0.3 + 0.4*extreme + 0.3*novelty       → 0.43
value_score = evidence * novelty / cost            → 0.3494
score consumido = round(value_score, 3)            → 0.349
```

**Causa de `0.349`:** combinación de (a) **1 solo eje movido** por idea (mapeo familia→eje simplificado en `lottery._create_idea`), (b) **redondeo a 3 decimales**, (c) **genome ausente** → `_structural_distance = 0.0` → bonus de diversidad nulo. No es «el scorer está roto»: es **ausencia de entradas discriminantes** + **cuantización**.

**Distancia y desempate:** `U(c) = score + 0.6*d_min − penalizaciones`; sin genomas `d=0`; `family=None` en ambos cuenta `None==None` como repetición. Desempate por `idea_id` (vacío → orden de entrada del pool).

**Distingo:** redondeo (cuantización) · inputs iguales (1 eje) · campos ausentes (genome/family/idea_id) · pérdida de representación (`family1/family2` no consumidas) · limitación de política (bonus nulo).

**Prohibido y no hecho:** modificar pesos/seeds/floor/desempates/fórmulas; fabricar genomas; añadir ruido. **Sin cambio semántico en este sprint.**

---

## 6. Ledger — esquema contado

**`OBSERVED`:** `pilot_ledger_schema.py` leído completo y cotejado con el canónico verificado.

| Concepto | Valor |
|---|---|
| Requisitos canónicos (§4) | **10** (no 9) |
| Estados semánticos (§4) | **5** (aparte, no apartados) |
| Campos atómicos derivados | **35** (verificado por ejecución) |
| Bloques de presentación | **15** |

**Corrección:** el propio paquete CBS (cap. 10) dice «9 apartados → 27 campos → 15 bloques». Es **incorrecto** para el canónico con hash `c9dcea22…`: tiene **10 requisitos**. Corregido en `PROMPT_10_CORRECCION_RECUENTO_LEDGER.md` y en los documentos afectados. No es un cambio del canónico (hashes idénticos): es un error de transcripción.

**Capas separadas:** organización aceptada · cobertura documental (construida) · validación sintética (hecha, `SYNTHETIC`) · cobertura en datos reales (**PENDIENTE**) · aprobación del esquema (**PENDIENTE**) · aprobación del prerregistro (**PENDIENTE**) · autorización (**NO**).

**Hash chain:** tamper-evident bajo supuestos; **no** append-only enforced.

---

## 7. Brazo B y estados

**`OBSERVED`:** sin backend/callback autorizado disponible (Ollama 11434→000, proxy 8645→000, SUPRA 8000→000; `CRIBA_EXTERNAL_API_KEY` ausente).

```
B_STRONG_PROMPT_STATUS = BLOCKED / UNAVAILABLE
comparación            = NOT_EXECUTED
```
**`INCONCLUSIVE` no aplica:** requiere evidencia válida insuficiente; aquí no hay comparación ejecutada. Una exploración de un solo brazo no sustituye el contraste.

---

## 8. Instrumento funcional

**`OBSERVED`:** no existe instrumento de evaluación funcional independiente del scorer. El harness mide diversidad/estructura (`duplication_rate`, `family_coverage`, `structural_diversity`), **no** validez funcional.

**Brecha concreta:** falta el artefacto evaluable (programa/ejecutable que demuestre la propiedad funcional del problema). Sin él, el endpoint 1/0 no es medible. **No se fabricó un puente ni arquitectura nueva** (bloqueado este bloque).

---

## 9. Problemas de desarrollo

**`OBSERVED`:** `problems_smoke.json` tiene **10** problemas (G01–G05, B01–B05) sin criterio de resolución. **No se prepararon problemas nuevos** (bloqueado por §8: el instrumento no permite criterios honestos). **DATASET_INCOMPLETE** declarado; no se maquilla a N=10.

---

## 10. Backups

| Artefacto | Ruta | Verificación |
|---|---|---|
| Bundle referencias | `C:\ASTRA_WORK\PREPLAN_BACKUP_20261022\f5_refs.bundle` | `git bundle verify` OK |
| Patch binario | `...\f5_unstaged_binary.patch` (8269 B) | hash `6027dab6…` |
| Snapshot WIP | `...\wip_snapshot\` (36 ficheros) | restauración byte-identica verificada |
| Copia previa | `docs/audits/_backup_20261022/` (8 ficheros) | MD5 registrados |

**Los 2 tests nuevos (untracked) están en `wip_snapshot/`** — el patch unstaged no los cubre. **No se sobrescribieron backups ni se movió WIP.**

---

## 11. Propuesta de publicación (NO ejecutada)

| Elemento | Propuesta |
|---|---|
| Comprometer (F5) | `criba_adapter.py` (+113/-9), `harness.py` (+18/-9) |
| Tests a incluir | `test_selection_report_attribution.py`, `test_selection_report_persistence.py` |
| Documentación aparte | `docs/audits/PROMPT_10_*`, `PREPLAN_*`, `pilot_ledger_schema.py` → conjunto documental, no producto |
| **No publicar** | `.hermes/`, `P10.md`, `audits.rar`, `_backup_20261022/`, logs, locks |
| Relación PR #23 | misma rama origen `integrate/shadow-supra-final`; avance rápido |
| Riesgo | atribución del informe (ya probada); compatibilidad `criba_fn` (preservada) |
| Rollback | revertir el slice de los 2 ficheros desde `f5_unstaged_binary.patch` |
| Gates antes de push | revisión con SHA propio; suite F5; no romper consumidores |
| Gates antes de merge | CI verde + aprobación del propietario |
| PR #23 | **NO cerrar, NO editar, NO crear sustituta** (sin evidencia de sustitución ni base incorrecta) |

---

## 12. Bloqueos y estado de cierre

```
PREREGISTRATION_STATUS              = NOT_APPROVED
LEDGER_SCHEMA_STATUS                = PENDING — NOT APPROVED
A_DIRECT_STATUS                     = BLOCKED
B_STRONG_PROMPT_STATUS              = BLOCKED / UNAVAILABLE
C_CRIBA_STATUS                      = EXECUTABLE
F2_STATUS                           = NOT_A_DEFECT
F3_STATUS                           = OPEN — BLOQUEANTE
F4_STATUS                           = CONFIRMED_LIMITATION
F5_STATUS                           = CORREGIDO_LOCALMENTE
PILOT_EXECUTION_ALLOWED             = NO
SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED = NO
```

**Estado de cierre:** `CBS_LOCAL_SPRINT_PARTIAL`.
- **Completado:** F5 revisado y probado (39 passed, mutación 10 failed); matriz reconciliada (143 rutas); ledger contado (10/35/15); ZIP CBS verificado; F3 diagnosticado con traza.
- **Pendiente (bloqueos):** instrumento funcional (§8), dataset de desarrollo (§9), aprobación del esquema ledger, SHA de revisión de F5, revisión del plan maestro.
- **No ejecutado:** piloto, cambios semánticos del selector, merge/push/commit, executor/STANDARD.
