@echo off
REM ============================================================================
REM  Uhermes - USB Hermes Portable Launcher (Windows)
REM
REM  Keep this file ASCII-only. cmd.exe parses .bat files in the console code
REM  page, so non-ASCII text here turns into mojibake when the OEM code page
REM  differs from the authoring one. All localized text is printed by
REM  hermes_boot.py, which controls its own encoding.
REM ============================================================================
setlocal EnableExtensions

REM UTF-8 console so the Python side can render CJK correctly.
chcp 65001 >nul 2>&1

set "DIR=%~dp0"
if "%DIR:~-1%"=="\" set "DIR=%DIR:~0,-1%"

REM --- Portable layout -------------------------------------------------------
REM   DIR\python       portable CPython. Relocatable: its prefix is derived from
REM                    its own location, so moving the stick or changing the
REM                    drive letter is safe. (A venv would embed an absolute
REM                    interpreter path in pyvenv.cfg / the .exe trampoline.)
REM   DIR\hermes-agent upstream source tree, pinned in versions.env
REM   DIR\hermes_home  all user data: .env, config.yaml, sessions, skills, state.db
REM   DIR\bin          optional bundled tools (uv), prepended to PATH
set "HERMES_HOME=%DIR%\hermes_home"
set "PYTHONPATH=%DIR%\hermes-agent"
set "PYTHONNOUSERSITE=1"
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "HERMES_LAZY_INSTALL_TARGET=%HERMES_HOME%\lazy-deps"
set "UV_CACHE_DIR=%HERMES_HOME%\cache\uv"
set "UV_PYTHON_INSTALL_DIR=%HERMES_HOME%\runtime"
if exist "%DIR%\bin" set "PATH=%DIR%\bin;%PATH%"

if not exist "%HERMES_HOME%" mkdir "%HERMES_HOME%" >nul 2>&1

set "PY=%DIR%\python\python.exe"
if not exist "%PY%" (
    echo.
    echo   [Uhermes] Portable Python not found:
    echo             "%PY%"
    echo   [Uhermes] The package looks incomplete. Re-extract the zip archive.
    echo.
    pause
    exit /b 1
)

"%PY%" "%DIR%\hermes_boot.py" %*
set "RC=%ERRORLEVEL%"
endlocal & exit /b %RC%
