#requires -Version 5.1
<#
    把本仓库推送到 GitHub（首次或后续更新）。
    需要本机已安装 Git，并且已经登录 GitHub（HTTPS 会弹出凭据窗口）。

    用法：
        powershell -ExecutionPolicy Bypass -File scripts\publish.ps1 `
            -RepoUrl https://github.com/<your-name>/voice-input-tool.git

    只推送当前分支和 tag，不会提交模型/构建产物（.gitignore 已排除）。
#>
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoUrl,
    [string]$Branch = 'main'
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$git = (Get-Command git -ErrorAction SilentlyContinue).Source
if (-not $git) { throw '找不到 git，请先安装 Git for Windows 或 GitHub Desktop' }

if (-not (Test-Path (Join-Path $root '.git'))) {
    throw '当前目录不是 Git 仓库'
}

Push-Location $root
try {
    $remotes = & $git remote
    if ($remotes -contains 'origin') {
        Write-Host '更新 origin 地址…'
        & $git remote set-url origin $RepoUrl
    } else {
        Write-Host '添加 origin…'
        & $git remote add origin $RepoUrl
    }

    & $git add -A
    $dirty = & $git status --porcelain
    if ($dirty) {
        Write-Host '发现未提交的改动，创建提交…'
        & $git commit -m 'chore: update before publish'
    }

    Write-Host "推送 $Branch …"
    & $git push -u origin $Branch
    if ($LASTEXITCODE -ne 0) { throw '推送失败，请检查仓库地址和登录状态' }

    Write-Host '推送 tags（会触发 GitHub Release 构建）…'
    & $git push origin --tags

    Write-Host ''
    Write-Host '完成。打开仓库 Actions 页面查看构建结果。' -ForegroundColor Green
    Write-Host "仓库地址：$RepoUrl"
} finally {
    Pop-Location
}
