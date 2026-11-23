# CBS F37 — La configuración analizada debe ser la misma que se verificó

Base: campaign/cbs-final-32-40 @ F36 7a496e22bbefc45b11b936968801540fa75382ee.
Alcance: model_config.py, ui/model_settings_dialog.py, ui/actions.py, tests unitarios. Sin cambios a model_runtime.py (propiedad de GGUF aún pendiente en worktree local de Ernie).

## F37-01 P1 — Doble lectura de archivo de configuración compartido

Contrato: una decisión de sobrescribir models.json autorizada por bytes A no puede construir el modelo de datos desde una segunda lectura B del mismo pathname. Si otro proceso cambia el archivo entre ambas lecturas, el objeto en memoria no está vinculado a los bytes que pasaron el guard estricto.

Ruta antes de F37: (a) ModelSettingsDialog: _read_shared_settings_snapshot() valida la lectura A y luego load_model_settings(path) abre de nuevo para inicializar el formulario; (b) _activate_ollama_choice: _bounded_shared_model_bytes(config_path) valida A, pero load_model_settings(config_path) relee archivo. F35/F36 fijaban la ruta, no la equivalencia de contenido en las dos lecturas.

Falsación: si un segundo escritor reemplaza A→B después del snapshot y antes de load_model_settings, el guard observa A y el objeto interno B. El check antes de guardar detecta cambios persistentes, pero no garantiza que el editor haya mostrado/interpretado exactamente el snapshot aprobado. El evento A→B→A tampoco se detecta con igualdad simple de bytes. No declarar CAS.

Fix mínimo publicado: extraer load_model_settings_bytes(raw_bytes: bytes | None) como normalizador tolerante puro sin I/O; load_model_settings(path) reusa ese parser con una única read_bytes; el diálogo usa _settings_open_bytes si el guard fue seguro y defaults deshabilitados si no; Ollama interpreta before_bytes sin volver a abrir el archivo. Guardar sigue comparando el snapshot contra lectura de la ruta al final. Ningún archivo externo ni proveedor contactado.

Pruebas añadidas: test_model_config.py (paridad snapshot vs lector, decoder usable después de eliminar el path temporal, entradas inválidas y None no promovidas a enabled); test_model_settings_dialog_stale.py (cambia el archivo DESPUÉS de capturar A y ANTES de inicializar el diálogo; exige que éste muestre A y rechace guardado); test_phase29_shadow_source_selector.py (observa un único parse de exactly bytes A y prohíbe el loader que reabre la ruta). Mutación de read_bytes->reopen debería hacer rojo al menos un sentinel.

## Riesgos aún abiertos y separación de causalidad

- P1 OPEN: falta CAS de filesystem entre el último check y os.replace. El cambio F37 no introduce un lock multiproceso ni comparación con versión a nivel de escritura. Los temporales únicos de F35 evitan colisiones físicas, no last-writer-wins.
- P1 OPEN: identidad física GGUF; modelo alias != archivo /props.model_path; los cuatro archivos locales de Ernie siguen sin publicar. No se ha integrado el supuesto fix ni se adjudica a la campaña.
- P1 OPEN: F28 conteo físico de intentos de modelo/POST remoto y los cinco fallos del banco dossier. F34 test fixes siguen EVIDENCE_PENDING en Windows, con F31 46 FAIL/2786 PASS/20 SKIP REPORTED_BY_AGENT.
- P0 OPEN: defectos de contrato científico F05-03 / G0 NO-GO. No han recibido una reparación causal ni acreditación experimental.

## Evaluación de evidencia

VERIFIED_BY_ME: SHAs y archivos del remoto inspeccionados; detección de doble lectura y secuencia exacta de comprobación/parse/guardado en código. STATICALLY_INSPECTED: cambios y nombres de tests publicados. NOT_EXECUTED: pytest PySide6, Ruff, mypy, compileall y CI sobre HEAD F37. NOT_ACCESSIBLE: worktree Windows y servidor SUPRA de usuario. REPORTED_BY_AGENT: métricas F31 de Ernie.

## Gate de verificación Windows

1. Crear worktree aislado sobre SHA exacto F37 (sin alterar F30/F31, main ni handoff). python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_config.py tests/unit/test_model_config_atomic_writer.py
2. QT_QPA_PLATFORM=offscreen, python -B -m pytest -p no:cacheprovider -q tests/unit/test_model_settings_dialog.py tests/unit/test_model_settings_dialog_stale.py tests/unit/test_phase29_shadow_source_selector.py
3. Probar F33/F34: tests/unit/test_chain_memory_lock_scope.py tests/unit/test_functional_proposal_journey.py tests/unit/test_offline_intelligence_store_isolation.py
4. Ruff, mypy (baseline F31 32 errores; no ocultar) y git diff --check. Registrar SKIPs y fallos por nodo de test, con SHA ejecutado.
5. No ejecutar inferencias reales, no contactar modelos externos, no lanzar dos suites completas paralelas, no detener Uvicorn SUPRA. Tras aceptar pruebas dirigidas, reconciliar full suite en ejecución aislada.

LOCAL_SYNC_PLAN: git status; proteger cambios locales; git fetch origin campaign/cbs-final-32-40; git worktree add --detach C:/ASTRA_WORK/cbs-f37-review <sha-confirmado>; ejecutar gates; no reset/clean/force-push ni merge a main.
