#!/bin/bash
set -e

# 设置默认环境变量
export STREAMLIT_SERVER_PORT=${STREAMLIT_SERVER_PORT:-8501}
export STREAMLIT_SERVER_ADDRESS=${STREAMLIT_SERVER_ADDRESS:-0.0.0.0}
export STREAMLIT_SERVER_HEADLESS=${STREAMLIT_SERVER_HEADLESS:-true}
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=${STREAMLIT_BROWSER_GATHER_USAGE_STATS:-false}

# 创建必要的目录
mkdir -p /app/logs /app/temp /app/sync_html_output

# 设置字体环境变量
if [ -f "/app/assets/fonts/SIMHEI.TTF" ]; then
    export STREAMLIT_SERVER_HEADLESS=true
fi

# 验证 pdf2htmlEX 安装
echo "验证 pdf2htmlEX 安装..."
if ! pdf2htmlEX --version > /dev/null 2>&1; then
    echo "警告: pdf2htmlEX 未正确安装，HTML-pdf2htmlEX 模式可能无法使用"
else
    echo "pdf2htmlEX 安装正常"
fi

# 设置工作目录
cd /app

# 如果提供了自定义启动参数，使用它们；否则使用默认参数
if [ "$#" -eq 0 ]; then
    echo "启动 Streamlit 应用..."
    echo ""
    echo "  You can now view your Streamlit app in your browser."
    echo ""
    echo "  URL: http://localhost:8501"
    echo ""
    exec streamlit run app/streamlit_app.py \
        --server.port="$STREAMLIT_SERVER_PORT" \
        --server.address="$STREAMLIT_SERVER_ADDRESS" \
        --server.headless="$STREAMLIT_SERVER_HEADLESS" \
        --browser.gatherUsageStats="$STREAMLIT_BROWSER_GATHER_USAGE_STATS"
else
    echo "使用自定义启动参数: $*"
    echo ""
    echo "  You can now view your Streamlit app in your browser."
    echo ""
    echo "  URL: http://localhost:8501"
    echo ""
    exec "$@"
fi
