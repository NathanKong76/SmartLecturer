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
Write-Info "PDF 讲解流 - 安装脚本"
Write-Info "=========================================="
Write-Host ""

# 查找 Python 3.11 的函数
function Find-Python313 {
    $python311Path = $null
    $python311Exe = $null
    
    # 方法1: 尝试使用 py launcher
    Write-Info "方法1: 尝试使用 py launcher (py -3.13)..."
    try {
        $pyOutput = py -3.13 --version 2>&1
        if ($LASTEXITCODE -eq 0 -and $pyOutput -match "Python 3\.13") {
            # 获取 Python 可执行文件路径
            $pyPath = py -3.13 -c "import sys; print(sys.executable)" 2>&1
            if ($LASTEXITCODE -eq 0) {
                $python313Exe = $pyPath.Trim()
                $python313Path = Split-Path -Parent $python313Exe
                Write-Success "通过 py launcher 找到 Python 3.13: $python313Exe"
                return $python313Exe
            }
        }
    } catch {
        Write-Warning "py launcher 不可用或未找到 Python 3.13"
    }
    
    # 方法2: 在常见安装位置查找
    Write-Info "方法2: 在常见安装位置查找..."
    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python313",
        "$env:ProgramFiles\Python313",
        "$env:ProgramFiles(x86)\Python313",
        "C:\Python313",
        "$env:USERPROFILE\Python313"
    )
    
    foreach ($path in $commonPaths) {
        $testExe = Join-Path $path "python.exe"
        if (Test-Path $testExe) {
            # 验证版本
            $version = & $testExe --version 2>&1
            if ($version -match "Python 3\.13") {
                Write-Success "在 $path 找到 Python 3.13"
                return $testExe
            }
        }
    }
    
    # 方法3: 在注册表中查找
    Write-Info "方法3: 在注册表中查找..."
    try {
        $regPaths = @(
            "HKLM:\SOFTWARE\Python\PythonCore\3.13\InstallPath",
            "HKCU:\SOFTWARE\Python\PythonCore\3.13\InstallPath"
        )
        
        foreach ($regPath in $regPaths) {
            if (Test-Path $regPath) {
                $installPath = (Get-ItemProperty -Path $regPath -Name "(default)" -ErrorAction SilentlyContinue).'(default)'
                if ($installPath) {
                    $testExe = Join-Path $installPath "python.exe"
                    if (Test-Path $testExe) {
                        $version = & $testExe --version 2>&1
                        if ($version -match "Python 3\.13") {
                            Write-Success "在注册表中找到 Python 3.13: $testExe"
                            return $testExe
                        }
                    }
                }
            }
        }
    } catch {
        Write-Warning "无法访问注册表"
    }
    
    # 方法4: 在 PATH 中查找所有 python.exe
    Write-Info "方法4: 在 PATH 环境变量中查找..."
    $currentPath = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [Environment]::GetEnvironmentVariable("Path", "User")
    $pathDirs = $currentPath -split ';' | Where-Object { $_ -ne '' }
    
    foreach ($dir in $pathDirs) {
        $testExe = Join-Path $dir "python.exe"
        if (Test-Path $testExe) {
            $version = & $testExe --version 2>&1
            if ($version -match "Python 3\.13") {
                Write-Success "在 PATH 中找到 Python 3.13: $testExe"
                return $testExe
            }
        }
    }
    
    return $null
}

# 查找 Python 3.13
Write-Info "正在查找 Python 3.13..."
$python313Exe = Find-Python313

if (-not $python313Exe) {
    Write-Error "未找到 Python 3.13"
    Write-Info ""
    Write-Info "请确保已安装 Python 3.13"
    Write-Info "下载地址: https://www.python.org/downloads/release/python-3130/"
    Write-Info ""
    Write-Info "如果已安装但脚本找不到，请："
    Write-Info "  1. 运行 .\scripts\add-python-to-path.ps1 将 Python 3.13 添加到 PATH"
    Write-Info "  2. 或者手动指定 Python 3.13 的路径"
    exit 1
}

# 验证 Python 版本
$pythonVersion = & $python313Exe --version 2>&1
Write-Success "找到 Python 3.13: $pythonVersion"
Write-Info "Python 路径: $python313Exe"

# 设置全局变量供后续使用
$script:pythonCmd = $python313Exe

# Check pip
Write-Info "检查 pip..."
try {
    $pipVersion = & $python313Exe -m pip --version 2>&1
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

& $python313Exe -m venv $venvPath
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
& $python313Exe -m pip install --upgrade pip
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

# 首先尝试安装所有依赖（优先使用二进制包）
Write-Info "尝试安装依赖（优先使用预编译二进制包）..."
$installOutput = & $python313Exe -m pip install --prefer-binary -r $requirementsFile 2>&1 | Out-String
if ($LASTEXITCODE -ne 0) {
    Write-Warning "使用预编译包安装失败，检查错误原因..."
    
    # 检查错误是否与 pyarrow 相关
    if ($installOutput -match "pyarrow|PyArrow|cmake") {
        Write-Warning "检测到 pyarrow 安装问题（需要从源码编译，但缺少构建工具）"
        Write-Warning ""
        Write-Warning "尝试分步安装，跳过 pyarrow..."
        
        # 步骤 1: 创建一个临时的 requirements 文件，排除 pyarrow
        Write-Info "步骤 1: 创建临时依赖文件（排除 pyarrow）..."
        $tempRequirements = Join-Path $projectRoot "requirements_temp.txt"
        Get-Content $requirementsFile | Where-Object { 
            $_ -notmatch "^pyarrow" -and 
            $_ -notmatch "^#.*pyarrow"
        } | Set-Content $tempRequirements
        
        # 步骤 2: 先安装 streamlit，使用 --no-deps 避免自动安装 pyarrow
        Write-Info "步骤 2: 安装 streamlit（不安装依赖）..."
        & $python313Exe -m pip install --prefer-binary --no-deps streamlit>=1.39.0
        $streamlitInstalled = $LASTEXITCODE -eq 0
        
        # 步骤 3: 手动安装 streamlit 的核心依赖（排除 pyarrow）
        if ($streamlitInstalled) {
            Write-Info "步骤 3: 安装 streamlit 的核心依赖（跳过 pyarrow）..."
            $streamlitDeps = @(
                "altair<6,>=4.0",
                "blinker<2,>=1.0.0",
                "cachetools<6,>=4.0",
                "click<9,>=7.0",
                "numpy<3,>=1.20",
                "packaging<25,>=20",
                "pandas<3,>=1.3.0",
                "protobuf<6,>=3.20",
                "pydeck<1,>=0.8.0b4",
                "requests<3,>=2.27",
                "rich<14,>=10.14.0",
                "tenacity<9,>=8.1.0",
                "toml<2,>=0.10.1",
                "typing-extensions<5,>=4.3.0",
                "gitpython!=3.1.19,<4,>=3.0.7",
                "tornado<7,>=6.0.3",
                "watchdog<5,>=2.1.5"
            )
            # 注意：这里故意跳过了 pyarrow
            foreach ($dep in $streamlitDeps) {
                & $python313Exe -m pip install --prefer-binary $dep 2>&1 | Out-Null
            }
        }
        
        # 步骤 4: 安装其他依赖
        Write-Info "步骤 4: 安装其他依赖..."
        & $python313Exe -m pip install --prefer-binary -r $tempRequirements
        $otherDepsSuccess = $LASTEXITCODE -eq 0
        
        # 清理临时文件
        Remove-Item $tempRequirements -ErrorAction SilentlyContinue
        
        if ($otherDepsSuccess) {
            Write-Success "已成功安装依赖（跳过 pyarrow）"
            Write-Warning ""
            Write-Warning "注意：pyarrow 未安装，这不会影响 PDF 处理功能"
            Write-Warning "pyarrow 只是 streamlit 的可选依赖，用于某些数据可视化功能"
            Write-Warning ""
            Write-Warning "streamlit 应该可以正常运行，但某些数据可视化功能可能不可用"
            Write-Warning ""
            Write-Warning "如果后续需要 pyarrow，可以："
            Write-Warning "  1. 安装 Visual Studio Build Tools 后运行: pip install pyarrow"
            Write-Warning "  2. 确保使用 Python 3.13"
        } else {
            Write-Error "即使跳过 pyarrow，依赖安装仍然失败"
            Write-Warning ""
            Write-Warning "问题分析："
            Write-Warning "  Python 版本不匹配，某些包可能没有预编译的 Windows wheel 包"
            Write-Warning ""
            Write-Warning "解决方案："
            Write-Warning "  方案 1: 安装 Visual Studio Build Tools"
            Write-Warning "    https://visualstudio.microsoft.com/downloads/"
            Write-Warning "    选择 'Desktop development with C++' 工作负载"
            Write-Warning ""
            Write-Warning "  方案 2: 确保使用 Python 3.13"
            Write-Warning "    Python 3.13 有更多预编译包可用"
            Write-Warning ""
            exit 1
        }
    } else {
        # 其他错误，尝试正常安装
        Write-Warning "尝试允许从源码编译..."
        & $python313Exe -m pip install -r $requirementsFile
        if ($LASTEXITCODE -ne 0) {
            Write-Error "依赖安装失败"
            exit 1
        }
    }
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
    # 使用虚拟环境中的 Python
    $venvPython = Join-Path $venvPath "Scripts\python.exe"
    if (Test-Path $venvPython) {
        $streamlitVersion = & $venvPython -m streamlit --version 2>&1
        Write-Success "Streamlit 安装成功: $streamlitVersion"
    } else {
        Write-Warning "无法验证 Streamlit 安装（虚拟环境 Python 未找到）"
    }
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

