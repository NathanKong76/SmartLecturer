#!/bin/bash
# -*- coding: utf-8 -*-
# PDF2htmlEX macOS Auto Installer
# Automatically installs pdf2htmlEX on macOS using Homebrew

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

info "=========================================="
info "PDF2htmlEX macOS 自动安装脚本"
info "=========================================="
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    error "此脚本仅支持 macOS 系统"
    exit 1
fi

# Check if Homebrew is installed
info "检查 Homebrew 安装状态..."
if ! command -v brew &> /dev/null; then
    warning "Homebrew 未安装，正在安装 Homebrew..."
    echo ""
    info "Homebrew 安装需要管理员权限，请输入密码"
    
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    
    if [ $? -ne 0 ]; then
        error "Homebrew 安装失败"
        exit 1
    fi
    
    # Add Homebrew to PATH (for Apple Silicon Macs)
    if [[ -f "/opt/homebrew/bin/brew" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f "/usr/local/bin/brew" ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    success "Homebrew 安装完成"
else
    success "Homebrew 已安装: $(brew --version | head -n 1)"
fi

# Update Homebrew
echo ""
info "更新 Homebrew..."
brew update || warning "Homebrew 更新失败，继续安装..."

# Check if pdf2htmlex is already installed
echo ""
info "检查 pdf2htmlEX 安装状态..."
if command -v pdf2htmlEX &> /dev/null; then
    VERSION=$(pdf2htmlEX --version 2>&1 || pdf2htmlEX -v 2>&1 || echo "unknown")
    success "pdf2htmlEX 已经安装: $VERSION"
    
    read -p "是否重新安装？(Y/N) " reinstall
    if [[ "$reinstall" != "Y" && "$reinstall" != "y" ]]; then
        info "跳过安装"
        exit 0
    fi
fi

# Install pdf2htmlex
echo ""
info "正在安装 pdf2htmlEX..."
info "这可能需要几分钟时间..."

brew install pdf2htmlex

if [ $? -ne 0 ]; then
    error "pdf2htmlEX 安装失败"
    echo ""
    info "如果遇到问题，可以尝试："
    info "1. 检查网络连接"
    info "2. 运行: brew doctor"
    info "3. 手动安装: brew install pdf2htmlex"
    exit 1
fi

# Verify installation
echo ""
info "验证安装..."
if command -v pdf2htmlEX &> /dev/null; then
    VERSION=$(pdf2htmlEX --version 2>&1 || pdf2htmlEX -v 2>&1 || echo "unknown")
    success "pdf2htmlEX 安装成功！"
    info "版本信息: $VERSION"
    info "安装路径: $(which pdf2htmlEX)"
else
    error "安装验证失败，pdf2htmlEX 命令未找到"
    exit 1
fi

echo ""
success "=========================================="
success "安装完成！"
success "=========================================="
echo ""
info "现在可以在终端中使用 pdf2htmlEX 了！"
echo ""

