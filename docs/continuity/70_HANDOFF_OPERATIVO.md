# HANDOFF OPERATIVO

OBSERVED_AT: 2026-10-05 · escritor: Hermes · destino del producto: rama activa
`codex/interpreter-hardening-20261004` @ 2dc009485848b55ada5009986fe7e78d67c31ade

## Estado en una línea
En 2dc0094, Hermes reportó M2_INTEGRATION_OFFSCREEN (7 tests), M3 dirigido
(12+15), suite CRIBA (1737 passed, 3 skipped) y arranque SUPRA sin llave.
Son resultados reportados por el writer, no aceptación del producto:
M2_GUI_VISIBLE = NO ACREDITADO; M2_ACCEPTANCE = PENDIENTE;
M3_ACCEPTANCE = PENDIENTE del recorrido completo desde Shadow.
BLACKFORGE sigue en HARD_PAUSE. Faltan la decisión H y la comprobación del
paquete Windows; no se amplía aquí la verificación.

## Decisión — máximo 3 acciones inmediatas

### Acción 1 (producto) — Cerrar M3 sobre el HEAD activo y publicar evidencia
- Qué: ejecutar el recorrido M3 completo desde Shadow contra el HEAD activo
  (2dc0094) y adjuntar el registro; hoy hay 12+15 verdes dirigidos, no un
  recorrido único de producto con reinicio real documentado.
- Archivos: `criba-blackforge/tests/integration/test_m2_vertical_slice_e2e.py`
  (ya prueba reinicio), `supra/tests/test_m3_restart_provenance_contract.py`.
- Prueba RED propuesta (si falta): aserción de que tras reiniciar el servidor
  real, el `status_source` del GET es PERSISTED_STATE (no MEMORY_CACHE) y el
  receipt sobrevive byte a byte.
- Aceptación: un test de producto, un SHA, un resultado.
- STOP: cambio de SHA durante la medición.

### Acción 2 (producto) — Resolver el estado contradictorio del EXE (C-05)
- Qué: re-ejecutar el smoke del EXE `C:\ASTRA_WORK\APPS\CribaShadow\CribaShadow.exe`
  contra el HEAD activo; registrar UN veredicto con SHA y MainWindowHandle
  (liveness != ventana). Hoy `desktop-smoke-final` dice passed=false y
  `final-verification.json` dice desktop_passed=true.
- Aceptación: un único `result.json` con passed=true/false, sha256 del EXE,
  SHA del código y evidencia de ventana real.
- STOP: si el EXE no abre ventana, capturar traceback con variante console.

### Acción 3 (BLACKFORGE, sólo decisión) — Responder la incógnita crítica H
- Qué: decidir si BLACKFORGE debe resistir a un administrador local hostil.
  Si SÍ, la arquitectura actual (SO+broker confiables) es insuficiente y hace
  falta autoridad fuera del host. Si NO, registrar el modelo de amenaza como
  aceptado_for_design.
- No implica implementar nada ni levantar HARD_PAUSE.
- Autoridad: usuario (decisión explícita).

## Respuestas a las cinco preguntas abiertas (SRC-P1 §4.1 / SRC-P2 §6)

1. ¿Qué TARGET_SHA contiene las correcciones a reutilizar?
   - Producto: rama activa 2dc0094 (base 15bc237). Correcciones de CRIBA+SUPRA
     verificadas ahí por ejecución.
   - BLACKFORGE v1: 3244879 (PR #11), base 15bc237, 41 tests verdes.
   - Nivel: VERIFIED_BY_EXECUTION (git rev-parse + suites).

2. ¿Qué entrypoints conservan capacidad de ejecutar o modificar objetivos?
   - `supra_agentic/integrations/criba_bridge.py` (subprocess.run CRIBA y
     BLACKFORGE), `criba/model_runtime.py` (Popen llama-server),
     `criba/cli.py` (blackforge, blackforge-gui), `criba/ui/app_bridge.py`
     (`-m criba.blackforge_gui`), `criba/blackforge_agentic.py`
     (BlackforgeCapabilityLayer, a CONGELAR).
   - Nivel: STATICALLY_INSPECTED. Ninguno pasa por el broker nuevo (vive sólo
     en PR #11).

3. ¿Qué registros históricos permiten reconstruir identidad y procedencia?
   - Ledger sqlite del broker (`grants`, `consumptions`, `attempts`) y journal
     `journal.jsonl` con fsync por append (PR #11).
   - SUPRA: artefactos por proyecto en `storage_dir` + `get_project_with_
     provenance` (provenance MEMORY_CACHE vs ARTIFACT; artifact_status).
   - CRIBA: `invention_ledger/verdicts.jsonl` en el estado de usuario.
   - Nivel: STATICALLY_INSPECTED.

4. ¿Qué propiedades acredita la llave disponible?
   - NINGUNA: no existe llave ni ceremonia de desafío. Búsqueda en todas las
     ramas remotas sin resultados. El broker modela `credential_ref` no vacío
     como requisito de grant despachable, pero no hay credencial real.
   - Nivel: STATICALLY_INSPECTED / NOT_ACCESSIBLE.

5. ¿Qué adaptadores permiten comprobar un efecto tras una caída sin repetirlo?
   - `pending_uncertainty()` (lista OUTCOME_UNKNOWN/DISPATCHED/RESERVED) y
     `get_attempt()`/`attempts_for_case()` en el broker (PR #11); el dispatch
     marca OUTCOME_UNKNOWN y NO reintenta. No existe adaptador de observación
     real contra un laboratorio: sólo `SyntheticLabExecutor`.
   - Nivel: STATICALLY_INSPECTED + VERIFIED_BY_EXECUTION (tests neg/mut).

## Reconciliación decisión | fuente | implementación | wiring | evidencia

| decisión | fuente | implementación | wiring | evidencia |
|---|---|---|---|---|
| D1 expediente defensivo | SRC-P2 §1 | parcial (case) | no | STATICALLY_INSPECTED |
| D2 arquitectura núcleo+broker | SRC-P2 §B | parcial (PR#11) | no | VERIFIED_BY_EXECUTION (tests) |
| D3 tres ejes | SRC-P2 §C | sí (PR#11) | n/a (librería) | VERIFIED_BY_EXECUTION |
| D4 llave física | SRC-P2 §D | no | no | UNKNOWN (no existe llave) |
| D5 S0-S3 | SRC-P2 Q4 | no | no | proposed |
| D6 recuperación | SRC-P2 §C | sí (PR#11) | n/a | VERIFIED_BY_EXECUTION |
| D7 doce invariantes | SRC-P2 §3 | parcial | no | mixed |
| D8 doce pruebas | SRC-P2 §4 | parcial (PR#11) | n/a | VERIFIED (26 neg + 15 mut) |
| D9 tesis Q3 | SRC-P2 tesis | no | no | NOT_EXECUTED |
| D10 tres cortes | SRC-P2 §E | corte 3 declarativo (PR#11) | no | STATICALLY_INSPECTED |
| D11 mapa código | SRC-P2 §F | no migrado | no | STATICALLY_INSPECTED |
| D12 anti-falsos | SRC-P2 §G | parcial | no | mixed |
| M2 producto | SRC-P1 §2.5 | sí | sí | REPORTADO: integración offscreen (7 passed); GUI visible y aceptación pendientes |
| M3 producto | SRC-P1 §2.5 | parcial | sí | REPORTADO: tests dirigidos (12+15); aceptación pendiente |

## Fuentes reales para el writer
- Rama de trabajo: `C:\ASTRA_WORK\Criba-Blackforge-Supra` (codex/interpreter-
  hardening-20261004), venvs `criba-blackforge/.venv` y `supra/.venv`.
- Worktree BLACKFORGE: `C:\ASTRA_WORK\iso-dossier` (astra/blackforge-dossier).
- Paquete: `C:\ASTRA_WORK\APPS\CribaShadow\CribaShadow.exe`.
- No tocar: worktrees ocupados por otro writer; no crear segunda UI.

## Condiciones STOP aplicables ahora
- EXE: evidencia contradictoria (C-05) -> detener la afirmación "paquete OK".
- HARD_PAUSE: sin llave -> S2/S3 bloqueados; S0/S1 no habilitados.
- Incógnita H sin resolver -> no prometer aislamiento frente a admin hostil.
