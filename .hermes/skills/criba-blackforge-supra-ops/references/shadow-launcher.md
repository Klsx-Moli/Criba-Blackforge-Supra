# Shadow launcher protocol

Entrypoint: `criba-blackforge/criba_shadow_main.py` → `main()`.
Bundle: `CribaShadow.exe` en `dist/CribaShadow/`.

## Secuencia de arranque
1. `data_root()` — estado persistente (`CRIBASHADOW_HOME` override, default `%LOCALAPPDATA%\CRIBA-Blackforge`).
2. `acquire_single_instance(root)` — OS lock (`CribaShadow.lock`, byte-range en Windows / `flock` en POSIX) + PID check. Segundo arranque → error real, salida 2.
3. `wire_import_paths()` — resuelve src layout (bundle_root, src, shadow_ui, supra_src, root.parent/supra/src).
4. `configure_frozen_gui_environment()` — en bundle congelado, pop `QT_QPA_PLATFORM` (que no herede offscreen test backend).
5. **SUPRA discovery:**
   - Si `SUPRA_ENDPOINT` está seteado y `health_ok()` → reutiliza.
   - Si no: `SupraServer` en `free_port()`, publica `SUPRA_ENDPOINT`/`SUPRA_STORAGE_DIR`/`SUPRA_USE_MODEL=false` en `os.environ`.
6. `uvicorn.Config(app, host=127.0.0.1, port=<efímero>, log_level="warning", use_colors=False)`.
7. `SupraServer.start()` → thread daemon, poll de /health hasta 60s.
8. Qt app: `ShadowWindow(database=str(root/criba.sqlite3"))`, `on_restore_latest_supra(window)`.
9. `app.exec()` — main loop.
10. `finally`: `supra.stop()` (should_exit=True + join(15s)), `release_single_instance(root)`.

## Riesgos de procesos huérfagos
- SupraServer es thread daemon: muere con el proceso principal si `app.exec()`
  retorna limpiaramente.
- Si el proceso es `SIGKILL`/taskkill (no llega a `finally`), el thread daemon
  NO ejecuta `stop()`. Uvicorn queda sin `should_exit`. Riesgo: puerto efímero
  en TIME_WAIT hasta que el SO libere el socket (típicamente < 60s).
- single-instance lock: protege contra arranques duplicados, NO contra
  process zombie. Si un lock queda huérfano (process kill -9), el byte-range
  lock del SO se libera al cerrar el handle; el PID en disco puede quedar stale.
- No hay watchdog de heartbeat para matar SUPRA si Shadow cae anímicamente.

## Env vars de Shadow
- `CRIBASHADOW_HOME` — override de data root (para test/probe sin tocar datos reales)
- `CRIBASHADOW_BUNDLE_PROBE` — activa probe de bundle (CI)
- `SUPRA_ENDPOINT` — endpoint existente a reutilizar (opcional)
- `SUPRA_STORAGE_DIR` — dir de storage SUPRA (publicada)
- `SUPRA_USE_MODEL=false` — desactiva LLM (publicada)
