@echo off
REM M4 - Windows One-Command Launcher for CRIBA Shadow UI
REM Objetivo: launcher/orquestador canónico; puerto dinámico/libre; comprobación
REM config/env; backend arrancado una vez; Shadow arrancado; shutdown limpio;
REM SIN requisito BLACKFORGE key.
setlocal enabledelayedexpansion

REM === Configuración ===
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"
set "_CMD_NAME=%~n0"
set "LOCALAPPDATA_LOW=%LOCALAPPDATA%\Supra"
set "SUPRA_STORAGE_DIR=%LOCALAPPDATA_LOW%\supra_state"
set "SUPRA_LOGS_DIR=%LOCALAPPDATA_LOW%\logs"

REM Crear carpetas de datos si no existen (no requiere BLACKFORGE)
if not exist "%SUPRA_STORAGE_DIR%" mkdir "%SUPRA_STORAGE_DIR%"
if not exist "%SUPRA_LOGS_DIR%" mkdir "%SUPRA_LOGS_DIR%"

REM Puerto dinámico/libre: dejar que el launcher elija el primer puerto libre
set "SUPRA_PORT="

REM === Comprobación config/env ===
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado en PATH. Instala Python 3.11+ y reintenta.
    exit /b 1
)

REM === Arrancar backend SUPRA una sola vez ===
if not exist "%LOCALAPPDATA_LOW%\supra.pid" (
    echo [INFO] Arrancando SUPRA en puerto dinamico...
    cd /d "%SCRIPT_DIR%"
    start /b python -m supra_agentic.service --port 0 > "%SUPRA_LOGS_DIR%\supra.log" 2>&1
    echo [INFO] SUPRA arrancado. PID en %LOCALAPPDATA_LOW%\supra.pid
    timeout /t 2 >nul
)

REM === Arranque Shadow UI ===
echo [INFO] Iniciando CRIBA Shadow UI...
cd /d "%SCRIPT_DIR%"
python -c "from criba_shadow_main import main; raise SystemExit(main())"
set "_EXIT_CODE=%ERRORLEVEL%"

REM === Shutdown limpio ===
if exist "%LOCALAPPDATA_LOW%\supra.pid" (
    echo [INFO] Cerrando SUPRA...
    for /f %%i in ('type "%LOCALAPPDATA_LOW%\supra.pid"') do taskkill /pid %%i /f >nul 2>&1
    del "%LOCALAPPDATA_LOW%\supra.pid"
)

echo [INFO] Cierre completo. Exit code: %_EXIT_CODE%
exit /b %_EXIT_CODE%
