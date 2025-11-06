#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML Pdf2htmlEX Generator
Generate single HTML file with pdf2htmlEX converted content on left and markdown-rendered explanations on right
Uses pdf2htmlEX for high-quality PDF to HTML conversion
"""

import os
import re
import base64
import subprocess
import tempfile
import shutil
from typing import Dict, Optional, List, Tuple
from pathlib import Path

from .logger import get_logger

logger = get_logger()


class HTMLPdf2htmlEXGenerator:
    """Generate HTML view with pdf2htmlEX converted content and explanations"""
    
    @staticmethod
    def check_pdf2htmlex_installed() -> Tuple[bool, Optional[str]]:
        """
        Check if pdf2htmlEX is installed and available
        Supports: Native (Linux/macOS), WSL (Windows), Docker
        
        Returns:
            (is_installed, version_or_error)
        """
        import platform
        
        # Method 1: Try native command first
        try:
            result = subprocess.run(
                ['pdf2htmlEX', '--version'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=5
            )
            if result.returncode == 0:
                version = result.stdout.strip() or result.stderr.strip()
                logger.info(f"pdf2htmlEX found (native): {version}")
                return True, f"Native: {version}"
        except FileNotFoundError:
            pass
        except Exception as e:
            logger.debug(f"Native pdf2htmlEX check failed: {e}")
        
        # Method 2: Try WSL on Windows
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['wsl', 'pdf2htmlEX', '--version'],
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=5
                )
                if result.returncode == 0:
                    version = result.stdout.strip() or result.stderr.strip()
                    logger.info(f"pdf2htmlEX found via WSL: {version}")
                    return True, f"WSL: {version}"
            except FileNotFoundError:
                logger.debug("WSL not found on Windows")
            except Exception as e:
                logger.debug(f"WSL pdf2htmlEX check failed: {e}")
        
        # Method 3: Try Docker (optional, not implemented yet)
        # Could check for docker and pdf2htmlex image
        
        # All methods failed
        error_msg = (
            "pdf2htmlEX not found. Please install it:\n\n"
            "Option 1 - WSL (Windows recommended):\n"
            "  1. Install WSL: wsl --install\n"
            "  2. In WSL: sudo apt-get update && sudo apt-get install pdf2htmlex\n"
            "  3. Test: wsl pdf2htmlEX --version\n\n"
            "Option 2 - Native:\n"
            "  - Linux: sudo apt-get install pdf2htmlex\n"
            "  - macOS: brew install pdf2htmlex\n\n"
            "Option 3 - Docker:\n"
            "  - docker pull pdf2htmlex/pdf2htmlex:0.18.8.rc1-master-20200820-ubuntu-20.04-x86_64\n\n"
            "GitHub: https://github.com/pdf2htmlEX/pdf2htmlEX"
        )
        logger.error(error_msg)
        return False, error_msg
    
    @staticmethod
    def _get_pdf2htmlex_command() -> Optional[List[str]]:
        """
        Detect and return the appropriate pdf2htmlEX command prefix
        
        Returns:
            Command prefix list (e.g., ['pdf2htmlEX'] or ['wsl', 'pdf2htmlEX']) or None
        """
        import platform
        
        # Try native command first
        try:
            result = subprocess.run(
                ['pdf2htmlEX', '--version'],
                capture_output=True,
                encoding='utf-8',
                errors='replace',
                timeout=3
            )
            if result.returncode == 0:
                logger.info("Using native pdf2htmlEX")
                return ['pdf2htmlEX']
        except:
            pass
        
        # Try WSL on Windows
        if platform.system() == 'Windows':
            try:
                result = subprocess.run(
                    ['wsl', 'pdf2htmlEX', '--version'],
                    capture_output=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=3
                )
                if result.returncode == 0:
                    logger.info("Using pdf2htmlEX via WSL")
                    return ['wsl', 'pdf2htmlEX']
            except:
                pass
        
        return None
    
    @staticmethod
    def _detect_pdf2htmlex_features(cmd_prefix: List[str]) -> Dict[str, bool]:
        """
        Detect which features/parameters are supported by the installed pdf2htmlEX version
        
        Args:
            cmd_prefix: Command prefix (e.g., ['pdf2htmlEX'] or ['wsl', 'pdf2htmlEX'])
            
        Returns:
            Dict of supported features
        """
        features = {
            'dpi': False,  # Single --dpi parameter
            'hdpi_vdpi': False,  # Separate --hdpi and --vdpi parameters
            'split_pages': False,
            'embed_options': False  # Individual --embed-css, --embed-font, etc.
        }
        
        # Test --help output to detect supported options
        try:
            result = subprocess.run(
                cmd_prefix + ['--help'],
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=3
            )
            help_text = result.stdout + result.stderr
            
            # Check for DPI options
            if '--dpi' in help_text and 'Resolution for graphics' in help_text:
                features['dpi'] = True
            if '--hdpi' in help_text:
                features['hdpi_vdpi'] = True
            
            # Check for split-pages
            if '--split-pages' in help_text:
                features['split_pages'] = True
            
            # Check for individual embed options
            if '--embed-css' in help_text and '--embed-font' in help_text:
                features['embed_options'] = True
                
            logger.info(f"Detected pdf2htmlEX features: {features}")
        except Exception as e:
            logger.warning(f"Could not detect pdf2htmlEX features: {e}")
        
        return features
    
    @staticmethod
    def call_pdf2htmlex(
        pdf_bytes: bytes,
        output_dir: str,
        zoom: float = 1.3,
        dpi: int = 144
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Call pdf2htmlEX to convert PDF to HTML
        Automatically detects whether to use native or WSL command
        
        Args:
            pdf_bytes: PDF file bytes
            output_dir: Output directory path
            zoom: Zoom level for rendering
            dpi: Resolution for graphics in DPI
            
        Returns:
            (success, html_path_or_none, error_message_or_none)
        """
        import platform
        
        # Get command prefix
        cmd_prefix = HTMLPdf2htmlEXGenerator._get_pdf2htmlex_command()
        if not cmd_prefix:
            return False, None, "pdf2htmlEX command not found"
        
        # Detect supported features
        features = HTMLPdf2htmlEXGenerator._detect_pdf2htmlex_features(cmd_prefix)
        
        # Create temp input file
        temp_pdf_path = os.path.join(output_dir, "input.pdf")
        output_html_name = "output.html"
        output_html_path = os.path.join(output_dir, output_html_name)
        
        try:
            # Write PDF bytes to temp file
            with open(temp_pdf_path, 'wb') as f:
                f.write(pdf_bytes)
            
            # For WSL, convert Windows paths to WSL paths
            if 'wsl' in cmd_prefix:
                # Convert Windows path to WSL path
                wsl_output_dir = HTMLPdf2htmlEXGenerator._convert_to_wsl_path(output_dir)
                wsl_temp_pdf = HTMLPdf2htmlEXGenerator._convert_to_wsl_path(temp_pdf_path)
                input_path = wsl_temp_pdf
                dest_dir = wsl_output_dir
            else:
                input_path = temp_pdf_path
                dest_dir = output_dir
            
            # Build command with compatibility checks
            # Start with basic parameters that all versions support
            cmd = cmd_prefix + ['--zoom', str(zoom)]
            
            # Add DPI parameters based on what's supported
            if features['dpi']:
                cmd.extend(['--dpi', str(dpi)])
            elif features['hdpi_vdpi']:
                cmd.extend(['--hdpi', str(dpi), '--vdpi', str(dpi)])
            
            # Use individual embed options if supported (more reliable)
            if features['embed_options']:
                cmd.extend([
                    '--embed-css', '1',
                    '--embed-font', '1',
                    '--embed-image', '1',
                    '--embed-javascript', '1',
                    '--embed-outline', '1'
                ])
            
            # Add split-pages for single HTML output (no separate page files)
            if features['split_pages']:
                cmd.extend(['--split-pages', '0'])
            
            # Add destination directory and files
            cmd.extend(['--dest-dir', dest_dir, input_path, output_html_name])
            
            logger.info(f"Running pdf2htmlEX: {' '.join(cmd)}")
            
            # Execute pdf2htmlEX
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode != 0:
                error_msg = f"pdf2htmlEX failed (exit code {result.returncode}):\n{result.stderr}"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Check if output file exists
            if not os.path.exists(output_html_path):
                error_msg = "pdf2htmlEX completed but output file not found"
                logger.error(error_msg)
                return False, None, error_msg
            
            logger.info(f"pdf2htmlEX conversion successful: {output_html_path}")
            return True, output_html_path, None
            
        except subprocess.TimeoutExpired:
            error_msg = "pdf2htmlEX conversion timeout (>5 minutes)"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"Error calling pdf2htmlEX: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
    
    @staticmethod
    def _convert_to_wsl_path(windows_path: str) -> str:
        """
        Convert Windows path to WSL path
        C:\\Users\\... -> /mnt/c/Users/...
        
        Args:
            windows_path: Windows-style path
            
        Returns:
            WSL-style path
        """
        import re
        
        # Normalize path separators
        path = windows_path.replace('\\', '/')
        
        # Convert drive letter: C:/... -> /mnt/c/...
        match = re.match(r'^([A-Za-z]):', path)
        if match:
            drive = match.group(1).lower()
            path = f"/mnt/{drive}" + path[2:]
        
        return path
    
    @staticmethod
    def parse_pdf2htmlex_html(html_path: str) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
        """
        Parse pdf2htmlEX generated HTML and extract CSS and pages
        
        Args:
            html_path: Path to pdf2htmlEX generated HTML file
            
        Returns:
            (css_content, page_htmls_list, error_message)
        """
        try:
            from bs4 import BeautifulSoup
            
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract CSS from <style> tags
            css_parts = []
            for style_tag in soup.find_all('style'):
                css_parts.append(style_tag.string or '')
            css_content = '\n'.join(css_parts)
            
            # Extract pages from page-container
            page_container = soup.find('div', id='page-container')
            if not page_container:
                return None, None, "No #page-container found in pdf2htmlEX output"
            
            # Find all page divs (class="pf")
            page_divs = page_container.find_all('div', class_='pf')
            if not page_divs:
                return None, None, "No page divs found in pdf2htmlEX output"
            
            # Extract each page's HTML
            page_htmls = []
            for i, page_div in enumerate(page_divs):
                page_html = str(page_div)
                page_htmls.append(page_html)
            
            logger.info(f"Parsed pdf2htmlEX HTML: {len(page_htmls)} pages, {len(css_content)} bytes CSS")
            return css_content, page_htmls, None
            
        except ImportError:
            error_msg = "BeautifulSoup not installed. Please install: pip install beautifulsoup4"
            logger.error(error_msg)
            return None, None, error_msg
        except Exception as e:
            error_msg = f"Error parsing pdf2htmlEX HTML: {str(e)}"
            logger.error(error_msg)
            return None, None, error_msg
    
    @staticmethod
    def isolate_pdf2htmlex_styles(css_content: str) -> str:
        """
        Add namespace prefix to pdf2htmlEX CSS to avoid conflicts
        
        Args:
            css_content: Original CSS from pdf2htmlEX
            
        Returns:
            Modified CSS with namespace prefix
        """
        if not css_content:
            return ""
        
        # Add .pdf2htmlex-container prefix to all selectors
        # This is a simple approach - might need refinement for complex CSS
        
        lines = css_content.split('\n')
        modified_lines = []
        
        in_media_query = False
        brace_depth = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Track media queries
            if stripped.startswith('@media'):
                in_media_query = True
                modified_lines.append(line)
                continue
            
            # Count braces to track nesting
            brace_depth += line.count('{') - line.count('}')
            
            # Check if we're exiting media query
            if in_media_query and brace_depth == 0:
                in_media_query = False
            
            # Skip empty lines, comments, @rules
            if not stripped or stripped.startswith('/*') or stripped.startswith('@'):
                modified_lines.append(line)
                continue
            
            # If line contains selector (before {)
            if '{' in line and not line.strip().startswith('}'):
                # Extract selector part
                parts = line.split('{', 1)
                selectors = parts[0].strip()
                rest = '{' + parts[1] if len(parts) > 1 else ''
                
                # Split multiple selectors
                selector_list = [s.strip() for s in selectors.split(',')]
                
                # Add prefix to each selector
                prefixed_selectors = []
                for selector in selector_list:
                    if selector and not selector.startswith('@'):
                        # Add .pdf2htmlex-container prefix
                        prefixed = f".pdf2htmlex-container {selector}"
                        prefixed_selectors.append(prefixed)
                    else:
                        prefixed_selectors.append(selector)
                
                # Reconstruct line
                modified_line = ', '.join(prefixed_selectors) + ' ' + rest
                modified_lines.append(modified_line)
            else:
                modified_lines.append(line)
        
        return '\n'.join(modified_lines)
    
    @staticmethod
    def _render_markdown_to_html(markdown_content: str) -> str:
        """
        Render markdown content to HTML
        (Copied from HTMLScreenshotGenerator for consistency)
        
        Args:
            markdown_content: Markdown formatted text
            
        Returns:
            Rendered HTML string
        """
        if not markdown_content or not markdown_content.strip():
            return "<p>暂无讲解内容</p>"
        
        try:
            import markdown
            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    'fenced_code',
                    'tables',
                    'nl2br',
                    'sane_lists'
                ]
            )
            return html_content
        except ImportError:
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
        except Exception as e:
            logger.warning(f"Failed to render markdown: {e}")
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
    
    @staticmethod
    def generate_html_pdf2htmlex_view(
        page_htmls: List[str],
        pdf2htmlex_css: str,
        explanations: Dict[int, str],
        total_pages: int,
        title: str = "PDF文档讲解",
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_count: int = 2,
        column_gap: int = 20,
        show_column_rule: bool = True
    ) -> str:
        """
        生成完整的HTML视图，包含pdf2htmlEX转换的PDF内容和讲解文本
        布局与HTML截图版完全一致：左侧PDF，右侧讲解
        
        Args:
            page_htmls: pdf2htmlEX生成的页面HTML字符串列表
            pdf2htmlex_css: pdf2htmlEX生成的CSS样式内容
            explanations: 字典，键为页码（从1开始），值为讲解文本
            total_pages: PDF总页数
            title: 文档标题
            font_name: 字体族名称
            font_size: 字体大小（pt单位）
            line_spacing: 行高倍数
            column_count: 讲解文本的列数
            column_gap: 列之间的间距（px单位）
            show_column_rule: 是否显示列分隔线
            
        Returns:
            完整的HTML文档字符串
        """
        logger.info(f"Generating HTML pdf2htmlEX view for {total_pages} pages")
        
        # 导入HTML截图生成器，复用其CSS样式生成功能
        from .html_screenshot_generator import HTMLScreenshotGenerator
        
        # 生成基础CSS样式（复用HTML截图版的样式，保持布局一致）
        base_css = HTMLScreenshotGenerator._generate_css_styles(
            font_name, font_size, line_spacing, column_count, column_gap, show_column_rule
        )
        
        # 隔离pdf2htmlEX的CSS，添加命名空间前缀避免样式冲突
        isolated_pdf2htmlex_css = HTMLPdf2htmlEXGenerator.isolate_pdf2htmlex_styles(pdf2htmlex_css)
        
        # pdf2htmlEX容器特定的CSS样式
        pdf2htmlex_container_css = """
/* pdf2htmlEX 容器特定样式 */
.pdf2htmlex-container {
    width: 100%;                    /* 宽度占满父容器 */
    height: 100%;                    /* 高度占满父容器 */
    overflow: visible;               /* 允许内容溢出显示 */
    display: flex;                   /* 使用弹性布局 */
    flex-direction: column;          /* 垂直方向排列（从上到下） */
    align-items: left;             /* 水平居中对齐 */
    padding: 0;                      /* 无内边距，避免额外空白 */
}

/* PDF 页面样式（.pf 是 pdf2htmlEX 生成的页面类名） */
.pdf2htmlex-container .pf {
    margin-bottom: 0px;              /* 页面底部间距为0，紧密排列 */
    background: white;               /* 白色背景 */
    border-radius: 4px;              /* 圆角4px，柔和边角 */
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);  /* 轻微阴影效果 */
    overflow: visible;               /* 允许内容溢出 */
    transition: all 0.3s ease;       /* 所有属性变化都有0.3秒平滑过渡 */
    position: relative;              /* 相对定位，用于内部绝对定位元素的参考 */
    transform-origin: top center;    /* 缩放变换的原点：顶部中心 */
    display: inline-block;           /* 行内块元素，保持内容宽度 */
}

/* 当前激活页面的样式（滚动到视口时高亮显示） */
.pdf2htmlex-container .pf.active {
    box-shadow: 0 8px 32px rgba(52, 152, 219, 0.6);  /* 更明显的蓝色阴影，突出当前页 */
}

/* 页面编号标签样式（显示"第 X 页"的蓝色标签） */
.pdf2htmlex-page-badge {
    position: absolute;               /* 绝对定位，相对于父容器（PDF页面） */
    top: 10px;                       /* 距离顶部10px */
    left: 10px;                      /* 距离左边10px */
    background: rgba(52, 152, 219, 0.6);  /* 蓝色半透明背景（90%不透明度） */
    color: white;                    /* 白色文字 */
    padding: 8px 16px;               /* 内边距：上下8px，左右16px */
    border-radius: 20px;            /* 圆角20px，形成胶囊形状 */
    font-weight: bold;               /* 粗体文字 */
    font-size: 12pt;                /* 字体大小12pt */
    z-index: 10;                     /* 层级为10，确保显示在PDF内容之上 */
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);  /* 轻微阴影，增加立体感 */
}
"""
        
        # 覆盖截图面板的内边距样式，与HTML截图版保持一致
        screenshots_panel_override = """
/* 覆盖截图面板的内边距 - 与HTML截图版保持一致 */
.screenshots-panel {
    padding: 5px !important;          /* 四周各5px内边距，使用!important确保优先级 */
}
"""
        
        # 合并所有CSS样式：基础样式 + pdf2htmlEX隔离样式 + 容器样式 + 面板覆盖样式
        combined_css = base_css + '\n' + isolated_pdf2htmlex_css + '\n' + pdf2htmlex_container_css + '\n' + screenshots_panel_override
        
        # 生成JavaScript代码（复用HTML截图版的逻辑，但适配pdf2htmlEX页面）
        javascript_code = HTMLPdf2htmlEXGenerator._generate_javascript_for_pdf2htmlex(total_pages)
        
        # 生成左侧PDF页面的HTML结构
        # 每个页面包含：外层容器、页面编号标签、pdf2htmlEX生成的页面内容
        pdf2htmlex_pages_html = ""
        for i, page_html in enumerate(page_htmls):
            page_num = i + 1
            pdf2htmlex_pages_html += f"""
            <div class="page-screenshot pf" id="page-{page_num}" data-page="{page_num}">
                <div class="pdf2htmlex-page-badge">第 {page_num} 页</div>
                {page_html}
            </div>
            """
        
        # 生成右侧讲解内容的HTML结构
        # 每个讲解项包含：页面标题、Markdown渲染后的讲解内容
        explanations_html = ""
        for page_num in range(1, total_pages + 1):
            explanation_text = explanations.get(page_num, "")
            
            # 将Markdown格式的讲解文本转换为HTML
            if explanation_text.strip():
                explanation_html = HTMLPdf2htmlEXGenerator._render_markdown_to_html(explanation_text)
            else:
                explanation_html = "<p>暂无讲解内容</p>"
            
            explanations_html += f"""
            <div class="explanation-item" id="explanation-{page_num}" data-page="{page_num}">
                <div class="explanation-page-title">📖 第 {page_num} 页讲解</div>
                <div class="explanation-content">
                    {explanation_html}
                </div>
            </div>
            """
        
        # 生成完整的HTML文档结构（布局与HTML截图版完全一致）
        html_document = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - HTML-pdf2htmlEX版</title>
    <style>{combined_css}</style>
</head>
<body>
    <!-- 顶部阅读进度条（显示右侧讲解面板的滚动进度） -->
    <div class="reading-progress"></div>
    
    <!-- 加载指示器（页面加载时显示，500ms后自动隐藏） -->
    <div class="loading">
        <div style="font-size: 16pt; font-weight: bold; color: #2c3e50;">正在加载...</div>
    </div>
    
    <!-- 主容器：采用左右分栏布局 -->
    <div class="main-container">
        <!-- 左侧面板：显示pdf2htmlEX转换的PDF页面 -->
        <div class="screenshots-panel">
            <div class="pdf2htmlex-container">
                {pdf2htmlex_pages_html}
            </div>
        </div>
        
        <!-- 右侧面板：显示讲解内容 -->
        <div class="explanations-panel">
            <!-- 顶部标题栏：包含文档标题、当前页码、字体设置按钮、主题切换按钮 -->
            <div class="explanation-header">
                <div style="text-align: center; flex: 1;">
                    <h1>📚 {title}</h1>
                    <div class="current-page-indicator">第 1 页 / 共 {total_pages} 页</div>
                </div>
                <button class="font-controls-toggle" title="字体设置">Aa</button>
                <button class="theme-toggle" title="切换主题">🌙</button>
            </div>
            <!-- 讲解内容容器：包含所有页面的讲解文本 -->
            <div class="explanations-container">
                {explanations_html}
            </div>
        </div>
    </div>
    
    <!-- 底部导航控制栏：上一页/下一页按钮和页码显示 -->
    <div class="nav-controls">
        <button class="nav-btn" id="prev-btn" title="上一页 (↑)">‹ 上一页</button>
        <span class="page-info">1 / {total_pages}</span>
        <button class="nav-btn" id="next-btn" title="下一页 (↓)">下一页 ›</button>
    </div>
    
    <!-- 字体控制面板：字体大小和行距调节滑块（默认隐藏，点击Aa按钮显示） -->
    <div class="font-controls">
        <div class="font-control-group">
            <label class="font-control-label">
                字体大小
                <span class="font-control-value" id="font-size-value">16pt</span>
            </label>
            <input 
                type="range" 
                class="font-control-slider" 
                id="font-size-slider" 
                min="12" 
                max="24" 
                step="1" 
                value="16"
            />
        </div>
        <div class="font-control-group">
            <label class="font-control-label">
                行距
                <span class="font-control-value" id="line-height-value">1.8</span>
            </label>
            <input 
                type="range" 
                class="font-control-slider" 
                id="line-height-slider" 
                min="1.3" 
                max="2.5" 
                step="0.1" 
                value="1.8"
            />
        </div>
    </div>
    
    <!-- JavaScript代码：处理页面同步、缩放、导航等交互逻辑 -->
    <script>{javascript_code}</script>
</body>
</html>
"""
        
        logger.info(f"HTML pdf2htmlEX view generated successfully, size: {len(html_document)} bytes")
        return html_document
    
    @staticmethod
    def _generate_javascript_for_pdf2htmlex(total_pages: int) -> str:
        """
        生成pdf2htmlEX视图的JavaScript代码
        从HTML截图版适配而来，处理pdf2htmlEX页面的布局和交互
        
        Args:
            total_pages: PDF总页数
            
        Returns:
            JavaScript代码字符串
        """
        js = f"""
// HTML pdf2htmlEX 视图同步类 - 适配pdf2htmlEX页面
// 负责处理：页面缩放、左右同步滚动、导航控制、主题切换等功能
class Pdf2htmlEXExplanationSync {{
    constructor() {{
        this.currentPage = 1;              // 当前显示的页码（从1开始）
        this.totalPages = {total_pages};    // PDF总页数
        this.observer = null;              // IntersectionObserver实例，用于检测页面进入视口
        this.fontControlsVisible = false;  // 字体控制面板是否可见
        this.pageScrollPositions = {{}};    // 存储每个页面在讲解面板中的滚动位置
        this.init();
    }}
    
    // 初始化所有功能模块
    init() {{
        // 隐藏加载指示器
        const loading = document.querySelector('.loading');
        if (loading) {{
            setTimeout(() => loading.remove(), 500);
        }}
        
        // 加载本地存储的设置（主题、字体大小、行距）
        this.loadSettings();
        // 计算并应用PDF页面的缩放比例
        this.scalePdf2htmlexPages();
        // 设置IntersectionObserver，监听页面进入视口
        this.setupObserver();
        // 设置导航控制（按钮点击、键盘快捷键）
        this.setupControls();
        // 设置阅读进度条（跟踪右侧讲解面板的滚动）
        this.setupReadingProgress();
        // 设置主题切换功能（明暗模式）
        this.setupThemeToggle();
        // 设置字体控制面板（字体大小、行距滑块）
        this.setupFontControls();
        // 显示第一页的讲解内容
        this.showExplanation(1);
        
        // 监听窗口大小变化，重新计算页面缩放
        window.addEventListener('resize', () => this.scalePdf2htmlexPages());
    }}
    
    // 从本地存储加载用户设置（主题、字体大小、行距）
    loadSettings() {{
        // 加载主题设置
        const savedTheme = localStorage.getItem('html-pdf2htmlex-theme');
        if (savedTheme === 'dark') {{
            document.body.classList.add('dark-mode');
        }}
        
        // 加载字体大小设置
        const savedFontSize = localStorage.getItem('html-pdf2htmlex-font-size');
        if (savedFontSize) {{
            document.documentElement.style.setProperty('--font-size', savedFontSize + 'pt');
        }}
        
        // 加载行距设置
        const savedLineHeight = localStorage.getItem('html-pdf2htmlex-line-height');
        if (savedLineHeight) {{
            document.documentElement.style.setProperty('--line-height', savedLineHeight);
        }}
    }}
    
    // 核心布局函数：计算并应用PDF页面的缩放比例
    // 使PDF页面充分利用左侧面板的可用空间，同时保持合适的显示大小
    scalePdf2htmlexPages() {{
        // 获取左侧PDF面板容器
        const container = document.querySelector('.screenshots-panel');
        // 获取所有PDF页面元素（.pf是pdf2htmlEX生成的页面类名）
        const pages = document.querySelectorAll('.pdf2htmlex-container .pf');
        
        if (!container || !pages.length) return;
        
        // 精确计算可用宽度：容器宽度减去左右内边距
        const containerPadding = 0; // 左右各0px内边距（已通过CSS设置）
        const containerWidth = container.clientWidth - containerPadding;
        
        // 遍历每个PDF页面，计算并应用缩放
        pages.forEach(page => {{
            // 重置transform，获取页面的原始尺寸
            page.style.transform = '';
            
            // 获取页面的原始宽度（scrollWidth优先，fallback到offsetWidth）
            const pageWidth = page.scrollWidth || page.offsetWidth;
            
            // 计算缩放比例：可用宽度 / 页面原始宽度
            const rawScale = containerWidth / pageWidth;
            // 限制缩放范围：最小0.3倍（避免过度缩小），最大1.2倍（避免过度放大）
            const scale = Math.min(Math.max(rawScale, 0.3), 1.2);
            
            // 应用CSS transform缩放变换
            page.style.transform = `scale(${{scale}})`;
            
            // 页面间距由CSS中的margin-bottom控制，无需在这里设置
        }});
    }}
    
    // 设置阅读进度条：跟踪右侧讲解面板的滚动进度
    setupReadingProgress() {{
        const explanationsPanel = document.querySelector('.explanations-panel');
        if (!explanationsPanel) return;
        
        // 使用节流机制（throttle），避免频繁更新进度条
        let ticking = false;
        explanationsPanel.addEventListener('scroll', () => {{
            if (!ticking) {{
                window.requestAnimationFrame(() => {{
                    // 计算滚动进度百分比
                    const scrollTop = explanationsPanel.scrollTop;  // 当前滚动位置
                    const scrollHeight = explanationsPanel.scrollHeight - explanationsPanel.clientHeight;  // 可滚动总高度
                    const progress = (scrollTop / scrollHeight) * 100;
                    
                    // 更新顶部进度条的宽度
                    const progressBar = document.querySelector('.reading-progress');
                    if (progressBar) {{
                        progressBar.style.width = Math.min(progress, 100) + '%';
                    }}
                    
                    ticking = false;
                }});
                ticking = true;
            }}
        }});
    }}
    
    // 设置主题切换功能：在明暗模式之间切换
    setupThemeToggle() {{
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;
        
        // 初始化主题图标
        this.updateThemeIcon();
        
        // 绑定点击事件：切换主题并保存到本地存储
        themeToggle.addEventListener('click', () => {{
            document.body.classList.toggle('dark-mode');
            const isDark = document.body.classList.contains('dark-mode');
            localStorage.setItem('html-pdf2htmlex-theme', isDark ? 'dark' : 'light');
            this.updateThemeIcon();
        }});
    }}
    
    // 更新主题切换按钮的图标：根据当前主题显示太阳或月亮图标
    updateThemeIcon() {{
        const themeToggle = document.querySelector('.theme-toggle');
        if (!themeToggle) return;
        
        const isDark = document.body.classList.contains('dark-mode');
        themeToggle.textContent = isDark ? '☀️' : '🌙';
        themeToggle.title = isDark ? 'Switch to light mode' : 'Switch to dark mode';
    }}
    
    // 设置字体控制面板：字体大小和行距滑块
    setupFontControls() {{
        const toggle = document.querySelector('.font-controls-toggle');
        const panel = document.querySelector('.font-controls');
        const fontSizeSlider = document.getElementById('font-size-slider');
        const lineHeightSlider = document.getElementById('line-height-slider');
        
        if (!toggle || !panel) return;
        
        // 绑定字体控制面板的显示/隐藏切换
        toggle.addEventListener('click', () => {{
            this.fontControlsVisible = !this.fontControlsVisible;
            panel.classList.toggle('visible', this.fontControlsVisible);
        }});
        
        // 设置字体大小滑块
        if (fontSizeSlider) {{
            // 从本地存储加载保存的字体大小，默认为16pt
            const savedFontSize = localStorage.getItem('html-pdf2htmlex-font-size') || '16';
            fontSizeSlider.value = savedFontSize;
            document.getElementById('font-size-value').textContent = savedFontSize + 'pt';
            
            // 监听滑块变化，实时更新字体大小并保存到本地存储
            fontSizeSlider.addEventListener('input', (e) => {{
                const value = e.target.value;
                document.documentElement.style.setProperty('--font-size', value + 'pt');
                document.getElementById('font-size-value').textContent = value + 'pt';
                localStorage.setItem('html-pdf2htmlex-font-size', value);
            }});
        }}
        
        // 设置行距滑块
        if (lineHeightSlider) {{
            // 从本地存储加载保存的行距，默认为1.8
            const savedLineHeight = localStorage.getItem('html-pdf2htmlex-line-height') || '1.8';
            lineHeightSlider.value = savedLineHeight;
            document.getElementById('line-height-value').textContent = savedLineHeight;
            
            // 监听滑块变化，实时更新行距并保存到本地存储
            lineHeightSlider.addEventListener('input', (e) => {{
                const value = e.target.value;
                document.documentElement.style.setProperty('--line-height', value);
                document.getElementById('line-height-value').textContent = value;
                localStorage.setItem('html-pdf2htmlex-line-height', value);
            }});
        }}
    }}
    
    // 设置IntersectionObserver：监听PDF页面进入视口，自动同步显示对应的讲解内容
    setupObserver() {{
        // 配置观察器选项
        const options = {{
            root: document.querySelector('.screenshots-panel'),  // 观察的根元素（左侧PDF面板）
            rootMargin: '-20% 0px -20% 0px',                      // 顶部和底部各缩小20%的视口区域
            threshold: 0.5                                        // 当页面50%进入视口时触发
        }};
        
        // 创建IntersectionObserver实例
        this.observer = new IntersectionObserver((entries) => {{
            entries.forEach(entry => {{
                // 当页面进入视口时
                if (entry.isIntersecting) {{
                    // 获取页面编号并显示对应的讲解内容
                    const pageNum = parseInt(entry.target.dataset.page);
                    this.showExplanation(pageNum);
                    
                    // 移除所有页面的active类，然后给当前页面添加active类（高亮显示）
                    document.querySelectorAll('.page-screenshot').forEach(el => {{
                        el.classList.remove('active');
                    }});
                    entry.target.classList.add('active');
                }}
            }});
        }}, options);
        
        // 开始观察所有PDF页面元素
        document.querySelectorAll('.page-screenshot').forEach(el => {{
            this.observer.observe(el);
        }});
    }}
    
    // 设置导航控制：按钮点击和键盘快捷键
    setupControls() {{
        // 获取上一页/下一页按钮
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        // 绑定按钮点击事件
        if (prevBtn) {{
            prevBtn.addEventListener('click', () => this.goToPrevPage());
        }}
        
        if (nextBtn) {{
            nextBtn.addEventListener('click', () => this.goToNextPage());
        }}
        
        // 绑定键盘快捷键
        document.addEventListener('keydown', (e) => {{
            // 如果焦点在输入框或文本域中，不拦截按键
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {{
                return;
            }}
            
            switch(e.key) {{
                case 'ArrowUp':      // 上箭头键
                case 'ArrowLeft':    // 左箭头键
                    e.preventDefault();
                    this.goToPrevPage();
                    break;
                case 'ArrowDown':    // 下箭头键
                case 'ArrowRight':   // 右箭头键
                case ' ':           // 空格键
                    e.preventDefault();
                    this.goToNextPage();
                    break;
                case 'Home':        // Home键：跳转到第一页
                    e.preventDefault();
                    this.goToPage(1);
                    break;
                case 'End':         // End键：跳转到最后一页
                    e.preventDefault();
                    this.goToPage(this.totalPages);
                    break;
            }}
        }});
        
        // 设置右侧讲解面板的滚动行为为平滑滚动
        const explanationsPanel = document.querySelector('.explanations-panel');
        if (explanationsPanel) {{
            explanationsPanel.style.scrollBehavior = 'smooth';
        }}
    }}
    
    // 显示指定页码的讲解内容（核心同步函数）
    showExplanation(pageNum) {{
        // 验证页码有效性
        if (pageNum < 1 || pageNum > this.totalPages) {{
            return;
        }}
        
        const explanationsPanel = document.querySelector('.explanations-panel');
        // 保存当前页面在讲解面板中的滚动位置
        if (explanationsPanel && this.currentPage) {{
            this.pageScrollPositions[this.currentPage] = explanationsPanel.scrollTop;
        }}
        
        // 更新当前页码
        this.currentPage = pageNum;
        
        // 隐藏所有讲解项，只显示当前页的讲解
        document.querySelectorAll('.explanation-item').forEach(el => {{
            el.classList.remove('active');
        }});
        
        // 显示当前页的讲解内容
        const targetExplanation = document.getElementById(`explanation-${{pageNum}}`);
        if (targetExplanation) {{
            targetExplanation.classList.add('active');
        }}
        
        // 恢复讲解面板的滚动位置（如果之前访问过该页）
        if (explanationsPanel) {{
            const originalBehavior = explanationsPanel.style.scrollBehavior;
            explanationsPanel.style.scrollBehavior = 'auto';  // 临时禁用平滑滚动
            
            if (this.pageScrollPositions[pageNum] !== undefined) {{
                // 恢复之前保存的滚动位置
                explanationsPanel.scrollTop = this.pageScrollPositions[pageNum];
            }} else {{
                // 首次访问该页，滚动到顶部
                explanationsPanel.scrollTop = 0;
            }}
            
            // 恢复平滑滚动行为
            setTimeout(() => {{
                explanationsPanel.style.scrollBehavior = originalBehavior;
            }}, 0);
        }}
        
        // 更新顶部标题栏的页码指示器
        const indicator = document.querySelector('.current-page-indicator');
        if (indicator) {{
            indicator.textContent = `第 ${{pageNum}} 页 / 共 ${{this.totalPages}} 页`;
        }}
        
        // 更新底部导航栏的页码显示
        const pageInfo = document.querySelector('.page-info');
        if (pageInfo) {{
            pageInfo.textContent = `${{pageNum}} / ${{this.totalPages}}`;
        }}
        
        // 更新按钮状态（禁用/启用上一页/下一页按钮）
        this.updateButtons();
        // 更新浏览器标签页标题
        document.title = `第${{pageNum}}页 - HTML-pdf2htmlEX版`;
    }}
    
    // 跳转到指定页码：平滑滚动左侧PDF面板，使目标页面居中显示
    goToPage(pageNum) {{
        // 验证页码有效性
        if (pageNum < 1 || pageNum > this.totalPages) {{
            return;
        }}
        
        // 获取目标页面元素并滚动到视口中心
        const screenshot = document.getElementById(`page-${{pageNum}}`);
        if (screenshot) {{
            screenshot.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
        }}
    }}
    
    // 跳转到上一页
    goToPrevPage() {{
        if (this.currentPage > 1) {{
            this.goToPage(this.currentPage - 1);
        }}
    }}
    
    // 跳转到下一页
    goToNextPage() {{
        if (this.currentPage < this.totalPages) {{
            this.goToPage(this.currentPage + 1);
        }}
    }}
    
    // 更新导航按钮状态：第一页时禁用"上一页"，最后一页时禁用"下一页"
    updateButtons() {{
        const prevBtn = document.getElementById('prev-btn');
        const nextBtn = document.getElementById('next-btn');
        
        if (prevBtn) {{
            prevBtn.disabled = this.currentPage <= 1;
        }}
        
        if (nextBtn) {{
            nextBtn.disabled = this.currentPage >= this.totalPages;
        }}
    }}
}}

// 页面加载完成后初始化同步功能
document.addEventListener('DOMContentLoaded', function() {{
    // 创建全局同步实例，绑定到window对象以便外部调用
    window.sync = new Pdf2htmlEXExplanationSync();
    console.log('HTML pdf2htmlEX View initialized with {{}} pages', {total_pages});
}});

// 提供全局函数，方便外部脚本调用（例如从URL跳转到指定页面）
window.goToPage = function(pageNum) {{
    if (window.sync) {{
        window.sync.goToPage(pageNum);
    }}
}};
"""
        return js

