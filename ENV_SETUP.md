# 环境变量配置说明

本文档说明如何通过环境变量配置 OpenAI API 相关参数。

## OpenAI 环境变量

### 必需的环境变量

#### 1. LLM_PROVIDER
设置 LLM 提供商为 OpenAI：
```bash
# Windows PowerShell
$env:LLM_PROVIDER = "openai"

# Linux/macOS
export LLM_PROVIDER="openai"
```

#### 2. OPENAI_API_KEY
设置 OpenAI API 密钥：
```bash
# Windows PowerShell
$env:OPENAI_API_KEY = "sk-your-api-key-here"

# Linux/macOS
export OPENAI_API_KEY="sk-your-api-key-here"
```

### 可选的环境变量

#### 3. OPENAI_API_BASE
设置 OpenAI API 基础 URL（用于自定义兼容接口）：
```bash
# Windows PowerShell
# 使用官方 OpenAI API
$env:OPENAI_API_BASE = "https://api.openai.com/v1"

# 使用自定义兼容接口（如 Azure OpenAI、本地服务等）
$env:OPENAI_API_BASE = "https://your-custom-domain.com/v1"

# Linux/macOS
export OPENAI_API_BASE="https://api.openai.com/v1"
```

**默认值**：如果不设置，将使用 `https://api.openai.com/v1`

#### 4. OPENAI_MODEL_NAME
设置 OpenAI 模型名称：
```bash
# Windows PowerShell
$env:OPENAI_MODEL_NAME = "gpt-4o-mini"

# Linux/macOS
export OPENAI_MODEL_NAME="gpt-4o-mini"
```

**支持的模型示例**：
- `gpt-4o-mini`（默认，推荐）
- `gpt-4o`
- `gpt-4-turbo`
- `gpt-3.5-turbo`
- 其他 OpenAI 兼容接口支持的模型

**默认值**：如果不设置，将使用 `gpt-4o-mini`

## 使用 .env 文件配置（推荐）

在项目根目录创建 `.env` 文件（使用 UTF-8 无 BOM 编码），内容如下：

```env
# LLM Provider
LLM_PROVIDER=openai

# OpenAI API Configuration
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_API_BASE=https://api.openai.com/v1
OPENAI_MODEL_NAME=gpt-4o-mini
```

应用会自动从 `.env` 文件加载这些环境变量（通过 `python-dotenv` 库）。

## 环境变量优先级

应用按以下优先级读取配置：

1. **UI 输入**：在 Streamlit 界面中手动输入的值（最高优先级）
2. **环境变量**：系统环境变量或 `.env` 文件中的值
3. **默认值**：代码中定义的默认值（最低优先级）

## 通用环境变量（向后兼容）

为了向后兼容，应用也支持以下通用环境变量：

- `API_KEY`：如果未设置 `OPENAI_API_KEY`，会尝试读取此值
- `LLM_API_BASE`：如果未设置 `OPENAI_API_BASE`，会尝试读取此值
- `MODEL_NAME`：如果未设置 `OPENAI_MODEL_NAME`，会尝试读取此值

## 配置示例

### 示例 1：使用官方 OpenAI API

```bash
# Windows PowerShell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "sk-proj-xxxxxxxxxxxxx"
$env:OPENAI_MODEL_NAME = "gpt-4o-mini"
# OPENAI_API_BASE 使用默认值 https://api.openai.com/v1

# Linux/macOS
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxx"
export OPENAI_MODEL_NAME="gpt-4o-mini"
```

### 示例 2：使用自定义兼容接口（如 Azure OpenAI）

```bash
# Windows PowerShell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "your-azure-api-key"
$env:OPENAI_API_BASE = "https://your-resource.openai.azure.com/v1"
$env:OPENAI_MODEL_NAME = "gpt-4o"

# Linux/macOS
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your-azure-api-key"
export OPENAI_API_BASE="https://your-resource.openai.azure.com/v1"
export OPENAI_MODEL_NAME="gpt-4o"
```

### 示例 3：使用本地部署的兼容接口

```bash
# Windows PowerShell
$env:LLM_PROVIDER = "openai"
$env:OPENAI_API_KEY = "not-needed-for-local"
$env:OPENAI_API_BASE = "http://localhost:8000/v1"
$env:OPENAI_MODEL_NAME = "local-model"

# Linux/macOS
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="not-needed-for-local"
export OPENAI_API_BASE="http://localhost:8000/v1"
export OPENAI_MODEL_NAME="local-model"
```

## 验证配置

启动应用后，在 Streamlit 界面的侧边栏中：

1. 选择 **LLM 提供方** 为 **OpenAI**
2. 检查 **API Base URL** 字段是否显示正确的值
3. 检查 **模型名称** 字段是否显示正确的值
4. 如果环境变量已正确设置，这些字段会自动填充

## 注意事项

1. **API Key 安全**：不要将包含真实 API Key 的 `.env` 文件提交到版本控制系统
2. **编码格式**：`.env` 文件必须使用 **UTF-8 无 BOM 编码**，否则可能出现中文乱码
3. **环境变量格式**：在 `.env` 文件中，不需要使用引号包裹值（除非值中包含空格）
4. **重启应用**：修改环境变量后，需要重启 Streamlit 应用才能生效

## 相关代码位置

环境变量的读取逻辑位于：
- `app/config.py`：`AppConfig.from_env()` 方法
- `app/streamlit_app.py`：侧边栏 UI 中的默认值读取


