# CONCILIACIÓN DEL LEDGER — PROMPT 10

**Fecha:** 2026-10-22 · **SHA observado:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Fuentes:** `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` §4 (canónico), `docs/audits/PROMPT_10_LEDGER_ESQUEMA.md`.

Vocabulario: `FACT`, `INFERENCE`, `NOT_EXECUTED`, `NOT_ACCESSIBLE`.

---

## 0. Resolución de la discrepancia prioritaria

**`FACT` (verificado por inspección del canónico):** el canónico §4 dice literalmente *"Cada fila debe incluir como mínimo:"* seguido de **10 requisitos** (bullets, líneas 43–54) y, aparte, **5 estados semánticos** (no son apartados del esquema). **No menciona ningún número de campos.**

**`FACT` (verificado):** la búsqueda de «15 campos / 15 fields / quince» en todo el paquete `PLAN_MAESTRO_RECONCILIADO_...2026-10-20` devuelve **0 resultados**.

**Resolución documental:** la «referencia previa a un ledger de 15 campos» **no procede del canónico**. Procede de la **directiva de la sesión** y de la **interpretación del propio esquema** («bloques temáticos»).

**No son equivalentes:**
- **Apartado canónico** = 1 bullet (9 en total).
- **Bloque temático** = agrupación de campos por tema (15, interpretación del esquema).
- **Campo de datos** = 1 dato atómico (**35** derivados de los 10 requisitos; recuento corregido y verificado por ejecución).

**Estado de la discrepancia (2026-10-22):** `DISCREPANCIA DOCUMENTADA — DECISIÓN DEL PROPIETARIO ACEPTADA CON COBERTURA`. El propietario aceptó la estructura de trabajo (10 requisitos → 35 campos → 15 bloques) **sometida a cotejo de cobertura** y retiró la exigencia de exactamente 15 campos atómicos. `LEDGER_SCHEMA_STATUS = PENDING — NOT APPROVED` hasta la aprobación explícita del esquema y la validación de cobertura sobre datos no sintéticos.

---

## 1. Tabla fila por fila (elemento canónico → campo de ledger)

| ID canónico | Texto exacto (línea) | Campo(s) de ledger | Tipo / semántica | Correspondencia | Evidencia | Decisión pendiente |
|---|---|---|---|---|---|---|
| B1a | "`episode_id`" (43) | `episode_id` | str único inmutable | **directa** | esquema §2 | — |
| B1b | "`root_problem_id`" (43) | `root_problem_id` | str | **directa** | esquema §2 | — |
| B1c | "candidate-set hash" (43) | `candidate_set_hash` | `sha256:<64hex>` | **derivación explícita** (hash canónico) | esquema §2 | formato del hash (¿del set JSON o del texto?) — pendiente |
| B1d | "y split" (43) | `split` | enum `exploratory`\|`confirmatory` | **directa** | esquema §1 | — |
| B2a | "contexto anterior" (44) | `context_before` | obj | **directa** | esquema §1 | — |
| B2b | "condiciones disponibles" (44) | `available_conditions` | obj | **directa** | esquema §1 | — |
| B2c | "versiones de modelo/herramientas/corpus" (44) | `versions` | obj `{modelo, herramientas, corpus}` | **derivación explícita** (3 subcampos) | esquema §1 | — |
| B3a | "predicción previa" (45) | `prediction_before.prediccion` | str | **directa** | esquema §1 | — |
| B3b | "con el responsable/origen" (45) | `prediction_before.origen` | str | **directa** | esquema §1 | — |
| B3c | "y timestamp de disponibilidad" (45) | `prediction_before.disponible_en` | ISO8601 | **directa** | esquema §1 | — |
| B4a | "regla/configuración del selector" (46) | `selector_rule` | str | **directa** | esquema §1 | — |
| B4b | "ranking si existe" (46) | `ranking` | lista | **directa** | esquema §1 | — |
| B4c | "decisión seleccionada" (46) | `selected_decision` | obj | **directa** | esquema §1 | — |
| B4d | "y desempates" (46) | `ties` | lista | **derivación explícita** | esquema §1 | — |
| B5a | "propensión efectiva si es conocida" (47) | `propensity` | num \| `UNKNOWN` | **directa** | esquema §1 | — |
| B5b | "para un selector determinista registrar regla" (47) | `propensity` (valor=regla) | str | **derivación explícita** | esquema §1 | — |
| B5c | "para LLM con probabilidad desconocida, `UNKNOWN` más prompt/configuración/salida" (47) | `propensity.{prompt,config,salida}` | obj | **derivación explícita** | esquema §1 | — |
| B5d | "no inferir propensión de la seed" (47) | regla de no-inferencia | — | **restricción** | esquema §1 | — |
| B6a | "artefacto/procedimiento realmente ejecutado" (48) | `executed_artifact` | obj | **directa** | esquema §1 | — |
| B6b | "hash/versión" (48) | `executed_artifact.{hash,version}` | `sha256` | **derivación explícita** | esquema §1 | — |
| B6c | "y diferencia frente al seleccionado" (48) | `executed_artifact.diff_vs_selected` | obj | **derivación explícita** | esquema §1 | — |
| B7a | "claim mecanístico, rival" (49) | `mechanistic_claim`, `rival_claim` | str | **derivación explícita** (2 campos) | esquema §1 | — |
| B7b | "protocolo preregistrado/hash" (49) | `protocol_hash` | `sha256:<64hex>` | **derivación explícita** | esquema §1 | — |
| B7c | "controles" (49) | `controls` | obj | **directa** | esquema §1 | — |
| B7d | "observables/unidades" (49) | `observables_units` | obj | **derivación explícita** | esquema §1 | — |
| B7e | "y regla de decisión" (49) | `decision_rule` | str | **directa** | esquema §1 | — |
| B8a | "ejecución, ambiente, tiempos, comandos/trace" (50) | `execution` | obj | **derivación explícita** | esquema §1 | — |
| B8b | "desviaciones" (50) | `deviations` | lista | **directa** | esquema §1 | — |
| B8c | "fallos/retries/timeouts/costes" (50) | `failures` | obj | **derivación explícita** | esquema §1 | — |
| B9a | "observación, instrumento, fuente/procedencia, timestamp y ausencia explícita" (51) | `observation` | obj | **derivación explícita** | esquema §1 | — |
| B9b | "resultado funcional" (52) | `functional_result` | enum `1`\|`0`\|`UNKNOWN`\|`INVALID_EXECUTION` | **derivación explícita** | esquema §1 | — |
| B9c | "interpretación acotada, decisión posterior, estado de integridad y link a evidencia" (52) | `interpretation`, `posterior_decision`, `integrity_status`, `evidence_link` | — | **derivación explícita** | esquema §1 | — |

**Recuento (corregido):** 10 requisitos → **35 campos atómicos** → **15 bloques temáticos** (1–4 agrupan 4+3+1+1). **Ningún campo inventado.**

---

## 2. Comprobaciones de propiedades (por separado)

| Propiedad exigida | Estado | Evidencia |
|---|---|---|
| Append-only | **FACT verificado** | prueba de cadena: válida `True`; tras tamper fila1 `False` |
| Detección de alteraciones | **FACT verificado** | la prueba de tamper rompe `prev_hash` de la fila siguiente |
| Identidad de episodio única | **PARTIAL** | esquema define `EP-{root}-{split}-{arm}-{seq}`; **no ejecutado** (ledger no creado) |
| Hashes (problema, set, protocolo, selector) | **PARTIAL** | definidos; **no ejecutados** |
| Campos completos | **FACT (derivación)** | 35/35 derivados de los 10 requisitos |
| Cadena de integridad como prueba de completitud | **NO** | una prueba de integridad **no** demuestra que el esquema tenga todos los campos correctos — se verifica por la tabla §1 |

**Nota:** la prueba de cadena de integridad es **necesaria pero no suficiente**. La completitud de campos se demuestra por la tabla §1 (derivación bullet a bullet), no por la prueba de integridad.

---

## 3. Estado

`LEDGER_SCHEMA_STATUS = PENDING — NOT APPROVED` (se conserva).

**Motivos:** (1) discrepancia entre «15 campos» (directiva) y «10 requisitos / 35 campos» (canónico) — resuelta por decisión de organización sometida a cobertura; (2) ledger definitivo **no creado**; (3) identidad de episodio y hashes **no ejecutados**; (4) formato del `candidate_set_hash` sin fijar.

**No se inventa una interpretación para forzar la aprobación.** La decisión humana necesaria: confirmar la descomposición 9→27→15 o exigir 15 campos atómicos (fusión, no invención).
