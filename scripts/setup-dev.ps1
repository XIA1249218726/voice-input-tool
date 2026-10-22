#requires -Version 5.1
<#
    开发环境初始化：安装依赖 + 下载模型。
    用法：
        powershell -ExecutionPolicy Bypass -File scripts\setup-dev.ps1
        powershell -ExecutionPolicy Bypass -File scripts\setup-dev.ps1 -Venv -BuildTools
#>
param(
    [switch]$Venv,
    [switch]$BuildTools,
    [switch]$NoModel
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $python) { throw '找不到 python，请先安装 Python 3.12（勾选 Add to PATH）' }

$version = & $python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
Write-Host "使用 Python $version：$python"
if ([version]$version -lt [version]'3.10') { throw '需要 Python 3.10 或更高版本' }

if ($Venv) {
    $venv = Join-Path $root '.venv'
    if (-not (Test-Path $venv)) {
        Write-Host '创建虚拟环境 .venv …'
        & $python -m venv $venv
    }
    $python = Join-Path $venv 'Scripts\python.exe'
    Write-Host "虚拟环境 Python：$python"
}

Write-Host '安装运行依赖…'
& $python -m pip install --disable-pip-version-check -r (Join-Path $root 'build\requirements.txt')
if ($LASTEXITCODE -ne 0) { throw '依赖安装失败' }

if ($BuildTools) {
    Write-Host '安装打包依赖…'
    & $python -m pip install --disable-pip-version-check -r (Join-Path $root 'build\requirements-build.txt')
    if ($LASTEXITCODE -ne 0) { throw '打包依赖安装失败' }
}

if (-not $NoModel) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot 'download-model.ps1')
    if ($LASTEXITCODE -ne 0) { throw '模型下载失败' }
}

Write-Host ''
Write-Host '初始化完成。运行：' -ForegroundColor Green
Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\run.ps1'
Write-Host '自检：'
Write-Host '  powershell -ExecutionPolicy Bypass -File scripts\selftest.ps1'
