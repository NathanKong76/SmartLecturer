推荐使用HTML-pdf2htmlEX版，排版几乎完美，支持手机和电脑端浏览器使用。但是要安装pdf2htmlEX
# PDF 讲解流 · Gemini / OpenAI

一个基于 Streamlit 的本地应用：批量读取 PDF，逐页调用 Google Gemini 或 OpenAI（含自定义兼容接口）生成中文讲解，支持多种输出格式（PDF讲解版、Markdown截图讲解、HTML截图版、HTML-pdf2htmlEX版）。支持批量下载、讲解 JSON 导出/导入与仅合成模式。

## 功能特性

### 核心功能
- **批量处理**：一次上传最多 20 个 PDF，逐页生成讲解并合成讲解版文档。
- **多模型支持**：内置 Gemini 2.5 Pro，亦可切换到 OpenAI GPT-4o/GPT-4o-mini，或使用自定义 OpenAI 兼容接口（如 Azure OpenAI、本地服务）。
- **四种输出模式**：
  - **PDF讲解版**：在PDF右侧添加讲解文字，保持矢量内容，三栏排版
  - **Markdown截图讲解**：生成包含页面截图和讲解的 Markdown 文档
  - **HTML截图版**：生成单个 HTML 文件，左侧显示 PDF 截图，右侧显示多栏 Markdown 渲染讲解
  - **HTML-pdf2htmlEX版**：使用 pdf2htmlEX 转换 PDF 为高质量 HTML，布局与 HTML 截图版一致（需安装 pdf2htmlEX）
- **保持矢量**：PDF模式下通过 PyMuPDF 将原页以矢量方式嵌入新页，避免栅格化导致的模糊。
- **可选渲染方式**：讲解可按 text、markdown 或 pandoc 渲染，支持表格、代码块等。
- **自定义 CJK 字体**：支持从系统字体选择或自定义字体路径，默认使用 SimHei。
- **速率控制**：内置 RPM/TPM/RPD 令牌与请求速率控制，减少 429/限流错误。
- **导出/导入讲解 JSON**：可将每页讲解导出为 JSON，再次导入后对同一 PDF 仅做合成。
- **智能缓存**：基于文件哈希的缓存机制，避免重复处理相同文件。
- **上下文增强**：可选启用前后各1页上下文，提高讲解连贯性。

### 技术特性
- **异步处理**：支持高并发页面处理，提高处理效率。
- **错误处理**：完善的错误处理和重试机制。
- **进度跟踪**：实时显示处理进度和状态。
- **批量重试**：支持批量重试失败的文件。

## 环境要求

- Python 3.10+
- Windows（PowerShell）或 Linux/macOS
- 至少配置一种 LLM：
  - Google Gemini（环境变量 `GEMINI_API_KEY`）
  - 或 OpenAI 及兼容服务（环境变量 `OPENAI_API_KEY`，可选 `OPENAI_API_BASE`）
- （可选）pdf2htmlEX：仅在使用 HTML-pdf2htmlEX 模式时需要



#### 方式一：Docker（推荐）
## 安装步骤

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

下载Docker Desktop 并打开

**方式A：构建并启动（首次使用或需要重新构建）**
```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f smart-lecturer

# 停止服务
docker-compose down
```

**方式B：直接使用已构建的镜像（推荐，更快）**

如果镜像已经构建完成，可以直接使用镜像启动，无需重新构建：

```bash
# 使用镜像配置文件启动（推荐）
docker-compose -f docker-compose.image.yml up -d

# 查看日志
docker-compose -f docker-compose.image.yml logs -f smart-lecturer

# 停止服务
docker-compose -f docker-compose.image.yml down
```

**或者修改 `docker-compose.yml`，将 `build` 部分改为：**
```yaml
services:
  smart-lecturer:
    image: lecturer-smart-lecturer:latest  # 直接使用镜像
    # 删除或注释掉 build 部分
    # build:
    #   context: .
    #   dockerfile: Dockerfile
```

然后使用：
```bash
docker-compose up -d
```

**检查镜像是否存在：**
```bash
# Windows PowerShell
docker images | Select-String "lecturer-smart-lecturer"

# Linux/macOS
docker images | grep lecturer-smart-lecturer
```

如果镜像不存在，需要先构建：
```bash
docker-compose build
```

### 方式二：使用发行版本

如果您下载的是 GitHub Release 发行版本，请参考 `RELEASE.md` 文件中的详细说明。

**快速开始：**

1. **解压发行包**到任意目录
2. **运行安装脚本**：
   ```powershell
   # Windows
   .\scripts\install.ps1
   ```
   ```bash
   # Linux/macOS
   chmod +x scripts/*.sh
   ./scripts/install.sh
   ```
3. **设置 API Key**（创建 `.env` 文件或设置环境变量）
4. **启动应用**：
   ```powershell
   # Windows
   .\scripts\start.ps1
   ```
   ```bash
   # Linux/macOS
   ./scripts/start.sh
   ```

### 方式二：从源代码安装

### 1. 克隆/下载项目

```powershell
# Windows PowerShell
cd C:\Users\Kong\project\lecturer
```

### 2. 创建虚拟环境并安装依赖

```powershell
# Windows PowerShell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

```bash
# Linux/macOS
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. 设置环境变量

**方式一：环境变量（推荐）**

```powershell
# Windows PowerShell
$env:LLM_PROVIDER = "gemini"            # 可选：gemini / openai
$env:GEMINI_API_KEY = "你的_GEMINI_API_KEY"
$env:OPENAI_API_KEY = "你的_OPENAI_API_KEY"   # 仅在使用 OpenAI 时需要
$env:OPENAI_API_BASE = "https://你的自定义域名/v1"  # 可选，自定义兼容接口地址
```

```bash
# Linux/macOS
export LLM_PROVIDER="gemini"
export GEMINI_API_KEY="你的_GEMINI_API_KEY"
export OPENAI_API_KEY="你的_OPENAI_API_KEY"
export OPENAI_API_BASE="https://你的自定义域名/v1"
```

**方式二：使用 .env 文件**

在项目根目录创建 `.env` 文件（注意使用 UTF-8 无 BOM 编码）：

```text
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的_GEMINI_API_KEY
# ↓ 如需改用 OpenAI，仅需切换 PROVIDER 并设置密钥
# LLM_PROVIDER=openai
# OPENAI_API_KEY=你的_OPENAI_API_KEY
# OPENAI_API_BASE=https://你的自定义域名/v1
```

### 4. （可选）安装 pdf2htmlEX

仅在需要使用 HTML-pdf2htmlEX 模式时安装。详细安装说明请参考 `HTML-pdf2htmlEX版使用说明.md`。

**Windows（推荐使用 WSL）：**

**方式一：自动安装（推荐）⭐**

运行自动安装脚本，脚本会自动检测并安装 WSL（如果未安装）和 pdf2htmlEX：

```powershell
# 以管理员身份运行 PowerShell
.\scripts\install-pdf2htmlex-wsl.ps1
```

此脚本将：
- 自动检测并安装 WSL（如果未安装，需要重启系统）
- 自动检测 Ubuntu 版本
- 自动下载并安装对应的 pdf2htmlEX 包
- 验证安装结果

**方式二：手动安装**

1) 启用 WSL：打开 PowerShell（管理员权限）
   ```powershell
   wsl --install
   ```


2) 在 WSL 里确认发行版与版本
. /etc/os-release; echo "$PRETTY_NAME"   # 例如 Ubuntu 20.04 / 22.04 / 24.04

3) 准备目录
mkdir -p ~/Downloads && cd ~/Downloads

4) 下载与自己系统接近的 .deb（示例：Ubuntu 20.04 focal 版）
到 GitHub Releases 页面挑选对应文件（名字里通常带 bionic/focal 等字样）
你也可以把下行 URL 换成你挑到的那个 .deb
wget -O pdf2htmlEX.deb \
  https://github.com/pdf2htmlEX/pdf2htmlEX/releases/download/v0.18.8.rc1/pdf2htmlEX-0.18.8.rc1-master-20200630-Ubuntu-focal-x86_64.deb

5) 用 APT 安装"本地 .deb"（注意有 ./ 前缀）
sudo apt update
sudo apt install ./pdf2htmlEX.deb

6) 验证
pdf2htmlEX -v
which pdf2htmlEX   # 一般在 /usr/local/bin

**macOS：**

**方式一：自动安装（推荐）⭐**

```bash
chmod +x scripts/install-pdf2htmlex-macos.sh
./scripts/install-pdf2htmlex-macos.sh
```

**方式二：手动安装**

```bash
brew install pdf2htmlex
```

**Linux：**

**方式一：自动安装（推荐）⭐**

```bash
chmod +x scripts/install-pdf2htmlex-linux.sh
./scripts/install-pdf2htmlex-linux.sh
```

**方式二：手动安装**

```bash
sudo apt-get update
sudo apt-get install pdf2htmlex
```

## 快速开始

### 启动应用

**使用发行版本：**

```powershell
# Windows
.\scripts\start.ps1
```

```bash
# Linux/macOS
./scripts/start.sh
```

**从源代码启动：**

```powershell
# Windows PowerShell
streamlit run app/streamlit_app.py
```

```bash
# Linux/macOS
streamlit run app/streamlit_app.py
```

浏览器将自动打开本地页面。若未自动打开，请访问 `http://localhost:8501`。

## 使用说明

### 1. 配置参数

在左侧侧边栏填写或确认参数：

#### 输出模式选择
- **PDF讲解版**：在 PDF 右侧添加讲解文字，保持矢量内容
- **Markdown截图讲解**：生成包含页面截图和讲解的 Markdown 文档
- **HTML截图版**：生成单个 HTML 文件，左侧显示 PDF 截图，右侧显示多栏 Markdown 渲染讲解
- **HTML-pdf2htmlEX版**：使用 pdf2htmlEX 转换 PDF 为高质量 HTML（需安装 pdf2htmlEX）

#### API 配置
- **GEMINI_API_KEY**：你的 Gemini API 密钥
- **模型名称**：默认 `gemini-2.5-pro`
- **温度**：默认 0.4，控制输出随机性
- **最大输出 Tokens**：默认 4096，限制单次响应长度

#### 性能配置
- **并发页数**：同时处理的页面数量上限（默认 50），过大可能触发限流
- **渲染 DPI**：默认 180，用于渲染页面 PNG 输入给模型
- **RPM 上限**：每分钟请求数限制（默认 150）
- **TPM 预算**：每分钟 Token 预算（默认 2000000）
- **RPD 上限**：每天请求数限制（默认 10000）

#### 高级排版配置（PDF模式）
- **右侧留白比例**：右侧讲解区域占页面宽度比例（默认 0.48）
- **右栏字体大小**：讲解文本字号（pt，默认 20）
- **讲解文本行距**：行高倍数（默认 1.2）
- **栏内边距**：控制每栏左右内边距（默认 10）
- **CJK 字体**：选择用于显示中文的字体（默认 SimHei）
- **右栏渲染方式**：`text`、`markdown` 或 `pandoc`

#### HTML/Markdown 模式参数
- **截图 DPI**：截图质量（72-300，默认 150），较高 DPI 生成更清晰的图片但文件更大
- **分栏数量**：讲解内容的分栏数量（1-3，默认 2），类似 Word 分栏排版
- **栏间距**：分栏之间的间距（10-40px，默认 20）
- **显示栏间分隔线**：是否在分栏之间显示分隔线（默认 是）
- **文档标题**：生成的文档标题（默认 "PDF文档讲解"）
- **嵌入图片到 Markdown**：是否将截图 base64 编码嵌入 markdown 文件（仅 Markdown 模式）

#### 讲解风格配置
- **讲解风格/要求**：自定义讲解提示词，指导 LLM 如何生成讲解内容
- **启用前后各1页上下文**：启用后，LLM 将同时看到前一页、当前页和后一页的内容，提高讲解连贯性（会增加 API 调用成本）

### 2. 上传文件

在主区域上传 1~20 个 PDF 文件。

### 3. 批量处理

点击"批量生成讲解与合成"，应用将：
- 逐页渲染为 PNG（仅供模型识别，不写入结果文档）
- 调用 Gemini 生成中文讲解
- 根据选择的输出模式生成相应文档：
  - **PDF讲解版**：左侧保留原页矢量，右侧三栏布局写入讲解
  - **Markdown截图讲解**：生成包含页面截图和讲解的 Markdown 文档
  - **HTML截图版**：生成单个 HTML 文件，左侧显示 PDF 截图，右侧显示多栏 Markdown 渲染讲解
  - **HTML-pdf2htmlEX版**：使用 pdf2htmlEX 转换 PDF 为高质量 HTML，结合讲解内容

### 4. 下载结果

- **分别下载**：为每个文件提供单独的文档与 JSON 下载按钮
- **打包下载**：一次性下载 ZIP 文件（内含讲解版文档与同名 JSON）

### 5. 导入讲解 JSON 与仅重新合成

在"批量根据JSON重新生成PDF/Markdown（单框上传）"区域：
- 上传 PDF 与 JSON 文件（可混合拖拽）
- 系统会自动智能配对 PDF 和 JSON 文件
- 点击"根据JSON重新生成[文档类型]"，可在不调用 LLM 的情况下直接生成讲解版文档

## 目录结构

```
app/
  services/
    gemini_client.py              # LLM 封装与限流
    pdf_processor.py              # PDF 渲染/合成/讲解生成（主入口）
    pdf_composer.py               # PDF 合成核心逻辑
    pdf_validator.py              # PDF 文件验证
    text_layout.py                # 文本布局算法
    markdown_generator.py         # Markdown 文档生成
    html_screenshot_generator.py  # HTML 截图版生成
    html_pdf2htmlex_generator.py # HTML-pdf2htmlEX版生成
    batch_processor.py            # 批量处理逻辑
    font_helper.py                # 字体检测与辅助
    validators.py                 # 参数验证
  ui/
    components/                   # UI 组件
    handlers/                     # 文件处理逻辑
    performance/                  # 性能优化模块
  cache_processor.py             # 缓存处理
  config.py                       # 配置管理
  streamlit_app.py                # Streamlit 主应用
  ui_helpers.py                   # UI 辅助函数
assets/
  fonts/
    SIMHEI.TTF                    # 默认中文字体
requirements.txt                  # Python 依赖
README.md                         # 本文件
HTML-pdf2htmlEX版使用说明.md      # pdf2htmlEX 详细使用说明
```

## 关键实现说明

### PDF 讲解版
- `pdf_composer.compose_pdf(...)`：
  - 新页宽度 = 原宽度 × 3
  - 左侧通过 `show_pdf_page` 嵌入原始矢量内容
  - 右侧按三栏矩形区域写入讲解
  - `render_mode=markdown` 时使用 `insert_htmlbox` 渲染（宽容渲染，支持表格/代码）
  - `render_mode=pandoc` 时使用 Pandoc 进行高质量 PDF 渲染（需安装 Pandoc）
  - 文本溢出会自动创建"续页"

### Markdown 截图讲解
- `markdown_generator.generate_markdown_with_screenshots(...)`：
  - 逐页生成 PDF 截图
  - 将截图嵌入或链接到 Markdown 文档
  - 支持自定义标题和图片嵌入方式

### HTML 截图版
- `html_screenshot_generator.HTMLScreenshotGenerator`：
  - 生成包含页面截图的 HTML 文档
  - 左侧显示 PDF 截图，右侧显示多栏 Markdown 渲染讲解
  - 支持自定义分栏数量、栏间距、字体等

### HTML-pdf2htmlEX版
- `html_pdf2htmlex_generator.HTMLPdf2htmlEXGenerator`：
  - 使用 pdf2htmlEX 将 PDF 转换为高质量 HTML
  - 保持原生文本和矢量内容，文字可选择和搜索
  - 结合 AI 生成的讲解内容，提供卓越阅读体验

### Gemini 客户端
- `gemini_client.GeminiClient`：
  - 使用 `langchain-google-genai` 调用 Gemini
  - 内置 RPM/TPM/RPD 多维度限流
  - 失败自动重试（指数回退）

### 缓存机制
- 基于文件内容和参数的哈希值进行缓存
- 避免重复处理相同文件，提高处理效率
- 支持缓存清理和手动刷新

## 字体与中文显示

- 默认使用系统字体 SimHei（黑体）
- 支持从 Windows 系统字体自动检测和选择
- 如需使用自定义字体，可在侧边栏指定字体路径
- 确保字体文件存在且字体许可允许嵌入

## 常见问题

### 安装与运行
- **运行时报缺少包/版本冲突**：
  - 建议使用独立虚拟环境，执行 `pip install -r requirements.txt`
  - 如仍有问题，尝试升级 pip：`pip install --upgrade pip`

- **`streamlit` 无法启动或端口被占用**：
  - 尝试 `streamlit run app/streamlit_app.py --server.port 8502`

### API 相关问题
- **出现 429 或速率限制**：
  - 下调"并发页数"
  - 提高 `RPM/TPM/RPD` 预算（确保与账号配额一致）
  - 检查 API Key 是否有效

- **API 调用失败**：
  - 检查 `GEMINI_API_KEY` 是否正确设置
  - 确认网络连接正常
  - 查看日志文件 `logs/app.log` 获取详细错误信息

### 渲染与显示
- **讲解区乱码或中文不成字**：
  - 指定可用的 CJK 字体文件路径
  - 确认导入字体许可及文件存在
  - 尝试使用系统字体（如 Microsoft YaHei、SimSun）

- **Markdown 数学公式渲染**：
  - 内置对 `$...$`/`$$...$$` 进行简单保护并转义为代码块，防止解析异常
  - 如需严格公式渲染，可改造为更完善的 Math 渲染流程

### HTML-pdf2htmlEX 模式
- **pdf2htmlEX 未找到**：
  - 确保已正确安装 pdf2htmlEX
  - Windows 用户推荐使用 WSL 安装
  - 检查系统 PATH 环境变量是否包含 pdf2htmlEX

- **pdf2htmlEX 转换失败**：
  - 检查 PDF 文件是否损坏
  - 尝试使用较低 DPI 设置
  - 查看详细错误日志

### 性能优化
- **处理速度慢**：
  - 适当提高"并发页数"（但注意 API 限流）
  - 使用缓存避免重复处理
  - 对于大文件，考虑分批处理

- **内存占用过高**：
  - 降低并发页数
  - 关闭不必要的输出模式
  - 定期清理缓存文件

## 运行示例（PowerShell）

```powershell
# 进入项目目录
cd C:\Users\Kong\project\lecturer

# 激活虚拟环境
.\.venv\Scripts\Activate.ps1

# 设置 API Key
$env:GEMINI_API_KEY = "你的_GEMINI_API_KEY"

# 启动应用
streamlit run app/streamlit_app.py
```

## 辅助脚本

项目包含若干用于观察渲染与排版效果的脚本与 PDF 示例（如 `test_*.py`、`test_*.pdf`）。你可以逐一运行以验证字体、行距、三栏布局等行为。

## 安全与隐私

- 本地应用，上传的 PDF 仅在本机处理
- 讲解文本由 Gemini 生成，请遵循你的 API 使用条款与合规要求
- 建议不要在生产环境中暴露 API Key
- 处理敏感文档时，确保网络连接安全

## 许可证

本项目代码仅供学习与研究用途。字体文件请遵循其各自的许可证与使用条款。

## 更新日志

### 主要功能
- ✅ 支持四种输出模式：PDF讲解版、Markdown截图讲解、HTML截图版、HTML-pdf2htmlEX版
- ✅ 智能缓存机制，避免重复处理
- ✅ 批量 JSON 导入与重新合成
- ✅ 上下文增强功能
- ✅ 系统字体自动检测
- ✅ 完善的错误处理和重试机制

### 技术改进
- ✅ 模块化代码结构，易于维护和扩展
- ✅ 异步处理支持，提高并发性能
- ✅ 完善的参数验证和错误提示
- ✅ 详细的日志记录
