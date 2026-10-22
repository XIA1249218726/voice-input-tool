#requires -Version 5.1
<#
    下载并解压离线识别模型 SenseVoiceSmall(int8)。
    默认放到 <repo>\models\sense-voice，已被 .gitignore 排除，不会提交到 Git。

    用法：
        powershell -ExecutionPolicy Bypass -File scripts\download-model.ps1
        powershell -ExecutionPolicy Bypass -File scripts\download-model.ps1 -Force
#>
param(
    [string]$Dest = (Join-Path (Split-Path -Parent $PSScriptRoot) 'models\sense-voice'),
    [string]$Url = 'https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-int8-2024-07-17.tar.bz2',
    [string]$ExpectedSha256 = 'C71F0CE00BEC95B07744E116345E33D8CBBE08CEF896382CF907BF4B51A2CD51',
    [string]$PythonExe = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$modelsRoot = Split-Path -Parent $Dest
$archive = Join-Path $modelsRoot 'sense-voice.tar.bz2'
$extract = Join-Path $modelsRoot '_extract'
$modelFile = Join-Path $Dest 'model.int8.onnx'
$tokensFile = Join-Path $Dest 'tokens.txt'

function Test-Model {
    if (-not (Test-Path $modelFile) -or -not (Test-Path $tokensFile)) { return $false }
    $hash = (Get-FileHash $modelFile -Algorithm SHA256).Hash.ToUpperInvariant()
    if ($hash -ne $ExpectedSha256.ToUpperInvariant()) {
        Write-Warning "模型校验不一致：$hash"
        return $false
    }
    return $true
}

if ((Test-Model) -and -not $Force) {
    Write-Host "模型已存在且校验通过：$Dest"
    exit 0
}

New-Item -ItemType Directory -Force -Path $modelsRoot | Out-Null
if ($Force -and (Test-Path $Dest)) { Remove-Item $Dest -Recurse -Force }

if (-not (Test-Path $archive)) {
    Write-Host '正在下载 SenseVoiceSmall int8（约 228 MB，只需一次）…'
    Write-Host "  $Url"
    $curl = Get-Command curl.exe -ErrorAction SilentlyContinue
    if ($curl) {
        & $curl.Source -L --fail --retry 3 --retry-delay 2 -o $archive $Url
        if ($LASTEXITCODE -ne 0) { throw '模型下载失败' }
    } else {
        Invoke-WebRequest -Uri $Url -OutFile $archive -UseBasicParsing
    }
}
if (-not (Test-Path $archive)) { throw '模型下载失败' }

Write-Host '正在解压…'
if (Test-Path $extract) { Remove-Item $extract -Recurse -Force }
New-Item -ItemType Directory -Force -Path $extract | Out-Null

# Windows 自带的 tar 不支持 bzip2，改用 Python 的 tarfile（项目本来就需要 Python）
$root = Split-Path -Parent $PSScriptRoot
if (-not $PythonExe) {
    $candidates = @(
        (Join-Path $root '.venv\Scripts\python.exe'),
        (Join-Path $root 'runtime\python\python.exe')
    )
    $PythonExe = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $PythonExe) {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if ($cmd) { $PythonExe = $cmd.Source }
}
if (-not $PythonExe) { throw '解压需要 Python，请先安装 Python 3.10+' }

$extractCode = @'
import sys, tarfile
with tarfile.open(sys.argv[1], "r:bz2") as t:
    try:
        t.extractall(sys.argv[2], filter="data")
    except TypeError:
        t.extractall(sys.argv[2])
'@
$extractPy = Join-Path $modelsRoot '_extract_model.py'
$extractCode | Set-Content $extractPy -Encoding utf8
try {
    & $PythonExe $extractPy $archive $extract
    if ($LASTEXITCODE -ne 0) { throw '解压失败' }
} finally {
    Remove-Item $extractPy -Force -ErrorAction SilentlyContinue
}

$folder = Get-ChildItem $extract -Directory | Select-Object -First 1
if (-not $folder) { throw '压缩包内没有找到模型目录' }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
Copy-Item (Join-Path $folder.FullName '*') $Dest -Recurse -Force

if (-not (Test-Model)) {
    throw "模型文件校验失败：$modelFile"
}

Remove-Item $archive -Force -ErrorAction SilentlyContinue
Remove-Item $extract -Recurse -Force -ErrorAction SilentlyContinue
Write-Host "完成：$Dest" -ForegroundColor Green
Write-Host ("模型大小：{0:N0} MB" -f ((Get-Item $modelFile).Length / 1MB))
