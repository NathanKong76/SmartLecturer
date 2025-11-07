#!/bin/bash
# -*- coding: utf-8 -*-
# Startup Script for Linux/macOS
# Activates virtual environment and starts Streamlit application

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
VENV_PATH="$PROJECT_ROOT/.venv"

info "=========================================="
info "PDF 讲解流 - 启动脚本"
info "=========================================="
echo ""

# Check virtual environment
if [ ! -d "$VENV_PATH" ]; then
    error "虚拟环境未找到: $VENV_PATH"
    info "请先运行安装脚本: ./scripts/install.sh"
    exit 1
fi

# Activate virtual environment
info "激活虚拟环境..."
source "$VENV_PATH/bin/activate"
if [ $? -ne 0 ]; then
    error "激活虚拟环境失败"
    exit 1
fi

# Check environment variable
echo ""
info "检查环境变量..."

# Try to load .env file
ENV_PATH="$PROJECT_ROOT/.env"
if [ -f "$ENV_PATH" ]; then
    info "加载 .env 文件..."
    set -a
    source "$ENV_PATH"
    set +a
fi

PROVIDER=${LLM_PROVIDER:-gemini}

case "${PROVIDER,,}" in
    openai)
        if [ -z "$OPENAI_API_KEY" ]; then
            warning "未设置 OPENAI_API_KEY 环境变量"
            info "请设置环境变量或创建 .env 文件"
            echo ""
            info "设置方式:"
            info '  export OPENAI_API_KEY="你的_OPENAI_API_KEY"'
            info '  可选: export OPENAI_API_BASE="https://你的自定义域名/v1"'
            info "  或在 .env 中设置 OPENAI_API_KEY、OPENAI_API_BASE"
            echo ""
            read -p "是否继续启动？(Y/N) " continue
            if [ "$continue" != "Y" ] && [ "$continue" != "y" ]; then
                exit 0
            fi
        else
            success "找到 OPENAI_API_KEY"
        fi
        ;;
    *)
        if [ -z "$GEMINI_API_KEY" ]; then
            warning "未设置 GEMINI_API_KEY 环境变量"
            info "请设置环境变量或创建 .env 文件"
            echo ""
            info "设置方式:"
            info '  export GEMINI_API_KEY="你的_GEMINI_API_KEY"'
            info "  或创建 .env 文件: GEMINI_API_KEY=你的_GEMINI_API_KEY"
            echo ""
            read -p "是否继续启动？(Y/N) " continue
            if [ "$continue" != "Y" ] && [ "$continue" != "y" ]; then
                exit 0
            fi
        else
            success "找到 GEMINI_API_KEY"
        fi
        ;;
esac

# Start Streamlit
echo ""
info "启动 Streamlit 应用..."
APP_PATH="$PROJECT_ROOT/app/streamlit_app.py"

if [ ! -f "$APP_PATH" ]; then
    error "应用文件未找到: $APP_PATH"
    exit 1
fi

echo ""
success "应用正在启动..."
info "浏览器将自动打开，或访问: http://localhost:8501"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Start Streamlit
streamlit run "$APP_PATH"

