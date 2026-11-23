# CBS F42 — Contraste literal acotado, anti-Goodhart y persistencia del diagnóstico

**Base:** campaña F41 `8e758ab10b93214703725bb20f09434c2c4c36a6`.
**Alcance:** `criba-blackforge/src/criba/intelligence/prior_art/literal_probe.py` (nuevo), `src/criba/inventar.py` (wiring + JSONL), `tests/intelligence/test_literal_mechanism_probe.py` (nuevo), `tests/unit/test_inventar.py` (integración y exportador).
**Protecciones:** sin cambios a ASTRA, main, handoff, worktree `iso-fixid-20261122`, servidor SUPRA ni reglas científicas globales.

## F42-01 — P1: ausencia total de comparación entre mecanismo y documentación (F41)

Inspección productiva: `inventar._assess_candidate` recuperaba `SourceQueryResult` y pasaba `matches=[]` al veredicto. F41 ya bloqueó la falsa inferencia SURVIVED_SEARCH pero no aportaba búsqueda de coincidencias reproducible. Implementar una similitud semántica arbitraria para forzar PARTIAL/GO sería Goodhart y no está autorizada por el ADR P10-T09.

**Etapa ejecutable F42:** `probe_literal_mechanism(candidate, results)` realiza comparación de la **secuencia completa de tokens del mecanismo** frente a campos individuales `title`, `abstract` y `EvidenceFragment.text` en documentos de fuentes que declaran `ok=True`, con `ProvenanceRecord` declarado, fuente y URL no vacías. Se normaliza con Unicode NFKC/casefold; los tokens y límites evitan coincidencias parciales dentro de palabras. Se utiliza `chr(0)` como separador de tokens, no una búsqueda cuadrática de subtuplas.

**Metadatos y límites:** no se comparan `metadata`, ni textos concatenados entre campos; mecanismo de 4 a 128 tokens y máximo 32768 caracteres, 64 documentos inspeccionados, 20 fragmentos por documento, 32768 caracteres por campo, source_id máximo 128, doc_id máximo 256, locator máximo 256; un presupuesto suministrado mayor de 64 se rechaza. Los documentos ambiguos con `doc_id` duplicado en la misma fuente se declaran *no inspeccionados* sin escoger cuerpo por orden. Orden de fuentes y documentos determinista.

**Contrato de salida deliberadamente trivaluado:**
- `POTENTIAL_LITERAL_OVERLAP`: uno o varios documentos contienen literalmente la frase completa (no garantiza que afirmen, apliquen o respalden el mecanismo; también cubre citas/negaciones).
- `NO_LITERAL_OVERLAP_IN_SCANNED_TEXT`: ninguna coincidencia en los campos concretos y dentro del presupuesto; **no** es ausencia de prior art ni evaluación semántica negativa.
- `INDETERMINATE`: mecanismo corto/largo, fuentes fallidas, campos de procedencia ausentes, ambigüedades documentales o presupuesto incompleto, sin promover lo desconocido a cero.

`materiality_assessed=False` es incondicional. Los candidatos contienen `source_id`, `doc_id`, `field`, `locator`; `mechanism_digest` es una huella de identidad para trazabilidad, **NO** prueba de autenticidad. No se vuelca texto bruto del documento a la salida del probe. Un URL declarado por la fuente no es una verificación independiente de su autenticidad.

## F42-02 — P1: wiring de Inventar sin promoción científica

`_assess_candidate` construye `literal_probe` desde los resultados que efectivamente se obtuvieron; lo agrega a los dicts de resultado (incluidos UNRESOLVED y fallos del bucle). Los veredictos favorables de la ruta sin matcher de **materialidad** siguen degradándose a `UNRESOLVED`, aunque la sonda haya encontrado texto literal. Se conservan queries, assessments y motivos para no reescribir el historial.

Tests de integración escritos con fuentes locales sintéticas: hit literal con procedencia, ausencia de hit que sigue UNRESOLVED, fallo de otra fuente que no se transforma en éxito. **NOT_EXECUTED** porque el checkout completo de CRIBA/PySide6 no está disponible en este entorno.

## F42-03 — P1: pérdida de diagnóstico en el exportador JSONL

`append_ledger(sheet)` seleccionaba campos manualmente y perdía `literal_probe`/rondas/assessments del `prior_art`. Ahora guarda `literal_probe`, `prior_art_assessments`, `prior_art_rounds`, `prior_art_mutations` por cada candidato. En registros antiguos o pendientes: campos inexistentes permanecen `None`, no 0, false, PASS o lista vacía inventada. Se agregaron dos tests del transporte `Inventar sheet→append_ledger→JSONL`, incluyendo preservación de casos legacy desconocidos. **NOT_EXECUTED** en el checkout real.

## PASS10 ejecutado — sentinels y falsación

**VERIFIED_BY_ME (Python 3.13, sin red, stubs limitados para contracts):**
- El archivo **exacto** `literal_probe.py` fue reconstruido en sandbox local y su hash Git coincide con el blob del remoto `e7d2aa7681faa556d19870433c873c0c892e29e5`.
- Los tests exactos de `test_literal_mechanism_probe.py` coinciden con el blob `413dba6aa739d24c0df2b08aa92d3aade0347fa0`.
- `pytest -q`: **30 passed** (0 failed), módulo puro; `compile()` PASS.
- Nueve mutaciones adversariales distintas introducidas individualmente en copias: coincidencia parcial, supresión de matches, ID duplicado, eliminación del presupuesto, promoción a materialidad, fuente fallida, falta de URL, falso estado negativo ante UNKNOWN y pérdida de ordenación. **9/9 matadas por regresiones que dieron rojo**. No equivale a verificar mutaciones en pipeline completo.
- Prueba metamórfica local de 12 000 pares de secuencias con acentos, puntuación, variantes Unicode y frases truncadas: `_contains_exact` produjo la misma respuesta que referencia ingenua de tokens, **12 000/12 000 PASS**.
- Benchmark ad hoc de un caso adversarial de 14 000 tokens con prefijos repetidos: diez barridos, comparación antigua aprox. 0,0457 s y nueva aprox. 0,0016 s; medida local, no promesa de rendimiento en otros equipos.

**NOT_EXECUTED / EVIDENCE_PENDING:** tests integrados de `Inventar`/JSONL, suite full CRIBA, tests Qt, CI, Ruff, mypy, Windows y ejecución sobre la copia local del usuario. Stubs locales no reemplazan el contrato completo de `contracts.py` ni el proceso real. No inferir GO de estos PASS.

## Siguiente punto exacto F43

1. Ejecutar en un worktree aislado Windows del HEAD F42 los 30 tests del probe contra contratos reales, más `test_inventar.py` y `test_prior_art_mutation_loop.py`; verificar que no se alteró un corpus ni un endpoint real.
2. Evaluar el diseño de un **comparador de materialidad** independiente con etiquetas explicitamente `REVIEW_REQUIRED` y evidencia de mecanismos/operadores; cubrir negación, cita literal sin aplicación, paráfrasis, mecanismo inverso, referencia REJECT, artículo posterior al candidato, fuentes contradictorias, duplicados multi-fuente/cross-run y casos concretos F05-03 de Ernie. Evitar umbrales lexicográficos confundidos con apoyo científico.
3. No promover hits literales a `PriorArtMatch` por puntuación heurística; exigir un contrato auditado de quién asigna materialidad, cómo se falsaría y qué evidencia autoriza cada estado.
4. Persisten bloqueos: GGUF físico `/props.model_path` del worktree no publicado, CAS multiproceso de `models.json`, F28 POST físicos, F05-03/corpus local, P0 semántico y G0 NO-GO.

**VEREDICTO:** F42 IMPLEMENTED, core independently executed 30 PASS / 9/9 mutants killed, **integration EVIDENCE_PENDING / NO-MERGE / G0 NO-GO**.
