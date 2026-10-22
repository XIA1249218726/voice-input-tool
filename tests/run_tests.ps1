#requires -Version 5.1
# 兼容入口：实际逻辑在 scripts\test.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
& powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root 'scripts\test.ps1')
exit $LASTEXITCODE
