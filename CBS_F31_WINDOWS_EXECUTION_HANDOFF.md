# CBS F31 — Windows validation handoff for Ernie (VERIFY ONLY)

## Estado y límites

**Rama de campaña:** `campaign/cbs-final-32-40`.
**Base F30:** `ea07a4e6fd98c6318e232feba955d5396b3bae78` (no cherry-pick por defecto).
**Estado:** F31 cambios publicados en rama; NO_MERGE / EVIDENCE_PENDING hasta suite real.
**IMPORTANTE:** esta tarea es exclusivamente de verificación. No modificar ni reiniciar la ejecución Uvicorn SUPRA que aparece en la consola Hermes; no detener, cerrar ni enviar señales a procesos existentes. No ejecutar endpoints remotos, inferencias de pago, ni pruebas que consuman credenciales del usuario.

## F31 reparaciones concretas

1. `src/criba/ui/actions.py:_hermes_run_env_snapshot`: snapshot read-only de identidad de proveedor/endpoint/clave/modelo/crítico/fallback. No serializar valores ni mostrarlos.
2. `on_inventar` Shadow: después de confirmación y antes de crear el runtime de modelo en el worker, rechazar si el entorno ya cambió; devuelve error explícito `REMOTE_CONFIG_CHANGED_BEFORE_DISPATCH` sin enviar POST.
3. `on_protocolo_operativo` Shadow: re-check antes de construir intérprete dentro del worker; si cambió, devolver PENDIENTE y evitar `refinar_propuesta`.
4. Hermes: fallback local de entorno explícito `CRIBA_EXTERNAL_FALLBACK_LOCAL=true` no debe pasar el guard de proxy para selección remota.
5. `_editable_model_settings_bytes`: roundtrip de perfiles mediante JSON canónico para comparar tipos numéricos exactamente; un JSON `8192.0` no es el mismo esquema serializado que `8192`, aunque Python los compare como iguales. La operación de cambio Ollama no sobrescribe archivos ambiguos.
6. `test_phase29_shadow_source_selector.py`: añade 6+6 mutaciones en cola, 1 fallback y 5 variantes de tipos numéricos, aparte de F30.

**Límite importante:** el snapshot detecta deriva ANTES de comenzar la tarea encolada; no es un lock inmutable del entorno durante todas las operaciones de la llamada HTTP. Reconfiguraciones posteriores, fallos de red, cambios de suscripción y costes físicos siguen requiriendo medidas independientes. Tampoco hay transacción CAS global de `models.json` entre procesos.

## Instrucciones al ejecutor Ernie

1. **READ ONLY primero**: `git status --short --branch`, SHA de `main`, handoff, rama de campaña, procesos Uvicorn; no detener ni modificar procesos. Detectar si ya existe un worktree de verificación: NO reutilizar sin revisar status, NO borrar.
2. Ejecutar `git fetch origin campaign/cbs-final-32-40` y checkout aislado por `git worktree add --detach` de SHA exacto comunicado al entregar el prompt (nunca HEAD implícito). No usar reset/clean/force/pull sobre copia activa. Si hay cambios locales, preservarlos y reportar.
3. Ejecutar suites dirigidas en Windows con el entorno de pruebas aislado, sin proveedor remoto, `QT_QPA_PLATFORM=offscreen`, `CRIBA_MODEL_CONFIG` en temp; utilizar el venv existente del repo si los módulos están presentes. Verificar import path hacia el **worktree** y no hacia la copia principal. Si faltan dependencias, marcar BLOCKED y no instalarlas sin consultar.
4. Orden: a) `test_phase29_interpreter_sources.py`, `test_phase29_shadow_source_selector.py`; b) `test_dossier_batch_phase13.py`, `test_dossier_phase27_cross_surface.py`; c) `test_interpreter_selector_startup.py`, `test_shadow_interpreter_journey.py`, `test_functional_proposal_journey.py`, `test_gui_inventar.py`, `test_refinamiento.py`; d) suites completas offline si está garantizado que no se accede a modelos/servicios externos.
5. Registrar: SHA exacto, comandos exactos, `python --version`, PySide6, pytest, cada PASS/FAIL/SKIP, salida de traceback íntegra **sin secretos**, `git diff --check <base> HEAD`, Ruff/mypy solo si están ya disponibles. En caso de fallo: repro aislada, recopilar archivo/línea, distinguir baseline vs introducido; **NO corregir todavía sin nueva autorización**.
6. Informar si las pruebas tienen cobertura falsa (workers mockeados, consentimientos no verificados en ruta productiva), crashes de Qt o ventanas modales bloqueantes. No declarar PASS si la prueba fue SKIPPED o no ejecutada.
7. No merge, no push a main, no cambios a ASTRA/G0/P0, no mover branches de handoff, no crear PR, no publicar, no gastar. La consola SUPRA visible puede ser el único Uvicorn legítimo.

## PowerShell orientativo, no destructivo

```powershell
$repo = 'C:\ASTRA_WORK\Criba-Blackforge-Supra'
$review = 'C:\ASTRA_WORK\cbs-f31-review'
cd $repo
git status --short --branch
git fetch origin campaign/cbs-final-32-40
# Sustituir <F31_SHA> por el SHA exacto del mensaje recibido
if (Test-Path $review) { throw 'Worktree objetivo ya existe: inspeccionar, no borrar' }
git worktree add --detach $review <F31_SHA>
cd (Join-Path $review 'criba-blackforge')
$python = Join-Path $repo 'criba-blackforge\.venv\Scripts\python.exe'
if (!(Test-Path $python)) { throw 'Python venv no disponible: reportar sin instalar' }
$env:QT_QPA_PLATFORM = 'offscreen'
$env:PYTHONPATH = "$PWD\src;$PWD\shadow_ui;$PWD"
$env:CRIBA_MODEL_CONFIG = Join-Path $env:TEMP 'cbs-f31-models-test.json'
& $python -m pytest -q tests/unit/test_phase29_interpreter_sources.py tests/unit/test_phase29_shadow_source_selector.py
& $python -m pytest -q tests/unit/test_dossier_batch_phase13.py tests/unit/test_dossier_phase27_cross_surface.py
& $python -m pytest -q tests/unit/test_interpreter_selector_startup.py tests/unit/test_shadow_interpreter_journey.py tests/unit/test_functional_proposal_journey.py tests/unit/test_gui_inventar.py tests/unit/test_refinamiento.py
git diff --check ea07a4e6fd98c6318e232feba955d5396b3bae78 HEAD
git status --short --branch
```

This commands block is a **starting runbook**, not proof of execution. If `$env:CRIBA_MODEL_CONFIG` temporary target exists, use a unique temporary path instead; never overwrite existing user data. Do not run the full suite if any test targets a live paid provider or writes into the user's running server workspace.

## Estado científico

F27–F31: IMPLEMENTED, EVIDENCE_PENDING; G0 NO-GO, semantic P0 OPEN. A green test subset does not attest scientific validity, service identity, upstream provider, physical attempt count, OAuth entitlements or on-disk GGUF identity. The next decision belongs to a verified regression report, not to a speculative claim.
