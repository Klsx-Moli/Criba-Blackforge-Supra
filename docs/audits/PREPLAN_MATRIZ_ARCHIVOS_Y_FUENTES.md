# MATRIZ ARCHIVO POR ARCHIVO — PREPLAN (143 remotas + delta local)

**Fecha:** 2026-10-22 · **SHA de referencia:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Fuentes unificadas:** matriz de riesgos recibida (143 rutas del diff remoto) + delta local nuevo + documentos/fuentes recibidas.

Vocabulario: `OBSERVED`, `STATIC_INSPECTION`, `PREVIOUS_REPORT`, `INFERENCE`, `NOT_VERIFIED`, `SUPERSEDED`.

---

## 1. Limitación declarada de la matriz recibida

**`FACT`:** la matriz recibida (`CBS_MATRIZ_RIESGOS_143_RUTAS_RECONSTRUIDA.csv/.md`) cubre **143 rutas del diff remoto** de referencia (`base_sha=defd0fd`, `candidate_sha=b07147b`), con `scope=PROPOSED_TRIAGE_NOT_EXECUTED_FINDING`. Es **triaje propuesto**, no revisión íntegra de cada archivo.

**`FACT`:** la matriz recibida **no contiene** las rutas nuevas del delta local de esta sesión (`criba_adapter.py`, `harness.py`, `pilot_ledger_schema.py`, tests de F5). El MD la menciona 3 veces; el CSV, 0.

**`FACT`:** la matriz recibida declara 24 GREEN / 112 YELLOW / 7 ORANGE / 1 RED = 144 (143 rutas + cabecera). Es **triaje de integración, no 143 bugs**.

---

## 2. Filas del delta local (esta sesión)

| Ruta | Origen/ref | Componente | Remoto | Local/delta | Contrato | Riesgo | Leído/probado | Disposición | Siguiente acción |
|---|---|---|---|---|---|---|---|---|---|
| `criba-blackforge/benchmarks/innovation/criba_adapter.py` | delta local | benchmark | no en diff remoto | MODIFICADO (+113/-9) | informe ligado a invocación | ORANGE | leído, probado (39 tests) | PORT_CANDIDATE | revisión con SHA propio |
| `criba-blackforge/benchmarks/innovation/harness.py` | delta local | benchmark | no en diff remoto | MODIFICADO (+18/-9) | contrato C_CRIBA | ORANGE | leído, probado | PORT_CANDIDATE | revisión con SHA propio |
| `criba-blackforge/tests/unit/test_selection_report_attribution.py` | nuevo | test | — | NUEVO | atribución F5 | YELLOW | probado (7 tests) | KEEP | añadir a suite |
| `criba-blackforge/tests/unit/test_selection_report_persistence.py` | nuevo | test | — | NUEVO | persistencia F5 | YELLOW | probado (4 tests) | KEEP | añadir a suite |
| `docs/audits/pilot_ledger_schema.py` | nuevo | doc/tooling | — | NUEVO | esquema ledger sintético | YELLOW | probado (validación) | KEEP | validar cobertura real |

**Disposición `PORT_CANDIDATE` = recomendación, NO permiso de port.** No se integran ramas ni se copia producto.

---

## 3. Filas de fuentes recibidas (no runtime)

| Ruta | SHA256 (16) | Alcance | Estado | Disposición |
|---|---|---|---|---|
| `C:\Users\KLSX\Downloads\CBS_MATRIZ_RIESGOS_143_RUTAS_RECONSTRUIDA.csv` | `2cf4c30df539f8bd` | triaje 143 rutas | leído | HISTORICAL_PRESERVED |
| `...\CBS_MATRIZ_RIESGOS_143_RUTAS_RECONSTRUIDA.md` | `ab5fce5eedddb5a0` | triaje (MD) | leído | HISTORICAL_PRESERVED |
| `...\CBS_VERIFICACION_HASH_Y_CORRECCION_LEDGER.json` | `427aeacd6c00ac3b` | hashes + corrección | leído | HISTORICAL_PRESERVED |
| `...\CBS_ADENDA_EJECUTIVA_STEER_Y_CONFLICTOS_20261022.md` | `51570f2976c342a9` | adenda ejecutiva | leído | HISTORICAL_PRESERVED |
| `...\VERIFICAR_CBS_SHA256_SOLO_LECTURA.py` | `49a0f5ee939862c0` | verificador | inspeccionado | HISTORICAL_PRESERVED |
| `...\PROMPT_10_CONCILIACION_LEDGER.md` | `6aa9e61078b3be9c` | informe F5/ledger | leído | SUPERSEDED (por corrección 10/35) |
| `...\PROMPT_10_DEFECTOS_F2_F5.md` | `3fcba5a2027380dd` | informe F5 | leído | HISTORICAL_PRESERVED |
| `...\PROMPT_10_LEDGER_ESQUEMA.md` | `bd790fe1d4c9964b` | esquema | leído | SUPERSEDED (por corrección 10/35) |
| `...\PROMPT_10_CONCILIACION_PREREGISTRO.md` | `321257732d18ec85` | conciliación | leído | HISTORICAL_PRESERVED |
| `...\PROMPT_10_ESTADO_BRAZOS_Y_BLOQUEOS.md` | `64d23044a2f63b38` | brazos | leído | HISTORICAL_PRESERVED |
| `...\PROMPT_10_PREFLIGHT_CIENTIFICO.md` | `a7f0bf5608d8eb13` | preflight | leído | HISTORICAL_PRESERVED |
| `...\ESTATUTO_EXCELENCIA_INTEGRIDAD_MEJORA_CONTINUA.md` | `fc4d2fd4f640de07` | Estatuto | íntegro | KEEP (fuente autoritativa) |
| `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (canónico) | `c9dcea221ac10edf` | canónico PROMPT 10 | íntegro | KEEP (fuente de verdad) |

**Fuentes NO localizadas en el scope de búsqueda (`C:\Users\KLSX\Downloads`):**
- `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` — vive en `C:\ASTRA_WORK\PLAN_MAESTRO_RECONCILIADO_...\prompts\` (hash verificado).
- `06_PROTOCOLO_CIENTIFICO_Y_PILOTO.md` — misma ubicación.
- ZIP/MD/guía del paquete CBS anterior — **NOT_ACCESSIBLE_FILE_NOT_PRESENT**.

---

## 4. Ficheros que no conviene distribuir como runtime

| Tipo | Ejemplos | Disposición |
|---|---|---|
| locks/PIDs históricos | `.git/index.lock`, `CribaShadow.lock` | HISTORICAL_PRESERVED (no borrar) |
| logs | `logs/*.log` | HISTORICAL_PRESERVED |
| scratch/fixtures de evaluación | `docs/audits/_backup_20261022/`, `audits.rar` | HISTORICAL_PRESERVED |
| secretos | `.env`, `auth.json` | NO respaldar en paquete compartido |

---

## 5. Contradicciones detectadas y resolución

| # | Contradicción | Fuente exacta | Resolución |
|---|---|---|---|
| C1 | Ledger: «15 campos» vs «10 requisitos / 35 campos» | directiva sesión vs canónico `c9dcea22…` | resuelta por decisión de organización sometida a cobertura |
| C2 | Recuento «9 requisitos» vs **10** | resúmenes previos (Perplexity/Hermes) | corregido; error de transcripción, hashes coinciden |
| C3 | Recuento «27 campos» vs **35** | esquema previo | corregido por ejecución |
| C4 | «opportunity_accounting descartado» vs «productor no ejecutado» | informe F5 | corregido: el productor (`invent()`) no se ejecuta en la ruta benchmark |
| C5 | Matriz recibida sin rutas locales nuevas | CSV vs delta local | documentado; se añaden filas §2 |
| C6 | `PROMPT_00.B1` vs `PROMPT_10.B1` | distintos ámbitos | namespaces separados (ya eran distintos) |

**No se reescribe historia.** Las cifras antiguas se conservan con corrección fechada.

---

## 6. Estados invariables

```
PREREGISTRATION_STATUS              = NOT_APPROVED
LEDGER_SCHEMA_STATUS                = PENDING — NOT APPROVED
A_DIRECT_STATUS                     = BLOCKED
B_STRONG_PROMPT_STATUS              = BLOCKED
C_CRIBA_STATUS                      = EXECUTABLE
F2_STATUS                           = NOT_A_DEFECT
F3_STATUS                           = OPEN — BLOQUEANTE
F4_STATUS                           = CONFIRMED_LIMITATION
F5_STATUS                           = CORREGIDO_LOCALMENTE (verificado con tests; SHA de revisión pendiente)
PILOT_EXECUTION_ALLOWED             = NO
SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED = NO
```
