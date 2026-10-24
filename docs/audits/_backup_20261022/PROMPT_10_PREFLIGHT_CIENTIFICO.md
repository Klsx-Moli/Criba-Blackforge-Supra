# PROMPT 10 — PREFlight CIENTIFICO (fase de inspeccion y preparacion)

**Fecha de ejecucion:** 2026-10-22
**Ambito:** CRIBA x BLACKFORGE x SUPRA — piloto del selector real
**SHA de trabajo:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Rama:** `reconcile/candidate-fix-20201020` (publicada como `origin/integrate/shadow-supra-final`, PR #23 OPEN, base `main`= `defd0fd` intacto)
**Fuentes normativas:** `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (canonico) + `06_PROTOCOLO_CIENTIFICO_Y_PILOTO.md`
**Modelo/entorno:** Hermes, Python 3.11.15 (`criba-blackforge/.venv/Scripts/python.exe`), solo lectura del repo; ningun archivo escrito en el repositorio.

---

## 0. Estado operativo de la continuidad (recuperada)

| Dato | Valor | Fuente |
|---|---|---|
| HEAD | `b07147b` | `git rev-parse HEAD` |
| `origin/integrate/shadow-supra-final` | `b07147b` | `git ls-remote origin` |
| `main` local y remoto | `defd0fd` | `git ls-remote origin` |
| PR #23 | OPEN, head `b07147b`, base `main` | `gh pr view 23` |
| Monorepo CI (run 39518923033) | **VERDE**: CRIBA/BLACKFORGE ok, SUPRA ok, Linux informativo ok, monorepo-result ok | `gh run view 39518923033` |
| Anti-Goodhart RETRYBOX Gate | SUCCESS | check rollup PR #23 |
| Shadow Windows Build Smoke | SUCCESS | check rollup PR #23 |
| WIP preexistente | `.hermes/`, `criba-blackforge/.hermes/iie/checkpoints/P10.md` (no rastreados) + `blackforge_broker.py`/`blackforge_case.py` (solo CRLF, numstat vacio) | `git status --porcelain` |
| Bundle preflight | MD5 `1b799fc50ddcde91810a255351212b50` (14.334.541 bytes) | verificado |

**B1 (CI remoto del SHA candidato) queda RESUELTO en evidencia:** el run 39518923033 sobre `b07147b` esta completo y verde (4/4 jobs SUCCESS). El checkpoint anterior lo dejaba como `PENDING_REMOTE_VERIFICATION`; hoy consta verificado por ejecucion. No se repitio: se consulto el run ya existente.

---

## 1. Matriz de requisitos y evidencias

### 1.1 Las TRES inspecciones iniciales (orden original del prompt)

| # | Inspeccion | Evidencia (ruta:linea / artefacto) | Resultado | Tipo |
|---|---|---|---|---|
| I1 | Selector/scorer productivo: entrypoint, campos, normalizacion, defaults/UNKNOWN, score consumido, desempates, llamada efectiva | `criba-blackforge/src/criba/selector.py:43` `select()`; consumidor real `criba-blackforge/src/criba/engine.py:1224` `selection = select(query, current)`; motor `engine.activate` `:1200`; consumidores `cli.py:52`, `gui.py:335`, `api.py:141`, `agentic.py:72`; ranking de candidatos `engine.py:1261-1265` (`value_score` `:1004`) | **INSPECCIONADO** | inspeccion + ejecucion |
| I2 | Driver de benchmark: candidate set, prompts, presupuesto, seeds, reintentos, seleccion, acceso a etiquetas | `criba-blackforge/benchmarks/innovation/harness.py` (condiciones A_DIRECT/B_STRONG_PROMPT/C_CRIBA, `run_condition` `:49`); `criba_adapter.py:18` `criba_fn`; problemas `problems_smoke.json` (10) | **INSPECCIONADO** | inspeccion + ejecucion |
| I3 | Puente protocolo->ejecucion->observacion (OutcomeStore) | `criba-blackforge/src/criba/intelligence/outcome_store.py:112` `TechniqueOutcomeStore`; `anti_goodhart/store.py`, `records.py`, `trace.py`, `observer.py`; ledger `inventar.py:863` `append_ledger` | **INSPECCIONADO** | inspeccion + ejecucion |

### 1.2 Requisitos del PROMPT 10

| ID | Requisito (literal) | Evidencia | Tipo | Estado | Riesgo / accion |
|---|---|---|---|---|---|
| R1 | "fija repo, candidate_ref, TARGET_SHA, BASE_SHA, estado de CI y ausencia de writer concurrente" | repo CBS; HEAD `b07147b`; `main` `defd0fd`; CI verde run 39518923033; procesos: solo Hermes (3 python + 1 hermes, todos del propio agente) | ejecucion (git/gh/ps) | **PASS** | ninguno |
| R2 | "Inspecciona solo estos tres rangos" | I1/I2/I3 acotados a selector.py/methods.py/engine.py/gate.py/harness.py/outcome_store.py | inspeccion | **PASS** | ninguno |
| R3 | "Si falta una precondicion cientifica esencial, la fase es BLOCKED" | ver R22-R27 | ejecucion | **BLOCKED** | requiere preregistro (seccion 3) |
| R4 | "30 problemas independientes" | `problems_smoke.json` = **10** problemas (G01-G05, B01-B05), claves `{id, perfil, texto}`; **no existe** dataset de 30 | inspeccion + ejecucion | **FAIL** | **GAP**: N=10 disponible, 30 inexistente |
| R5 | "definicion de resolucion de cada problema" | ningun problema declara `resolucion`/`criterio`/`solucion`; solo `texto` | inspeccion + ejecucion | **FAIL** | **GAP**: sin criterio externo de validez funcional |
| R6 | "cuatro candidatos congelados" | `criba_fn(..., n_candidatos=4)` produce 4 candidatos deterministas por problema (verificado) | ejecucion | **PASS** | ninguno (construccion existente) |
| R7 | "un candidato funcionalmente valido de referencia; un control negativo; dos alternativas" | **no existe** construccion con etiquetas de control/positivo/negativo; `criba_fn` devuelve 4 candidatos sin etiquetas | inspeccion + ejecucion | **FAIL** | **GAP**: diseno de candidatos inexistente |
| R8 | "Evaluacion funcional con protocolo independiente del scorer" | las metricas del harness son de **diversidad/estructura** (`duplication_rate`, `family_coverage`, `structural_diversity`, `unique_mechanisms`), NO de validez funcional | inspeccion + ejecucion | **FAIL** | **GAP**: instrumento inexistente |
| R9 | "Congelar todas las selecciones ... antes de abrir etiquetas" | no existe ledger de selecciones congeladas; `append_ledger` es de `invent()`, no del piloto | inspeccion + ejecucion | **FAIL** | **GAP** |
| R10 | "preregistro exigido" | no existe artefacto de preregistro del piloto (busqueda acotada: 0 resultados) | inspeccion + ejecucion | **FAIL** | **GAP**: obligatorio antes de cualquier fase |
| R11 | "ledger externo por episodio" con 15 campos | no existe ledger de episodios; `veredicts.jsonl` (430 filas, 2026-09-05) es de `invent()` y **no** tiene `episode_id`/`candidate_set_hash`/`protocol_sha256` | inspeccion + ejecucion | **FAIL** | **GAP**: ledger del piloto inexistente |
| R12 | "Ambos brazos reciben el mismo problema, contexto y 4 candidatos" | CRIBA (brazo tratamiento) deterministico y reproducible por seed (verificado); brazo B = `A_DIRECT`/`B_STRONG_PROMPT` **requieren model_fn (LLM)**, sin LLM disponible -> `UNAVAILABLE` | ejecucion | **BLOCKED** | requiere backend LLM |
| R13 | "El baseline es un prompt fuerte congelado" | `B_STRONG_PROMPT` definido como plantilla en `harness.py:30`, pero **no ejecutable sin model_fn** | inspeccion + ejecucion | **BLOCKED** | requiere backend LLM |
| R14 | "Sin APIs nuevas de pago" | no se requirio ninguna; canales: LLM local/proxy (inactivo), SUPRA local (inactivo) | ejecucion | **PASS** | ninguno |
| R15 | "Prohibiciones tras resultado positivo" | gate anti-Goodhart: `STANDARD_RELEASE_STATE=DISABLED`, `ObserverMode=[OFF, STANDARD]`; `main` no fusionado; sin push nuevo | ejecucion | **PASS** | ninguna ejecutada |

### 1.3 Hallazgos de verificacion cientifica (mutacion/anti-Goodhart)

| ID | Hallazgo | Evidencia | Clasificacion |
|---|---|---|---|
| F1 | El selector productivo es **keyword/signal**, deterministico; 43% de queries caen al baseline (score=15) | `selector.py:43`; muestra de 30 queries: 13/30 en baseline | **DEFECTO DE DISENO (no de producto)**: discriminacion debil |
| F2 | `select_blackforge(seed=...)` **ignora la semilla** (mismo set para seeds 1-8) | ejecucion: 8/8 seeds mismo `selected_ids` | **DEFECTO VERIFICADO** (semilla muerta) |
| F3 | Los 4 candidatos de `criba_fn` tienen **score identico (0.349)**; el ranking no discrimina entre ellos | ejecucion: scores `[0.349,0.349,0.349,0.349]` | **DEFECTO VERIFICADO** (cobertura falsa: el "ranking" no aporta) |
| F4 | El desempate es **por orden de entrada del pool** (barajar el pool cambia la seleccion) | `diversity_selector.py` `tiebreak_rule`; ejecucion: pool barajado -> seleccion distinta | **DEFECTO VERIFICADO** (no determinismo por contenido) |
| F5 | El `_report` de `select_finalists` (tie_sets, discarded_by_floor, opportunity_accounting) es **descartado** por `criba_adapter` | `criba_adapter.py` `finalists, _report = ...` y no lo usa | **DEFECTO VERIFICADO** (contabilidad incompleta) |
| F6 | `engine._evaluate_idea` es **resistente a verborrea** (score identico con 5000 chars) | ejecucion: corto vs verborrea -> mismo `value_score` | **CONTROL VERDE** (D2 score-hacking mitigado en este eje) |
| F7 | `invent()` sin seed fija usa seed aleatoria -> no reproducible por defecto | ejecucion: seed1 != seed2 sin fijar | **DEFECTO VERIFICADO** (reproducibilidad exige seed explicita) |
| F8 | El producto degrada **honesto** sin SUPRA (offline y online-con-SUPRA-caido dan el mismo paquete) | ejecucion: firmas identicas; errores de transporte visibles, no silenciosos | **CONTROL VERDE** |
| F9 | CRIBA offline es **byte-idempotente** con seed fija (3 corridas identicas) | ejecucion: hash de paquete identico | **CONTROL VERDE** |

---

## 2. Estado de las 30 problemas

**No existe dataset de 30 problemas.** El unico pool es `problems_smoke.json` con **10** problemas, cuya nota declara: *"Dataset humo (megaprompt §48): valida schema/runner/metricas, NO concluye superioridad. 5 generales + 5 BLACKFORGE."*

| ID | Perfil | Texto (resumen) | Criterio de resolucion |
|---|---|---|---|
| G01 | general | Reducir consumo de agua de huerto urbano | **NO DEFINIDO** |
| G02 | general | Detectar abuso de permisos en agentes autonomos | **NO DEFINIDO** |
| G03 | general | Reducir cola de atencion de oficina | **NO DEFINIDO** |
| G04 | general | Recuperar valor de lotes defectuosos | **NO DEFINIDO** |
| G05 | general | Mejorar adopcion de herramienta interna | **NO DEFINIDO** |
| B01 | blackforge | Reducir autorizaciones excesivas de agente | **NO DEFINIDO** |
| B02 | blackforge | Detectar exfiltracion via DNS | **NO DEFINIDO** |
| B03 | blackforge | Priorizar parcheo de vulnerabilidades | **NO DEFINIDO** |
| B04 | blackforge | Endurecer pipelines CI sin bloquear entrega | **NO DEFINIDO** |
| B05 | blackforge | Detectar credenciales reutilizadas | **NO DEFINIDO** |

**Impacto del gap:** sin 30 problemas independientes y sin criterio de resolucion por problema, el endpoint primario del piloto ("si el candidato seleccionado satisface los criterios funcionales... 1/0") **no es evaluable**. Cualquier seleccion de 10 problemas seria el piloto exploratorio con N menor, que el propio prompt exige declarar y **no maquillar** ("Si 30 no son de verdad independientes o operacionalizables, informar limitacion y no maquillar N").

---

## 3. Prerregistro y ledger: estado real

| Elemento | Estado | Evidencia |
|---|---|---|
| Prerregistro del piloto selector (hipotesis, comparadores, metricas, margen 20pp, semillas, particiones, regla de parada) | **INEXISTENTE** | busqueda acotada en `src`, `benchmarks`, `scripts`, `verification`, `docs`: 0 artefactos de preregistro del piloto |
| Ledger externo del piloto (15 campos por episodio) | **INEXISTENTE** | no existe `episode_id`/`candidate_set_hash`/`protocol_sha256` en ningun artefacto |
| Ledger `veredicts.jsonl` (LOCALAPPDATA) | **EXISTENTE, NO ES DEL PILOTO** | 430 filas, 2026-09-05, esquema `{entries, generated_at, query, seed, totals, ...}`; es salida de `invent()` |
| `evaluate_product_value.py` (schema `criba-llm-paired/1`) | **EXISTENTE, NO VALIDADO para el piloto** | exige `manifest.json`+`reviews.json` con `protocol_sha256`; no hay manifest del piloto; declara explicitamente "All blinding and preregistration remain DECLARED, not verified" |
| Instrumento de evaluacion funcional (criterio externo, ciego al scorer) | **INEXISTENTE** | el harness mide diversidad/estructura, no validez funcional |

**Decision:** el preregistro es **condicion obligatoria** (Art. 3 y seccion 4 del PROMPT 10). No se ejecuta ninguna fase experimental antes de fijarlo.

---

## 4. Decision fundamentada sobre la siguiente fase

```
READY_FOR_PILOTO_EXECUTION = NO
READY_FOR_PHASE_PREP        = YES
```

**Fundamentacion:** las inspecciones I1-I3 estan completas con evidencia ejecutada; la ruta real del selector y del motor esta verificada; la reproducibility del brazo CRIBA esta demostrada. Pero **cuatro precondiciones esenciales no se cumplen** y bloquean la fase experimental:

1. **N insuficiente / indefinido** (R4): 10 problemas disponibles, 30 exigidos, sin dataset de 30.
2. **Sin criterio de resolucion** (R5): el endpoint primario 1/0 no es evaluable.
3. **Sin construccion de 4 candidatos etiquetados** (R7): no hay control negativo/positivo.
4. **Prerregistro y ledger inexistentes** (R10, R11): obligatorios antes de abrir cualquier resultado.
5. **Brazo B no ejecutable** (R12, R13): requiere backend LLM; el harness lo devuelve `UNAVAILABLE`.

**Ademas**, los hallazgos F2-F5 son defectos del diseno de medicion que invalidarian cualquier resultado del piloto aunque se ejecutara hoy: ranking que no discrimina entre los 4 candidatos, desempate por orden de entrada, semilla muerta, y descarte del report de seleccion. Un piloto sobre este diseno solo produciria `BENCHMARK_CONTAMINATED` o un falso `NO_EVIDENCE_OF_CRIBA_ADVANTAGE`.

**Siguiente accion exacta (minima, verificable):** redactar el **prerregistro** del piloto (hipotesis, comparadores A/B, margen 20pp, semillas, particiones, regla de parada, definicion de validez funcional y del ledger de 15 campos) en un artefacto nuevo fuera del arbol canonico del producto, y **no** iniciar el pilotaje hasta que este preregistro exista y sea aprobado.

---

## 5. Proteccion del repositorio

- **Ningun archivo del repositorio fue creado ni modificado** por esta sesion (`git status --porcelain` = solo WIP preexistente `.hermes/` y `P10.md`).
- **Sin reset, clean, normalizacion CRLF, merge a `main`, push, ni activacion del executor de BLACKFORGE.**
- WIP preexistente preservado: `blackforge_broker.py`/`blackforge_case.py` (solo CRLF), `.hermes/`, `P10.md`.
- Bundle preflight intacto (MD5 `1b799fc5...`).
- Los unicos artefactos escritos por esta sesion son: este informe y (opcionalmente) un checkpoint de Hermes.

---

## 6. Checkpoint de cierre

| Campo | Valor |
|---|---|
| SHA | `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` |
| Rama | `reconcile/candidate-fix-20261020` |
| HEAD remoto PR #23 | `b07147b` (PUBLICADO, CI verde 39518923033) |
| `main` | `defd0fd` intacto |
| Archivos modificados/creados (repo) | **ninguno** |
| Artefactos escritos (fuera del repo) | `docs/audits/PROMPT_10_PREFLIGHT_CIENTIFICO.md` |
| Inspecciones completadas | I1, I2, I3 (con evidencia ejecutada) |
| Prerregistro | **INEXISTENTE** |
| Ledger del piloto | **INEXISTENTE** |
| Problemas resueltos | 0 |
| Problemas pendientes | 10 problemas sin criterio de resolucion; N=10 no 30 |
| Problemas bloqueados | brazo B (sin LLM), prerregistro, ledger, instrumento funcional |
| Siguiente accion exacta | Redactar prerregistro del piloto (R10) y ledger (R11); resolver brazo B (R12) o declarar `INCONCLUSIVE`/`BLOCKED` por brazo; no ejecutar el piloto |
| Estado | **INCOMPLETO** (fase de inspeccion completada; fase experimental no iniciada) |
