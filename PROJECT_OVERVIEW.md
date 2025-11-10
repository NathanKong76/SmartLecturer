# 智讲 / PDF-Lecture-AI - 全面技术文档

## 项目概述

智讲（PDF-Lecture-AI）是一个基于Streamlit的PDF文档智能讲解生成系统，支持批量处理多种输出格式，集成Gemini和OpenAI等大语言模型，为PDF文档提供智能化的中文讲解功能。

## 核心功能特性

### 🔥 主要功能
- **批量PDF处理**：支持同时处理最多20个PDF文件
- **多模型支持**：内置Gemini 2.5 Pro，兼容OpenAI GPT-4o系列
- **四种输出模式**：
  - PDF讲解版：三栏排版，保持矢量内容
  - Markdown截图讲解：包含页面截图的Markdown文档
  - HTML截图版：响应式HTML布局
  - HTML-pdf2htmlEX版：高质量HTML转换（推荐）
- **智能缓存机制**：避免重复处理，提高效率
- **并发控制**：支持高并发处理，优化性能
- **上下文增强**：可选启用前后页面上下文

### ⚡ 技术特性
- **异步处理**：使用asyncio实现高并发页面处理
- **多层次并发控制**：
  - 页面级并发：异步信号量控制
  - 文件级并发：线程池处理
  - 全局并发：统一资源管理
- **智能限流**：RPM/TPM/RPD多维度API限制
- **错误处理**：完善的异常处理和重试机制
- **跨平台支持**：Windows/Linux/macOS全平台兼容

## 项目架构

### 核心模块
```
app/
├── services/              # 核心服务模块
│   ├── gemini_client.py           # LLM客户端
│   ├── pdf_processor.py           # PDF处理主入口
│   ├── pdf_composer.py            # PDF合成核心
│   ├── html_pdf2htmlex_generator.py # HTML-pdf2htmlEX生成
│   ├── html_screenshot_generator.py # HTML截图生成
│   ├── markdown_generator.py      # Markdown生成器
│   ├── batch_processor.py         # 批量处理
│   ├── cache_processor.py         # 缓存处理
│   └── concurrency_controller.py  # 并发控制器
├── ui/                   # 用户界面模块
│   ├── components/       # UI组件
│   ├── handlers/         # 文件处理
│   └── performance/      # 性能优化
├── streamlit_app.py      # 主应用入口
├── config.py             # 配置管理
└── cache_processor.py    # 缓存处理
```

### 技术栈
- **后端框架**：Streamlit
- **LLM集成**：Google Gemini、OpenAI API
- **PDF处理**：PyMuPDF (fitz)
- **HTML生成**：BeautifulSoup、markdown
- **并发处理**：asyncio、ThreadPoolExecutor
- **容器化**：Docker + Docker Compose

## 快速开始

### 环境要求
- Python 3.10+
- API密钥（Gemini或OpenAI）
- （可选）pdf2htmlEX（用于HTML-pdf2htmlEX模式）

### 1. 克隆项目
```bash
git clone <项目地址>
cd PDF-Lecture-AI
```

### 2. 安装依赖
```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量
创建`.env`文件：
```bash
# LLM提供商选择
LLM_PROVIDER=gemini
GEMINI_API_KEY=你的_GEMINI_API_KEY
# 或者使用OpenAI
# LLM_PROVIDER=openai
# OPENAI_API_KEY=你的_OPENAI_API_KEY
```

### 4. 启动应用
```bash
# 从源代码启动
streamlit run app/streamlit_app.py

# 或使用Docker启动
docker-compose up -d
```

访问 http://localhost:8501 开始使用。

## 详细文档

### 📖 用户指南
- **主要功能**：[README.md](README.md)
- **HTML-pdf2htmlEX版**：[HTML-pdf2htmlEX版使用说明.md](HTML-pdf2htmlEX版使用说明.md)
- **环境配置**：[ENV_SETUP.md](ENV_SETUP.md)

### 🐳 部署指南
- **Docker部署**：[Docker-Deployment-Guide.md](Docker-Deployment-Guide.md)
- **生产环境**：推荐使用Docker部署方案

### 🔧 技术文档
- **并发实现**：[CONCURRENCY_IMPLEMENTATION_DETAILS.md](CONCURRENCY_IMPLEMENTATION_DETAILS.md)
- **测试报告**：[COMPREHENSIVE_TEST_SUMMARY.md](COMPREHENSIVE_TEST_SUMMARY.md)

### 📚 培训材料（开发用）
- **面试准备**：[PDF讲解项目面试准备指南.md](PDF讲解项目面试准备指南.md)
- **技术详解**：[并发控制与限流机制面试详解.md](并发控制与限流机制面试详解.md)
- **实战练习**：[技术问题实战练习指南.md](技术问题实战练习指南.md)

## 性能与优化

### 并发控制
- **页面级并发**：默认50个页面同时处理
- **文件级并发**：最多20个文件并行处理
- **全局并发**：默认限制200个总并发
- **API限流**：RPM/TPM/RPD智能控制

### 性能参数
- **小文档**（<20页）：页面并发50，文件并发5
- **中等文档**（20-100页）：页面并发30，文件并发3
- **大型文档**（>100页）：页面并发20，文件并发2

### 缓存机制
- **文件哈希**：基于内容哈希避免重复处理
- **参数敏感**：参数变化时自动重新处理
- **存储位置**：`temp/`目录

## 常见问题

### 安装问题
**Q: 运行时缺少包或版本冲突**
A: 建议使用独立虚拟环境，执行`pip install -r requirements.txt`

**Q: Streamlit无法启动**
A: 尝试使用其他端口：`streamlit run app/streamlit_app.py --server.port 8502`

### API问题
**Q: 出现429或速率限制**
A: 降低并发页数，提高RPM/TPM预算，检查API密钥

**Q: API调用失败**
A: 检查网络连接，验证API密钥，查看日志文件

### 处理问题
**Q: 讲解区乱码或中文不成字**
A: 指定可用的CJK字体文件路径，确认字体许可

**Q: HTML-pdf2htmlEX模式pdf2htmlEX未找到**
A: 确保已正确安装pdf2htmlEX，Windows用户推荐使用WSL安装

## 贡献指南

### 开发环境
1. Fork项目到你的GitHub账户
2. 克隆到本地环境
3. 创建开发分支：`git checkout -b feature/your-feature`
4. 安装开发依赖：`pip install -r requirements.txt`
5. 运行测试：`pytest tests/ -v`

### 代码规范
- 遵循PEP 8代码风格
- 添加类型注解
- 编写单元测试
- 更新相关文档

### 提交规范
- 使用清晰的提交信息
- 关联相关Issue
- 保持提交原子性

## 许可证

本项目代码仅供学习与研究用途。字体文件请遵循其各自的许可证与使用条款。

## 技术支持

- **问题报告**：请提供错误信息截图、PDF文件类型描述、参数配置
- **功能建议**：欢迎提交Issue或Pull Request
- **文档改进**：欢迎改进文档内容

---

**最后更新**: 2025-11-09  
**版本**: v2.0  
**维护状态**: 积极维护中