@echo off
REM Umes - USB Hermes Portable Launcher (Windows)
REM 解压后双击此文件即可启动 Hermes Agent

setlocal
set DIR=%~dp0
set HERMES_HOME=%DIR%hermes_home

REM 确保配置目录存在
if not exist "%HERMES_HOME%\skills" mkdir "%HERMES_HOME%\skills"
if not exist "%HERMES_HOME%\sessions" mkdir "%HERMES_HOME%\sessions"

REM 检查是否已配置
if not exist "%HERMES_HOME%\.env" (
    echo.
    echo  ==========================================
    echo         Umes - USB Hermes Agent
    echo  ==========================================
    echo.
    echo  首次使用，请先配置 API 密钥：
    echo.
    echo  1. 复制配置模板：
    echo     copy hermes_home\.env.example hermes_home\.env
    echo     copy hermes_home\config.yaml.example hermes_home\config.yaml
    echo.
    echo  2. 用记事本编辑 .env 文件，填入 API 密钥
    echo.
    echo  详细说明请查看 README.md
    echo.
    pause
    exit /b 1
)

"%DIR%python\python.exe" "%DIR%hermes-win.pyz" %*
pause
