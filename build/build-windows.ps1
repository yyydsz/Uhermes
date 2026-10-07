# Uhermes 便携包构建（Windows）
#
# 用法：
#   pwsh -File build\build-windows.ps1                      # 构建 Windows 便携包
#   pwsh -File build\build-windows.ps1 -Platform all -Cross  # 同时交叉构建 Linux 包
#   pwsh -File build\build-windows.ps1 -Extras core          # 只装核心依赖（体积小很多）
#   pwsh -File build\build-windows.ps1 -WithUv               # 把 uv 也打进包（按需安装依赖用）
#
# 网络：需要能访问 github.com 与 pypi.org。若要走代理，先设置环境变量：
#   $env:HTTPS_PROXY = 'http://127.0.0.1:7890'; $env:HTTP_PROXY = 'http://127.0.0.1:7890'
#
# 依赖：Python 3.9+ 和 uv（https://docs.astral.sh/uv/）。不需要 git。

[CmdletBinding()]
param(
    [ValidateSet('windows', 'linux', 'all')][string]$Platform = 'windows',
    [string]$Extras = 'all',
    [switch]$Cross,
    [switch]$WithUv,
    [switch]$NoZip,
    [switch]$Check
)

$ErrorActionPreference = 'Stop'

$py = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $py) { $py = (Get-Command py -ErrorAction SilentlyContinue).Source }
if (-not $py) { throw 'python not found on PATH (need Python 3.9+)' }

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Warning 'uv not found on PATH. Build will fall back to pip for native builds and will refuse cross-builds.'
    Write-Warning 'Install: https://docs.astral.sh/uv/getting-started/installation/'
}

$script = Join-Path $PSScriptRoot 'build.py'
$argv = @($script)
if ($Check) {
    $argv += '--check'
} else {
    $argv += @('--platform', $Platform, '--extras', $Extras)
    if ($Cross) { $argv += '--cross' }
    if ($WithUv) { $argv += '--with-uv' }
    if ($NoZip) { $argv += '--no-zip' }
}

& $py @argv
exit $LASTEXITCODE
