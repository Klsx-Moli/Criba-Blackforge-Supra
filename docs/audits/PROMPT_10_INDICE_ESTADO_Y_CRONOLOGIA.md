# ÍNDICE ÚNICO DEL ESTADO — PROMPT 10

**Fecha del índice:** 2026-10-22
**SHA de referencia:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` (rama `reconcile/candidate-fix-20261020`)
**Nota:** este índice es **punto de entrada**, no sustituye la evidencia original. Los estados históricos se distinguen de los vigentes.

Vocabulario: `FACT` (verificado en esta ejecución), `REPORTED` (comunicado por un informe previo, no reproducido aquí), `INFERENCE`, `NOT_VERIFIED` (no comprobado en esta ejecución), `NOT_ACCESSIBLE`.

---

## 1. Puerta de salida vigente

| Clave | Valor vigente |
|---|---|
| `PREREGISTRATION_STATUS` | `NO APROBADO` |
| `LEDGER_SCHEMA_STATUS` | `PENDING — NOT APPROVED` |
| `A_DIRECT_STATUS` | `BLOCKED` |
| `B_STRONG_PROMPT_STATUS` | `BLOCKED` |
| `C_CRIBA_STATUS` | `EXECUTABLE` (tratamiento) |
| `F2_STATUS` | `NOT_A_DEFECT` (por contrato) |
| `F3_STATUS` | `OPEN — BLOQUEANTE` |
| `F4_STATUS` | `CONFIRMED_LIMITATION` (no activo) |
| `F5_STATUS` | `CORREGIDO_LOCALMENTE` (verificado con tests; SHA de revisión pendiente) |
| `PILOT_EXECUTION_ALLOWED` | `NO` |
| `SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED` | `NO` |

---

## 2. Informes pertinentes (ruta + estado que aporta)

| Informe | Ruta | Estado que aporta |
|---|---|---|
| PROMPT 00 — Paso E | `docs/audits/PROMPT_00_PASO_E_CONTINUIDAD.md` | continuidad E6–E9, PHYSICAL_REPOS |
| PROMPT 00 — Paso F | `docs/audits/PROMPT_00_PASO_F_SALIDAS.md` | salidas, gates, B1/B2/B3 |
| PROMPT 00 — B2/B3 | `docs/audits/PROMPT_00_B2_B3_RESOLUCION.md` | B2 `FIXED_AND_VERIFIED`, B3 `RECONCILED` |
| PROMPT 00 — B1 plan | `docs/audits/PROMPT_00_B1_PLAN_PUBLICACION.md` | plan de publicación (histórico) |
| PROMPT 00 — checkpoint | `docs/audits/checkpoints/PROMPT_00_CHECKPOINT_2026-10-20.md` | cronología PROMPT 00 |
| PROMPT 10 — preflight | `docs/audits/PROMPT_10_PREFLIGHT_CIENTIFICO.md` | I1–I3, hallazgos F1–F9, decisión `READY_FOR_PHASE_PREP` |
| PROMPT 10 — prerregistro | `docs/audits/PROMPT_10_PREREGISTRO_BORRADOR.md` | borrador NO APROBADO + lagunas L1–L7 |
| PROMPT 10 — ledger esquema | `docs/audits/PROMPT_10_LEDGER_ESQUEMA.md` | 10 requisitos → 35 campos → 15 bloques |
| PROMPT 10 — conciliación prerregistro | `docs/audits/PROMPT_10_CONCILIACION_PREREGISTRO.md` | 22 requisitos: 16 SATISFIED / 4 PARTIAL / 2 MISSING |
| PROMPT 10 — conciliación ledger | `docs/audits/PROMPT_10_CONCILIACION_LEDGER.md` | resolución de la discrepancia 15 vs 9 |
| PROMPT 10 — brazos | `docs/audits/PROMPT_10_ESTADO_BRAZOS_Y_BLOQUEOS.md` | A/B `BLOCKED`, C `EXECUTABLE`, 8 bloqueos |
| PROMPT 10 — defectos | `docs/audits/PROMPT_10_DEFECTOS_F2_F5.md` | F2 `NOT_A_DEFECT`, F4 `CONFIRMED_LIMITATION`, F3/F5 `OPEN` |
| PROMPT 10 — skill audit | `docs/audits/PROMPT_10_CAMBIO_SKILL_AUDIT.md` | cambio de skill fuera del repo |
| **PROMPT 10 — índice** | `docs/audits/PROMPT_10_INDICE_ESTADO_Y_CRONOLOGIA.md` | este documento |

---

## 3. Estado vigente de F2–F5

| ID | Estado vigente | Justificación |
|---|---|---|
| F2 | `NOT_A_DEFECT` | contrato `blackforge_selector.py:9`: seed registrada solo para API/informe, no perturba ranking |
| F3 | `OPEN — BLOQUEANTE` | 4 candidatos con score idéntico (0.349); ranking no discrimina |
| F4 | `CONFIRMED_LIMITATION (no activo)` | pool determinista real estable; fragilidad solo si se reordena el pool |
| F5 | `OPEN — BLOQUEANTE` | `criba_adapter` descarta el report (tie_sets, discarded_by_floor, opportunity_accounting) |

---

## 4. Cronología (estados históricos ≠ vigentes)

| Fecha | Informe / evento | Estado que declaraba | ¿Vigente? |
|---|---|---|---|
| 2026-10-20 | PROMPT_00 checkpoint (1ª sesión) | HEAD 58e6171; Paso F pendiente | **HISTÓRICO** |
| 2026-10-20 | PROMPT_00 Paso E | E6–E9 confirmados | **HISTÓRICO** (resueltos en B2/B3) |
| 2026-10-20 | PROMPT_00 Paso F | `READY_FOR_PROMPT_10 = NO` (B1/B2/B3) | **HISTÓRICO** |
| 2026-10-21 | PROMPT_00 cierre sesión | B2 `FIXED_AND_VERIFIED`, B3 `RECONCILED`, B1 `PENDING_REMOTE_VERIFICATION` | **HISTÓRICO** |
| 2026-10-22 | PROMPT_10 preflight | B1 resuelto por CI verde; `READY_FOR_PHASE_PREP=YES`, ejecución `NO` | **VIGENTE** |
| 2026-10-22 | PROMPT_10 prerregistro/ledger | borrador NO APROBADO; esquema PENDING | **VIGENTE** |
| 2026-10-22 | PROMPT_10 conciliaciones | ledger: **10 requisitos / 35 campos / 15 bloques** (corregido); F2 `NOT_A_DEFECT`, F4 `CONFIRMED_LIMITATION` | **VIGENTE** |
| 2026-10-22 | PROMPT_10 índice | este documento | **VIGENTE** |
| 2026-10-22 | F5 atribución | `CribaResult` liga informe a invocación; 39 passed; mutación 10 failed | **VIGENTE** |

**B1 (histórico):** el checkpoint de 2026-10-21 lo dejaba `PENDING_REMOTE_VERIFICATION`. El preflight de 2026-10-22 lo declaró `RESOLVED_BY_EXECUTION` (run 39518923033 verde sobre `b07147b`). No se reconsultó en esta ejecución → `REPORTED`, no `FACT` de esta sesión.

---

## 5. Clasificación de las afirmaciones

| Categoría | Ejemplos |
|---|---|
| **FACT (esta ejecución)** | SHA/rama/main; `git status`; 22 requisitos conciliados; 10 requisitos del canónico; 35 campos derivados; F2/F4 reclasificados; 8 bloqueos |
| **REPORTED (informe previo, no reproducido)** | CI verde run 39518923033; suites CRIBA 2234 passed; tests P10 39 passed; MD5 del bundle |
| **INFERENCE** | descomposición 9→27→15 como interpretación; conclusión de potencia (n=30 no garantiza decidir 20 pp) |
| **NOT_VERIFIED (esta ejecución)** | contenido de `audits.rar`; el cambio exacto de la skill (sin copia previa) |
| **NOT_ACCESSIBLE** | versión previa de `SKILL.md`; dataset de 30 problemas; backends LLM |

---

## 6. Decisiones pendientes del propietario

| # | Decisión | Bloqueo asociado |
|---|---|---|
| 1 | Ledger: el propietario ya aceptó la organización (10 requisitos → 35 campos → 15 bloques) sometida a cobertura; falta la **aprobación explícita del esquema**. | B6 |
| 2 | Prerregistro: ¿aprueba el borrador con N=10 exploratorio, o construye el dataset de 30? | B1, B5 |
| 3 | ¿Define el instrumento de evaluación funcional independiente del scorer? | B4 |
| 4 | ¿Resuelve el brazo B (backend LLM) o se declara `BLOCKED`/`INCONCLUSIVE`? | B7 |
| 5 | ¿Aprueba la construcción de 4 candidatos con etiquetas de control/positivo/negativo? | B3 |
| 6 | ¿Define el criterio de resolución por problema? | B2 |
| 7 | ¿Ordena corrección de F3/F5 (fase posterior aislada)? | B8 |

---

## 7. Próxima acción permitida y condición verificable

**Próxima acción permitida:** resolución documental y de decisiones del propietario (esta fase). No está permitida la ejecución del piloto.

**Condición verificable para la siguiente fase:**
1. `PREREGISTRATION_STATUS = APPROVED` (aprobación explícita del propietario — **condición futura**, hoy `NOT_APPROVED`).
2. `LEDGER_SCHEMA_STATUS = APPROVED` (**condición futura**, hoy `PENDING — NOT APPROVED`; la discrepancia 15 vs 10 requisitos está resuelta por decisión de organización sometida a cobertura).
3. Instrumento de evaluación funcional **independiente del scorer** operativo.
4. Dataset y criterios de resolución definidos (N justificado para confirmatorio, o N=10 declarado como exploratorio).
5. Brazo B disponible **o** declarado `INCONCLUSIVE` con alcance limitado.
6. F3/F5 corregidos en fase aislada con SHA propio y regresión ejecutada.

**Hasta que se cumplan las 6, `PILOT_EXECUTION_ALLOWED = NO` y `SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED = NO`.**
