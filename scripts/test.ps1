#requires -Version 5.1
# 运行全部单元测试和字节码编译检查。
#   powershell -ExecutionPolicy Bypass -File scripts\test.ps1
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
    & $python -m compileall -q main.py app tests
    if ($LASTEXITCODE -ne 0) { throw '编译检查失败' }
    & $python -m unittest discover -s tests -v
    exit $LASTEXITCODE
} finally {
    Pop-Location
}
