# CBS F33 — Acoplamiento de transacción SQLite abierta durante serialización

**Base F32:** `f68bb1ed225fb9630519bf175f8b8a539fcecfe3`.
**Rama:** `campaign/cbs-final-32-40`.
**Alcance:** un cambio mínimo en `criba-blackforge/src/criba/storage.py:Storage.save_chain_memory`, cuatro tests nuevos en `criba-blackforge/tests/unit/test_chain_memory_lock_scope.py`; NO toca ASTRA, motor de intérprete, base de datos real, procesos SUPRA, `main` ni handoff.
**Estado:** implementación publicada; F33 pytest de repositorio **NOT_EXECUTED**.

## Hallazgo F33-S01 — escritura SQLite bloqueada durante serialización CPU

**Contrato:** la deduplicación de `chain_memory` requiere un SELECT + INSERT bajo la misma reserva de escritura; el cálculo/JSON previo NO necesita esa reserva.

**Ruta productiva encontrada:** `chain.py:run_stage` → `Storage.save_chain_memory` → por cada `memory.items()` se hacía `json.dumps(value, ensure_ascii=False)` *después* de `BEGIN IMMEDIATE`. Con memorias grandes, la serialización bajo write lock impide a otras conexiones iniciar nuevas escrituras, incluso si trabajan sobre tablas no relacionadas. La longitud del lock crece con tamaño del JSON y número de campos; no es una llamada HTTP ni prueba de deadlock permanente.

**Evidencia:** fuente remota F32 inspeccionada por conector GitHub. REPRODUCCIÓN AISLADA en Python sqlite3 de Linux (no repo): segundo escritor con `PRAGMA busy_timeout=50`, `BEGIN IMMEDIATE` falla `OperationalError: database is locked` en ~0.051 s si primer escritor mantiene la transacción; sin él, el segundo adquiere el lock. Esto **verifica la semántica SQLite**, no ejecuta la función del repositorio ni mide su latencia real.

**Corrección mínima:** serializar toda la lista de pares `(field_name, field_value)` antes de llamar a `self.connect()` o `BEGIN IMMEDIATE`, conservando los tipos de salida y `ensure_ascii=False`. Después reservar el escritor y ejecutar el SELECT/INSERT por cada par sin abrir una ventana de carrera entre ellos. Si hay un campo no serializable, fallar ANTES de escribir parcialmente (antes la transacción hacía rollback). No se ha eliminado el lock crítico de deduplicación.

**Regression sentinels publicados:**
1. `test_serialization_happens_before_sqlite_begin_immediate`: durante la llamada `json.dumps`, una conexión separada debe poder ejecutar su propio `BEGIN IMMEDIATE`. En el código previo, la prueba debería fallar con `database is locked`; en el nuevo, debería pasar. Se usa `contextlib.closing` por seguridad de archivos temporales Windows.
2. `test_concurrent_identical_writes_still_deduplicate_atomically`: 12 escrituras concurrentes de los mismos valores producen 1 fila exacta.
3. `test_bad_later_json_value_never_causes_partial_chain_memory_write`: un campo incorrecto no permite que campos anteriores se guarden parcialmente.
4. `test_distinct_field_values_preserve_original_dedup_semantics`: los valores diferentes no se pierden, los idénticos no se duplican; mantiene Unicode y `str(None)` heredados.

**Límites y alternativas:** `Storage.record_event` y `record_decision` siguen haciendo parse/serialización de `evidence_json` tras tomar `BEGIN IMMEDIATE` porque hacen read-modify-write concurrente. Cambiar esos códigos requiere estrategia distinta (por ejemplo, event ledger append-only) y pruebas contra lost update; NO mover directamente `json.dumps(updated)` fuera del lock, porque usaría un snapshot obsoleto. `Storage.reserve_semantic_attempt` y `BlackforgeBroker.reserve` requieren la transacción atómica para identidad/autorización y no se alteraron.

## Reconciliación F31 real (evidencia incompleta)

El usuario ha pegado una ejecución Ernie en Windows para SHA exacto **`6bef11aef156132883b2ef89e94d58c3c37021e7`**, reportando:
- A: `1 FAILED, 86 PASSED` (61.27 s)
- B: `2 FAILED, 40 PASSED` (20.48 s)
- C: detalles del grupo no visibles.
- Reejecuciones completas F30/F31 lanzadas en **PARALELO**, todavía sin cierre visible en el fragmento; herramientas del usuario `proc_d715027` y `proc_70f62da` continúan en su contexto según captura.
- Informe local `C:\Users\KLSX\Desktop\CBS_F31_WINDOWS_EXECUTION_REPORT.txt` (400 líneas) NO accesible desde este conector. La captura indica artefacto de line-endings CRLF en 4 ficheros BLACKFORGE y cero cambios semánticos según Ernie, pero ese diff no fue ejecutado por ChatGPT.

**ESTADOS:** `REPORTED_BY_AGENT` para los recuentos y checks de Windows; `VERIFIED_BY_ME` para repositorio GitHub y un experimento SQLite aislado; `NOT_ACCESSIBLE` para informe/stack traces locales y procesos; `NOT_EXECUTED` para pytest de F33 y suites completas.

**NO declarar GO ni arreglar ciegamente los fallos A/B.** Esperar los nombres, diffs y tracebacks completos; especialmente distinguir el conjunto de F30 y F31 y si los procesos finalizaron. No añadir una tercera ejecución completa en paralelo, no matar Uvicorn SUPRA, no confundir `grep` con un diagnóstico válido cuando está ejecutándose la suite. El worker del agente pausado por `judge API unreachable` no demuestra que el proceso pytest local haya terminado.

## Gates de aceptación

```powershell
# En un worktree de verificación NUEVO y un SHA F33 exacto, únicamente
# cuando hayan terminado las suites F30/F31 existentes.
$env:QT_QPA_PLATFORM = 'offscreen'
python -B -m pytest -p no:cacheprovider -q tests/unit/test_chain_memory_lock_scope.py
python -B -m pytest -p no:cacheprovider -q tests/unit/test_storage_decision_evidence.py
# Si las pruebas offline están identificadas, completar suites dirigidas y static.
git diff --check
```

F33 GATE: sentinels 1–4 verificadas con `pytest` sobre Windows y no regresiones de `chain.py`; sólo entonces actualizar estado. G0 científico NO-GO, P0 semántico OPEN, F28 contabilidad física P1 OPEN.
