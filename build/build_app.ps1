#requires -Version 5.1
<#
    打包便携版 App（PyInstaller onedir）
    用法：
        powershell -ExecutionPolicy Bypass -File build\build_app.ps1
        powershell -ExecutionPolicy Bypass -File build\build_app.ps1 -SkipInstall
    产物：
        dist\语音输入工具\语音输入工具.exe
        dist\语音输入工具\_internal\...
        dist\语音输入工具\models\sense-voice\...
#>
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$PythonExe = '',
    [string]$ModelDir = '',
    [switch]$SkipInstall
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path $ProjectRoot).Path
$AppDir = Join-Path $Root 'dist\语音输入工具'
$RawDir = Join-Path $Root 'dist_raw'
$WorkDir = Join-Path $Root '_build\pyinstaller'
$SpecDir = Join-Path $Root '_build'
$VersionFile = Join-Path $PSScriptRoot 'version_info.txt'
$Icon = Join-Path $Root 'app.ico'
$Main = Join-Path $Root 'main.py'
$Model = if ($ModelDir) { (Resolve-Path $ModelDir).Path } else { Join-Path $Root 'models\sense-voice' }

function Resolve-Python {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path $Explicit)) { throw "找不到 Python：$Explicit" }
        return (Resolve-Path $Explicit).Path
    }
    $candidates = @(
        (Join-Path $Root 'runtime\python\python.exe'),
        (Join-Path $Root '.venv\Scripts\python.exe'),
        (Join-Path $Root 'venv\Scripts\python.exe')
    )
    foreach ($p in $candidates) {
        if (Test-Path $p) { return (Resolve-Path $p).Path }
    }
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw '找不到 Python，请安装 Python 3.12 或使用 -PythonExe 指定'
}

$Python = Resolve-Python $PythonExe
if (-not (Test-Path $Model)) { throw "找不到模型目录：$Model（先运行 scripts\download-model.ps1）" }

if (-not $SkipInstall) {
    Write-Host '检查 PyInstaller…'
    & $Python -c "import PyInstaller" 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host '安装打包依赖…'
        & $Python -m pip install --disable-pip-version-check -r (Join-Path $PSScriptRoot 'requirements-build.txt')
        if ($LASTEXITCODE -ne 0) { throw '打包依赖安装失败' }
    }
}

Write-Host '清理旧产物…'
foreach ($p in @($RawDir, $AppDir)) {
    if (Test-Path $p) { Remove-Item $p -Recurse -Force }
}
New-Item -ItemType Directory -Force -Path $RawDir, $AppDir | Out-Null

Write-Host 'PyInstaller 正在收集依赖（约 1 分钟）…'
$pyArgs = @(
    '-m', 'PyInstaller',
    '--noconfirm', '--clean',
    '--windowed', '--onedir',
    '--name', 'VoiceInputTool',
    '--distpath', $RawDir,
    '--workpath', $WorkDir,
    '--specpath', $SpecDir,
    '--icon', $Icon,
    '--version-file', $VersionFile,
    '--add-data', "$Icon;.",
    '--collect-all', 'sherpa_onnx',
    '--collect-all', 'sounddevice',
    '--collect-all', 'pynput',
    '--collect-submodules', 'requests',
    '--collect-data', 'certifi',
    $Main
)
& $Python @pyArgs
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 打包失败' }

Write-Host '组装便携目录…'
Copy-Item (Join-Path $RawDir 'VoiceInputTool\*') $AppDir -Recurse -Force
Rename-Item (Join-Path $AppDir 'VoiceInputTool.exe') '语音输入工具.exe'
Copy-Item $Icon $AppDir -Force

New-Item -ItemType Directory -Force -Path (Join-Path $AppDir 'models') | Out-Null
& robocopy $Model (Join-Path $AppDir 'models\sense-voice') /E /NFL /NDL /NJH /NJS /NP | Out-Null

# 安装包素材：说明、自检脚本、示例配置
Copy-Item (Join-Path $PSScriptRoot 'assets\*') $AppDir -Force
# 打包目录里不能残留测试产生的用户数据
$userdata = Join-Path $AppDir 'userdata'
if (Test-Path $userdata) { Remove-Item $userdata -Recurse -Force }

Write-Host ''
Write-Host "完成：$AppDir" -ForegroundColor Green
$size = (Get-ChildItem $AppDir -Recurse -File | Measure-Object Length -Sum).Sum / 1MB
Write-Host ("大小：{0:N1} MB" -f $size)
exit 0
