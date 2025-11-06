#!/bin/bash
# -*- coding: utf-8 -*-
# PDF2htmlEX Linux Auto Installer
# Automatically installs pdf2htmlEX on Linux systems

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
info "PDF2htmlEX Linux 自动安装脚本"
info "=========================================="
echo ""

# Check if running on Linux
if [[ "$OSTYPE" != "linux-gnu"* ]]; then
    error "此脚本仅支持 Linux 系统"
    exit 1
fi

# Detect Linux distribution
info "检测 Linux 发行版..."
if [ -f /etc/os-release ]; then
    . /etc/os-release
    DISTRO_ID="$ID"
    DISTRO_VERSION="$VERSION_ID"
    DISTRO_CODENAME="$VERSION_CODENAME"
    
    success "检测到: $PRETTY_NAME"
else
    error "无法检测 Linux 发行版"
    exit 1
fi

# Check if pdf2htmlEX is already installed
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

# Install based on distribution
echo ""
info "开始安装 pdf2htmlEX..."

case "$DISTRO_ID" in
    ubuntu|debian)
        info "使用 apt-get 安装..."
        
        # Update package list
        info "更新软件包列表..."
        sudo apt-get update
        
        # Try to install from repository first
        info "尝试从软件仓库安装..."
        if sudo apt-get install -y pdf2htmlex 2>/dev/null; then
            success "从软件仓库安装成功"
        else
            warning "软件仓库中未找到 pdf2htmlEX，尝试从 GitHub Releases 下载..."
            
            # Download .deb package based on Ubuntu version
            DOWNLOAD_DIR="$HOME/Downloads"
            mkdir -p "$DOWNLOAD_DIR"
            cd "$DOWNLOAD_DIR"
            
            BASE_URL="https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1"
            
            # Map Ubuntu/Debian versions to .deb packages
            DEB_FILE=""
            case "$DISTRO_CODENAME" in
                focal|bionic)
                    DEB_FILE="pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
                    ;;
                jammy)
                    # Try focal version as fallback
                    DEB_FILE="pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
                    ;;
                *)
                    # Default to focal
                    DEB_FILE="pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb"
                    warning "未找到精确匹配的版本，使用 Ubuntu 20.04 (focal) 版本"
                    ;;
            esac
            
            DEB_URL="$BASE_URL/$DEB_FILE"
            info "下载 URL: $DEB_URL"
            
            # Download .deb file
            info "正在下载 .deb 包..."
            if command -v wget &> /dev/null; then
                wget -O pdf2htmlEX.deb "$DEB_URL"
            elif command -v curl &> /dev/null; then
                curl -L -o pdf2htmlEX.deb "$DEB_URL"
            else
                error "未找到 wget 或 curl，无法下载"
                exit 1
            fi
            
            if [ ! -f pdf2htmlEX.deb ]; then
                error "下载失败"
                exit 1
            fi
            
            # Install .deb package
            info "正在安装 .deb 包..."
            sudo apt-get install -y ./pdf2htmlEX.deb
            
            # Cleanup
            rm -f pdf2htmlEX.deb
            
            if [ $? -eq 0 ]; then
                success "安装成功"
            else
                error "安装失败"
                exit 1
            fi
        fi
        ;;
    fedora|rhel|centos)
        info "使用 dnf/yum 安装..."
        
        if command -v dnf &> /dev/null; then
            sudo dnf update -y
            # Try to install from EPEL or other repositories
            if sudo dnf install -y pdf2htmlEX 2>/dev/null; then
                success "安装成功"
            else
                error "未找到 pdf2htmlEX 软件包"
                info "请手动安装或参考官方文档: https://github.com/pdf2htmlEX/pdf2htmlEX"
                exit 1
            fi
        elif command -v yum &> /dev/null; then
            sudo yum update -y
            if sudo yum install -y pdf2htmlEX 2>/dev/null; then
                success "安装成功"
            else
                error "未找到 pdf2htmlEX 软件包"
                info "请手动安装或参考官方文档: https://github.com/pdf2htmlEX/pdf2htmlEX"
                exit 1
            fi
        else
            error "未找到包管理器"
            exit 1
        fi
        ;;
    arch|manjaro)
        info "使用 pacman 安装..."
        
        # Update package database
        sudo pacman -Sy
        
        # Try to install from AUR or repository
        if sudo pacman -S --noconfirm pdf2htmlEX 2>/dev/null; then
            success "安装成功"
        else
            warning "官方仓库中未找到，可能需要从 AUR 安装"
            info "请手动安装或参考官方文档: https://github.com/pdf2htmlEX/pdf2htmlEX"
            exit 1
        fi
        ;;
    *)
        error "不支持的 Linux 发行版: $DISTRO_ID"
        info "请手动安装 pdf2htmlEX 或参考官方文档: https://github.com/pdf2htmlEX/pdf2htmlEX"
        exit 1
        ;;
esac

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

