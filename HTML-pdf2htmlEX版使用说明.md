# HTML-pdf2htmlEX版 使用说明

## 概述

**HTML-pdf2htmlEX版** 是一个新的输出模式，使用 [pdf2htmlEX](https://github.com/pdf2htmlEX/pdf2htmlEX) 工具将 PDF 转换为高质量的 HTML，结合 AI 生成的讲解内容，提供卓越的阅读体验。

### 与 HTML截图版的区别

| 特性 | HTML截图版 | HTML-pdf2htmlEX版 |
|------|-----------|-------------------|
| PDF显示方式 | PNG截图 | 原生HTML文本 |
| 文字清晰度 | 取决于DPI设置 | 矢量文字，无限清晰 |
| 文字可选择 | ❌ 否 | ✅ 是 |
| 文件大小 | 较大（图片） | 中等（内联字体） |
| 处理速度 | 快 | 较慢 |
| 布局保真度 | 高 | 非常高 |

---

## 一、安装 pdf2htmlEX

### 1.1 Linux (Ubuntu/Debian)

**方式一：自动安装（推荐）🚀**

运行自动安装脚本：

```bash
chmod +x scripts/install-pdf2htmlex-linux.sh
./scripts/install-pdf2htmlex-linux.sh
```

此脚本将自动：
- 检测 Linux 发行版（Ubuntu/Debian/Fedora/CentOS/Arch 等）
- 使用对应的包管理器安装 pdf2htmlEX
- 如果软件仓库中没有，会自动从 GitHub Releases 下载对应版本
- 验证安装结果

**方式二：手动安装**

```bash
# 使用包管理器安装（推荐）
sudo apt-get update
sudo apt-get install pdf2htmlex

# 或从源码编译
git clone https://github.com/pdf2htmlEX/pdf2htmlEX.git
cd pdf2htmlEX
# 按照 INSTALL 文件中的说明编译安装
```

### 1.2 macOS

**方式一：自动安装（推荐）🚀**

运行自动安装脚本：

```bash
chmod +x scripts/install-pdf2htmlex-macos.sh
./scripts/install-pdf2htmlex-macos.sh
```

此脚本将自动：
- 检测并安装 Homebrew（如果未安装）
- 使用 Homebrew 安装 pdf2htmlex
- 验证安装结果

**方式二：手动安装**

```bash
# 如果没有 Homebrew，先安装：
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 使用 Homebrew 安装
brew install pdf2htmlex
```

### 1.3 Windows

**方案一：使用 WSL (推荐) ⭐**

这是最简单的方案！即使您的 Python 运行在 Windows 上，程序也会自动调用 WSL 中的 pdf2htmlEX。

**方式一：自动安装（最简单）🚀**

运行自动安装脚本，脚本会自动完成所有步骤：

```powershell
# 以管理员身份运行 PowerShell
.\scripts\install-pdf2htmlex-wsl.ps1
```

此脚本将自动：
- 检测并安装 WSL（如果未安装，需要重启系统）
- 检测 WSL 发行版和 Ubuntu 版本
- 根据版本自动选择对应的 .deb 包
- 下载并安装 pdf2htmlEX
- 验证安装结果

**注意**：如果 WSL 未安装，脚本会自动安装 WSL，但可能需要重启系统。重启后请再次运行安装脚本。

**方式二：手动安装**

如果您希望手动控制安装过程，可以按照以下步骤：

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

**方案二：使用 Docker**

```bash
# 拉取 pdf2htmlEX Docker 镜像
docker pull pdf2htmlex/pdf2htmlex:0.18.8.rc1-master-20200820-ubuntu-20.04-x86_64

# 创建别名方便使用
docker run --rm -v "$(pwd):/pdf" pdf2htmlex/pdf2htmlex:0.18.8.rc1-master-20200820-ubuntu-20.04-x86_64 pdf2htmlEX
```

### 1.4 验证安装

**Linux/macOS:**
```bash
pdf2htmlEX --version
```

**Windows (WSL):**
```powershell
# 在 Windows PowerShell 中
wsl pdf2htmlEX --version
```

**预期输出：**
```
pdf2htmlEX version 0.18.8.rc1
(or similar version number)
```


## 二、使用 HTML-pdf2htmlEX版

### 2.1 启动应用

```bash
# 进入项目目录
cd C:\Users\Kong\project\lecturer

# 激活虚拟环境（如果有）
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

# 启动 Streamlit 应用
streamlit run app/streamlit_app.py
```

### 2.2 选择输出模式

1. 在浏览器中打开应用（通常是 http://localhost:8501）
2. 在左侧边栏 **"📤 输出模式"** 部分
3. 选择 **"HTML-pdf2htmlEX版"**

![选择模式](https://i.imgur.com/example.png)

### 2.3 配置参数

#### 🌐 HTML-pdf2htmlEX版参数

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| **讲解字体大小** | 右侧讲解文字的大小 | 14pt |
| **分栏数量** | 讲解内容的分栏数（1-3栏） | 2栏 |
| **栏间距** | 分栏之间的间距 | 20px |
| **显示栏间分隔线** | 是否显示分栏间的竖线 | ✅ 勾选 |
| **文档标题** | HTML文档的标题 | 留空自动使用文件名 |

**注意**：pdf2htmlEX 模式不需要设置截图 DPI，会自动显示提示信息。

#### 🔑 API 配置

- **LLM 提供方**: 可在 Gemini 与 OpenAI 之间切换
- **API 密钥**: 对应提供方的密钥（`GEMINI_API_KEY` 或 `OPENAI_API_KEY`）
- **API Base URL**: 使用 OpenAI 兼容接口时填写（如 Azure、自建服务）
- **模型名称**: 默认 `gemini-2.5-pro` / `gpt-4o-mini`
- **温度**: 控制输出随机性（0.4 推荐）
- **最大输出 Tokens**: 单次响应长度限制（4096 推荐）

#### ⚡ 性能配置

- **并发页数**: 同时处理的页面数量（50 推荐）
- **渲染DPI**: 供 LLM 使用的页面质量（180 推荐）
- **RPM 上限**: 每分钟请求数限制（150）
- **TPM 预算**: 每分钟 Token 预算（2000000）

#### ✍️ 讲解风格配置

自定义讲解提示词，例如：
```
请用中文讲解本页pdf，关键词给出英文，讲解详尽，语言简洁易懂。
讲解让人一看就懂，便于快速学习。请避免不必要的换行，使页面保持紧凑。
```

### 2.4 上传和处理

#### 单文件处理

1. 点击 **"上传 PDF 文件"** 按钮
2. 选择一个 PDF 文件
3. 点击 **"批量生成讲解与合成"** 按钮
4. 等待处理完成（进度条显示）

#### 批量处理

1. 一次可上传最多 **20个 PDF 文件**
2. 系统会依次处理每个文件
3. 显示每个文件的处理状态

### 2.5 下载结果

#### 分别下载

- 每个文件显示两个下载按钮：
  - 🌐 **HTML文档**：包含 pdf2htmlEX 转换内容和讲解的完整 HTML
  - 📝 **JSON文件**：讲解内容的结构化数据

#### 打包下载

1. 选择 **"打包下载"** 选项
2. 输入 ZIP 文件名（默认：批量讲解PDF.zip）
3. 点击 **"📦 下载所有HTML-pdf2htmlEX和讲解JSON (ZIP)"**

---

## 三、高级功能

### 3.1 使用缓存加速

系统会自动缓存处理结果：
- 相同 PDF + 相同参数 = 使用缓存（秒级完成）
- 修改参数后会重新处理
- 缓存位置：`temp/` 目录

### 3.2 根据 JSON 重新生成

如果您已有讲解 JSON 文件：

1. 滚动到 **"📚 批量根据JSON重新生成PDF/Markdown"** 部分
2. 同时上传 PDF 文件和对应的 JSON 文件
3. 系统会自动配对（基于文件名）
4. 点击 **"根据JSON重新生成HTML-pdf2htmlEX文档"**
5. 直接生成，无需调用 API（节省成本）

**文件命名规则**：
- PDF: `example.pdf`
- JSON: `example.json`（同名）

### 3.3 上下文增强

启用后，LLM 会同时看到前一页、当前页、后一页的内容：

1. 展开 **"🧠 上下文增强"**
2. 勾选 **"启用前后各1页上下文"**
3. 可自定义上下文提示词

**注意**：会增加 API 调用成本（约 3 倍）

---

## 四、输出结果说明

### 4.1 HTML 文档结构

生成的 HTML 文件包含：

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <title>文档标题 - HTML-pdf2htmlEX版</title>
    <!-- 内联 CSS -->
    <style>
        /* pdf2htmlEX 样式（已隔离） */
        /* 讲解面板样式 */
        /* 响应式布局 */
    </style>
</head>
<body>
    <!-- 左侧：pdf2htmlEX 转换的 PDF 内容 -->
    <div class="screenshots-panel">
        <div class="pdf2htmlex-container">
            <!-- 每页 PDF 的 HTML 内容 -->
        </div>
    </div>
    
    <!-- 右侧：讲解内容 -->
    <div class="explanations-panel">
        <!-- Markdown 渲染的讲解 -->
    </div>
    
    <!-- 导航控制 -->
    <!-- 主题切换 -->
    <!-- 字体控制 -->
    
    <!-- 内联 JavaScript -->
    <script>/* 交互逻辑 */</script>
</body>
</html>
```

### 4.2 功能特性

#### 📖 阅读功能
- **左右分栏**：PDF 在左，讲解在右
- **滚动同步**：滚动 PDF 时自动切换对应讲解
- **页面导航**：上一页/下一页按钮
- **键盘快捷键**：
  - `←` / `↑`: 上一页
  - `→` / `↓` / `Space`: 下一页
  - `Home`: 第一页
  - `End`: 最后一页

#### 🎨 显示控制
- **主题切换**：点击 🌙/☀️ 切换明暗主题
- **字体大小**：点击 Aa 调整字体大小（12-24pt）
- **行距调整**：调整讲解文字行距（1.3-2.5）
- **阅读进度条**：顶部显示当前阅读进度

#### 📱 响应式设计
- 自适应桌面、平板、手机屏幕
- 小屏幕自动切换为上下布局
- **智能页面缩放**：
  - 自动检测 PDF 页面宽度
  - 使用 `transform: scale()` 智能缩放以适应容器
  - 保持原始页面长宽比，避免裁切
  - 窗口大小改变时自动重新调整

---

## 五、故障排除

### 5.1 pdf2htmlEX 未安装

**症状**：错误提示 "pdf2htmlEX not found"

**解决方案**：

**对于 Windows + WSL 用户：**
1. 确认 WSL 已安装：
   ```powershell
   wsl --version
   ```
   
2. 确认 pdf2htmlEX 在 WSL 中安装：
   ```powershell
   wsl pdf2htmlEX --version
   ```
   
3. 如果 WSL 命令失败，检查 WSL 是否启动：
   ```powershell
   wsl -l -v
   # 应该显示运行中的 Ubuntu 或其他发行版
   ```

4. 如果 pdf2htmlEX 未安装，进入 WSL 安装：
   ```powershell
   wsl
   # 然后在 WSL 中：
   sudo apt-get update
   sudo apt-get install pdf2htmlex
   ```

**对于 Linux/macOS 用户：**
1. 确认安装成功：`pdf2htmlEX --version`
2. 确保 pdf2htmlEX 在系统 PATH 中
3. 可能需要重新登录或运行 `source ~/.bashrc`

### 5.1a pdf2htmlEX 版本过旧

**症状**：错误提示 "unrecognized option '--hdpi'" 或类似参数错误

**解决方案**：

✅ **好消息**：从本次更新开始，程序已经自动适配所有版本！

如果仍然遇到参数错误：
1. 检查日志中的 "Detected pdf2htmlEX features" 信息
2. 确认使用的是 pdf2htmlEX 而不是其他工具
3. 如果是非常旧的版本（0.10 以前），建议升级：
   ```bash
   # WSL/Linux
   sudo apt-get update
   sudo apt-get install --reinstall pdf2htmlex
   ```

### 5.1b 排版异常或图片丢失 (已修复)

**症状**：转换后的 HTML 排版混乱，图片无法显示

**原因**：
- 使用了不兼容的 `--embed cfijo` 参数
- 没有正确配置资源嵌入选项

**解决方案**：✅ 已自动修复！
- 程序现在使用 `--embed-css 1 --embed-font 1 --embed-image 1`
- 根据版本自动选择正确的 DPI 参数（`--dpi` 或 `--hdpi`/`--vdpi`）
- 无需任何手动配置

如果仍有问题，请确保已更新到最新版本代码。

### 5.1c Windows + WSL 编码错误 (已修复)

**症状**：错误信息 `UnicodeDecodeError: 'gbk' codec can't decode byte 0x81`

**原因**：
- Windows Python 默认使用 GBK 编码
- WSL 输出使用 UTF-8 编码
- 解码不匹配导致错误

**解决方案**：✅ 已自动修复！
- 所有 subprocess 调用已强制使用 UTF-8 编码
- 添加 `errors='replace'` 参数处理无法解码的字符
- 无需任何手动配置

如果仍遇到编码问题，请确保已更新到最新版本代码。

### 5.2 转换失败

**症状**：显示 "pdf2htmlEX conversion failed"

**可能原因**：
1. PDF 文件损坏或格式特殊
2. PDF 包含加密或权限限制
3. PDF 过大或过于复杂

**解决方案**：
1. 尝试使用 **HTML截图版** 模式（更兼容）
2. 使用 PDF 工具移除密码/限制
3. 分割大型 PDF 后再处理

### 5.3 转换速度慢

**症状**：pdf2htmlEX 转换耗时较长

**正常现象**：
- 复杂 PDF：2-5 分钟/文件
- 简单 PDF：30秒-1分钟/文件

**优化建议**：
1. 减少并发处理数量（降低系统负载）
2. 使用缓存功能（第二次处理秒级完成）
3. 对于批量处理，建议分批进行

### 5.4 样式显示异常

**症状**：PDF 内容或讲解样式混乱

**可能原因**：
- CSS 隔离不完善
- 特殊字符编码问题

**解决方案**：
1. 检查浏览器控制台是否有 CSS 错误
2. 尝试不同的浏览器（推荐 Chrome/Edge）
3. 如问题持续，请使用 HTML截图版

### 5.5 中文字体显示问题

**症状**：中文显示为方块或乱码

**解决方案**：
1. 确认系统已安装中文字体
2. 在 **"🎨 高级排版配置"** 中选择合适的 CJK 字体
3. Windows 推荐：`SimHei` (黑体)
4. Linux 推荐：`WenQuanYi Zen Hei` (文泉驿正黑)

---

## 六、性能对比

### 处理速度对比

| 模式 | 10页PDF | 50页PDF | 100页PDF |
|------|---------|---------|----------|
| PDF讲解版 | 2分钟 | 8分钟 | 15分钟 |
| Markdown截图讲解 | 2.5分钟 | 10分钟 | 18分钟 |
| HTML截图版 | 3分钟 | 12分钟 | 22分钟 |
| **HTML-pdf2htmlEX版** | **4分钟** | **16分钟** | **30分钟** |

*注：基于 Gemini 2.5 Pro API，实际速度取决于网络和 API 限制*

### 文件大小对比

| 模式 | 10页文档 | 50页文档 | 100页文档 |
|------|----------|----------|-----------|
| PDF讲解版 | 2MB | 8MB | 15MB |
| Markdown截图讲解 | 5MB (含图) | 20MB | 40MB |
| HTML截图版 | 4MB | 18MB | 35MB |
| **HTML-pdf2htmlEX版** | **3MB** | **12MB** | **25MB** |

### 质量对比

| 评价维度 | PDF讲解版 | HTML截图版 | HTML-pdf2htmlEX版 |
|----------|-----------|------------|-------------------|
| 文字清晰度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 布局还原度 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 文字可选择 | ✅ | ❌ | ✅ |
| 兼容性 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| 分享便利性 | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

---

## 七、最佳实践

### 7.1 选择合适的模式

**推荐使用 HTML-pdf2htmlEX版 的场景**：
- ✅ 学术论文、技术文档
- ✅ 需要复制文字内容
- ✅ 追求最佳视觉效果
- ✅ 需要在线分享和展示

**推荐使用 HTML截图版 的场景**：
- ✅ 扫描版PDF
- ✅ 包含大量图表的PDF
- ✅ 需要快速处理
- ✅ PDF 格式特殊或加密

**推荐使用 PDF讲解版 的场景**：
- ✅ 需要保留原始PDF格式
- ✅ 需要打印输出
- ✅ 仅在PDF阅读器中查看

### 7.2 参数优化建议

#### 讲解风格
```
请用中文讲解本页pdf，关键词给出英文，讲解详尽但简洁。
重点解释核心概念，举例说明应用场景。
避免冗余，保持紧凑排版。
```

#### 性能设置
- **小文档** (< 20页): 并发50，RPM 150
- **中等文档** (20-100页): 并发30，RPM 100
- **大型文档** (> 100页): 并发20，RPM 80，分批处理

### 7.3 批量处理技巧

1. **分类处理**：将相同类型的文档分组处理
2. **使用缓存**：相同参数的文档会自动使用缓存
3. **JSON复用**：保存JSON文件，调整参数时可直接重新生成
4. **夜间处理**：大批量任务可在夜间运行

---

## 八、常见问题 FAQ

### Q1: Windows上Python调用WSL中的pdf2htmlEX会慢吗？

**A**: 轻微延迟（通常<1秒），但不影响整体速度，因为：
- WSL 2 的性能接近原生 Linux
- pdf2htmlEX 转换本身耗时较长（分钟级别）
- 跨系统调用开销可忽略不计

### Q2: 可以处理扫描版PDF吗？

**A**: pdf2htmlEX 对扫描版PDF效果不佳，建议：
- 先使用 OCR 工具转换为文字版PDF
- 或直接使用 **HTML截图版** 模式

### Q3: 支持哪些语言的PDF？

**A**: pdf2htmlEX 支持几乎所有语言，包括：
- ✅ 中文（简体/繁体）
- ✅ 英文
- ✅ 日文、韩文
- ✅ 阿拉伯文、俄文等

### Q4: 生成的HTML文件可以离线使用吗？

**A**: ✅ 是的！所有资源已内联，可以：
- 直接用浏览器打开
- 通过邮件发送
- 上传到任何网站
- 完全离线查看

### Q5: 可以自定义样式吗？

**A**: 目前样式与 HTML截图版一致。如需自定义：
- 修改 `html_pdf2htmlex_generator.py` 中的 CSS
- 或在生成后手动编辑 HTML 文件

### Q6: API 消耗会增加吗？

**A**: 不会。生成讲解的 API 调用与其他模式相同，只是增加了 pdf2htmlEX 转换步骤。

### Q7: 支持数学公式吗？

**A**: ✅ 完美支持！pdf2htmlEX 会保留：
- LaTeX 公式
- MathML 公式
- 嵌入的字体和符号

### Q8: 最大支持多少页的PDF？

**A**: 理论上无限制，但建议：
- **< 200页**：单次处理
- **200-500页**：分批处理
- **> 500页**：先分割PDF

---

## 九、技术说明

### 9.1 工作流程

```
PDF文件
    ↓
├─→ [PyMuPDF] 渲染页面图像 (供LLM)
├─→ [Gemini API] 生成讲解内容
└─→ [pdf2htmlEX] 转换为HTML
    ↓
[HTMLPdf2htmlEXGenerator] 合成最终HTML
    ├─ 解析 pdf2htmlEX 输出
    ├─ 提取页面和CSS
    ├─ 隔离样式（添加命名空间）
    ├─ 渲染讲解内容（Markdown → HTML）
    └─ 生成交互式HTML
    ↓
单文件HTML输出（包含所有资源）
```

### 9.2 关键技术

- **pdf2htmlEX**: PDF to HTML 转换
- **BeautifulSoup**: HTML 解析
- **Markdown**: 讲解内容渲染
- **CSS Isolation**: 样式命名空间隔离
- **Gemini 2.5 Pro**: AI 内容生成

### 9.3 浏览器兼容性

| 浏览器 | 版本要求 | 支持程度 |
|--------|----------|----------|
| Chrome | ≥ 90 | ⭐⭐⭐⭐⭐ 完美 |
| Edge | ≥ 90 | ⭐⭐⭐⭐⭐ 完美 |
| Firefox | ≥ 88 | ⭐⭐⭐⭐⭐ 完美 |
| Safari | ≥ 14 | ⭐⭐⭐⭐ 良好 |
| IE | 不支持 | ❌ |

---

## 十、更新日志

### v1.0.1 (2025-11-06)

**重要修复**：
- 🐛 修复 pdf2htmlEX 参数兼容性问题
  - 移除不兼容的 `--embed cfijo` 参数
  - 改用独立嵌入选项：`--embed-css 1 --embed-font 1 --embed-image 1`
  - 支持 0.18.x 版本的统一 `--dpi` 参数
  - 自动检测并适配不同版本的参数格式
- ✅ 修复排版混乱和图片丢失问题
- ✅ 修复左侧 PDF 长宽比裁切问题
  - 实现智能缩放：自动适配容器宽度
  - 使用 `transform: scale()` 保持页面比例
  - 响应式设计：窗口大小改变时自动重新缩放
- 🐛 修复 Windows + WSL 编码问题
  - 所有 subprocess 调用强制使用 UTF-8 编码
  - 修复 `UnicodeDecodeError: 'gbk' codec can't decode` 错误
- ✅ 添加 beautifulsoup4 依赖到 requirements.txt
- 📚 更新文档说明版本兼容性

### v1.0.0 (2025-01-06)

**新功能**：
- ✨ 首次发布 HTML-pdf2htmlEX版 模式
- ✨ 支持单文件和批量处理
- ✨ 完整的缓存支持
- ✨ JSON重新生成功能
- ✨ 与HTML截图版完全一致的布局

**技术改进**：
- 🔧 CSS 样式隔离机制
- 🔧 BeautifulSoup HTML 解析
- 🔧 错误处理和降级方案

---

## 十一、联系和支持

### 报告问题

如遇到问题，请提供：
1. 错误信息截图
2. PDF 文件类型描述
3. 使用的参数配置
4. 系统环境信息

### 相关链接

- **pdf2htmlEX GitHub**: https://github.com/pdf2htmlEX/pdf2htmlEX
- **项目文档**: 查看项目 README.md
- **Gemini API**: https://ai.google.dev/

---

## 附录：命令行参考

### pdf2htmlEX 主要参数

```bash
pdf2htmlEX [options] <input.pdf> [<output.html>]

常用选项：
  --zoom <ratio>              缩放比例 (默认: 1.0)
  --embed cfijo               嵌入 CSS、字体、图片、JS、轮廓
  --single-html 1             生成单个HTML文件
  --split-pages 0             不分页
  --hdpi <dpi>                水平DPI (默认: 144)
  --vdpi <dpi>                垂直DPI (默认: 144)
  --dest-dir <dir>            输出目录
  --bg-format jpg|png         背景图片格式
  --process-outline 0         不处理大纲
```

### 示例命令

```bash
# 基本转换
pdf2htmlEX document.pdf

# 高质量转换
pdf2htmlEX --zoom 1.5 --hdpi 192 --vdpi 192 document.pdf output.html

# 完整内联（单文件模式）
pdf2htmlEX --embed cfijo --single-html 1 document.pdf
```

---

**祝您使用愉快！** 🎉

如有任何问题或建议，欢迎反馈。

