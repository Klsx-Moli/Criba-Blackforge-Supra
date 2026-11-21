@echo off
REM M4 - Windows One-Command Launcher for CRIBA Shadow UI (Option A)
REM Objetivo: launcher/orquestador canónico; puerto dinámico/libre; comprobación
REM config/env; backend arrancado una sola vez; Shadow arrancado; shutdown limpio;
REM SIN requisito BLACKFORGE key.
REM
REM Toda la orquestación real (single-instance lock, puerto libre, SUPRA
REM in-process o reuso de backend existente, health real, shutdown limpio via
REM finally, estado fuera del bundle, SUPRA_USE_MODEL=false) vive en
REM criba_shadow_main.py. Este .cmd SOLO valida el entorno mínimo y ejecuta el
REM entrypoint canónico: `python -m criba criba gui`.
REM
REM PROHIBIDO en este archivo:
REM   - arrancar SUPRA como proceso separado
REM   - elegir puerto en batch
REM   - sleep ciego (timeout)
REM   - escribir/leer supra.pid
REM   - duplicar health checks
REM   - requerir llave física BLACKFORGE
setlocal enabledelayedexpansion

REM === Validar Python disponible ===
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH. Instala Python 3.11+ y reintenta.
    exit /b 1
)

REM === Validar raíz mínima: este .cmd vive al lado del paquete criba-blackforge ===
set "_CMD_DIR=%~dp0"
set "_CMD_DIR=%_CMD_DIR:~0,-1%"
if not exist "%_CMD_DIR%\pyproject.toml" (
    if not exist "%_CMD_DIR%\..\pyproject.toml" (
        echo [ERROR] No se encontro pyproject.toml. Ejecuta desde el monorepo criba-blackforge-supra.
        exit /b 1
    )
)

REM === Ejecutar entrypoint canonico (single command) ===
REM `criba gui` delega en criba_shadow_main.py, que:
REM   - adquiere el OS lock single-instance
REM   - elige un puerto libre dinamico
REM   - arranca SUPRA in-process con SUPRA_USE_MODEL=false (NO requiere BLACKFORGE key)
REM   - verifica /health real antes de lanzar la UI
REM   - reusa un backend ya corriente si existe y pasa health
REM   - hace shutdown limpio del backend en el finally del proceso
REM   - mantiene el estado fuera del bundle (CRIBASHADOW_HOME redirigible)
python -m criba gui
set "_EXIT_CODE=%ERRORLEVEL%"
exit /b %_EXIT_CODE%
