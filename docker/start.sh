#!/bin/bash

# Smart Lecturer Docker 快速启动脚本
# 作者: Smart Lecturer Team
# 版本: 1.0.0
# 日期: 2025-11-08

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker 20.10+"
        exit 1
    fi
    
    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose 2.0+"
        exit 1
    fi
    
    # 检查 Docker 守护进程
    if ! docker info &> /dev/null; then
        log_error "Docker 守护进程未运行，请启动 Docker Desktop"
        exit 1
    fi
    
    log_success "系统依赖检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."
    
    mkdir -p data logs temp sync_html_output
    
    log_success "目录创建完成"
}

# 配置环境变量
setup_environment() {
    log_info "配置环境变量..."
    
    if [ ! -f .env ]; then
        log_info "创建 .env 文件..."
        cat > .env << EOF
# Smart Lecturer 环境配置
# LLM 提供商选择：gemini 或 openai
LLM_PROVIDER=gemini

# Gemini API 配置（如果使用 Gemini）
GEMINI_API_KEY=你的_GEMINI_API_KEY

# OpenAI API 配置（如果使用 OpenAI）
# OPENAI_API_KEY=你的_OPENAI_API_KEY
# OPENAI_API_BASE=https://你的自定义域名/v1

# 应用配置
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0
STREAMLIT_SERVER_HEADLESS=true
STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# 时区和语言设置
TZ=Asia/Shanghai
LC_ALL=C.UTF-8
LANG=C.UTF-8
EOF
        log_warning "请编辑 .env 文件并填入你的 API 密钥"
    else
        log_success ".env 文件已存在"
    fi
}

# 构建镜像
build_image() {
    log_info "构建 Docker 镜像..."
    
    docker-compose build --no-cache
    
    log_success "镜像构建完成"
}

# 启动服务
start_services() {
    log_info "启动服务..."
    
    # 选择启动模式
    echo "请选择启动模式："
    echo "1) Streamlit 直连 (端口 8501)"
    echo "2) Nginx 反向代理 (端口 80)"
    echo "3) 退出"
    
    read -p "请输入选择 (1-3): " choice
    
    case $choice in
        1)
            log_info "启动 Streamlit 服务..."
            docker-compose up -d
            log_success "服务已启动"
            log_info "访问地址: http://localhost:8501"
            ;;
        2)
            log_info "启动 Nginx 反向代理..."
            docker-compose --profile production up -d
            log_success "服务已启动"
            log_info "访问地址: http://localhost"
            ;;
        3)
            log_info "退出"
            exit 0
            ;;
        *)
            log_error "无效选择"
            exit 1
            ;;
    esac
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose ps
    
    echo ""
    log_info "健康检查："
    docker-compose exec -T smart-lecturer curl -f http://localhost:8501/_stcore/health 2>/dev/null || log_warning "服务可能未完全启动"
    
    echo ""
    log_info "查看日志："
    echo "  docker-compose logs -f smart-lecturer"
    echo ""
    log_info "停止服务："
    echo "  docker-compose down"
}

# 主函数
main() {
    echo "=========================================="
    echo "    Smart Lecturer Docker 快速启动"
    echo "=========================================="
    echo ""
    
    # 检查是否以 root 用户运行
    if [ "$EUID" -eq 0 ]; then
        log_warning "建议不要以 root 用户运行此脚本"
        read -p "是否继续? (y/N): " confirm
        if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
            exit 1
        fi
    fi
    
    # 执行启动流程
    check_dependencies
    create_directories
    setup_environment
    build_image
    start_services
    
    echo ""
    echo "=========================================="
    log_success "Smart Lecturer 启动完成！"
    echo "=========================================="
    echo ""
    
    show_status
}

# 显示帮助信息
show_help() {
    echo "Smart Lecturer Docker 快速启动脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -c, --check    仅检查依赖"
    echo "  -b, --build    仅构建镜像"
    echo "  -s, --start    启动服务"
    echo ""
    echo "示例:"
    echo "  $0              # 完整启动流程"
    echo "  $0 --check      # 检查依赖"
    echo "  $0 --build      # 构建镜像"
    echo ""
}

# 命令行参数处理
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -c|--check)
        check_dependencies
        exit 0
        ;;
    -b|--build)
        check_dependencies
        create_directories
        setup_environment
        build_image
        exit 0
        ;;
    -s|--start)
        start_services
        show_status
        exit 0
        ;;
    "")
        main
        ;;
    *)
        log_error "未知参数: $1"
        show_help
        exit 1
        ;;
esac
