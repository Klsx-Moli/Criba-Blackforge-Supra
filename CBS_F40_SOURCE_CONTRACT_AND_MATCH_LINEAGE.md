# CBS F40 — Contratos de fuente en el veredicto científico y linaje mínimo de matches

**Base:** F39 `c96b6b90c42e170d0d70e9bfb5283ed0a4a498dd`
**Rama:** `campaign/cbs-final-32-40`, sin tocar main, ASTRA, handoff ni el worktree privado `iso-fixid-20261122`.
**Estado:** código/tests publicados, aún **NOT_EXECUTED** en checkout Windows. Una reproducción aislada del mecanismo lógico fue **VERIFIED_BY_ME** en Python 3.13, pero no ejecutó los módulos del proyecto.

## F40-01 · P1 contrato público · Éxito falso al interpretar ok="false"

- **Contrato:** `SourceQueryResult.ok` representa bool, `query_text` debe ser texto no vacío, `documents` debe ser una lista de objetos `EvidenceDocument`, cada `doc_id` exacto y cada `document.source_id` coherente con el identificador de fuente.
- **Producer→consumer:** `CrossDomainScout.cross_search` → `PriorArtSkeptic.review` (valida tipos) → `PriorArtVerdictEngine.assess` (API pública e invocable por el bucle de mutación). Si se llama directamente o el objeto es mutado después del skeptic, el veredicto no puede depender de validación omitida por un caller anterior.
- **Defecto F39 inspeccionado:** `PriorArtVerdictEngine.assess` comprobaba `isinstance(SourceQueryResult)` pero no `type(result.ok)`. En Python, `bool("false") == True`; con documentos con provenance, `if not result.ok` daba False y podía devolver `SURVIVED_SEARCH` con una fuente cuyo supuesto éxito era texto, no bool. También aceptaba listas de documentos adulteradas y documentos con source_id ajeno al resultado.
- **Fix F40:** validar claves de fuente exactas, query_text no vacío, bool estricto para `ok`, lista de documentos, tipo EvidenceDocument e identidad `(doc_id,source_id)` antes de calcular gaps. Mensajes `SOURCE_ID_INVALID`, `SOURCE_QUERY_INVALID`, `SOURCE_OK_NOT_BOOLEAN`, `SOURCE_DOCUMENTS_NOT_LIST`, `SOURCE_DOCUMENT_TYPE_INVALID`, `SOURCE_DOCUMENT_IDENTITY_INVALID`.
- **Tests nuevos:** seis mutaciones `ok` ([string false, true, 0, 1, None, []]); cuatro colecciones inválidas; cinco identidades de documento corruptas; una consulta vacía, un caso de control positivo. El informe legítimo se crea primero y los resultados se corrompen después para probar la frontera directa que el skeptic no protege.
- **VERIFIED_BY_ME:** prueba independiente con dataclasses sintéticas reprodujo que `ok="false"` se trata como éxito en las condiciones F39 y que un guard bool rechaza ese estado. **No se ha ejecutado el código real del repo**; NOT_EXECUTED para pytest F40.

## F40-02 · P1 contrato público · Coincidencias de fuentes ajenas al universo actual

- **Defecto F39:** un `PriorArtMatch(doc=EvidenceDocument(source_id="foreign"...))` con una puntuación válida podía producir `PARTIAL_PRIOR_ART` a pesar de que `results` solo describa `science` y `code`. El motor validaba la clase del documento, no la pertenencia a un origen consultado.
- **Fix conservador:** exigir `match.doc.source_id` como clave en `results` y `doc_id` no vacío y exacto. No exigir que su doc_id aparezca en `results[source_id].documents` **de la ronda actual**: `run_prior_art_mutation_loop` transporta matches históricos de rondas anteriores y ese contrato necesita conservarse hasta diseñar un ledger explícito de linaje.
- **Tests:** 6 casos de origen/id falsificados; 1 control positivo con match de la ronda anterior y source_id legítimo, que debe seguir dando PARTIAL_PRIOR_ART. Si se mutase el guard a «doc_id tiene que aparecer ahora», el control positivo pasaría a rojo.

## PASS10 — Riesgos pendientes, no corregidos automáticamente

1. **P1 / RESEARCH_QUESTION:** verificar pertenencia del *documento* histórico a un conjunto acumulado de evidencias con fingerprint/round/source. Comprobar mismo doc_id distinto contenido, document order y fuentes omitidas/reintroducidas antes de implementar. F40 solo verifica *source universe*, no la identidad del documento, ni la relevancia semántica real.
2. **EVIDENCE_PENDING:** `provenance != None` no demuestra URL auténtica, contenido o relevancia; no convertir SURVIVED_SEARCH o PARTIAL_PRIOR_ART en PROVEN_NEW, FACT ni REVIEW_SUPPORTED.
3. **OPEN:** CAS real de modelos.json, GGUF /props.model_path SIN COMMIT local, F28 contabilización de intentos físicos, F05-03 referencia REJECT con REVIEW_SUPPORTED, G0 NO-GO y P0 semántico.
4. **FALSE COVERAGE potencial:** las pruebas históricas del PriorArtVerdictEngine invocan generalmente `PriorArtSkeptic.review` antes del veredicto; ese productor bloquea `ok` inválido. Los tests F40 mutan `results` DESPUÉS del informe escéptico para hacer observable el bug del consumidor.

## Verificación segura pendiente

En worktree Windows aislado sobre el SHA exacto F40:
```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
python -B -m pytest -p no:cacheprovider -q tests/intelligence/test_prior_art_verdict_engine.py tests/intelligence/test_prior_art_skeptic.py tests/intelligence/test_prior_art_mutation_loop.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_config.py tests/unit/test_model_config_atomic_writer.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_settings_dialog_stale.py tests/unit/test_phase29_shadow_source_selector.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_chain_memory_lock_scope.py tests/unit/test_offline_intelligence_store_isolation.py
git diff --check
```
Ruff y mypy (baseline anterior de 32 errores) también deben ejecutarse sobre el SHA exacto. Documentar PASS/FAIL/SKIP, no ocultar diferencias por haber cambiado la cantidad de tests. No inferencias, modelos reales, endpoint SUPRA, despliegue ni publicación de trabajo de Ernie.

**Etiquetas:** VERIFIED_BY_ME = SHAs remotos y reproducción sintética; STATICALLY_INSPECTED = código exacto y tests publicados; REPORTED_BY_AGENT = F31 Windows; NOT_EXECUTED = tests del repositorio; NOT_ACCESSIBLE = worktrees/procesos Windows y corpus F05-03 local.
