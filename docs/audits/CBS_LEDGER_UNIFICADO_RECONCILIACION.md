# CBS — LEDGER UNIFICADO DE RECONCILIACIÓN

**Fecha:** 2026-10-23 · **Rama activa:** `reconcile/candidate-fix-20261020` · **HEAD:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Base remota de referencia:** `origin/integrate/shadow-supra-final` @ `b07147b` (base `main` @ `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b`)
**PR #23:** OPEN, head `b07147b`, sin modificar.

Vocabulario de disposición: ALREADY_PRESENT · KEEP · PORT_CANDIDATE · ACTIONABLE_GAP · VERIFY · HISTORICAL_PRESERVED · SUPERSEDED · DEFERRED · RESEARCH_ONLY · BLOCKED · REJECTED_WITH_REASON.

---

## 1. Línea base

| Elemento | Valor | Estado |
|---|---|---|
| Repo | `C:\ASTRA_WORK\Criba-Blackforge-Supra` | FACT |
| Rama activa | `reconcile/candidate-fix-20261020` | FACT |
| HEAD | `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` | FACT |
| main / origin/main | `defd0fd9955c5aaf3f7ff8b23fdf016639ed062b` | FACT |
| Staged | vacío (no staging) | FACT |
| Unstaged | 7 ficheros (5 producto + 2 EOL-only) | FACT |
| Untracked | 13 ficheros (tests + docs) | FACT |
| PR #23 | OPEN | FACT |
| Worktrees | 5 (incl. `Criba-Blackforge-Supra-main-baseline`, `integracion-f03`, `iso-deep-execution-20261005`, `iso-dossier`) | FACT |

## 2. Delta local (working tree, no committed)

| Archivo | Disposición | Evidencia |
|---|---|---|
| `criba-blackforge/benchmarks/innovation/criba_adapter.py` | KEEP (F5 + family) | F5 13 passed, family verificada |
| `criba-blackforge/benchmarks/innovation/harness.py` | KEEP (F5) | F5 13 passed |
| `criba-blackforge/src/criba/lottery.py` | KEEP (F3) | 6 tests + mutación 5 failed |
| `criba-blackforge/src/criba/inventar.py` | KEEP (F3) | family/genome en entries verificado |
| `criba-blackforge/src/criba/intelligence/execution.py` | KEEP (canon) | T061/T054 en `_INPUT_ADAPTERS` |
| `criba-blackforge/src/criba/intelligence/invention/recombination.py` | KEEP (canon) | NUEVO: T061 + T054 |
| `criba-blackforge/tests/unit/test_lottery_family_delivery.py` | KEEP | NUEVO: 6 tests |
| `criba-blackforge/tests/intelligence/test_t061_attribute_substitution.py` | KEEP | NUEVO: 11 tests |
| `criba-blackforge/tests/intelligence/test_t061_wiring.py` | KEEP | NUEVO: 5 tests |
| `criba-blackforge/tests/intelligence/test_t054_technological_recombination.py` | KEEP | NUEVO: 6 tests |
| `criba-blackforge/src/criba/blackforge_broker.py` | SUPERSEDED (EOL only) | Contenido byte-idéntico a HEAD |
| `criba-blackforge/src/criba/blackforge_case.py` | SUPERSEDED (EOL only) | Contenido byte-idéntico a HEAD |
| `criba-blackforge/tests/unit/test_selection_report_attribution.py` | KEEP (F5) | 11 passed |
| `criba-blackforge/tests/unit/test_selection_report_persistence.py` | KEEP (F5) | 11 passed |
| `docs/audits/CBS_SPRINT_LOCAL_F5_F3_INFORME.md` | KEEP | Informe F5/F3 |
| `docs/audits/CBS_MAXIMUM_RECONCILIATION_CHECKPOINT.md` | KEEP | Checkpoint |
| `docs/audits/PREPLAN_*.md` | HISTORICAL_PRESERVED | Referencia previa |
| `docs/audits/PROMPT_10_*.md` (11) | HISTORICAL_PRESERVED | Conciliación documental |
| `.hermes/` · `P10.md` | HISTORICAL_PRESERVED | Artefactos existentes |

## 3. Canon T001–T130 (fuente real: `data/intelligence/technique_registry.yaml`)

| Disposición | Nº | IDs |
|---|---|---|
| VERIFIED_FOR_SCOPE | 29 | T019 T048 T049 T053 T055 T057 T059 T060 T062 T063 T064 T065 T067 T068 T069 T070 T071 T086 T091 T094 T095 T096 T097 T098 T099 T101 T116 T128 T129 |
| ALREADY_PRESENT | 45 | incl. T054 T061 (implementados esta sesión) |
| ACTIONABLE_GAP | 28 | T021 T031 T036 T046 T050 T051 T052 T056 T079 T081 T083 T084 T085 T093 T100 T102 T103 T104 T107 T108 T109 T111 T112 T113 T114 T115 T121 T122 |
| RESEARCH_ONLY | 28 | requieren red |

Defecto de trazabilidad: los campos `tests` del canon apuntan a ficheros inexistentes (0/48 resueltos en `tests/`); la cobertura real está en `tests/intelligence/*` con nombres distintos.

## 4. Estado de verificación

| Superficie | Resultado | Alcance |
|---|---|---|
| `tests/unit` | 1327 passed, 11 skipped | completo |
| `tests/intelligence` | 448 passed | completo |
| `tests/integration` (contrato SupraClient) | 41 passed | parcial |
| `tests/integration` (restart/replay/dossier) | 18 passed | parcial |
| `tests/integration` (b01/cb_i01) | 16 passed | parcial |
| BLACKFORGE defensivo | 73 passed | parcial |
| Shadow launcher + smoke | 42 passed | parcial |
| Lock + k7 readiness | 26 passed | parcial |
| Intérprete | 106 passed | parcial |

Crash: NO reproducible. 0 ocurrencias de fatal/access violation; suite completa verde.

## 5. Ledger sintáctico (`pilot_ledger_schema.py`)

Verificado por ejecución:
- `SCHEMA_ID = pilot-selector-ledger/1`, `SYNTHETIC_MARK = SYNTHETIC / NOT_EXPERIMENTAL_EVIDENCE`.
- `ATOMIC_FIELDS = 35`, `BLOCKS = 15`, `REQUIRED_BLOCKS = 15` (coincide con la corrección vigente: 10 requisitos / 5 estados / 35 campos / 15 bloques).
- `build_synthetic_row()` → 37 claves, determinista; `coverage()` → `covered: True` (15/15 bloques, 0 campos ausentes).
- `PilotLedger.append()` → hash sha256 de la línea; persistencia JSONL real.
- `verify_chain()` → `(True, 'N filas enlazadas')`.

**Limitación verificada (no append-only enforced):** la cadena enlaza por `prev_hash` recalculando el hash de cada línea. Con **2+ filas**, modificar el contenido de una fila rompe el enlace de la siguiente → detectado (`fila 2: prev_hash no enlaza`). Con **una sola fila**, no hay eslabón siguiente y un cambio de contenido **no** se detecta. Es tamper-evident de enlace, no integridad de contenido por fila aislada. No se presenta como append-only enforced.

## 6. ACTIONABLE_GAP — verificado: sin consumer real (DEFERRED)

**Corrección aplicada (2026-10-23):** la clasificación inicial buscó `criba.intelligence.scoring.*` (los módulos declarados en el canon). Existe además un paquete **`criba/scoring/`** (fuera de `intelligence`) con `novelty.py`, `information_theory.py`, `mcda.py`, `network.py`.

**Rectificación de trazabilidad (2026-10-23, segunda pasada):** la afirmación previa de que el paquete `criba/scoring/` tiene "consumer real (`inventar.py`)" es **FALSA**. `inventar.py` no importa nada de `criba.scoring` (verificado por grep exhaustivo). El estado real del paquete `criba/scoring/`:
- `network.IdeaNetwork` → **consumer real** en `ui/actions.py:1625` (instancia, `build_from_ideas`, `summary`); panel "Red de Ideas" de Shadow.
- `mcda.MCDAAnalyzer` → solo **re-export** en `criba/mcda.py:29` (`# noqa: F401`); no se invoca en producción.
- `novelty.local_novelty` → **sin consumer de producción** (solo tests).
- `information_theory` → **sin consumer de producción** (solo docstring).

Por tanto, la única técnica del paquete `criba/scoring/` con cableado a producción es `network` (T090 Knowledge graph, implícito). `novelty` (T081), `information_theory` y `mcda.MCDAAnalyzer` permanecen **sin consumer de producción**; la categoría IMPLEMENTED_NOT_WIRED de T081 se conserva (implementado con tests y contrato honesto, sin cableado).

- **T081 (Local novelty)** → **IMPLEMENTED_NOT_WIRED**, no ACTIONABLE_GAP. `criba.scoring.novelty.local_novelty` verificado por ejecución: `None` (sin datos) ≠ `0.0` (idéntico) ≠ `0.667` (parcial) ≠ `1.0` (distinto). Contrato honesto. **Pero**: el campo `contracts.py:648 local_novelty` queda en `0.0` por defecto; ninguna ruta de producción lo calcula (solo tests `test_mcda.py`).
- **Hallazgo de trazabilidad:** el canon declara `criba.intelligence.scoring.novelty`, pero la implementación real está en `criba.scoring.novelty` (paquete distinto, mismo nombre base). No es una brecha de implementación: es un **desfase de ruta en el registry**. No se corrige el registry sin evidencia de autoridad (podría romper consumidores que ya importan `criba.scoring.novelty`).
- T083 (Temporal novelty) y T085 (Density estimation): sin implementación localizada.
- T084 (Semantic distance): existe como **campo de contrato** (`contracts.py:652 semantic_distance: float = 0.0`), no como módulo de scoring.

Las 28 brechas restantes agrupan en **17 módulos ausentes**. Verificado por búsqueda en `src/` (excluyendo `registry.py`, `taxonomy.py`, `execution.py`): **ninguno tiene consumer real en el runtime**. `scoring/` (intelligence) solo aparece en comentarios; `signals.topics`/`signals.convergence`/`problems.pain_points`/`retrieval.*`/`invention.biomimicry`/`graph.embeddings`/`prior_art.query_lattice` no se importan en ningún módulo de producción.

Disposición: **DEFERRED** (no RESEARCH_ONLY ni BLOCKED) — causa: implementarlas sin consumer sería código muerto, y el mandato §10 prohíbe crear componentes por la cifra. Se implementarán cuando exista contrato de consumidor o wiring real.

| Módulo | IDs | Consumer |
|---|---|---|
| `scoring.novelty` (T081) | T081 | **IMPLEMENTED_NOT_WIRED**: `criba/scoring/novelty.py` existe con tests (`test_mcda.py`), pero el campo `contracts.py:648 local_novelty` queda en `0.0` por defecto: ninguna ruta de producción lo calcula. |
| `scoring.novelty` (T083 T084 T085) | T083 T084 T085 | solo campos de contrato (`contracts.py`), sin implementación |
| `scoring.evidence` | T100 T103 T115 | **Módulo existe** (`intelligence/scoring/evidence.py`), pero NO implementa T100/T103/T115: define `confidence()` (T104) y `feasibility()` (T111) + `mcda_inputs`/`mcda_sources`. T100/T103/T115 siguen PLANNED sin función. Sin consumer de producción. |
| `scoring.opportunity` | T107 T113 | ninguno |
| `scoring.prototypeability` | T112 T114 | ninguno |
| `scoring.competition` | T108 T109 | ninguno |
| `scoring.confidence` | T104 | **Desfase de ruta (mismo tipo que T081, dirección opuesta):** el canon declara módulo `criba.intelligence.scoring.confidence` (fichero inexistente); la implementación real vive como función `confidence()` dentro de `intelligence/scoring/evidence.py`. Verificado: `confidence()`/`feasibility()` existen; `scoring/confidence.py` y `scoring/feasibility.py` NO existen como ficheros. Test real: `tests/intelligence/test_t104_t111_scoring.py`. Sin consumer de producción. |
| `scoring.feasibility` | T111 | **Desfase de ruta:** idem. Canon declara `criba.intelligence.scoring.feasibility` (inexistente); la función `feasibility()` vive en `intelligence/scoring/evidence.py`. Sin consumer de producción. |
| `scoring.trl` | T102 | ninguno |
| `signals.topics` | T046 T050 T051 | ninguno |
| `signals.convergence` | T052 T079 | ninguno |
| `problems.pain_points` | T021 | ninguno |
| `retrieval.decomposition` | T036 | ninguno |
| `retrieval.semantic` | T031 | ninguno |
| `retrieval.query_mutation` | T122 | ninguno |
| `invention.biomimicry` | T056 | ninguno |
| `graph.embeddings` | T093 | ninguno |
| `prior_art.query_lattice` | T121 | ninguno |

## 7. Pendiente y siguiente acción

- 28 ACTIONABLE_GAP: DEFERRED (sin consumer real, verificado).
- Propuesta de integración a main: preparar (qué contenido, de dónde, qué sustituye, qué conserva, evidencia) — NO ejecutar.
- Instrumento funcional (§13): BLOCKED por falta de artefacto evaluable.
- Aprobación esquema ledger: PENDING.
