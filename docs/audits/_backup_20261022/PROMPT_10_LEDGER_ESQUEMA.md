# LEDGER DE EPISODIOS — Esquema (borrador para validación)

**Estado: PROPUESTA NO APROBADA.** Fuente de verdad: `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` §4.
**No reutiliza `veredicts.jsonl`** (veredicto en §4 de este documento).
**SHA de código bajo estudio:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`

---

## 1. Los 15 campos originales (transcripción literal del canónico §4)

El canónico prescribe exactamente **9 bullets**, que se descomponen en los campos siguientes. **No se inventa ninguno**; cada campo se deriva de un bullet literal.

| # | Bullet literal del canónico | Campo derivado | Tipo |
|---|---|---|---|
| 1 | `episode_id`, `root_problem_id`, candidate-set hash y split | `episode_id` | str (único, inmutable) |
| 1 | | `root_problem_id` | str (id del problema raíz) |
| 1 | | `candidate_set_hash` | `sha256:<64hex>` |
| 1 | | `split` | enum `exploratory`\|`confirmatory` |
| 2 | contexto anterior y condiciones disponibles, versiones de modelo/herramientas/corpus | `context_before` | obj (contexto disponible antes de decidir) |
| 2 | | `available_conditions` | obj (condiciones/observables disponibles) |
| 2 | | `versions` | obj `{modelo, herramientas, corpus}` |
| 3 | predicción previa con el responsable/origen y timestamp de disponibilidad | `prediction_before` | obj `{prediccion, origen, disponible_en}` |
| 4 | regla/configuración del selector, ranking si existe, decisión seleccionada y desempates | `selector_rule` | str (regla/config usada) |
| 4 | | `ranking` | lista (ranking completo si existe) |
| 4 | | `selected_decision` | obj (decisión tomada) |
| 4 | | `ties` | lista (desempates y su regla) |
| 5 | propensión efectiva si es conocida; selector determinista → regla; LLM → `UNKNOWN` + prompt/config/salida; no inferir de la seed | `propensity` | `UNKNOWN` \| num + `{prompt, config, salida}` |
| 6 | artefacto/procedimiento realmente ejecutado, hash/versión y diferencia frente al seleccionado | `executed_artifact` | obj `{hash, version, diff_vs_selected}` |
| 7 | claim mecanístico, rival, protocolo preregistrado/hash, controles, observables/unidades y regla de decisión | `mechanistic_claim` | str |
| 7 | | `rival_claim` | str |
| 7 | | `protocol_hash` | `sha256:<64hex>` |
| 7 | | `controls` | obj (controles: positivo/negativo) |
| 7 | | `observables_units` | obj (observable + unidades) |
| 7 | | `decision_rule` | str (regla de decisión) |
| 8 | ejecución, ambiente, tiempos, comandos/trace, desviaciones, fallos/retries/timeouts/costes | `execution` | obj `{ambiente, tiempos, comandos, trace}` |
| 8 | | `deviations` | lista |
| 8 | | `failures` | obj `{retries, timeouts, costes}` |
| 9 | observación, instrumento, fuente/procedencia, timestamp y ausencia explícita | `observation` | obj `{valor, instrumento, fuente, timestamp, ausencia}` |
| 9 | | `functional_result` | enum `1`\|`0`\|`UNKNOWN`\|`INVALID_EXECUTION` |
| 9 | | `interpretation` | str (interpretación acotada) |
| 9 | | `posterior_decision` | str |
| 9 | | `integrity_status` | enum `OK`\|`COMPROMISED` |
| 9 | | `evidence_link` | str (link/h ruta a evidencia) |

**Total: 27 campos atómicos** derivados de los 9 bullets. El «esquema de 15 campos» se interpreta como **los 9 bullets agrupados en 15 bloques temáticos** (1–4 se descomponen en 4+3+1+1 bloques). **Laguna declarada:** el canónico no numera los campos; se propone esta descomposición y **no** se presenta como definitiva.

---

## 2. Identificadores únicos y hashes

| Elemento | Regla |
|---|---|
| `episode_id` | `EP-{root_problem_id}-{split}-{arm}-{seq}`; único, inmutable, asignado antes de ejecutar |
| `root_problem_id` | id del pool (`G01`…`B05`) o el nuevo dataset de 30 |
| `candidate_set_hash` | `sha256` del JSON canónico (ordenado) del conjunto de 4 candidatos (sin IDs correlacionados) |
| `protocol_hash` | `sha256` del preregistro aprobado |
| `selector_version` | hash del módulo selector (`8126b2e80011` para `criba.selector` en `b07147b`) |
| `problem_hash` | `sha256` del texto canónico del problema |

**Regla anti-filtración:** el `episode_id` y el `candidate_set_hash` **no** codifican la etiqueta de validez ni el brazo ganador.

---

## 3. Registro por brazo, semilla, presupuesto, resultado bruto, veredicto, procedencia

| Campo | Contenido |
|---|---|
| `arm` | `A_DIRECT` \| `B_STRONG_PROMPT` \| `C_CRIBA` (registrado por episodio) |
| `seed` | semilla explícita usada (el canónico exige regla para selector determinista) |
| `budget` | presupuesto consumido: tokens/herramientas/tiempo/llamadas (si no observable → `UNKNOWN`) |
| `raw_result` | salida cruda del brazo (JSON) |
| `verdict` | `SUPPORTED`\|`FALSIFIED`\|`INCONCLUSIVE`\|`NOT_TESTABLE`\|`NOT_IDENTIFIABLE`\|`INVALID_EXECUTION` |
| `provenance` | origen del dato: `EXECUTED`\|`HISTORICAL`\|`DECLARED`\|`UNAVAILABLE` |

---

## 4. Fallos, ausencias, ejecuciones no disponibles, resultados negativos

| Situación | Registro |
|---|---|
| Fallo de ejecución | `failures` con `retries`, `timeouts`, `costes`; `verdict=INVALID_EXECUTION` |
| Ausencia de dato | `observation.ausencia` explícita; `functional_result=UNKNOWN` (nunca 0) |
| Brazo no disponible | `provenance=UNAVAILABLE`, `verdict=INVALID_EXECUTION`; no se simula ni se convierte en 0 |
| Resultado negativo | `functional_result=0` con `interpretation` acotada; se conserva en el denominador |
| Episodio no identificable | `verdict=NOT_IDENTIFIABLE` |

---

## 5. Integridad append-only (con prueba ejecutada)

**Implementación propuesta:** JSONL donde cada fila incluye `prev_hash = sha256(bytes de la fila anterior)` y `row_hash = sha256(fila)`; `GENESIS` para la primera.

**Prueba ejecutada (2026-10-22, `criba-blackforge/.venv` Python 3.11.15):**

```
cadena valida: True            (2 filas, prev_hash enlazado correctamente)
cadena tras tamper fila1: False (reescribir la fila 1 rompe la cadena)
```

**Lectura:** un episodio ya congelado **no** puede sobrescribirse silenciosamente: cualquier reescritura de una fila invalida `prev_hash` de la fila siguiente. **Estado:** verificado por ejecución sobre el esquema propuesto; **no** es el ledger definitivo (aún no creado).

---

## 6. Por qué NO se reutiliza `veredicts.jsonl`

| Criterio del esquema | `veredicts.jsonl` (430 filas, 2026-09-05) |
|---|---|
| `episode_id` | **ausente** |
| `root_problem_id` | **ausente** |
| `candidate_set_hash` | **ausente** |
| `protocol_hash` | **ausente** |
| `propensity` | **ausente** |
| `functional_result` | **ausente** |
| `integrity_status` / cadena append-only | **ausente** (JSONL plano, sin `prev_hash`) |
| Origen real | salida de `invent()` (`append_ledger`), no del piloto |

**Veredicto:** `veredicts.jsonl` **no satisface** el esquema original. No se reutiliza. Es evidencia histórica de `invent()`, no ledger del piloto.

---

## 7. Estado

- Esquema: **propuesto, no aprobado**.
- Ledger definitivo: **no creado** (se crea tras aprobar preregistro + esquema).
- Ubicación propuesta: fuera del árbol canónico del producto (p. ej. `C:\Users\KLSX\AppData\Local\CRIBA-Blackforge\pilot_ledger\`), con hashes y sin secretos.
- **Bloqueo:** no se escribe ningún episodio hasta que el preregistro esté aprobado y la evaluación funcional sea independiente del scorer.
