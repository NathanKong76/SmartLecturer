# PDF 讲解流 - 发行版本说明

## 版本信息

本发行版本包含完整的 PDF 讲解流应用程序，支持批量处理 PDF 文件并生成中文讲解文档。

## 系统要求

- **Python**: 3.10 或更高版本
- **操作系统**: Windows（PowerShell）或 Linux/macOS
- **API Key**: 至少配置一种 LLM 凭据
  - Google Gemini（`GEMINI_API_KEY`）
  - 或 OpenAI 兼容接口（`OPENAI_API_KEY`，可选 `OPENAI_API_BASE`）

## 快速开始

### Windows 用户

1. **解压发行包**
   ```powershell
   # 解压 lecturer-v{version}.zip 到任意目录
   ```

2. **运行安装脚本**（以管理员身份运行 PowerShell）
   ```powershell
   cd lecturer-v{version}
   .\scripts\install.ps1
   ```

3. **设置 LLM 配置**
   ```powershell
   # 方式一：创建 .env 文件
   # 复制 .env.example 为 .env，然后编辑添加你的 API Key
   
   # 方式二：设置环境变量
   $env:LLM_PROVIDER = "gemini"            # gemini / openai
   $env:GEMINI_API_KEY = "你的_GEMINI_API_KEY"
   $env:OPENAI_API_KEY = "你的_OPENAI_API_KEY"   # 使用 OpenAI 时设置
   $env:OPENAI_API_BASE = "https://你的自定义域名/v1"  # 自定义兼容接口
   ```

4. **启动应用**
   ```powershell
   .\scripts\start.ps1
   ```

### Linux/macOS 用户

1. **解压发行包**
   ```bash
   unzip lecturer-v{version}.zip
   cd lecturer-v{version}
   ```

2. **运行安装脚本**
   ```bash
   chmod +x scripts/*.sh
   ./scripts/install.sh
   ```

3. **设置 LLM 配置**
   ```bash
   # 方式一：创建 .env 文件
   cp .env.example .env
   # 编辑 .env 文件，添加你的 API Key
   
   # 方式二：设置环境变量
   export LLM_PROVIDER="gemini"
   export GEMINI_API_KEY="你的_GEMINI_API_KEY"
   export OPENAI_API_KEY="你的_OPENAI_API_KEY"
   export OPENAI_API_BASE="https://你的自定义域名/v1"
   ```

4. **启动应用**
   ```bash
   ./scripts/start.sh
   ```

## 可选：安装 pdf2htmlEX（用于 HTML-pdf2htmlEX 模式）

### Windows 用户（推荐使用 WSL）

运行自动安装脚本（需要管理员权限）：

```powershell
# 以管理员身份运行 PowerShell
.\scripts\install-pdf2htmlex-wsl.ps1
```

此脚本将：
- 自动检测并安装 WSL（如果未安装）
- 自动检测 Ubuntu 版本
- 自动下载并安装对应的 pdf2htmlEX 包
- 验证安装结果

**注意**：如果 WSL 未安装，脚本会自动安装 WSL，但可能需要重启系统。重启后请再次运行安装脚本。

### macOS 用户

运行自动安装脚本：

```bash
chmod +x scripts/install-pdf2htmlex-macos.sh
./scripts/install-pdf2htmlex-macos.sh
```

此脚本将：
- 自动检测并安装 Homebrew（如果未安装）
- 使用 Homebrew 安装 pdf2htmlEX
- 验证安装结果

### Linux 用户

运行自动安装脚本：

```bash
chmod +x scripts/install-pdf2htmlex-linux.sh
./scripts/install-pdf2htmlex-linux.sh
```

此脚本将：
- 自动检测 Linux 发行版（Ubuntu/Debian/Fedora/CentOS/Arch 等）
- 使用对应的包管理器安装 pdf2htmlEX
- 如果软件仓库中没有，会自动从 GitHub Releases 下载对应版本
- 验证安装结果

**注意**：Linux 安装脚本需要 sudo 权限。

详细安装说明请参考 `HTML-pdf2htmlEX版使用说明.md`。

## PyInstaller 打包版本

如果您使用的是 PyInstaller 打包的独立可执行文件版本：

### Windows 版本
- 解压 `lecturer-windows-v{version}.zip`
- 双击 `start.bat` 或运行 `lecturer.exe`
- 无需安装 Python 或依赖

### Linux 版本
- 解压 `lecturer-linux-v{version}.tar.gz`
- 运行 `chmod +x lecturer` 和 `./lecturer`
- 或使用 `./start.sh`
- 无需安装 Python 或依赖

### macOS 版本
- 解压 `lecturer-macos-v{version}.zip`
- 运行 `./start.sh` 或直接运行 `lecturer.app`
- 无需安装 Python 或依赖

**注意**：打包版本仍然需要设置 `GEMINI_API_KEY` 环境变量或创建 `.env` 文件。

## 使用说明

1. **启动应用**后，浏览器会自动打开应用界面（默认地址：http://localhost:8501）

2. **配置参数**：
   - 在左侧边栏选择 LLM 提供方，设置对应的 API Key（如 `GEMINI_API_KEY` 或 `OPENAI_API_KEY`）
   - 选择输出模式（PDF讲解版、Markdown截图讲解、HTML截图版、HTML-pdf2htmlEX版）
   - 调整其他参数（温度、并发数等）

3. **上传 PDF 文件**：
   - 点击上传区域，选择 1-20 个 PDF 文件

4. **生成讲解**：
   - 点击"批量生成讲解与合成"按钮
   - 等待处理完成（进度会实时显示）

5. **下载结果**：
   - 选择"分别下载"或"打包下载"
   - 下载生成的讲解文档和 JSON 文件

## 功能特性

- **批量处理**：一次处理最多 20 个 PDF 文件
- **四种输出模式**：
  - PDF讲解版：在 PDF 右侧添加讲解文字，保持矢量内容
  - Markdown截图讲解：生成包含页面截图和讲解的 Markdown 文档
  - HTML截图版：生成单个 HTML 文件，左侧显示 PDF 截图，右侧显示讲解
  - HTML-pdf2htmlEX版：使用 pdf2htmlEX 转换的高质量 HTML（需安装 pdf2htmlEX）
- **智能缓存**：避免重复处理相同文件
- **JSON 导入导出**：支持导出讲解 JSON，后续可仅重新合成文档

## 常见问题

### 安装问题

**Q: 安装脚本提示找不到 Python**
A: 请先安装 Python 3.10 或更高版本：https://www.python.org/downloads/

**Q: 安装依赖时出错**
A: 确保网络连接正常，或尝试使用国内镜像：
```powershell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 运行问题

**Q: 启动时提示缺少 API Key**
A: 请根据所选 LLM 提供方设置对应的环境变量（Gemini 使用 `GEMINI_API_KEY`，OpenAI 使用 `OPENAI_API_KEY`），参考"快速开始"部分

**Q: 应用启动失败**
A: 确保虚拟环境已正确创建，尝试重新运行安装脚本

### pdf2htmlEX 相关问题

**Q: HTML-pdf2htmlEX 模式提示找不到 pdf2htmlEX**
A: 请运行 `.\scripts\install-pdf2htmlex-wsl.ps1` 安装（Windows）或参考 `HTML-pdf2htmlEX版使用说明.md`

**Q: WSL 安装后需要重启**
A: 这是正常的，WSL 安装需要重启系统。重启后再次运行安装脚本即可。

## 技术支持

- 查看详细文档：`README.md`
- pdf2htmlEX 使用说明：`HTML-pdf2htmlEX版使用说明.md`
- 项目 GitHub 仓库：查看项目主页获取最新信息和问题反馈

## 更新日志

### v1.0.0
- 初始发行版本
- 支持四种输出模式
- 自动安装脚本
- 完整的文档和示例

