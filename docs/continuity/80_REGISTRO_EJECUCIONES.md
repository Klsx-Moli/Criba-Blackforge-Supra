# Registro de ejecuciones (Hermes) — plantilla del mandato

Plantilla de referencia exigida por el mandato (SRC-P3 §15 y revisión del
usuario): comando · CWD/worktree · TARGET_SHA · estado del árbol antes/después ·
intérprete/entorno · inicio/fin · exit code · stdout/stderr · resultado · límites.
Las entradas siguientes son resúmenes históricos; NO completan todos esos
campos. Algunos comandos están abreviados y faltan horarios y salidas completas.

AVISO: todas las ejecuciones las hizo Hermes (writer). Son EVIDENCIA REPORTADA
POR HERMES, no verificación independiente. Este paquete no conserva archivos
separados con stdout/stderr completos de E-01 a E-10. El enlace a este registro
permite leer los resúmenes, no reproducir ni acreditar las ejecuciones originales.
No se han repetido las suites para rellenar documentación.

---

## E-01 · Suite completa CRIBA
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q`
- CWD/worktree: `C:\ASTRA_WORK\Criba-Blackforge-Supra\criba-blackforge`
- TARGET_SHA: 2dc009485848b55ada5009986fe7e78d67c31ade
- Árbol antes/después: limpio / limpio (los 2 JSON de verification quedaron
  con ruido CRLF; descartados con `git checkout --`)
- Intérprete: `criba-blackforge/.venv/Scripts/python.exe` (CPython 3.11.15)
- Duración: 441.60s (7:21). Exit code: 0
- stdout/stderr: capturado por `tail -20` en el comando; no en fichero aparte
- Resultado: **1737 passed, 3 skipped, 1 warning**
- Limitaciones: offscreen no aplica (no es GUI); no presenciado por tercero

## E-02 · M2 slice vertical real
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest tests/integration/test_m2_vertical_slice_e2e.py -q`
- CWD/worktree: `C:\ASTRA_WORK\Criba-Blackforge-Supra\criba-blackforge`
- TARGET_SHA: 2dc0094
- Árbol: limpio / limpio. Intérprete: venv CRIBA (3.11.15)
- Duración: 15.87s. Exit code: 0
- Resultado: **7 passed**
- Limitaciones: GUI en **offscreen**. OFFSCREEN != escritorio Windows visible.
  El propio test declara la ruta sin mocks (servidor SUPRA subprocess real).

## E-03 · M3 restart/replay (CRIBA)
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q -k "m3 or restart or replay"`
- CWD: `...\criba-blackforge` · TARGET_SHA: 2dc0094
- Duración: 17.39s. Exit code: 0
- Resultado: **12 passed, 1728 deselected**
- Limitaciones: selección por NOMBRE de test (m3/restart/replay). NO demuestra
  por sí solo el recorrido completo de recuperación desde Shadow; hay que
  identificar qué reinicia cada test y qué estado recupera (ver 30 §3.3).

## E-04 · M3 restart/replay (SUPRA)
- Comando: `python -m pytest tests/test_b03_replay_restart_contract.py tests/test_m3_restart_provenance_contract.py -q`
- CWD: `...\supra` · TARGET_SHA: 2dc0094
- Duración: 5.43s. Exit code: 0
- Resultado: **15 passed**
- Limitaciones: idem E-03; distingue persistencia durable de cache en los
  casos que cubre, no necesariamente vía Shadow.

## E-05 · SUPRA arranca sin llave BLACKFORGE
- Comando: `SUPRA_STORAGE_DIR=<scratch> python -c "...TestClient(app); GET /health; GET /api/v1/projects"`
- CWD: `...\supra` · TARGET_SHA: 2dc0094 · Intérprete: venv SUPRA
- Exit code: 0
- Resultado: `/health -> 200 healthy`; `/api/v1/projects -> 200 count=0
  storage_errors=[]`
- Limitaciones: TestClient en proceso, no servidor de red; valida arranque y
  contrato, no despliegue.

## E-06 · Shadow UI audit
- Comando: `QT_QPA_PLATFORM=offscreen python shadow_ui/entrypoint.py --audit`
- CWD: `...\criba-blackforge` · TARGET_SHA: 2dc0094
- Exit code: 0
- Resultado: callbacks_found 20, callbacks_missing ninguno, ShadowWindow,
  targets_total 26/26 OK
- Limitaciones: offscreen; audita bindings, no interacción visible.

## E-07 · Shadow + tests de sombra
- Comando: `QT_QPA_PLATFORM=offscreen python -m pytest tests/unit/test_criba_shadow_launcher.py tests/unit/test_shadow_i18n_keys.py tests/unit/test_shadow_interpreter_journey.py -q`
- CWD: `...\criba-blackforge` · TARGET_SHA: 2dc0094 · Duración: 26.78s
- Exit code: 0 · Resultado: **43 passed**
- Limitaciones: offscreen.

## E-08 · Arranque Shadow SIN módulos BLACKFORGE
- Comando: `python -c "…MetaPathFinder bloquea criba.blackforge*; import shadow_window"`
- CWD: `...\criba-blackforge` · TARGET_SHA: 2dc0094 · Exit code: 0
- Resultado: `shadow_window import OK WITHOUT blackforge`
- Limitaciones: sonda de import, no ejecución de la ventana completa.

## E-09 · Desacoplamiento núcleo CRIBA (P0)
- Comando: `python -c "…blocker criba.blackforge*; import criba.gates/chain/latency/logging/hybrid/canonical/ui.actions"`
- CWD: `...\criba-blackforge` · TARGET_SHA: 2dc0094 · Exit code: 0
- Resultado: los 7 módulos **OK** sin BLACKFORGE
- Limitaciones: import-time, no cubre rutas que importen perezosamente.

## E-10 · BLACKFORGE v1 (PR #11) — negativos + mutaciones
- Comando (CON fuga editable): `PYTHONPATH=src:scripts <venv> -m pytest tests/unit/test_blackforge_v1_negative10.py tests/unit/test_blackforge_v1_mutations.py -q`
- Comando (SIN fuga): `PYTHONPATH="...\iso-dossier\...\src;...\scripts" <venv> -m pytest … -p no_leak_plugin`
- CWD: `C:\ASTRA_WORK\iso-dossier\criba-blackforge` · TARGET_SHA: 3244879e7b2a2b4510dd997f4a343e26b1811b1b
- Árbol: limpio. Intérprete: venv CRIBA del worktree principal (3.11.15)
- Exit code: 0 en ambos
- Resultado: **41 passed** con fuga (14.68s) y **41 passed** sin fuga (19.85s)
- Limitaciones: la rama no tiene venv propio; se usó el del worktree principal
  con la fuga cuantificada (2 módulos: canonical, version). El resultado NO
  cambió al retirar el finder. No presenciado por tercero.

## E-11 · Comparación byte a byte de las copias
- Comando: execute_code comparando `paste_*.txt` vs `*_literal.md` (tamaño +
  SHA-256)
- CWD: `C:\ASTRA_WORK\MEMORIA_CBS_20261005` · Exit code: 0
- Resultado: los 3 pares **IGUAL=True** (tamaño y sha256 idénticos)
- Limitaciones: ejecutado por Hermes.

## E-12 · Verificación de anexo íntegro en el mega prompt
- Comando: execute_code comprobando `src_bytes in mega_bytes`
- Resultado: las 3 fuentes aparecen **verbatim** dentro de
  `60_MEGA_PROMPT_CBS_v3.md`.
- Limitaciones: ejecutado por Hermes. El tamaño 104022 bytes corresponde al
  registro histórico, no al documento actual. Preparando esta PR se compararon
  de nuevo los bytes: el documento actual tiene 104996 bytes y SHA-256
  `1eba6d392c0a850118d627f0515ec9ec10b5d42bdc65f07a43b131e699410678`;
  las tres fuentes literales aparecen íntegras en él. Esta comprobación documental
  no repite ninguna suite ni modifica las fuentes.
