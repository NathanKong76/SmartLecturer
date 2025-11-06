#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# Build All Platforms with PyInstaller
# Creates packages for Windows, Linux, and macOS

param(
    [string]$Version = "1.0.0",
    [switch]$Windows = $false,
    [switch]$Linux = $false,
    [switch]$MacOS = $false,
    [switch]$All = $false
)

$ErrorActionPreference = "Continue"

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

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

Write-Info "=========================================="
Write-Info "PyInstaller 全平台打包脚本"
Write-Info "=========================================="
Write-Host ""

# Determine which platforms to build
$buildWindows = $Windows -or $All
$buildLinux = $Linux -or $All
$buildMacOS = $MacOS -or $All

# If no platform specified, detect current platform
if (-not ($buildWindows -or $buildLinux -or $buildMacOS)) {
    $os = [System.Environment]::OSVersion.Platform
    if ($os -eq "Win32NT") {
        $buildWindows = $true
        Write-Info "检测到 Windows 系统，将打包 Windows 版本"
    } else {
        Write-Warning "未指定平台，默认仅打包当前平台"
        $buildWindows = $true
    }
}

# Build Windows
if ($buildWindows) {
    Write-Host ""
    Write-Info "=========================================="
    Write-Info "开始打包 Windows 版本"
    Write-Info "=========================================="
    $windowsScript = Join-Path $scriptDir "build-pyi-windows.ps1"
    if (Test-Path $windowsScript) {
        & $windowsScript -Version $Version
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Windows 版本打包完成"
        } else {
            Write-Error "Windows 版本打包失败"
        }
    } else {
        Write-Error "未找到 Windows 打包脚本: $windowsScript"
    }
}

# Build Linux (requires WSL or Linux system)
if ($buildLinux) {
    Write-Host ""
    Write-Info "=========================================="
    Write-Info "开始打包 Linux 版本"
    Write-Info "=========================================="
    Write-Warning "Linux 版本需要在 Linux 系统或 WSL 中打包"
    
    # Check if WSL is available
    try {
        $wslAvailable = wsl --list --quiet 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Info "检测到 WSL，尝试在 WSL 中打包..."
            $linuxScript = Join-Path $scriptDir "build-pyi-linux.sh"
            $wslPath = wsl wslpath -a $linuxScript 2>&1
            if ($LASTEXITCODE -eq 0) {
                wsl bash $wslPath $Version
                if ($LASTEXITCODE -eq 0) {
                    Write-Success "Linux 版本打包完成"
                } else {
                    Write-Error "Linux 版本打包失败"
                }
            } else {
                Write-Warning "无法转换路径，跳过 Linux 打包"
            }
        } else {
            Write-Warning "未找到 WSL，跳过 Linux 打包"
        }
    } catch {
        Write-Warning "无法检测 WSL，跳过 Linux 打包"
    }
}

# Build macOS (requires macOS system)
if ($buildMacOS) {
    Write-Host ""
    Write-Info "=========================================="
    Write-Info "开始打包 macOS 版本"
    Write-Info "=========================================="
    Write-Warning "macOS 版本需要在 macOS 系统中打包"
    Write-Info "请在 macOS 系统上运行: ./scripts/build-pyi-macos.sh $Version"
}

Write-Host ""
Write-Info "=========================================="
Write-Info "打包任务完成"
Write-Info "=========================================="
Write-Host ""
Write-Info "打包文件位于: dist/ 目录"
Write-Host ""

