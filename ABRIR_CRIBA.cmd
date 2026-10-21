@echo off
REM M4 - One-Command Launcher canonical (Option A) for CRIBA Shadow UI
REM Objetivo: launcher/orquestador can�nico; puerto din�mico/libre; comprobaci�n
REM config/env; backend arrancado una sola vez; Shadow arrancado; shutdown limpio;
REM SIN requisito BLACKFORGE key.
REM
REM Toda la orquestaci�n real (single-instance lock, puerto libre, SUPRA
REM in-process o reuso de backend existente, health real, shutdown limpio via
REM finally, estado fuera del bundle, SUPRA_USE_MODEL=false) vive en
REM criba_shadow_main.py. Este .cmd SOLO valida el entorno m�nimo y ejecuta el
REM entrypoint can�nico: `python -m criba gui`.
REM
REM PROHIBIDO en este archivo:
REM   - arrancar SUPRA como proceso separado
REM   - elegir puerto en batch
REM   - sleep ciego (timeout)
REM   - escribir/leer supra.pid
REM   - duplicar health checks
REM   - requerir llave f�sica BLACKFORGE
setlocal enabledelayedexpansion

REM === Validar ra�z: este .cmd vive en la ra�z del monorepo ===
set "_CMD_DIR=%~dp0"
set "_CMD_DIR=%_CMD_DIR:~0,-1%"
set "_CRIBA_DIR=%_CMD_DIR%\criba-blackforge"
if not exist "%_CRIBA_DIR%\pyproject.toml" (
    if not exist "%_CMD_DIR%\pyproject.toml" (
        echo [ERROR] No se encontro pyproject.toml. Ejecuta desde el monorepo Criba-Blackforge-Supra.
        exit /b 1
    )
    set "_CRIBA_DIR=%_CMD_DIR%"
)

REM === Validar entorno Python: venv del repo, o uv run como fallback ===
set "_PYTHON="
set "_VENV_PY=%_CRIBA_DIR%\.venv\Scripts\python.exe"
if exist "%_VENV_PY%" (
    set "_PYTHON=%_VENV_PY%"
    echo [INFO] Usando venv del repo: %_VENV_PY%
) else (
    REM Fallback: uv run (CI-style) o python en PATH
    where uv >nul 2>&1
    if not errorlevel 1 (
        echo [INFO] venv no encontrado, usando uv run
        pushd "%_CRIBA_DIR%"
        uv run python -m criba gui
        set "_EXIT_CODE=%ERRORLEVEL%"
        popd
        exit /b %_EXIT_CODE%
    )
    where python >nul 2>&1
    if errorlevel 1 (
        echo [ERROR] Python no encontrado. Instala Python 3.11+ o ejecuta desde el venv.
        exit /b 1
    )
    set "_PYTHON=python"
    echo [INFO] Usando python en PATH (instala el paquete con 'pip install -e .')
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
pushd "%_CRIBA_DIR%"
set "SUPRA_USE_MODEL=false"
"%_PYTHON%" -m criba gui
set "_EXIT_CODE=%ERRORLEVEL%"
popd
exit /b %_EXIT_CODE%
