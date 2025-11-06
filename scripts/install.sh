#!/bin/bash
# -*- coding: utf-8 -*-
# Installation Script for Linux/macOS
# Sets up Python virtual environment and installs dependencies

set -e

# Color output functions
function info() {
    echo -e "\033[0;36m$1\033[0m"
}

function success() {
    echo -e "\033[0;32m$1\033[0m"
}

function warning() {
    echo -e "\033[0;33m$1\033[0m"
}

function error() {
    echo -e "\033[0;31m$1\033[0m"
}

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

info "=========================================="
info "PDF 讲解流 - 安装脚本"
info "=========================================="
echo ""

# Check Python installation
info "检查 Python 安装..."
if ! command -v python3 &> /dev/null; then
    error "未找到 Python 3，请先安装 Python 3.10 或更高版本"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1)
success "找到 Python: $PYTHON_VERSION"

# Check Python version (3.10+)
PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    error "需要 Python 3.10 或更高版本，当前版本: $PYTHON_VERSION"
    exit 1
fi

# Check pip
info "检查 pip..."
if ! python3 -m pip --version &> /dev/null; then
    error "未找到 pip，请先安装 pip"
    exit 1
fi

PIP_VERSION=$(python3 -m pip --version 2>&1)
success "找到 pip: $PIP_VERSION"

# Create virtual environment
VENV_PATH="$PROJECT_ROOT/.venv"
echo ""
info "创建虚拟环境..."
if [ -d "$VENV_PATH" ]; then
    warning "虚拟环境已存在，将重新创建..."
    rm -rf "$VENV_PATH"
fi

python3 -m venv "$VENV_PATH"
if [ $? -ne 0 ]; then
    error "创建虚拟环境失败"
    exit 1
fi
success "虚拟环境创建成功: $VENV_PATH"

# Activate virtual environment
echo ""
info "激活虚拟环境..."
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    error "激活虚拟环境失败"
    exit 1
fi

# Upgrade pip
echo ""
info "升级 pip..."
python -m pip install --upgrade pip || warning "pip 升级失败，继续安装依赖..."

# Install dependencies
echo ""
info "安装依赖包..."
REQUIREMENTS_FILE="$PROJECT_ROOT/requirements.txt"
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    error "未找到 requirements.txt"
    exit 1
fi

python -m pip install -r "$REQUIREMENTS_FILE"
if [ $? -ne 0 ]; then
    error "依赖安装失败"
    exit 1
fi
success "依赖安装完成"

# Create .env.example if not exists
echo ""
info "检查环境变量配置..."
ENV_EXAMPLE_PATH="$PROJECT_ROOT/.env.example"
ENV_PATH="$PROJECT_ROOT/.env"

if [ ! -f "$ENV_EXAMPLE_PATH" ]; then
    info "创建 .env.example..."
    cat > "$ENV_EXAMPLE_PATH" << EOF
GEMINI_API_KEY=your_gemini_api_key_here
EOF
fi

if [ ! -f "$ENV_PATH" ]; then
    warning "未找到 .env 文件"
    info "请创建 .env 文件并设置 GEMINI_API_KEY"
    info "参考 .env.example 文件"
    echo ""
    info "或者使用以下命令设置环境变量:"
    info '  export GEMINI_API_KEY="你的_API_KEY"'
else
    success ".env 文件已存在"
fi

# Verify installation
echo ""
info "验证安装..."
if python -m streamlit --version &> /dev/null; then
    STREAMLIT_VERSION=$(python -m streamlit --version 2>&1)
    success "Streamlit 安装成功: $STREAMLIT_VERSION"
else
    warning "无法验证 Streamlit 安装"
fi

echo ""
success "=========================================="
success "安装完成！"
success "=========================================="
echo ""
info "下一步："
info "1. 设置 GEMINI_API_KEY 环境变量或创建 .env 文件"
info "2. 运行启动脚本: ./scripts/start.sh"
info "   或者直接运行: streamlit run app/streamlit_app.py"
echo ""

