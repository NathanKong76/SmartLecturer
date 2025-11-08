# 多阶段构建，优化镜像大小
FROM ubuntu:22.04 as builder

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-dev \
    python3.10-distutils \
    python3-pip \
    wget \
    curl \
    ca-certificates \
    fonts-liberation \
    fontconfig \
    libfontconfig1 \
    xdg-utils \
    git \
    build-essential \
    cmake \
    pkg-config \
    libpoppler-private-dev \
    libpoppler-dev \
    libpoppler-glib-dev \
    libfontconfig1-dev \
    libfreetype6-dev \
    libpng-dev \
    libjpeg-dev \
    zlib1g-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    libspiro-dev \
    libgtk-3-dev \
    libharfbuzz-dev \
    libfribidi-dev \
    libxcb1-dev \
    && rm -rf /var/lib/apt/lists/*

# 安装pdf2htmlEX
WORKDIR /tmp
RUN wget -O pdf2htmlEX.deb https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb \
    && dpkg -i pdf2htmlEX.deb \
    || apt-get install -f -y \
    && rm -f pdf2htmlEX.deb

# 验证pdf2htmlEX安装
RUN pdf2htmlEX --version

# 创建工作目录
WORKDIR /app

# 复制requirements.txt并安装Python依赖
COPY requirements.txt /app/
RUN python3.10 -m pip install --upgrade pip \
    && python3.10 -m pip install --no-cache-dir -r requirements.txt

# 最终阶段
FROM ubuntu:22.04

# 设置环境变量
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/app
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
ENV STREAMLIT_SERVER_BASE_URL_HOST=localhost

# 安装运行时依赖（包括pdf2htmlEX的依赖）
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3.10-distutils \
    python3-pip \
    fontforge \
    fonts-liberation \
    fontconfig \
    libfontconfig1 \
    libfreetype6 \
    libjpeg8 \
    libpng16-16 \
    libopenjp2-7 \
    libtiff5 \
    libspiro1 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz0b \
    libfribidi0 \
    libxcb1 \
    libx11-6 \
    wget \
    curl \
    ca-certificates \
    libcairo2 \
    libpoppler-glib8 \
    libpoppler-cpp0v5 \
    && rm -rf /var/lib/apt/lists/*

# 从构建阶段复制pdf2htmlEX
COPY --from=builder /usr/local/bin/pdf2htmlEX /usr/local/bin/pdf2htmlEX
COPY --from=builder /usr/local/lib/libpdf2htmlEX* /usr/local/lib/

# 创建应用用户
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app /app/logs /app/temp /app/assets/fonts && \
    chown -R appuser:appuser /app

# 设置工作目录
WORKDIR /app

# 复制Python环境
COPY --from=builder /usr/local/lib/python3.10 /usr/local/lib/python3.10
COPY --from=builder /usr/local/bin /usr/local/bin

# 复制应用文件
COPY --chown=appuser:appuser app/ /app/app/
COPY --chown=appuser:appuser requirements.txt /app/
COPY --chown=appuser:appuser assets/fonts/ /app/assets/fonts/

# 复制启动脚本
COPY --chown=appuser:appuser docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 切换到应用用户
USER appuser

# 设置工作目录
WORKDIR /app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# 暴露端口
EXPOSE 8501

# 设置入口点
ENTRYPOINT ["/app/entrypoint.sh"]

# 默认启动命令
CMD ["streamlit", "run", "app/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
