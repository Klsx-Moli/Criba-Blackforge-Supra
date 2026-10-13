# CB-BUILD-WINDOWS — Paquete CribaShadow.exe (onedir) verificado

Fecha: 2026-10-13 (Europe/Madrid). Rama: audit/fase0-fase1. BLACKFORGE inerte.

## BASELINE
- main local == origin == 0d8b9db al iniciar. Arbol commiteado == arbol construido.

## BUILD (VERIFIED_BY_EXECUTION)
- Procedimiento existente reutilizado: criba-blackforge/CribaShadow.spec +
  scripts/verify_shadow_windows.py + scripts/verify_shadow_bundle_journey.py.
- SUPRA se hace importable para el freeze via PYTHONPATH nativa
  (criba-blackforge/src;supra/src), equivalente al paso "Make SUPRA importable"
  del workflow CI. Sin instalar nada, sin tocar locks.
- Comando: python -m PyInstaller CribaShadow.spec --noconfirm
  (Python 3.11.15, PyInstaller 6.22.2, PySide6 6.11.2, Windows 10 26100).
- exit 0. Artefacto onedir: criba-blackforge/dist/CribaShadow/ (149 MB; EXE 10.6 MB).
- Contenido del EXE verificado (PYZ embebido): 123 modulos criba, 20 supra_agentic,
  shadow_window/shadow_context, fastapi y uvicorn presentes. _internal/ con
  assets, data, schemas, styles.qss.
- BLACKFORGE: 7 modulos criba.blackforge_* viajan congelados en el PYZ (el spec
  solo excluye el paquete externo blackforge). NO se activan en ninguna fase.

## SMOKE (verify_shadow_windows.py, datos aislados en tempdir)
- STARTUP_SMOKE_PASS. Traza: supra:ready -> qt:window-created ->
  qt:window-shown visible=True minimized=False -> qt:restore-started, proceso vivo.
- Nivel GUI: offscreen/automatico (Qt paint buffer). NO es aceptacion visual humana.

## JOURNEY DEL EXE (verify_shadow_bundle_journey.py, EXE real, 2 procesos)
- BUNDLED_E2E_PASS. bundle_real_qt_callbacks=true, real_supra_http_readback=true
  (HTTP 200), durable_state_restored_after_full_process_restart=true,
  project_id astram2d2400114de identico en journey y restore, exit 0 en ambos.
- Proveedor: sintetico sin red (model_calls=NONE_REQUIRED). No es proveedor real.

## RESTART (distincion honesta)
- El journey del EXE valida restart por identidad + artefacto + HTTP 200, pero su
  provenance_source es IN_PROCESS_MEMORY_CACHE: el contrato de supra_client dice
  que eso es estado real pero NO es PERSISTED_STATE.
- Recuperacion desde disco verificada aparte con verification/journey_e2e_no_model.py:
  RESTART_PROCESS source=PERSISTED_STATE (pid nuevo) y REOPEN_RELOAD
  artifact=VERIFIED_FROM_ARTIFACT. PRIMER_BORDE_PROBLEMATICO=ninguno.
- Contrato semantico del dossier conservado tras restart: execution_status
  NOT_EXECUTED, scientific_status NOT_VALIDATED (sin promocion de estado),
  provenance completa.

## CAMBIOS
- NINGUNO en codigo ni workflows. dist/ y build/ son artefactos (gitignored).

## PENDIENTES (no comprobados)
- Aceptacion visual humana, proveedor LLM real, instalador, licencia/distribucion.
- Hueco del harness del EXE sobre status_source==PERSISTED_STATE y campos semanticos.

## PAQUETE PARA MOLI
- Carpeta onedir completa: criba-blackforge/dist/CribaShadow/
- Abrir con dist/CribaShadow/CribaShadow.exe (no separar el EXE de _internal\).
