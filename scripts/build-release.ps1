#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# Build Release Package Script
# Creates a ZIP package for GitHub Release

param(
    [string]$Version = "1.0.0"
)

$ErrorActionPreference = "Stop"

# Color output functions
function Write-Info {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host $Message -ForegroundColor Red
}

# Get script directory
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
$releaseDir = Join-Path $projectRoot "release"
$packageName = "lecturer-v$Version"
$packageDir = Join-Path $releaseDir $packageName
$zipFile = Join-Path $releaseDir "$packageName.zip"

Write-Info "=========================================="
Write-Info "构建发布包: $packageName"
Write-Info "=========================================="
Write-Host ""

# Clean old release directory
if (Test-Path $releaseDir) {
    Write-Info "清理旧的发布目录..."
    Remove-Item -Path $releaseDir -Recurse -Force
}

# Create release directory structure
Write-Info "创建发布目录结构..."
New-Item -ItemType Directory -Path $packageDir -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "app") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "assets") -Force | Out-Null
New-Item -ItemType Directory -Path (Join-Path $packageDir "scripts") -Force | Out-Null

# Files and directories to exclude
$excludePatterns = @(
    "__pycache__",
    ".venv",
    "venv",
    "*.pyc",
    "*.pyo",
    "*.log",
    ".git",
    ".env",
    "logs",
    "test-*.html",
    "test-*.py",
    "sync_html_output",
    "release",
    "md"
)

# Copy app directory
Write-Info "复制 app 目录..."
$appSource = Join-Path $projectRoot "app"
$appDest = Join-Path $packageDir "app"

# Ensure destination directory exists
if (-not (Test-Path $appDest)) {
    New-Item -ItemType Directory -Path $appDest -Force | Out-Null
}

# Copy contents of app directory, not the directory itself
Get-ChildItem -Path $appSource -Exclude $excludePatterns | ForEach-Object {
    $destPath = Join-Path $appDest $_.Name
    Copy-Item -Path $_.FullName -Destination $destPath -Recurse -Force
}

# Copy assets directory
Write-Info "复制 assets 目录..."
$assetsSource = Join-Path $projectRoot "assets"
if (Test-Path $assetsSource) {
    $assetsDest = Join-Path $packageDir "assets"
    if (-not (Test-Path $assetsDest)) {
        New-Item -ItemType Directory -Path $assetsDest -Force | Out-Null
    }
    Get-ChildItem -Path $assetsSource | ForEach-Object {
        $destPath = Join-Path $assetsDest $_.Name
        Copy-Item -Path $_.FullName -Destination $destPath -Recurse -Force
    }
}

# Copy requirements.txt
Write-Info "复制 requirements.txt..."
Copy-Item -Path (Join-Path $projectRoot "requirements.txt") -Destination $packageDir -Force

# Copy README.md
Write-Info "复制 README.md..."
Copy-Item -Path (Join-Path $projectRoot "README.md") -Destination $packageDir -Force

# Create .env.example
Write-Info "创建 .env.example..."
$envExample = @"
GEMINI_API_KEY=your_gemini_api_key_here
"@
$envExample | Out-File -FilePath (Join-Path $packageDir ".env.example") -Encoding UTF8 -NoNewline

# Copy scripts
Write-Info "复制脚本文件..."
$scriptsToCopy = @(
    "install.ps1",
    "install.sh",
    "install-pdf2htmlex-wsl.ps1",
    "install-pdf2htmlex-macos.sh",
    "install-pdf2htmlex-linux.sh",
    "start.ps1",
    "start.sh"
)

foreach ($script in $scriptsToCopy) {
    $scriptPath = Join-Path $scriptDir $script
    if (Test-Path $scriptPath) {
        Copy-Item -Path $scriptPath -Destination (Join-Path $packageDir "scripts") -Force
        Write-Info "  - 已复制: $script"
    } else {
        Write-Warning "  - 未找到: $script"
    }
}

# Copy RELEASE.md if exists
if (Test-Path (Join-Path $projectRoot "RELEASE.md")) {
    Write-Info "复制 RELEASE.md..."
    Copy-Item -Path (Join-Path $projectRoot "RELEASE.md") -Destination $packageDir -Force
}

# Copy HTML-pdf2htmlEX版使用说明.md
if (Test-Path (Join-Path $projectRoot "HTML-pdf2htmlEX版使用说明.md")) {
    Write-Info "复制 HTML-pdf2htmlEX版使用说明.md..."
    Copy-Item -Path (Join-Path $projectRoot "HTML-pdf2htmlEX版使用说明.md") -Destination $packageDir -Force
}

# Clean up Python cache files
Write-Info "清理 Python 缓存文件..."
Get-ChildItem -Path $packageDir -Recurse -Include "*.pyc", "*.pyo", "__pycache__" | Remove-Item -Recurse -Force

# Create ZIP file
Write-Info "创建 ZIP 文件..."
if (Test-Path $zipFile) {
    Remove-Item -Path $zipFile -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($packageDir, $zipFile)

Write-Host ""
Write-Success "=========================================="
Write-Success "发布包构建完成！"
Write-Success "=========================================="
Write-Host ""
Write-Info "发布包位置: $zipFile"
Write-Info "包大小: $([math]::Round((Get-Item $zipFile).Length / 1MB, 2)) MB"
Write-Host ""
Write-Info "发布包内容:"
Get-ChildItem -Path $packageDir -Recurse | Measure-Object | ForEach-Object {
    Write-Info "  - 文件数: $($_.Count)"
}

Write-Host ""
Write-Info "下一步："
Write-Info "1. 在 GitHub 上创建 Release 标签: v$Version"
Write-Info "2. 上传 ZIP 文件: $zipFile"
Write-Info "3. 添加发布说明"

