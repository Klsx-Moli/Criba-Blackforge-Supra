# CBS F41 — Linaje candidato/documento y comparador de antecedentes NO conectado

**Base comprobada:** F40 `29858c3cf24dc6b12d890313c7234b1f4233f0f7` en `campaign/cbs-final-32-40`.
**Ámbito:** `prior_art/mutation_loop.py`, `prior_art/verdict.py`, `inventar.py` y tres baterías de tests. Sin tocar ASTRA, main, handoff, SUPRA, perfiles de Windows, los cuatro archivos no publicados de Ernie ni despliegues.

## F41-I01 — P1 · Contaminación entre candidatos en replays

**Contrato:** `candidate.candidate_id == initial_assessment.candidate_id == protocol.candidate_id`. Antes de F41 `run_prior_art_mutation_loop` no contrastaba estas tres identidades; podía arrastrar matches del candidato B al A. Dos pruebas históricas de presupuesto incluso creaban un protocolo `cand_test` para el candidato `cand_t10_001` sin detectar el error.

**FIX:** verificación fail-closed `CANDIDATE_LINEAGE_MISMATCH` antes de búsquedas/transportes. También validar tipo de entradas, `initial_assessment.coverage_limitations` incompatible con veredicto favorable, `SURVIVED_SEARCH` con matches y `PARTIAL_PRIOR_ART` sin matches. Las dos pruebas de presupuesto conservan su propósito, pero ahora usan el ID real del candidato. Cinco sentinels parametrizados con guard de "no efectuar búsqueda".

**NOTA:** esto establece igualdad textual de IDs, no que alguien no pueda falsificar los tres iguales. No se acredita identidad de candidato mediante digest inmutable.

## F41-I02 — P1 · Reutilización de documentos históricos modificados

**Contrato:** coincidencias históricas son representables (el loop deliberadamente arrastra `current_matches`) pero no se puede reutilizar `(source_id, doc_id)` en otra ronda con título/abstract/url/contenido material contradictorio. Tampoco un caller debe poder cambiar el contenido de un match después de iniciar el replay.

**FIX:** snapshot independiente `deepcopy(initial_assessment.matches)` al principio, guard de matches lista y tipo; `_material_document_identity` compara fuente, ID, título, clase, publicación, URL, abstract, fragmentos textuales y referencia/hash de procedencia, ignorando campos temporales como fecha de recuperación. `_execute_round` rechaza `DOCUMENT_ID_CONTENT_COLLISION` si la misma identidad reaparece con contenido material diferente, sin exigir que el documento reaparezca en todas las rondas.

**Tests:** cambios de título/abstract/url (3 casos) → rechazo; mismo contenido con fecha de recuperación distinta → aceptación; mutación del documento original durante callback de búsqueda → copia histórica estable; colección de matches no lista/generador → denegación antes del I/O. Total 6 casos nuevos en este bloque.

**Límite:** fingerprint lógico no es firma criptográfica, no verifica autenticidad de fuentes ni igualdad semántica. Dos documentos con IDs diferentes pero el mismo episodio siguen sin deduplicación causal.

## F41-I03 — P1 · Documentos duplicados en un resultado

**Ruta:** `PriorArtVerdictEngine.assess` verificaba identidad y tipo documental, pero no prohibía dos documentos con mismo `doc_id` dentro de una fuente. Permitía duplicación por padding o dos cuerpos con la misma identidad.

**FIX:** conjunto `seen_doc_ids` por `source_id` con `SOURCE_DOCUMENT_ID_COLLISION`. Dos pruebas (documento idéntico y documento contradictorio bajo el mismo ID) rechazan; control positivo verifica que `science/doc1` y `code/doc1` no colisionan. No inventar diversidad ni multiplicar cantidad de evidencia por duplicados.

## F41-I04 — P1 científico · SURVIVED_SEARCH sin comparador realmente ejecutado

**RUTA PRODUCTIVA VERIFICADA POR INSPECCIÓN:** `criba-blackforge/src/criba/inventar.py:_assess_candidate` hace `verdict_engine.assess(candidate, results, report, matches=[])` directamente. No ejecuta comparación de mecanismo del candidato contra fragmentos de los documentos recuperados. Un resultado de fuentes `ok=True` con provenance y matches vacío podía convertirse en `SURVIVED_SEARCH`; `_estado_antecedentes` lo traducía a "sin_coincidencia_cercana_en_fuentes_consultadas". Eso confunde **no se comparó** con **se comparó y no se encontró**.

**FIX acotado al caller Inventar:** cuando el primer assessment es `SURVIVED_SEARCH` sin comparador conectado, conservar consultas y assessments como historial, pero devolver `verdict=UNRESOLVED`, `detail=prior-art-match-not-executed`, `rounds=0`, `mutations=0`; no gastar rondas buscando documentos adicionales sin poder compararlos. Una protección adicional degrada futuras salidas positivas inesperadas del mutation loop cuando el comparador sigue sin estar conectado. **NO** alterar la clasificación de la API genérica PriorArtVerdictEngine, ni inventar un score o una etiqueta experimental.

**FIX adicional:** el `except ValueError` de mutation loop devolvía el veredicto favorable anterior en vez de UNRESOLVED después de fallos (incluidas nuevas colisiones). Ahora devuelve UNRESOLVED, manteniendo `assessments=[valor_anterior]` en la traza. `_estado_antecedentes` prioriza `mutation-loop-fail-closed` y `prior-art-match-not-executed` antes de estados positivos, también para expedientes históricos.

**Tests añadidos en test_inventar.py:** dos fuentes offline sintéticas con documentos y provenance, consultas sin comparador jamás terminan en "sin coincidencia"; expedientes históricos SURVIVED_SEARCH/PARTIAL con error posterior muestran búsqueda incompleta; mutación tardía ValueError obliga UNRESOLVED; resultado futuro positivo sin matcher aún se degrada. Sin llamadas HTTP ni motores reales.

## Refutación y riesgos materiales

- Se inspeccionó el caller productivo `_assess_candidate`: protocolo, candidato y evaluación se construyen normalmente con el mismo ID, pero la API pública `run_prior_art_mutation_loop` no garantizaba el contrato. La validación agregada protege llamadas directas y futuras integraciones; no afirmar explotación observada.
- `run_prior_art_mutation_loop` no crea *matches nuevos* a partir de resultados de fuentes: solo pasa `matches=list(prior_matches)` a `verdict_engine.assess`. Esto justifica mantener el comparador ausente como NO-GO, no fabricar `SURVIVED_SEARCH`. Las llamadas a fuentes sí son reales, pero recuperación ≠ comparación.
- El cambio del estado público de Inventar puede alterar UX/exports/analíticas históricas que esperan SURVIVED_SEARCH; hace falta ejecutar regresiones Windows y comprobar consumidores. No declarar funcionalidad científica completa.
- **OPEN:** matcher semántico real con evidencia/provenance/criterios reproducibles, linaje de documento cross-run con fingerprint firmado o corpus versionado, dedup semántico, `F05-03` referencia REJECT + REVIEW_SUPPORTED (ruta diferente reportada por Ernie), GGUF físico /props, CAS models.json, F28 costeo/POST, G0 NO-GO y P0 semántico.
- El trabajo no publicado en `C:/ASTRA_WORK/iso-fixid-20261122` NO se ha importado; necesita consentimiento explícito para transferir tras inspección.

## Evidencia ejecutada y pendiente

- **VERIFIED_BY_ME:** GitHub refs/código y reproducción aislada stdlib Python 3 de: incompatibilidad entre candidate IDs, `deepcopy` frente a mutación posterior, documento misma clave distinto contenido, y reproducción del estado engañoso de fallback. **Esto NO ejecuta módulos del checkout ni cuenta como PASS de las pruebas F41.**
- **STATICALLY_INSPECTED:** callers, fuente/contratos/ADR/tests actualizados y contenido remoto de todos los archivos tocados. Se inspeccionan marcadores de conflicto y whitespace, no equivale a `git diff --check` local.
- **NOT_EXECUTED:** pytest F33–F41, Ruff, mypy, compileall, CI y pruebas Qt Windows. No acceso de red al repo desde contenedor (git ls-remote falló DNS), y PySide6 no disponible.
- **REPORTED_BY_AGENT:** último baseline conocido Ernie F31 = 46 FAIL, 2786 PASS, 20 SKIP, NO-GO. No promover a cero ni asumir baseline nuevo.
- **NOT_ACCESSIBLE:** worktree Windows/servidor SUPRA y cambios sin commit de Ernie.

### Gates de integración (NO-MERGE)

1. En worktree Windows nuevo con SHA F41 exacto: correr `python -B -m pytest -p no:cacheprovider -q tests/intelligence/test_prior_art_mutation_loop.py tests/intelligence/test_prior_art_verdict_engine.py tests/unit/test_inventar.py`.
2. Ejecutar F33–F40 dirigidos; Ruff, mypy contra errores base y compilación; `git diff F40_SHA F41_SHA --check`; confirmar estado del worktree y no inferencias externas.
3. Buscar tests de consumidores UI/export/ledger de `SURVIVED_SEARCH` que asuman equivalencia con ausencia de comparación; confirmar equivalencia y revisar de nuevo.
4. Sin aprobación explícita del usuario, no merge main, force-push, reset, clean, despliegue, gasto, edición del worktree de Ernie, ni transferencias locales. Verificar SHA remoto y entregar LOCAL_SYNC_PLAN.

**Veredicto F41: IMPLEMENTED / EVIDENCE_PENDING / NO-MERGE / G0 NO-GO.**
