# PREREGISTRO (BORRADOR — NO APROBADO) — Piloto del selector CRIBA

**Estado: NO APROBADO.** Borrador de preparación científica.
**No sustituye ni modifica `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (fuente canónica).**
**Fecha de redacción:** 2026-10-22
**SHA de código bajo estudio:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` (rama `reconcile/candidate-fix-20261020`)
**Entorno:** Python 3.11.15 (`criba-blackforge/.venv/Scripts/python.exe`), Windows 11, sin servicios LLM/SUPRA activos.

---

## 0. Fuente y alcance

Este borrador se redacta bajo `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (canónico) y `06_PROTOCOLO_CIENTIFICO_Y_PILOTO.md`. **Conserva las definiciones originales del canónico donde este las prescribe** (afirmación, margen 20 pp, unidad, cegamiento, estados semánticos, prohibiciones) y **marca como laguna** lo que el canónico no define con suficiente precisión para ejecutar. No resuelve lagunas con supuestos ocultos.

---

## 1. Hipótesis primaria y explicaciones alternativas

**H1 (afirmación preregistrada, literal del canónico §2):** en esta población limitada de problemas, con el mismo candidate set, contexto y oportunidades de selección, el selector real de CRIBA eleva al menos **20 puntos porcentuales** la proporción de selecciones funcionalmente válidas frente a un prompt fuerte congelado.

**Rivales (registradas ANTES de ejecutar):**
- **H0_PROCESO:** la diferencia observada se explica por defecto de datos/ejecución/medición (artefacto de evaluación no correspondiente, fallo de integridad). → diagnóstico `H0_PROCESS`.
- **H1_POLITICA:** la información discriminante está disponible y representada, pero el selector la usa mal (regla keyword que no resuelve la consulta). → `CAUSE_H1_MODEL_POLICY`.
- **H2_REPRESENTACION:** la información discriminante está disponible antes de decidir, pero el contrato de candidatos pierde una distinción que la consulta preregistrada necesita. → `CAUSE_H2_REPRESENTATION`.
- **H_NULL:** no hay diferencia; el intervalo de Δ cruza 0 o el margen. → `NO_EVIDENCE_OF_CRIBA_ADVANTAGE`.

**Falsadores:** (a) si el IC95 de Δ queda por debajo de +20 pp, el margen preregistrado queda refutado para este alcance; (b) si el IC es demasiado ancho, `INCONCLUSIVE`; (c) si integridad falla, `BENCHMARK_CONTAMINATED`.

---

## 2. Comparadores y contrastes ejecutables

| Brazo | Definición canónica | ¿Ejecutable hoy? | Evidencia |
|---|---|---|---|
| **A_DIRECT** | prompt mínimo «Genera N soluciones…» | **NO** — requiere `model_fn` | `harness.py:27`; `run_condition` sin `model_fn` → `UNAVAILABLE` |
| **B_STRONG_PROMPT** | prompt fuerte congelado, sin CRIBA | **NO** — requiere `model_fn` | `harness.py:30` |
| **C_CRIBA** | selector real de producción | **SÍ** — determinista offline | `criba_fn` verificado: 4 candidatos, reproducible por seed |

**Contraste realmente ejecutable hoy:** C_CRIBA **contra sí mismo bajo variaciones controladas** (p. ej. distintos `seed`), no contra A/B. Esto **no** es el contraste preregistrado y **no** puede usarse para afirmar ni negar la ventaja de CRIBA. Se declara `NOT_EVIDENCE_OF_CRIBA_ADVANTAGE` si se usa como única evidencia.

**Contexto/presupuesto/candidatos:** el canónico exige que ambos brazos reciban *los mismos cuatro candidatos, contexto y oportunidades comparables*. Con A/B no ejecutables, **la igualdad de oportunidades no es demostrable** → `BLOCKED` para el contraste A/B.

---

## 3. Definición operacional de validez funcional y adjudicación independiente

**Laguna declarada:** el canónico exige «evaluación funcional con protocolo independiente del scorer» y un «criterio externo», pero **no define** la operación concreta de validez funcional ni el instrumento.

**Propuesta de borrador (a aprobar, no ejecutada):**
- **Validez funcional** = el candidato seleccionado, ejecutado sobre el problema, satisface una condición observable externa declarada antes de revelar etiquetas (p. ej. «produce un artefacto que cumple la condición X del problema»).
- **Instrumento:** evaluador **ciego al scorer** (no recibe `value_score`, ni `idea_id` correlacionado, ni la etiqueta de control). Requiere: (a) criterio binario 1/0 con regla escrita; (b) evaluador independiente del código de puntuación; (c) control positivo y control negativo en cada episodio.
- **Estado actual:** **INEXISTENTE**. El harness existente mide diversidad/estructura (`duplication_rate`, `family_coverage`, `structural_diversity`), **no** validez funcional. No se sustituye por un score propio (prohibido: `BENCHMARK_CONTAMINATED`).

---

## 4. Endpoint primario, métricas secundarias y margen

- **Endpoint primario (canónico §6):** 1 si el candidato seleccionado satisface los criterios funcionales en ejecución válida; 0 si se demuestra que falla. Las ausencias/invalidaciones se conservan en el denominador.
- **Comparación:** pareada por problema; Δ = tasa_CRIBA − tasa_baseline; **IC 95 %** con método exacto apropiado a los pares (McNemar exacto), **fijado antes** de abrir resultados.
- **Margen de relevancia práctica:** +20 pp (umbral de decisión del piloto, no universal).
- **Métricas secundarias (informativas, no reward):** coste de preparación del candidate set, latencia, reintentos, desacuerdo entre evaluadores, cobertura por tipo de problema.

**Cálculo de potencia (ejecutado, borrador):** con n=30 pares y Δ=20 pp, la potencia de McNemar es alta bajo el escenario favorable, pero el **IC95 cruza el margen** (simulación: n=30 → IC [−0.07, +0.43]). **Conclusión:** n=30 es mínimo operativo, **no** garantiza decidir el margen; el canónico ya lo advierte. No se declara potencia suficiente.

---

## 5. Tamaño muestral y justificación

- **Canónico:** mínimo operativo 30 problemas independientes.
- **Realidad verificada:** el único pool es `problems_smoke.json` con **10** problemas (G01–G05, B01–B05), cuya nota declara «Dataset humo… NO concluye superioridad». **No existe dataset de 30.**
- **Decisión de borrador:** ejecutar el piloto con **N=10 disponible** solo como **exploratorio**, declarando explícitamente N=10 y **no** maquillarlo como el piloto de 30. Para el piloto de 30, hace falta construir 20 problemas adicionales con procedencia y criterios de independencia documentados.
- **Unidad:** problema/episodio raíz. Paráfrasis/seeds/variantes hermanas **no** suman N.

---

## 6. Procedencia de los problemas, inclusión/exclusión, particiones, duplicados

- **Procedencia:** `criba-blackforge/benchmarks/innovation/problems_smoke.json` (10), perfil `general` (5) y `blackforge` (5).
- **Inclusión (propuesta):** problema con resultado externo verificable, alternativas plausibles, ambigüedad funcional auténtica, condición que discrimina.
- **Exclusión (propuesta):** problemas sin observable externo; problemas con respuesta trivial; problemas hermanos/paráfrasis de otro incluido.
- **Particiones:** `exploratory` / `confirmatory` (esquema `criba-llm-paired/1` de `evaluate_product_value.py`). Holdout **no** usado para afinar (si se usa, queda consumido).
- **Control de duplicados:** misma identidad con contenido distinto y viceversa se marcan; no cuentan como unidades nuevas.

**Laguna:** el canónico no prescribe la regla exacta de independencia; se propone la de arriba como candidato a aprobar, **no** como definitiva.

---

## 7. Semillas, presupuestos, contexto y repetición

- **Semilla:** explícita por episodio, registrada. **Nota de borrador:** `invent()` sin seed fija usa seed aleatoria (verificado F7) → **exige seed explícita** en el piloto.
- **Presupuesto:** mismo límite de llamadas/herramientas/tiempo para ambos brazos; si no se puede observar, se limita la afirmación de comparabilidad.
- **Contexto suministrado:** idéntico a ambos brazos (problema + contexto + 4 candidatos).
- **Repetición:** cada problema se ejecuta una vez por brazo; las repeticiones por estabilidad se registran aparte y **no** suman N.

---

## 8. Cegamiento, congelación, orden, filtraciones

- **Cegamiento (canónico §5):** generación/ranking/learning no ven etiquetas de validez, control, resultados reservados, salida del otro brazo, ni IDs correlacionados. Las transformaciones (resumen, embedding, score, cache, nombre de archivo) heredan la restricción.
- **Congelación (canónico §3):** congelar **todas** las selecciones de ambos brazos para **todos** los episodios **antes** de abrir etiquetas y ejecutar la evaluación.
- **Orden:** aleatorizar orden/IDs por episodio, independiente.
- **Contaminación:** declarar `BENCHMARK_CONTAMINATED` si hay acceso prohibido, cambios post hoc de prompts/tareas/criterios/seeds/evaluadores, subconjunto favorable, presupuestos desiguales, omisión de candidatos/intentos/costes, o sustitución de la evaluación independiente por un score propio.

---

## 9. Datos ausentes, multiplicidad, parada, inconcluso

- **Ausencias:** no convertir en cero ni en éxito; conservar en el denominador y registrar la razón (`UNKNOWN`, `INVALID_EXECUTION`).
- **Multiplicidad:** reportar ajuste si se comparan múltiples tipos de problema; no multiplicar métricas en un score arbitrario.
- **Parada (canónica §6):** timebox 10 días naturales, máx. 14 para incidencias técnicas; tope 16 h preparación/auditoría; hasta 60 llamadas principales si la ruta real cabe; sin APIs de pago nuevas; publicar costes reales.
- **Inconcluso:** `INCONCLUSIVE` si los datos son válidos pero no bastan para decidir; `NOT_IDENTIFIABLE` si no se identifica la inferencia; `BLOCKED` si falta una condición esencial.

---

## 10. Versiones y SHA

| Elemento | Valor |
|---|---|
| Código | `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0` |
| Protocolo | este borrador (hash a registrar al aprobar) |
| Datos (problemas) | `problems_smoke.json` (10) |
| Artefactos | por crear (ledger) |

**Firmas de módulos probados (2026-10-22):** selector `8126b2e80011`, engine `d41a9fa71a57`, methods `11f2fc6ddf4c`, diversity_selector `290e02c34b59`, lottery `a38bf9379c9a`, blackforge_selector `8e9328d0f012`, gate `8d7a5a8c485b`, inventar `fdfe79e3743f`.

---

## 11. Plan de análisis (fijado antes de revelar resultados)

1. Congelar selecciones de ambos brazos para todos los episodios.
2. Abrir etiquetas y ejecutar evaluación funcional con instrumento independiente y ciego.
3. Calcular Δ pareado con IC95 (McNemar exacto) y método preregistrado.
4. Clasificar: `SUPPORTED_WITH_SCOPE` (integridad OK e IC respalda +20 pp) / `NO_EVIDENCE_OF_CRIBA_ADVANTAGE` (IC descarta o es ancho) / `INCONCLUSIVE` / `NOT_IDENTIFIABLE` / `INVALID_EXECUTION` / `BENCHMARK_CONTAMINATED`.
5. Reportar costes, fallos, timeouts, desacuerdo y resultados por tipo de tarea.
6. No promover canon, ni añadir ejes/operadores, ni declarar diversidad causal ni superioridad del sistema completo.

---

## 12. Lagunas sin resolver (NO resueltas con supuestos ocultos)

| # | Laguna | Impacto |
|---|---|---|
| L1 | No existe dataset de 30 problemas | N insuficiente; solo exploratorio con N=10 |
| L2 | No existe criterio de resolución por problema | Endpoint 1/0 no evaluable |
| L3 | No existe construcción de 4 candidatos con etiquetas de control | Diseño de candidatos inexistente |
| L4 | No existe instrumento de evaluación funcional independiente | Adjudicación imposible |
| L5 | No existe preregistro previo ni ledger del piloto | Obligatorio antes de abrir resultados |
| L6 | Brazo B no ejecutable sin `model_fn` | Contraste A/B bloqueado |
| L7 | El canónico no prescribe regla exacta de independencia entre problemas | Se propone candidata a aprobar |

## 5. Consistencia de estados entre documentos (verificado 2026-10-22)

| Estado | Valor vigente | Documentos donde aparece | ¿Contradictorio? |
|---|---|---|---|
| `PREREGISTRATION_STATUS` | `NO APROBADO` | PREREGISTRO_BORRADOR §12, CONCILIACION_PREREGISTRO §4 | NO |
| `LEDGER_SCHEMA_STATUS` | `PENDING — NOT APPROVED` | LEDGER_ESQUEMA §7 (corregido), CONCILIACION_LEDGER §3 | NO (tras corrección de «NOT APPROBATED») |
| `A_DIRECT_STATUS` | `BLOCKED` | ESTADO_BRAZOS_Y_BLOQUEOS §1 | NO |
| `B_STRONG_PROMPT_STATUS` | `BLOCKED` | ESTADO_BRAZOS_Y_BLOQUEOS §2 | NO |
| `C_CRIBA_STATUS` | `EXECUTABLE` (tratamiento) | ESTADO_BRAZOS_Y_BLOQUEOS §3 | NO |
| `PILOT_EXECUTION_ALLOWED` | `NO` | todos los informes | NO |
| `SCIENTIFIC_SUPERIORITY_CONCLUSION_ALLOWED` | `NO` | todos los informes | NO |

**Ocho bloqueos (B1–B8)** conservados y **no** descritos como resueltos en ningún documento:
B1 dataset 30 inexistente · B2 sin criterio de resolución · B3 sin candidatos etiquetados · B4 sin instrumento funcional · B5 prerregistro no aprobado · B6 ledger no creado · B7 brazos A/B bloqueados · B8 F3/F4/F5.

**Cobertura documental ≠ preparación operativa:** que el borrador cubra un requisito **no** significa que el instrumento, los datos o el brazo experimental estén disponibles. Los `MISSING`/`PARTIAL` de la conciliación reflejan exactamente esa diferencia.

**N=10 vs confirmatorio:** no se declara N=10 suficiente para el contraste confirmatorio. Se distingue la **exploración con 10 problemas** (N=10 declarado, no maquillado) del **estudio confirmatorio** (tamaño muestral justificado, hoy inexistente).

**Criterios funcionales que faltan:** se dejan como **decisión de diseño necesaria** (B2/B4). No se inventan.

**Ninguna modificación documental de esta fase autoriza implícitamente el piloto.**
