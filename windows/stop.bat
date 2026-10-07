@echo off
REM ============================================================================
REM  Uhermes - stop the Hermes gateway and remove host autostart, so the drive
REM  can be ejected safely.
REM
REM  Use this when "Safely Remove Hardware" refuses the USB drive, or before
REM  unplugging the stick after having used the messaging gateway.
REM
REM  ASCII-only on purpose: cmd.exe parses .bat files in the console code page.
REM ============================================================================
setlocal EnableExtensions
chcp 65001 >nul 2>&1

set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

set "HERMES_HOME=%DIR%\hermes_home"
set "PYTHONPATH=%DIR%\hermes-agent"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
if exist "%DIR%\bin" set "PATH=%DIR%\bin;%PATH%"

set "PY=%DIR%\python\python.exe"
if not exist "%PY%" (
    echo.
    echo   [Uhermes] Portable Python not found: "%PY%"
    echo   [Uhermes] Re-extract the package.
    echo.
    pause
    exit /b 1
)

echo.
echo   Stopping Hermes gateway ...
"%PY%" "%DIR%\hermes_boot.py" gateway stop
echo.
echo   Removing host autostart entries ...
"%PY%" "%DIR%\hermes_boot.py" gateway uninstall
echo.
echo   ------------------------------------------------------------------
echo   Done. No gateway process should hold this drive any more.
echo   You can now eject the USB drive safely.
echo.
echo   (This only touched the Hermes gateway. Your own files are untouched.)
echo   ------------------------------------------------------------------
echo.
pause
endlocal
