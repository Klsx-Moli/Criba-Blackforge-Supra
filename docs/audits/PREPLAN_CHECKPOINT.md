# PUNTO DE ENTRADA ÚNICO — CHECKPOINT PREPLAN

**Fecha:** 2026-10-22 · **Última actualización:** tras cierre de F5 y reconciliación documental.
**Rol:** único punto de entrada reanudable. No sustituye la evidencia original.

Vocabulario: `OBSERVED` (esta sesión), `STATIC_INSPECTION`, `PREVIOUS_REPORT`, `INFERENCE`, `NOT_VERIFIED`.

---

## 1. Baseline y delta

| Campo | Valor |
|---|---|
| Repo real | `C:\ASTRA_WORK\Criba-Blackforge-Supra` |
| Rama | `reconcile/candidate-fix-20261020` |
| HEAD | `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` |
| `main` / `origin/main` | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` (intacto) |
| PR #23 | OPEN, head `b07147b` |
| Escritor | único (Hermes) |

**Delta local (código producto):**
```
M  criba-blackforge/benchmarks/innovation/criba_adapter.py   (+113/-9)
M  criba-blackforge/benchmarks/innovation/harness.py          (+18/-9)
?? criba-blackforge/tests/unit/test_selection_report_attribution.py
?? criba-blackforge/tests/unit/test_selection_report_persistence.py
?? docs/audits/pilot_ledger_schema.py
```
**Hash del delta probado:** `git diff --binary` → `PREPLAN_BACKUP_20261022/f5_unstaged_binary.patch` (8269 bytes).

---

## 2. Qué se modificó y qué quedó intacto

- **Modificado:** adaptador de benchmark y harness (atribución F5). Sin cambios de scoring, pesos, semillas ni desempates.
- **Intacto:** `selector.py`, `engine.py`, `diversity_selector.py`, `lottery.py`, `blackforge_selector.py`, `main`, WIP preexistente, `.hermes/`, `P10.md`.
- **No se ejecutó:** piloto, executor BLACKFORGE, STANDARD, suites completas.

---

## 3. Backups y recuperación

| Artefacto | Ruta | Verificación |
|---|---|---|
| Bundle referencias | `C:\ASTRA_WORK\PREPLAN_BACKUP_20261022\f5_refs.bundle` (14386619 B) | `git bundle verify` → complete history |
| Diff binario unstaged | `...\f5_unstaged_binary.patch` (8269 B) | generado |
| Snapshot WIP (36 ficheros) | `...\wip_snapshot\` | restauración byte-identica verificada (criba_adapter `4de3d6b8…`, harness `204b4c91…`) |
| Copia previa de esta fase | `docs/audits/_backup_20261022/` (8 ficheros) | MD5 registrados |
| Bundle preflight previo | `C:\ASTRA_WORK\PREFLIGHT_BACKUP_20261020\bundle_20261020.bundle` | MD5 `1b799fc50ddcde91810a255351212b50` |

**Restauración:** solo delta propio; sin reset/clean ni copia global encima de WIP.

---

## 4. Estados vigentes

```
PREREGISTRATION_STATUS              = NOT_APPROVED
LEDGER_SCHEMA_STATUS                = PENDING — NOT APPROVED
LEDGER_DESIGN_DECISION              = ACCEPTED_WITH_COVERAGE_CHECK
A_DIRECT_STATUS                     = BLOCKED
B_STRONG_PROMPT_STATUS              = BLOCKED
C_CRIBA_STATUS                      = EXECUTABLE
F2_STATUS                           = NOT_A_DEFECT
F3_STATUS                           = OPEN — BLOQUEANTE
F4_STATUS                           = CONFIRMED_LIMITATION
F5_STATUS                           = CORREGIDO_LOCALMENTE
PILOT_EXECUTION_ALLOWED             = NO
SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED = NO
```

---

## 5. F5 — causa, cambio, RED/GREEN, límites

**Causa:** `criba_adapter.criba_fn` descartaba el `report` de `select_finalists` (`finalists, _report = ...`). El `opportunity_accounting` no existía en esta ruta (su productor vive en `invent()`, que el benchmark no llama). El harness persistía solo candidatos.

**Cambio (mínimo, aditivo):**
- `CribaResult` liga candidatos + informe a la misma invocación.
- `run_criba_selection()` devuelve `CribaResult`; `criba_fn()` conserva su firma legacy (lista → `REPORT_UNAVAILABLE`).
- El harness recoge el informe del objeto devuelto (no de un getter global) y copia profunda.
- Contabilidad de la ruta declarada explícitamente (`budget_complete=False`).

**Evidencia:**
| Prueba | Resultado |
|---|---|
| RED inicial (persistencia) | 2 failed, 1 passed |
| RED atribución (6 tests) | 3 failed → 4 failed → 1 failed |
| GREEN atribución (7 tests) | **7 passed** |
| Regresión F5 (persistence+attribution+harness+diversity) | **39 passed** |
| Mutación aislada (quitar `CribaResult`) | **10 failed** (detectada) |

**Límites:**
- El contrato aditivo es **por invocación**; la concurrencia de ESCRITURA (múltiples procesos) **no** está soportada (documentado, no proclamado).
- El getter global `last_selection_report()` se conserva como superficie secundaria; **no** es la fuente de atribución.
- `F5_STATUS = CORREGIDO_LOCALMENTE`: falta el **SHA de revisión** (sin commit) y la evaluación separada exigida por el registro de defectos.

---

## 6. Ledger — recuentos correctos y capas

| Concepto | Valor |
|---|---|
| Requisitos canónicos (§4) | **10** (no 9) |
| Estados semánticos (§4) | **5** (no son apartados del esquema) |
| Campos atómicos derivados | **35** (no 27) |
| Bloques de presentación | **15** |
| Hash canónico | `c9dcea221ac10edf5f1bed330b12621afec912dfb2ccf6672f03b514914a851c` |

**Capas separadas:** DECISIÓN DE ORGANIZACIÓN (aceptada) · COBERTURA DOCUMENTAL (construida) · VALIDACIÓN SINTÉTICA (hecha, fila `SYNTHETIC`) · COBERTURA EN DATOS REALES (**PENDIENTE**) · APROBACIÓN DEL ESQUEMA (**PENDIENTE**) · APROBACIÓN DEL PRERREGISTRO (**PENDIENTE**) · AUTORIZACIÓN (**NO**).

**Hash chain:** tamper-evident bajo supuestos (escritor único, ancla externa, sin reescritura). **No** append-only enforced.

---

## 7. Informes y artefactos (referencias)

| Contenido | Ruta |
|---|---|
| Este checkpoint | `docs/audits/PREPLAN_CHECKPOINT.md` |
| Corrección recuento ledger | `docs/audits/PROMPT_10_CORRECCION_RECUENTO_LEDGER.md` |
| Matriz archivos/fuentes | `docs/audits/PREPLAN_MATRIZ_ARCHIVOS_Y_FUENTES.md` |
| Índice cronología (actualizado) | `docs/audits/PROMPT_10_INDICE_ESTADO_Y_CRONOLOGIA.md` |
| Esquema ledger (corregido) | `docs/audits/PROMPT_10_LEDGER_ESQUEMA.md` |
| Esquema ledger sintético | `docs/audits/pilot_ledger_schema.py` |
| Defectos F2–F5 | `docs/audits/PROMPT_10_DEFECTOS_F2_F5.md` |
| Preflight | `docs/audits/PROMPT_10_PREFLIGHT_CIENTIFICO.md` |

---

## 8. Qué NO debe ejecutarse todavía

- El piloto de PROMPT 10.
- Cambios semánticos del selector (pesos, seeds, floor, desempates).
- Executor BLACKFORGE / STANDARD.
- Merge, push, commit, release.
- Nuevas llamadas reales a modelos.

---

## 9. Siguiente acción exacta

1. **Revisión con SHA propio** de los diffs de F5 (`criba_adapter.py`, `harness.py`) — requiere autorización de commit.
2. **F3**: presentar el diagnóstico ya ejecutado (causa numérica `0.349`, inputs, fórmula, distancia, desempate) sin cambiar el scorer.
3. **Instrumento funcional**: definir el criterio de validez independiente del scorer (fase 3A del plan).
4. **Dataset**: preparar hasta 10 problemas de desarrollo (fase 3B).
5. **Aprobación del esquema ledger** (propietario) y **cobertura en datos reales**.

---

## 10. Clasificación de afirmaciones

| Categoría | Ejemplos |
|---|---|
| **OBSERVED (esta sesión)** | HEAD/rama/status; 39 tests passed; mutación 10 failed; hashes de fuentes; 10 requisitos; 35 campos; restauración byte-identica |
| **STATIC_INSPECTION** | causa F5; contrato aditivo; hash chain tamper-evident |
| **PREVIOUS_REPORT** | CI verde run 39518923033; suites históricas; MD5 bundle preflight |
| **INFERENCE** | causa numérica 0.349 (fórmula); cobertura por requisito |
| **NOT_VERIFIED** | contenido ZIP CBS; cobertura en datos reales; enforcement append-only |
