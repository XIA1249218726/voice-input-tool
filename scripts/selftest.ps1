#requires -Version 5.1
# 运行自检并保留控制台输出。用法：
#   powershell -ExecutionPolicy Bypass -File scripts\selftest.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $python)) { $python = Join-Path $root 'runtime\python\python.exe' }
if (-not (Test-Path $python)) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}
if (-not $python) { throw '找不到 Python，请先运行 scripts\setup-dev.ps1' }

Push-Location $root
try {
    & $python main.py --selftest
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
