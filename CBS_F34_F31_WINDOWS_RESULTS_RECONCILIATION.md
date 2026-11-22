# CBS F34 — Reconciliación de la verificación real F31 en Windows

**Origen de evidencia:** extracto de consola aportado por el usuario de la ejecución de Ernie y corrección del informe local `C:\Users\KLSX\Desktop\CBS_F31_WINDOWS_EXECUTION_REPORT.txt`. El contenido completo de ese TXT local NO fue accesible directamente para esta auditoría. Se distinguen estrictamente `REPORTED_BY_AGENT` y `STATICALLY_INSPECTED`.

**SHA probado por Ernie:** `6bef11aef156132883b2ef89e94d58c3c37021e7`, con base de comparación `ea07a4e6fd98c6318e232feba955d5396b3bae78`.
**Correcciones F34:** en rama `campaign/cbs-final-32-40`, después de F33; no están incluidas en el SHA F31 ejecutado por Ernie.

## 1. Resultado real reportado y correcciones del informe

| Métrica | F30 | F31 | Alcance |
|---|---:|---:|---|
| Suite `tests/unit` FAIL | 49 | 46 | -3, NO-GO (suite roja) |
| Suite `tests/unit` PASS | 2776 | 2786 | +10 |
| Suite `tests/unit` SKIP | 9 | 20 | +11, razones no enumeradas |
| mypy | 32 errores | 32 errores | deuda previa, *no* PASS |
| Ruff | no observado en extracto | PASS | reportado por Ernie |
| `git diff --check` | no observado en extracto | limpio | reportado por Ernie |

Resultados dirigidos tras corrección del propio Ernie: grupo A 1F/86P; B 2F/40P; C **4F/58P** en la pasada más desfavorable (otra pasada 3F/59P, intermitencia); D 0F/117P. La suma de grupos individuales no equivale a la corrida completa y puede contener tests solapados. El extracto final consigna `6 failed / 301 passed` para dirigidos, sin listado completo de nombres/stack traces.

`REPORTED_BY_AGENT`: Ernie mantuvo Uvicorn `:8000` PID 9684; DB del usuario `%LOCALAPPDATA%/CRIBA-Blackforge/intelligence.sqlite3` no cambiada según mtime; HEAD main `1304649`, handoff `757519c`, ASTRA `73f198c`; 4 `M` de BLACKFORGE aparente por CRLF. Son observaciones de su entorno, no verificadas en la máquina desde esta respuesta. Ernie no reparó código.

## 2. Hallazgo F34-T01 — False-positive test temperature-0

**Contrato real:** el valor por defecto de `ModelProfile.temperature` es **0.45** (verificado en `src/criba/model_config.py`). El test nuevo `test_f31_json_roundtrip_rejects_type_changes_even_when_python_equals` incluía `("temperature", 0)` y afirmaba `0.45 == 0`, falso. El test fallaba ANTES de ejercer el código de protección de JSON.

**Corrección publicada:** eliminar exclusivamente esa tupla errónea de test de igualdad; mantener los 4 casos donde los valores son numéricamente iguales pero sus tipos JSON difieren; añadir un caso **separado** que comprueba que cambiar temperatura 0.45→0 se rechaza por pérdida de identidad de datos. No se modifica el producto ni el default del modelo. **STATICALLY_INSPECTED / NOT_EXECUTED** la prueba reparada.

## 3. Hallazgo F34-T02 — Test del journey pulsaba Generar sin modelo

**Contrato real desde F29:** `ShadowWindow` inicia en `Cargar modelo` y `actions.on_inventar` no puede generar antes de seleccionar un backend/modelo ejecutable.

**Fuente:** `tests/unit/test_functional_proposal_journey.py:test_shadow_primary_generate_uses_canonical_invention_service` (líneas aprox. 234–270). El test creaba `ShadowWindow`, establecía el problema y hacía `win.topcards.btn_gen.click()`, pero **no seleccionaba modelo**. `calls` quedaba vacío; `assert calls == [(sheet["query"], win.store)]` mostraba `Right contains one more item (... agua ... , Storage object)`: significa que faltaba una llamada *esperada*, NO demuestra un registro real mal contaminado. La frase del agua procede del texto de la propia fixture `sheet["query"]`.

**Corrección publicada:** añadir una selección explícita `("openai_compatible", "fixture-no-model")` en el selector Shadow; configurar solo proxy local y autorizar el modal dentro del test con `QMessageBox.question` simulado; el servicio `criba.inventar.invent` y el intérprete ya están sustituidos por test doubles, así que no se realiza proveedor externo. Mantiene la aserción de enrutamiento al servicio canónico. La prueba negativa «no modelo» sigue cubierta separadamente por F29.

**ADVERTENCIA:** Ernie atribuyó ese traceback a contaminación del store compartido. Tal causalidad NO se establece por ese traceback. El riesgo de acceso a la DB real sí es independiente y está demostrado por el código de `default_store`.

## 4. Hallazgo F34-S01 — Protección de la DB real en pruebas

**Ruta productiva:** `criba.intelligence.refresh.default_store()` construye `Path(LOCALAPPDATA) / "CRIBA-Blackforge" / "intelligence.sqlite3"` y es invocado por `invention_service.run_invention` para pasar el evidence store a `invent()`. En Windows sin aislamiento, un test Qt que no sustituya `default_store` puede abrir/escribir el archivo REAL del usuario. F31 aislaba `CRIBA_MODEL_CONFIG`, no `LOCALAPPDATA`.

**Corrección SOLO en pruebas:** en `tests/conftest.py:offline_inference_boundary`, autouse por test, `monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "isolated-appdata"))`, preservando el antiguo aislamiento `CRIBA_MODEL_CONFIG` y el bloque de inferencia offline. El valor original de entorno se restaura al finalizar el test por `monkeypatch`. La aplicación productiva y el CLI no cambian de ruta.

**Nuevos sentinels:** `tests/unit/test_offline_intelligence_store_isolation.py`: 2 ejecuciones parametrizadas verifican `default_store` en subdirectorio exclusivo de `tmp_path`, y un caso comprueba `model_config_path` también aislado. Ninguno debe visitar el fichero real, y cierran `IntelligenceStore` antes de terminar.

**Límites:** si un test borra explícitamente `LOCALAPPDATA` o escribe mediante una ruta absoluta de usuario, ese desvío no queda protegido por el fixture. Los defaults constantes calculados antes de ejecutar fixtures (por ejemplo `criba.constants.DEFAULT_DB` en ciertos modos) requieren controles independientes. Estos riesgos no se declaran cerrados.

## 5. Hallazgos que NO deben recibir arreglos ciegos

- **5 fallos de dossier/BOUNDARY** informados como preexistentes en F30. El extracto no incluye sus nombres, expected/actual completos ni garantías de cuál `project_id` canónico corresponde al contrato de F27. Actualizar tests para que pasen sin verificar producer→serializer→transport→consumer podría ocultar una violación de autorización o idempotencia.
- **Mypy 32** errores coincidentes entre F30 y F31: no corregidos por F34. Requieren baseline de deuda explícita con tipos/líneas exactos, no `baseline=0` ni promoción a PASS.
- **11 SKIPs adicionales** F31: sin listado por test y motivo, su incremento podría esconder regresiones o cambios de disponibilidad. No afirmar cobertura equivalente.
- **Intermitencia** de `test_inventar_passes_default_store_like_cli` y jornadas Qt: puede involucrar cola Qt/hilos, eventos pendientes y mocks, además de DB compartida. Se ha mitigado una ruta DB, no verificado el origen completo.

## 6. Estado de F33 (ciclo inmediatamente anterior)

F33 movió la serialización JSON de `Storage.save_chain_memory` fuera de `BEGIN IMMEDIATE`; dejó dentro el SELECT/INSERT deduplicado y añadió cinco sentinels de lock, atomicidad, concurrencia y rollback. NO probado aún en Windows. No confundir ese cambio adicional con el SHA F31 ya ejecutado por Ernie.

## 7. Plan seguro de verificación

- No tocar worktree F31: `C:\ASTRA_WORK\cbs-f31-review` sobre `6bef11ae` ni F30 sobre `ea07a4e6`; son evidencia histórica.
- Crear OTRO worktree aislado para el SHA actual de campaña al cierre de F34. Ejecutar primero `test_phase29_shadow_source_selector.py::test_f31_json_roundtrip_rejects_type_changes_even_when_python_equals`, `::test_f31_json_roundtrip_rejects_changed_temperature`, `test_functional_proposal_journey.py::test_shadow_primary_generate_uses_canonical_invention_service`, `test_offline_intelligence_store_isolation.py`, `test_chain_memory_lock_scope.py`.
- Después test GUI clásico, dossier Phase13/F27 en modo offline; no lanzar otra full mientras existan suites corriendo. Registrar todos los `FAIL/SKIP` y hacer comparación por nombres, no solo totales.
- `ruff check`, `mypy`, `git diff --check` y Python compileall si disponibles; anotar baseline mypy 32, no ocultarlos.
- Sin proveedores reales, servidor SUPRA, nuevas sesiones ni modificaciones a ASTRA/main/handoff.
- Flujo: AUDITAR→REPARAR→VERIFICAR→PUSH (campaña únicamente)→SINCRONIZAR LOCAL en worktree aislado→VERIFICAR LOCAL.

**Veredicto F34:** reparaciones publicadas; **EVIDENCE_PENDING**, no AUDIT COMPLETE, no F31 PASS, G0 NO-GO y P0 semántico OPEN.
