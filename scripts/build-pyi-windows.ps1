#!/usr/bin/env pwsh
# -*- coding: utf-8 -*-
# PyInstaller Build Script for Windows
# Packages the Streamlit application into a standalone executable

param(
    [string]$Version = "1.0.0",
    [switch]$Clean = $false
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
$distDir = Join-Path $projectRoot "dist"
$buildDir = Join-Path $projectRoot "build"

Write-Info "=========================================="
Write-Info "PyInstaller Windows 打包脚本"
Write-Info "=========================================="
Write-Host ""

# Check if PyInstaller is installed
Write-Info "检查 PyInstaller..."
try {
    $pyiVersion = python -m PyInstaller --version 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller not found"
    }
    Write-Success "PyInstaller 已安装: $pyiVersion"
}
catch {
    Write-Warning "PyInstaller 未安装，正在安装..."
    python -m pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Error "PyInstaller 安装失败"
        exit 1
    }
    Write-Success "PyInstaller 安装完成"
}

# Clean previous builds
if ($Clean) {
    Write-Info "清理旧的构建文件..."
    if (Test-Path $distDir) {
        Remove-Item -Path $distDir -Recurse -Force
    }
    if (Test-Path $buildDir) {
        Remove-Item -Path $buildDir -Recurse -Force
    }
    Write-Success "清理完成"
}

# Create PyInstaller spec file content
Write-Info "生成 PyInstaller 配置文件..."

# Find Python site-packages directory
# 首先尝试使用 site.getsitepackages()
$pythonPath = python -c "import site; print(site.getsitepackages()[0])" 2>&1
if ($LASTEXITCODE -ne 0) {
    $pythonPath = $null
}

# 验证路径是否正确（应该是 site-packages 目录）
if ($pythonPath -and (Test-Path $pythonPath)) {
    # 检查是否是 site-packages 目录（包含 __init__.py 或 dist-info/egg-info）
    $isSitePackages = (Test-Path (Join-Path $pythonPath "__init__.py")) -or 
                      (Get-ChildItem $pythonPath -Filter "*.dist-info" -ErrorAction SilentlyContinue | Measure-Object).Count -gt 0
    
    if (-not $isSitePackages) {
        # 可能是虚拟环境根目录，需要添加 Lib\site-packages
        $testPath = Join-Path $pythonPath "Lib\site-packages"
        if (Test-Path $testPath) {
            $pythonPath = $testPath
        }
    }
}

# 如果还是找不到，尝试其他方法
if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
    # 方法1: 从环境变量
    if ($env:PYTHON_HOME) {
        $pythonPath = Join-Path $env:PYTHON_HOME "Lib\site-packages"
    }
    
    # 方法2: 从 Python 可执行文件路径推断
    if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
        $pythonExe = (Get-Command python).Source
        $pythonDir = Split-Path -Parent $pythonExe
        $pythonPath = Join-Path $pythonDir "Lib\site-packages"
    }
    
    # 方法3: 尝试虚拟环境路径
    if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
        $venvPath = Join-Path $projectRoot ".venv"
        if (Test-Path $venvPath) {
            $pythonPath = Join-Path $venvPath "Lib\site-packages"
        }
    }
}

# 最终验证
if (-not $pythonPath -or -not (Test-Path $pythonPath)) {
    Write-Warning "无法找到 site-packages 目录，将跳过元数据文件收集"
    Write-Warning "尝试的路径: $pythonPath"
    $pythonPath = $null
} else {
    Write-Info "Python site-packages: $pythonPath"
}

# Collect package metadata files
$metadataFiles = @()
if ($pythonPath) {
    $packages = @('streamlit', 'langchain', 'langchain_google_genai', 'langchain_openai', 'google-generativeai', 
                  'PyMuPDF', 'Pillow', 'python-dotenv', 'tqdm', 'markdown', 
                  'beautifulsoup4', 'pymdown-extensions', 'openai')

    foreach ($pkg in $packages) {
        # Try .dist-info first
        $distInfo = Join-Path $pythonPath "$pkg.dist-info"
        if (Test-Path $distInfo) {
            $metadataFiles += "('$distInfo', '$pkg.dist-info')"
            Write-Info "  找到: $pkg.dist-info"
        } else {
            # Try .egg-info
            $eggInfo = Join-Path $pythonPath "$pkg.egg-info"
            if (Test-Path $eggInfo) {
                $metadataFiles += "('$eggInfo', '$pkg.egg-info')"
                Write-Info "  找到: $pkg.egg-info"
            }
        }
    }

    # 收集 Streamlit 静态文件
    $streamlitStaticFiles = @()
    $streamlitPath = Join-Path $pythonPath "streamlit"
    if (Test-Path $streamlitPath) {
        $staticPath = Join-Path $streamlitPath "static"
        if (Test-Path $staticPath) {
            $escapedStaticPath = $staticPath -replace '\\', '\\\\'
            $streamlitStaticFiles += "('$escapedStaticPath', 'streamlit/static')"
            Write-Info "  找到: streamlit/static"
        }
        
        # 收集 Streamlit 的其他资源文件
        $runtimePath = Join-Path $streamlitPath "runtime"
        if (Test-Path $runtimePath) {
            $escapedRuntimePath = $runtimePath -replace '\\', '\\\\'
            $streamlitStaticFiles += "('$escapedRuntimePath', 'streamlit/runtime')"
            Write-Info "  找到: streamlit/runtime"
        }
    }
} else {
    $streamlitStaticFiles = @()
    Write-Warning "跳过元数据和静态文件收集（site-packages 路径未找到）"
}

$metadataData = if ($metadataFiles.Count -gt 0) {
    $allFiles = $metadataFiles
    if ($streamlitStaticFiles.Count -gt 0) {
        $allFiles += $streamlitStaticFiles
    }
    $allFiles -join ",`n        "
} else {
    if ($streamlitStaticFiles.Count -gt 0) {
        $streamlitStaticFiles -join ",`n        "
    } else {
        "# No metadata files found"
    }
}

# 获取 site-packages 路径用于 pathex
$pathexPath = if ($pythonPath) {
    # 转换反斜杠为正斜杠，避免 Unicode 转义问题
    $escapedPath = $pythonPath -replace '\\', '/'
    "['$escapedPath']"
} else {
    "[]"
}

$specContent = @"
# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# 收集 Streamlit 的所有子模块和数据文件
try:
    streamlit_submodules = collect_submodules('streamlit')
    streamlit_data = collect_data_files('streamlit')
    print(f"Collected {len(streamlit_submodules)} streamlit submodules")
    print(f"Collected {len(streamlit_data)} streamlit data files")
except Exception as e:
    print(f"Warning: Could not collect streamlit modules: {e}")
    import traceback
    traceback.print_exc()
    streamlit_submodules = ['streamlit']  # 至少包含基础模块
    streamlit_data = []

a = Analysis(
    ['pyi_entry.py'],
    pathex=$pathexPath,
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('app', 'app'),
        ('scripts', 'scripts'),  # 包含安装脚本，用于自动安装 pdf2htmlEX
        ('resource/logo.png', 'resource'),  # 包含图标文件
        $metadataData
    ] + streamlit_data,
    hiddenimports=[
        # Streamlit 核心模块
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner.script_runner',
        'streamlit.runtime.state',
        'streamlit.components.v1',
        'streamlit.version',
        'streamlit.config',
        'streamlit.runtime',
        'streamlit.runtime.caching',
        'streamlit.runtime.legacy_caching',
        'streamlit.runtime.metrics_util',
        'streamlit.runtime.scriptrunner',
        'streamlit.runtime.state.session_state',
        'streamlit.runtime.state.widgets',
        'streamlit.web',
        'streamlit.web.server',
        # 元数据支持
        'importlib.metadata',
        'importlib_metadata',
        # 其他依赖
        'langchain',
        'langchain_google_genai',
        'langchain_openai',
        'google.generativeai',
        'openai',
        'PIL',
        'pymupdf',
        'fitz',
        'dotenv',
        'tqdm',
        'markdown',
        'beautifulsoup4',
        'bs4',
        'pymdown_extensions',
        'pkg_resources',
    ] + streamlit_submodules,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='lecturer',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 改为 True 以便看到错误信息，调试完成后可改回 False
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resource/logo.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lecturer',
)
"@

$specFile = Join-Path $projectRoot "lecturer.spec"
$specContent | Out-File -FilePath $specFile -Encoding UTF8

Write-Success "配置文件已生成: $specFile"

# Build with PyInstaller
Write-Host ""
Write-Info "开始打包..."
Write-Info "这可能需要几分钟时间..."

# Change to project root directory
Set-Location $projectRoot

# Verify spec file exists
if (-not (Test-Path $specFile)) {
    Write-Error "配置文件未找到: $specFile"
    exit 1
}

Write-Info "当前工作目录: $(Get-Location)"
Write-Info "使用配置文件: $specFile"

# 使用 spec 文件打包
python -m PyInstaller $specFile --clean --noconfirm

if ($LASTEXITCODE -ne 0) {
    Write-Error "打包失败"
    exit 1
}

# Use the PyInstaller generated directory directly
$lecturerDir = Join-Path $distDir "lecturer"
$lecturerExe = Join-Path $distDir "lecturer.exe"

# Check which format was created
if (Test-Path $lecturerDir) {
    # Directory format (onefile=False)
    $packageDir = $lecturerDir
    Write-Success "使用目录格式: $packageDir"
}
elseif (Test-Path $lecturerExe) {
    # Single exe format (onefile=True)
    $packageDir = $distDir
    Write-Success "使用单文件格式: $packageDir"
}
else {
    Write-Error "未找到打包输出文件"
    Write-Info "检查目录: $distDir"
    Get-ChildItem $distDir | ForEach-Object { Write-Info "  - $($_.Name)" }
    exit 1
}

# Copy additional files to the package directory
Write-Info "复制额外文件..."
Copy-Item -Path (Join-Path $projectRoot "README.md") -Destination $packageDir -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $projectRoot "RELEASE.md") -Destination $packageDir -Force -ErrorAction SilentlyContinue
Copy-Item -Path (Join-Path $projectRoot "HTML-pdf2htmlEX版使用说明.md") -Destination $packageDir -Force -ErrorAction SilentlyContinue

# Create .env.example
$envExample = @"
GEMINI_API_KEY=your_gemini_api_key_here
"@
$envExample | Out-File -FilePath (Join-Path $packageDir ".env.example") -Encoding UTF8 -NoNewline

# Create startup script with better error handling
$startScript = @"
@echo off
cd /d "%~dp0"
echo ==========================================
echo PDF 讲解流 - 启动中...
echo ==========================================
echo.
echo 正在启动应用，请稍候...
echo 浏览器将自动打开，或访问: http://localhost:8501
echo.
echo 按 Ctrl+C 可停止应用
echo ==========================================
echo.

if exist "lecturer.exe" (
    lecturer.exe
) else if exist "lecturer\lecturer.exe" (
    lecturer\lecturer.exe
) else (
    echo 错误: 未找到可执行文件
    echo 请检查打包是否完整
    pause
)
"@
$startScript | Out-File -FilePath (Join-Path $packageDir "start.bat") -Encoding ASCII

Write-Host ""
Write-Success "=========================================="
Write-Success "Windows 打包完成！"
Write-Success "=========================================="
Write-Host ""
Write-Info "打包目录: $packageDir"

# Check which format was created
if (Test-Path (Join-Path $packageDir "lecturer.exe")) {
    Write-Info "可执行文件: $packageDir\lecturer.exe"
}
elseif (Test-Path (Join-Path $packageDir "lecturer\lecturer.exe")) {
    Write-Info "可执行文件: $packageDir\lecturer\lecturer.exe"
}
else {
    Write-Warning "未找到可执行文件，请检查打包输出"
}

Write-Host ""
Write-Info "下一步："
Write-Info "1. 测试运行: $packageDir\lecturer.exe"
Write-Info "2. 或使用启动脚本: $packageDir\start.bat"
Write-Host ""

