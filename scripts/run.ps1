#requires -Version 5.1
<#
    启动程序（自动选择 .venv / runtime / PATH 中的 Python）。
    用法：
        powershell -ExecutionPolicy Bypass -File scripts\run.ps1
        powershell -ExecutionPolicy Bypass -File scripts\run.ps1 -Arg '--headless'
#>
param(
    [string]$Arg = ''
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$candidates = @(
    (Join-Path $root '.venv\Scripts\python.exe'),
    (Join-Path $root 'runtime\python\python.exe')
)
$python = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $python) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $python = $cmd.Source }
}
if (-not $python) { throw '找不到 Python，请先运行 scripts\setup-dev.ps1' }

Push-Location $root
try {
    if ($Arg) { & $python main.py $Arg } else { & $python main.py }
} finally {
    Pop-Location
}
