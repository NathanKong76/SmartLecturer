#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# Startup Script for Windows
# Activates virtual environment and starts Streamlit application

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
$venvPath = Join-Path $projectRoot ".venv"

Write-Info "=========================================="
Write-Info "PDF 讲解流 - 启动脚本"
Write-Info "=========================================="
Write-Host ""
Write-Info "项目根目录: $projectRoot"
Write-Info "虚拟环境路径: $venvPath"

# Check virtual environment
if (-not (Test-Path $venvPath)) {
    Write-Error "虚拟环境未找到: $venvPath"
    Write-Info "请先运行安装脚本: .\scripts\install.ps1"
    Write-Host ""
    Write-Info "当前工作目录: $(Get-Location)"
    exit 1
}

# Activate virtual environment
Write-Info "激活虚拟环境..."
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (-not (Test-Path $activateScript)) {
    Write-Error "虚拟环境激活脚本未找到: $activateScript"
    Write-Info "虚拟环境可能未正确创建，请重新运行安装脚本"
    exit 1
}

# Change to project root before activating
Set-Location $projectRoot

# Activate virtual environment using dot sourcing
try {
    & $activateScript
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne $null) {
        Write-Error "激活虚拟环境失败，退出代码: $LASTEXITCODE"
        exit 1
    }
}
catch {
    Write-Error "激活虚拟环境时发生错误: $_"
    exit 1
}

# Verify activation by checking if python is from venv
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if ($pythonPath -and $pythonPath -like "*$venvPath*") {
    Write-Success "虚拟环境激活成功"
}
else {
    Write-Warning "无法确认虚拟环境是否已激活，继续执行..."
}

# Check environment variable
Write-Host ""
Write-Info "检查环境变量..."

# Try to load .env file
$envPath = Join-Path $projectRoot ".env"
if (Test-Path $envPath) {
    Write-Info "加载 .env 文件..."
    Get-Content $envPath | ForEach-Object {
        if ($_ -match '^\s*([^#][^=]+)=(.*)$') {
            $key = $matches[1].Trim()
            $value = $matches[2].Trim()
            [Environment]::SetEnvironmentVariable($key, $value, "Process")
        }
    }
}

$provider = $env:LLM_PROVIDER
if ([string]::IsNullOrWhiteSpace($provider)) {
    $provider = "gemini"
}

switch ($provider.ToLower()) {
    "openai" {
        $apiKey = $env:OPENAI_API_KEY
        if ([string]::IsNullOrEmpty($apiKey)) {
            Write-Warning "未设置 OPENAI_API_KEY 环境变量"
            Write-Info "请设置环境变量或创建 .env 文件"
            Write-Host ""
            Write-Info "设置方式:"
            Write-Info '  $env:OPENAI_API_KEY = "你的_OPENAI_API_KEY"'
            Write-Info "  可选: $env:OPENAI_API_BASE = \"https://你的自定义域名/v1\""
            Write-Info "  或在 .env 中设置 OPENAI_API_KEY、OPENAI_API_BASE"
            Write-Host ""
            $continue = Read-Host "是否继续启动？(Y/N)"
            if ($continue -ne "Y" -and $continue -ne "y") {
                exit 0
            }
        }
        else {
            Write-Success "找到 OPENAI_API_KEY"
        }
    }
    default {
        $apiKey = $env:GEMINI_API_KEY
        if ([string]::IsNullOrEmpty($apiKey)) {
            Write-Warning "未设置 GEMINI_API_KEY 环境变量"
            Write-Info "请设置环境变量或创建 .env 文件"
            Write-Host ""
            Write-Info "设置方式:"
            Write-Info '  $env:GEMINI_API_KEY = "你的_GEMINI_API_KEY"'
            Write-Info "  或创建 .env 文件: GEMINI_API_KEY=你的_GEMINI_API_KEY"
            Write-Host ""
            $continue = Read-Host "是否继续启动？(Y/N)"
            if ($continue -ne "Y" -and $continue -ne "y") {
                exit 0
            }
        }
        else {
            Write-Success "找到 GEMINI_API_KEY"
        }
    }
}

# Start Streamlit
Write-Host ""
Write-Info "启动 Streamlit 应用..."
$appPath = Join-Path $projectRoot "app\streamlit_app.py"

if (-not (Test-Path $appPath)) {
    Write-Error "应用文件未找到: $appPath"
    Write-Info "当前工作目录: $(Get-Location)"
    exit 1
}

Write-Host ""
Write-Success "应用正在启动..."
Write-Info "浏览器将自动打开，或访问: http://localhost:8501"
Write-Host ""

# Ensure we're in project root
Set-Location $projectRoot

# Start Streamlit
python -m streamlit run $appPath

