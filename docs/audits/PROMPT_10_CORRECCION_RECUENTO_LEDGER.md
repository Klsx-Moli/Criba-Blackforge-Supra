# CORRECCIÓN DEL RECUENTO DEL LEDGER — PROMPT 10

**Fecha:** 2026-10-22
**Fuente canónica (verificada por SHA-256):**
`PROMPT_10_PILOTO_SELECTOR_CRIBA.md` — `c9dcea221ac10edf5f1bed330b12621afec912dfb2ccf6672f03b514914a851c`
Coincide con la copia adjunta por el propietario. El canónico **no vive en el repo**: reside en `C:\ASTRA_WORK\PLAN_MAESTRO_RECONCILIADO_CRIBA_BLACKFORGE_SUPRA_2026-10-20 (2)\...\prompts\`.

Vocabulario: `FACT` (verificado en esta sesión), `REPORTED`, `INFERENCE`, `NOT_VERIFIED`.

---

## 1. Recuento correcto

| Concepto | Valor | Evidencia |
|---|---|---|
| **Requisitos del ledger (§4)** | **10** | 10 bullets tras «como mínimo» |
| **Estados semánticos (§4)** | **5** | `UNKNOWN`, `INCONCLUSIVE`, `INVALID_EXECUTION`, `NOT_IDENTIFIABLE`, `FALSIFIED`/`SUPPORTED` — **no son apartados del esquema** |
| **Campos atómicos derivados (esquema)** | **35** | verificado por ejecución (`pilot_ledger_schema.py`) |
| **Bloques temáticos (presentación)** | **15** | agrupación, no numeración canónica |

**Corrección del error histórico:** el recuento de **«9 requisitos»** era **incorrecto**. Apareció en resúmenes previos (Perplexity y Hermes) y en los documentos de PROMPT 10. El canónico tiene **10 requisitos**. Los hashes coinciden, por lo que **no es un cambio del canónico**: es un error de transcripción de los resúmenes.

**No se reemplaza globalmente «9» por «10» ni «27» por «35».** Cada aparición se distingue:
- Afirmación histórica incorrecta → se corrige con procedencia.
- Descripción vigente → se actualiza a 10 requisitos / 35 campos.
- Número de requisito → 10.
- Campos derivados → 35.
- Bloques de presentación → 15.

---

## 2. Correspondencia requisito → campo/subcampo → validación → prueba negativa

| # | Requisito literal (§4) | Campo(s) | Tipo / cardinalidad | Missingness | Validación | Prueba negativa |
|---|---|---|---|---|---|---|
| R1 | `episode_id`, `root_problem_id`, candidate-set hash y split | `episode_id`, `root_problem_id`, `candidate_set_hash`, `split` | str/str/`sha256`/enum | `episode_id` nunca nulo; `split` enum | `split ∈ {exploratory, confirmatory}` | fila con `split="dev"` → FAIL |
| R2 | contexto anterior y condiciones disponibles, versiones de modelo/herramientas/corpus | `context_before`, `available_conditions`, `versions.{modelo,herramientas,corpus}` | obj/obj/obj | `versions` puede ser `UNKNOWN` | 3 subcampos presentes | falta `corpus` → FAIL |
| R3 | predicción previa con el responsable/origen y timestamp de disponibilidad | `prediction_before.{prediccion, origen, disponible_en}` | str/str/ISO8601 | `origen` requerido | timestamp parseable | `disponible_en` no fecha → FAIL |
| R4 | regla/configuración del selector, ranking si existe, decisión seleccionada y desempates | `selector_rule`, `ranking`, `selected_decision`, `ties` | str/lista/obj/lista | `ranking` puede ser vacío si no existe | `ties` lista | `ties` es str → FAIL |
| R5 | propensión efectiva; determinista → regla; LLM → `UNKNOWN` + prompt/config/salida; no inferir de la seed | `propensity` | `UNKNOWN` \| num + `{prompt, config, salida}` | `UNKNOWN` explícito permitido | no numérica sin contexto | numérica sin `prompt` → FAIL |
| R6 | artefacto realmente ejecutado, hash/versión y diferencia frente al seleccionado | `executed_artifact.{hash, version, diff_vs_selected}` | `sha256`/str/obj | `hash` puede ser `UNKNOWN` | distingue seleccionado vs ejecutado | `diff_vs_selected` ausente → FAIL |
| R7 | claim mecanístico, rival, protocolo preregistrado/hash, controles, observables/unidades y regla de decisión | `mechanistic_claim`, `rival_claim`, `protocol_hash`, `controls`, `observables_units`, `decision_rule` | str/str/`sha256`/obj/obj/str | `protocol_hash` `UNKNOWN` si no hay protocolo | 6 campos | falta `decision_rule` → FAIL |
| R8 | ejecución, ambiente, tiempos, comandos/trace, desviaciones, fallos/retries/timeouts/costes | `execution.{ambiente, tiempos, comandos, trace}`, `deviations`, `failures.{retries, timeouts, costes}` | obj/lista/obj | `costes` puede ser `UNKNOWN` | subcampos presentes | falta `costes` → FAIL |
| R9 | observación, instrumento, fuente/procedencia, timestamp y ausencia explícita | `observation.{valor, instrumento, fuente, timestamp, ausencia}` | obj | `valor` puede ser nulo | `ausencia` explícita | `ausencia` implícita → FAIL |
| R10 | resultado funcional, interpretación acotada, decisión posterior, estado de integridad y link a evidencia | `functional_result`, `interpretation`, `posterior_decision`, `integrity_status`, `evidence_link` | enum/str/str/enum/str | `functional_result` nunca 0 por ausencia | enum válido | `functional_result=0` sin interpretación → FAIL |

**Total: 10 requisitos → 35 campos atómicos (hojas) + 15 bloques de presentación.**

---

## 3. Estados separados de la cobertura

| Estado | Valor vigente | Fuente |
|---|---|---|
| `LEDGER_DESIGN_DECISION` | `ACCEPTED_WITH_COVERAGE_CHECK` | propietario 2026-10-22 |
| `LEDGER_SCHEMA_STATUS` | `PENDING — NOT APPROVED` | aprobación explícita pendiente |
| `PREREGISTRATION_STATUS` | `NOT_APPROVED` | propietario |
| `PILOT_EXECUTION_ALLOWED` | `NO` | — |
| `SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED` | `NO` | — |

**Separación de capas (no son equivalentes):**
- **DECISIÓN DE ORGANIZACIÓN ACEPTADA** — el propietario aceptó la estructura de trabajo (10 requisitos → 35 campos → 15 bloques) **sometida a cotejo de cobertura**.
- **COBERTURA DOCUMENTAL** — la tabla §2 (requisito → campo) está construida; no implica datos reales.
- **VALIDACIÓN ESTRUCTURAL/SINTÉTICA** — `pilot_ledger_schema.py` valida forma con fila **sintética** (`SYNTHETIC / NOT_EXPERIMENTAL_EVIDENCE`).
- **COBERTURA EN DATOS REALES PREEXISTENTES** — **PENDIENTE**: no hay datos no sintéticos autorizados; no se ejecuta el piloto para producirlos.
- **APROBACIÓN DEL ESQUEMA** — **PENDIENTE** (propietario).
- **APROBACIÓN DEL PRERREGISTRO** — **PENDIENTE** (propietario).
- **AUTORIZACIÓN DE EJECUCIÓN** — **NO**.

**Nota de autoridad:** la aceptación del propietario se dio sobre una propuesta que decía «27 campos». El recuento correcto es **35**. No se atribuye al propietario una aprobación de 35 campos: se conserva la **aceptación de organización** y se registra la **corrección de conteo** con su procedencia (esta sesión). Son decisiones distintas.

---

## 4. Hash chain — alcance real

**`FACT`:** la cadena de hashes (`prev_hash` por fila) es **tamper-evident**, no **append-only enforced**. Detecta alteraciones respecto a un ancla confiable, pero:
- **no impide** reescribir el archivo y recalcular toda la cadena;
- requiere una **ancla confiable** externa (no solo el propio archivo);
- no garantiza **atomicidad** de escritura ante fallo;
- no resuelve **concurrencia** de escritura (dos procesos escribiendo a la vez).

**Declaración:** el esquema es **tamper-evident bajo supuestos** (escritor único, sin reescritura, ancla externa). **No** se declara append-only enforced.

---

## 5. Corrección de documentos afectados

| Documento | Antes (incorrecto) | Después (correcto) |
|---|---|---|
| `PROMPT_10_LEDGER_ESQUEMA.md` | «9 bullets», «27 campos» | «10 requisitos», «35 campos atómicos», «15 bloques» |
| `PROMPT_10_CONCILIACION_LEDGER.md` | «9 bullets», «27 campos» | «10 requisitos», «35 campos atómicos», «15 bloques» |
| `PROMPT_10_INDICE_ESTADO_Y_CRONOLOGIA.md` | «9 apartados → 27 campos» | «10 requisitos → 35 campos» |
| `PROMPT_10_PREFLIGHT_CIENTIFICO.md` | «9 bullets» | «10 requisitos» |

**Historial conservado:** las cifras 9 y 27 se preservan como error histórico con su corrección fechada, no se sobrescriben sin trazabilidad.
