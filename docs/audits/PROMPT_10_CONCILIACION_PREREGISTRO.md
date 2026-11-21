# CONCILIACIÓN DEL PRERREGISTRO — PROMPT 10

**Fecha:** 2026-10-22 · **SHA observado:** `b07147bcb7580a2e1688909d3cc3b85cb2fc5ab0`
**Fuentes leídas íntegramente:** `PROMPT_10_PILOTO_SELECTOR_CRIBA.md` (canónico), `docs/audits/PROMPT_10_PREFLIGHT_CIENTIFICO.md`, `docs/audits/PROMPT_10_PREREGISTRO_BORRADOR.md`.

Vocabulario: `FACT` (verificado por ejecución/inspección en esta sesión), `INFERENCE`, `NOT_EXECUTED`, `NOT_ACCESSIBLE`.

---

## 1. Tabla de correspondencia (canónico → borrador)

| # | Texto/referencia canónica exacta | Borrador | Estado | Evidencia | Decisión/info pendiente |
|---|---|---|---|---|---|
| C1 | §2: "el selector real de CRIBA eleva al menos **20 puntos porcentuales** la proporción de selecciones funcionalmente válidas frente a un prompt fuerte congelado" | §1 H1, copia literal | **SATISFIED** | borrador §1 | — |
| C2 | §2: "El margen es un umbral de decisión del piloto, no universal" | §1/§4, margen +20 pp como umbral | **SATISFIED** | borrador §4 | — |
| C3 | §2: "mínimo operativo de 30 problemas independientes" | §5 declara 10 disponibles y NO maquilla | **PARTIAL** | `problems_smoke.json` = 10 (FACT); dataset 30 **NOT_ACCESSIBLE** | propietario: aprobar N=10 exploratorio o construir 30 |
| C4 | §3: "cuatro candidatos congelados: una referencia funcional positiva; un control negativo funcional pero plausible; y dos alternativas plausibles" | §3 propone instrumento; §5 lagunas L3 | **MISSING** | no existe construcción etiquetada (FACT) | propietario: definir diseño de candidatos |
| C5 | §3: "Aleatorizar el orden/IDs de forma independiente por episodio" | §8 orden aleatorio | **SATISFIED** | borrador §8 | — |
| C6 | §3: "El selector real de producción no se sustituye ni se retoca" | §1/§11 | **SATISFIED** | borrador §11 | — |
| C7 | §3: "Evaluación funcional con protocolo independiente del scorer, criterio externo… congelados antes de revelar etiquetas" | §3 propone definición + laguna L4 | **MISSING** | instrumento funcional inexistente (FACT) | propietario: aprobar instrumento |
| C8 | §3: "Congelar todas las selecciones de ambos brazos… antes de abrir las etiquetas" | §8 congelación | **SATISFIED** | borrador §8 | — |
| C9 | §3: "Registrar por separado el coste de preparar el conjunto candidato" | §4 coste de preparación | **SATISFIED** | borrador §4 | — |
| C10 | §3: "H1 y rival H2… registrarlos antes de ejecutar… Si el protocolo no los distingue, no atribuir" | §1 rivales H0/H1/H2/NULL | **PARTIAL** | rivales sí; H1/H2 **no distinguibles** sin instrumento | propietario: aprobar diagnóstico |
| C11 | §4: ledger (15 campos discutidos en conciliación aparte) | §10 versiones/SHA | **PARTIAL** | ledger en conciliación propia | — |
| C12 | §5: cegamiento (etiquetas, control, reservados, salida del otro brazo, IDs correlacionados) | §8 | **SATISFIED** | borrador §8 | — |
| C13 | §5: "Declarar `BENCHMARK_CONTAMINATED` si hay acceso prohibido, cambios post hoc, selección de subconjunto favorable, presupuestos desiguales, omisión…" | §8 | **SATISFIED** | borrador §8 | — |
| C14 | §5: "Contabilizar todas las oportunidades: cuatro candidatos por tarea y todas las llamadas… Un candidato descartado no desaparece de la contabilidad" | §4/§9; laguna L3/L5 | **PARTIAL** | `criba_adapter` descarta report (FACT) | propietario: corregir contabilidad (F5) |
| C15 | §6: endpoint primario 1/0; ausencias conservadas en el denominador | §4 | **SATISFIED** | borrador §4 | — |
| C16 | §6: "comparación pareada por problema, intervalo del 95%, método exacto… Congelar el método antes de abrir resultados" | §4 McNemar exacto + IC95 | **SATISFIED** | borrador §4 | — |
| C17 | §6: "~95,8% de probabilidad de ver al menos un fallo… NO garantiza potencia para afirmar una ventaja de 20 pp" | §4 cálculo + simulación | **SATISFIED** | ver §2 | — |
| C18 | §6: estados `BENCHMARK_CONTAMINATED` / `NO_EVIDENCE_OF_CRIBA_ADVANTAGE` / `SUPPORTED_WITH_SCOPE` / `BLOCKED`/`NOT_TESTABLE`/`NOT_IDENTIFIABLE` | §1/§11 | **SATISFIED** | borrador §11 | — |
| C19 | §6: timebox 10 días, máx. 14, tope 16 h, 60 llamadas, sin APIs de pago | §9 | **SATISFIED** | borrador §9 | — |
| C20 | §7: prohibiciones (ejes, operadores, MAP-Elites, routing, UCB/SNIPS, canon, diversidad causal, BLACKFORGE OFF, STANDARD desactivado) | §11 | **SATISFIED** | `gate.py` STANDARD=DISABLED (FACT) | — |
| C21 | §7: "No ocultar un resultado negativo ni llamar `DONE` a un intento" | §11 | **SATISFIED** | borrador §11 | — |
| C22 | §3: "Unidad independiente: problema/episodio raíz… Variantes de estilo, semillas o candidatos hermanos no aumentan N" | §5 unidad | **SATISFIED** | borrador §5 | — |

**Resumen:** SATISFIED 16 · PARTIAL 4 · MISSING 2 · CONFLICT 0.

---

## 2. Margen de 20 pp y cálculo de potencia — distinción explícita

| Capa | Contenido | Clasificación |
|---|---|---|
| **Requisito canónico** | margen +20 pp es umbral de decisión; método exacto pareado; IC95; congelar método antes de abrir resultados | **FACT** (texto canónico §2, §6) |
| **Supuesto estadístico** | comparación pareada McNemar; distribución de pares discordantes; alpha=0.05 bilateral | **INFERENCE** (método elegido, no prescrito por el canónico) |
| **Resultado de simulación** | potencia máxima ≈ 1.000 para delta=20 pp (n=10/30/60, p10=0.21) **bajo escenario favorable**; IC95 (Newcombe/Wilson) cruza +0.20 en n=10/30/60 | **FACT** (cálculo ejecutado 2026-10-22) |
| **Conclusión** | n=30 **no** garantiza decidir el margen; la simulación favorable **no** es garantía de potencia | **INFERENCE** derivada de la simulación |

**Advertencia registrada:** la simulación de potencia se calculó con un escenario **favorable** (p10=0.21, p01=0.01). No se presenta como garantía. El canónico ya advierte que 30 casos no bastan para afirmar 20 pp.

---

## 3. Cambios de valores canónicos

**Ninguno.** El borrador conserva afirmación, margen, unidad, cegamiento, reglas de decisión y estados semánticos. No se identificó autoridad documental que permita alterarlos; no se alteraron.

---

## 4. Estado del documento

`PREREGISTRATION_STATUS = NO APROBADO` (se conserva). Persisten: C3/C4 (dataset y criterio), C7 (instrumento), C10 (diagnóstico H1/H2), C14 (contabilidad) y las lagunas L1–L7. **No se aprueba en nombre del propietario.**
