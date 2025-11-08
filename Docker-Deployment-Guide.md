# Smart Lecturer Docker 部署使用说明

## 概述

本项目提供了完整的 Docker 部署方案，包含 pdf2htmlEX 工具和主应用，让您在任何支持 Docker 的环境中轻松运行 Smart Lecturer。

## 🚀 快速开始

### 前置要求

- Docker 20.10+
- Docker Compose 2.0+
- 可用的 API 密钥（Gemini 或 OpenAI）

### 1. 克隆项目

```bash
git clone <项目地址>
cd lecturer
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 复制环境变量模板
cp .env.example .env
```

编辑 `.env` 文件：

```bash
# LLM 提供商选择：gemini 或 openai
LLM_PROVIDER=gemini

# Gemini API 配置（如果使用 Gemini）
GEMINI_API_KEY=你的_GEMINI_API_KEY

# OpenAI API 配置（如果使用 OpenAI）
OPENAI_API_KEY=你的_OPENAI_API_KEY
OPENAI_API_BASE=你的自定义API地址  # 可选

# 应用配置
STREAMLIT_SERVER_PORT=8501
TZ=Asia/Shanghai
LC_ALL=C.UTF-8
LANG=C.UTF-8
```

### 3. 启动服务

#### 方式一：仅使用 Streamlit（推荐用于开发和测试）

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f smart-lecturer

# 停止服务
docker-compose down
```

#### 方式二：使用 Nginx 反向代理（推荐用于生产环境）

```bash
# 启动所有服务（包括 Nginx）
docker-compose --profile production up -d

# 查看日志
docker-compose logs -f

# 停止所有服务
docker-compose --profile production down
```

### 4. 访问应用

- **Streamlit 直连**: http://localhost:8501
- **Nginx 代理**: http://localhost (80 端口)

## 📁 目录结构

Docker 部署包含以下重要文件：

```
项目根目录/
├── Dockerfile                 # Docker 镜像构建文件
├── docker-compose.yml         # Docker 编排配置
├── .dockerignore             # Docker 构建忽略文件
├── docker/
│   ├── entrypoint.sh         # 容器启动脚本
│   └── nginx.conf            # Nginx 配置文件
├── .env                      # 环境变量配置
├── data/                     # 数据持久化目录（自动创建）
├── logs/                     # 日志目录（自动创建）
├── temp/                     # 临时文件目录（自动创建）
└── sync_html_output/         # HTML 输出目录（自动创建）
```

## 🔧 高级配置

### 端口配置

修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8501:8501"  # 改为你的端口
```

### 数据持久化

所有数据目录都已挂载到宿主机：

- `./data` → `/app/data` - 用户上传的文件
- `./logs` → `/app/logs` - 应用日志
- `./temp` → `/app/temp` - 临时文件
- `./sync_html_output` → `/app/sync_html_output` - 生成的 HTML 文件

### 性能优化

#### 1. 资源限制

在 `docker-compose.yml` 中添加资源限制：

```yaml
services:
  smart-lecturer:
    # ... 其他配置
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '1.0'
          memory: 1G
```

#### 2. 调优 Java 堆内存

```yaml
environment:
  - JAVA_OPTS=-Xmx1g -Xms512m
```

### 字体自定义

如果您需要使用自定义字体：

1. 创建目录：`mkdir -p custom_fonts`
2. 复制字体文件到该目录
3. 取消注释 `docker-compose.yml` 中的字体挂载行：
   ```yaml
   - ./custom_fonts:/app/assets/fonts
   ```

## 🛠️ 常用操作

### 查看服务状态

```bash
# 查看运行状态
docker-compose ps

# 查看实时日志
docker-compose logs -f smart-lecturer

# 查看资源使用
docker stats
```

### 容器管理

```bash
# 重启服务
docker-compose restart

# 重建镜像
docker-compose build --no-cache

# 清理容器和镜像
docker-compose down --rmi all

# 清理所有数据
docker-compose down -v
```

### 备份和恢复

#### 备份数据

```bash
# 备份持久化数据
tar -czf smart-lecturer-backup-$(date +%Y%m%d).tar.gz data/ logs/ temp/ sync_html_output/
```

#### 恢复数据

```bash
# 停止服务
docker-compose down

# 恢复数据
tar -xzf smart-lecturer-backup-YYYYMMDD.tar.gz

# 重新启动
docker-compose up -d
```

## 🌐 生产环境部署

### 1. 域名和 SSL

修改 `docker/nginx.conf` 中的 HTTPS 配置部分，取消注释并配置：

```bash
# 生成 SSL 证书
mkdir -p docker/ssl
# 放置你的证书文件：
# - cert.pem
# - key.pem
```

更新 `docker-compose.yml` 中的域名：

```yaml
server_name your-domain.com;
```

### 2. 安全加固

#### 防火墙设置

```bash
# Ubuntu/Debian
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

#### 容器安全

1. **使用非 root 用户** - 容器内已配置
2. **资源限制** - 已在配置中设置
3. **只读根文件系统**：
   ```yaml
   read_only: true
   tmpfs:
     - /tmp
   ```

### 3. 监控和日志

#### 集成外部日志系统

```yaml
# 在 docker-compose.yml 中添加
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

#### 健康检查

容器已配置健康检查，可以通过以下命令查看：

```bash
docker-compose ps
```

## 🔍 故障排除

### 常见问题

#### 1. 容器启动失败

```bash
# 查看详细错误
docker-compose logs smart-lecturer

# 检查端口占用
netstat -tulpn | grep 8501
```

#### 2. PDF 处理失败

检查 pdf2htmlEX 是否正确安装：

```bash
# 进入容器
docker-compose exec smart-lecturer bash

# 检查 pdf2htmlEX
pdf2htmlEX --version
```

#### 3. 内存不足

调整内存限制：

```yaml
# 在 docker-compose.yml 中
services:
  smart-lecturer:
    deploy:
      resources:
        limits:
          memory: 4G  # 增加内存限制
```

#### 4. API 连接失败

检查环境变量配置：

```bash
# 查看容器内环境变量
docker-compose exec smart-lecturer env | grep API
```

### 调试模式

启动调试模式：

```bash
# 交互式启动
docker-compose run --rm smart-lecturer bash

# 在容器内调试
cd /app
python -c "import app.streamlit_app"
```

## 📈 性能优化

### 1. 多进程处理

修改 Streamlit 配置以支持多进程：

```yaml
environment:
  - STREAMLIT_SERVER_MAX_UPLOAD_SIZE=200
  - STREAMLIT_SERVER_MAX_MESSAGE_SIZE=200
  - STREAMLIT_SERVER_MAX_CORS_ORIGIN=*
```

### 2. 缓存优化

启用 Redis 缓存（可选）：

```yaml
# 添加 Redis 服务
redis:
  image: redis:alpine
  volumes:
    - redis_data:/data

services:
  smart-lecturer:
    environment:
      - REDIS_URL=redis://redis:6379
```

### 3. 数据库集成

集成 PostgreSQL 进行数据持久化：

```yaml
# 添加 PostgreSQL 服务
postgres:
  image: postgres:13
  environment:
    POSTGRES_DB: smart_lecturer
    POSTGRES_USER: admin
    POSTGRES_PASSWORD: password
  volumes:
    - postgres_data:/var/lib/postgresql/data
```

## 🔧 自定义配置

### 1. 修改启动参数

在 `docker/entrypoint.sh` 中添加自定义参数：

```bash
exec streamlit run app/streamlit_app.py \
  --server.port="$STREAMLIT_SERVER_PORT" \
  --server.address="$STREAMLIT_SERVER_ADDRESS" \
  --server.headless="$STREAMLIT_SERVER_HEADLESS" \
  --browser.gatherUsageStats="$STREAMLIT_BROWSER_GATHER_USAGE_STATS" \
  --server.maxUploadSize=200 \
  --server.maxMessageSize=200
```

### 2. 添加插件

将插件文件挂载到容器：

```yaml
volumes:
  - ./plugins:/app/plugins
  - ./config:/app/config
```

## 📞 技术支持

### 获取帮助

- **日志文件**: `logs/app.log`
- **容器状态**: `docker-compose ps`
- **系统资源**: `docker stats`

### 报告问题

报告问题时，请提供：

1. Docker 版本：`docker --version`
2. Docker Compose 版本：`docker-compose --version`
3. 系统信息：`uname -a`
4. 错误日志：`docker-compose logs smart-lecturer`
5. 配置文件：相关的 `.env` 和配置片段

## 📋 更新日志

### v1.0.0 (2025-11-08)
- ✅ 初始 Docker 部署支持
- ✅ pdf2htmlEX 集成
- ✅ 多阶段构建优化
- ✅ Nginx 反向代理支持
- ✅ 完整的监控和健康检查
- ✅ 生产环境部署指南

---

**祝您使用愉快！** 🎉

如有任何问题或建议，欢迎提交 Issue 或 Pull Request。
