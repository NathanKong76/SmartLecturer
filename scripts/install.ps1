#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# Installation Script for Windows
# Sets up Python virtual environment and installs dependencies

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

Write-Info "=========================================="
Write-Info "智讲 / PDF-Lecture-AI - 安装脚本"
Write-Info "=========================================="
Write-Host ""

# Check Python installation
Write-Info "检查 Python 安装..."
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "Python not found"
    }
    Write-Success "找到 Python: $pythonVersion"
    
    # Check Python version (3.10+)
    $versionMatch = $pythonVersion -match "Python (\d+)\.(\d+)"
    if ($versionMatch) {
        $majorVersion = [int]$matches[1]
        $minorVersion = [int]$matches[2]
        if ($majorVersion -lt 3 -or ($majorVersion -eq 3 -and $minorVersion -lt 10)) {
            Write-Error "需要 Python 3.10 或更高版本，当前版本: $pythonVersion"
            exit 1
        }
    }
} catch {
    Write-Error "未找到 Python，请先安装 Python 3.10 或更高版本"
    Write-Info "下载地址: https://www.python.org/downloads/"
    exit 1
}

# Check pip
Write-Info "检查 pip..."
try {
    $pipVersion = python -m pip --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "pip not found"
    }
    Write-Success "找到 pip: $pipVersion"
} catch {
    Write-Error "未找到 pip，请先安装 pip"
    exit 1
}

# Create virtual environment
$venvPath = Join-Path $projectRoot ".venv"
Write-Host ""
Write-Info "创建虚拟环境..."
if (Test-Path $venvPath) {
    Write-Warning "虚拟环境已存在，将重新创建..."
    Remove-Item -Path $venvPath -Recurse -Force
}

python -m venv $venvPath
if ($LASTEXITCODE -ne 0) {
    Write-Error "创建虚拟环境失败"
    exit 1
}
Write-Success "虚拟环境创建成功: $venvPath"

# Activate virtual environment
Write-Host ""
Write-Info "激活虚拟环境..."
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"
if (-not (Test-Path $activateScript)) {
    Write-Error "虚拟环境激活脚本未找到"
    exit 1
}

& $activateScript
if ($LASTEXITCODE -ne 0) {
    Write-Error "激活虚拟环境失败"
    exit 1
}

# Upgrade pip
Write-Host ""
Write-Info "升级 pip..."
python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    Write-Warning "pip 升级失败，继续安装依赖..."
}

# Install dependencies
Write-Host ""
Write-Info "安装依赖包..."
$requirementsFile = Join-Path $projectRoot "requirements.txt"
if (-not (Test-Path $requirementsFile)) {
    Write-Error "未找到 requirements.txt"
    exit 1
}

python -m pip install -r $requirementsFile
if ($LASTEXITCODE -ne 0) {
    Write-Error "依赖安装失败"
    exit 1
}
Write-Success "依赖安装完成"

# Create .env.example if not exists
Write-Host ""
Write-Info "检查环境变量配置..."
$envExamplePath = Join-Path $projectRoot ".env.example"
$envPath = Join-Path $projectRoot ".env"

if (-not (Test-Path $envExamplePath)) {
    Write-Info "创建 .env.example..."
    $envExample = @"
GEMINI_API_KEY=your_gemini_api_key_here
"@
    $envExample | Out-File -FilePath $envExamplePath -Encoding UTF8 -NoNewline
}

if (-not (Test-Path $envPath)) {
    Write-Warning "未找到 .env 文件"
    Write-Info "请创建 .env 文件并设置 GEMINI_API_KEY"
    Write-Info "参考 .env.example 文件"
    Write-Host ""
    Write-Info "或者使用以下命令设置环境变量:"
    Write-Info '  $env:GEMINI_API_KEY = "你的_API_KEY"'
} else {
    Write-Success ".env 文件已存在"
}

# Verify installation
Write-Host ""
Write-Info "验证安装..."
try {
    $streamlitVersion = python -m streamlit --version 2>&1
    Write-Success "Streamlit 安装成功: $streamlitVersion"
} catch {
    Write-Warning "无法验证 Streamlit 安装"
}

Write-Host ""
Write-Success "=========================================="
Write-Success "安装完成！"
Write-Success "=========================================="
Write-Host ""
Write-Info "下一步："
Write-Info "1. 设置 GEMINI_API_KEY 环境变量或创建 .env 文件"
Write-Info "2. 运行启动脚本: .\scripts\start.ps1"
Write-Info "   或者直接运行: streamlit run app\streamlit_app.py"
Write-Host ""

