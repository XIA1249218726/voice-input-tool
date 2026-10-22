#requires -Version 5.1
<#
    生成安装程序（NSIS 3.x，简体中文界面，当前用户安装）
    用法：
        powershell -ExecutionPolicy Bypass -File build\build_installer.ps1
        powershell -ExecutionPolicy Bypass -File build\build_installer.ps1 -Makensis "C:\...\makensis.exe"
    产物：
        dist\VoiceInputTool-Setup-1.0.0.exe
#>
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$Makensis = $env:MAKENSIS,
    [string]$Version = '1.0.0'
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path $ProjectRoot).Path
$Version = ($Version -as [string]).Trim().TrimStart([char[]]@('v', 'V'))
if (-not $Version) { throw '版本号不能为空' }
$Version4 = (($Version.Split('.') + @('0', '0', '0', '0'))[0..3]) -join '.'
$AppDir = Join-Path $Root 'dist\语音输入工具'
$OutFile = Join-Path $Root "dist\VoiceInputTool-Setup-$Version.exe"
$Nsi = Join-Path $PSScriptRoot 'installer.nsi'
$Icon = Join-Path $Root 'app.ico'

if (-not (Test-Path (Join-Path $AppDir '语音输入工具.exe'))) {
    throw "找不到已打包的 App：$AppDir（先运行 build_app.ps1）"
}

if (-not $Makensis) {
    $candidates = @(
        (Join-Path $Root '_build\nsis-3.11\makensis.exe'),
        'C:\Program Files (x86)\NSIS\makensis.exe',
        'C:\Program Files\NSIS\makensis.exe'
    )
    $Makensis = $candidates | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Makensis -or -not (Test-Path $Makensis)) {
    throw '找不到 makensis.exe，请安装 NSIS 3.x 或设置环境变量 MAKENSIS'
}

# NSIS 需要临时目录；某些受限环境无法写 %TEMP%，统一切到项目内
$TempDir = Join-Path $Root '_build\tmp'
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null
$env:TMP = $TempDir
$env:TEMP = $TempDir

Write-Host '正在压缩并生成安装程序（约 2~6 分钟）…'
& $Makensis /V2 "/DAPP_SRC=$AppDir" "/DOUTFILE=$OutFile" "/DAPP_ICON=$Icon" "/DAPP_VERSION=$Version" "/DAPP_VERSION4=$Version4" $Nsi
if ($LASTEXITCODE -ne 0) { throw 'NSIS 编译失败，查看上面的日志' }

if (-not (Test-Path $OutFile)) { throw '安装程序没有生成' }
Get-Item $OutFile | Select-Object FullName, @{N='大小(MB)';E={[math]::Round($_.Length/1MB,1)}} | Format-List
exit 0
