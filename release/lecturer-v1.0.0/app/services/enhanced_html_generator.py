#!/usr/bin/env python3
"""
增强版HTML PDF生成器
实现PDF页面与讲解内容的一一对应，支持同步导航功能
"""

import json
import math
import uuid
import re
from typing import Dict, List, Optional, Tuple


class EnhancedHTMLGenerator:
    """增强版HTML PDF页面生成器，支持PDF-讲解同步"""
    
    @staticmethod
    def _render_markdown_to_html(markdown_content: str) -> str:
        """
        将Markdown格式的讲解内容渲染为HTML
        
        Args:
            markdown_content: Markdown格式的文本
            
        Returns:
            渲染后的HTML字符串
        """
        if not markdown_content or not markdown_content.strip():
            return "<p>暂无讲解内容</p>"
        
        try:
            # 尝试使用markdown库进行渲染
            import markdown
            html_content = markdown.markdown(
                markdown_content,
                extensions=[
                    'fenced_code',  # 代码块支持
                    'tables',       # 表格支持
                    'nl2br',        # 自动换行
                    'sane_lists'    # 更好的列表处理
                ]
            )
            return html_content
        except ImportError:
            # 如果没有markdown库，使用简单的文本转换
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
        except Exception as e:
            # 如果渲染失败，返回原始内容（转义后）
            print(f"Warning: Failed to render markdown: {e}")
            html_content = markdown_content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            html_content = html_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
            return f"<p>{html_content}</p>"
    
    @staticmethod
    def generate_sync_styles(
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_padding: int = 10
    ) -> str:
        """生成支持同步功能的CSS样式"""
        css = f"""
/* 同步PDF-讲解布局样式 */
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: '{font_name}', 'Microsoft YaHei', 'SimHei', sans-serif;
    font-size: {font_size}pt;
    line-height: {line_spacing};
    color: #333;
    background-color: #ffffff;
    height: 100vh;
    overflow: hidden;
}}

.sync-container {{
    display: flex;
    height: 100vh;
    width: 100vw;
}}

.pdf-panel {{
    flex: 1;
    max-width: 50%;
    background: #f8f9fa;
    border-right: 1px solid #e0e0e0;
    display: flex;
    flex-direction: column;
    position: relative;
}}

.pdf-viewer {{
    flex: 1;
    position: relative;
    overflow: hidden;
}}

/* 覆盖在 PDF 上方用于捕获滚轮的层（可开/关） */
.wheel-overlay {{
    position: absolute;
    inset: 0;
    z-index: 10;
    background: transparent;
}}

.pdf-viewer embed,
.pdf-viewer iframe {{
    width: 100%;
    height: 100%;
    border: none;
    background: white;
}}

.pdf-controls {{
    position: absolute;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 10px 20px;
    border-radius: 25px;
    display: flex;
    align-items: center;
    gap: 15px;
    z-index: 1000;
}}

.pdf-controls input[type="number"] {{
    width: 90px;
    padding: 6px 8px;
    border-radius: 5px;
    border: 1px solid #ced4da;
    font-size: 12pt;
    background: #ffffff;
    color: #212529;
}}

.pdf-controls label {{
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 11pt;
}}

.pdf-controls button {{
    background: #007bff;
    color: white;
    border: none;
    padding: 8px 12px;
    border-radius: 5px;
    cursor: pointer;
    font-size: 12pt;
    transition: background-color 0.2s;
}}

.pdf-controls button:hover {{
    background: #0056b3;
}}

.pdf-controls button:disabled {{
    background: #6c757d;
    cursor: not-allowed;
}}

.page-info {{
    font-size: 12pt;
    font-weight: bold;
    min-width: 80px;
    text-align: center;
}}

.explanation-panel {{
    flex: 1;
    max-width: 50%;
    background: white;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}}

.explanation-header {{
    padding: 20px;
    background: #007bff;
    color: white;
    text-align: center;
    border-bottom: 3px solid #0056b3;
}}

.explanation-header h2 {{
    margin: 0;
    font-size: 18pt;
    font-weight: bold;
}}

.explanation-content {{
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    line-height: {line_spacing};
}}

.explanation-page {{
    display: none;
    animation: fadeIn 0.3s ease-in-out;
}}

.explanation-page.active {{
    display: block;
}}

.explanation-page h1,
.explanation-page h2,
.explanation-page h3,
.explanation-page h4 {{
    color: #2c3e50;
    margin-bottom: 15px;
    line-height: 1.3;
}}

.explanation-page h1 {{
    font-size: 20pt;
    border-bottom: 2px solid #007bff;
    padding-bottom: 10px;
}}

.explanation-page h2 {{
    font-size: 18pt;
    color: #007bff;
}}

.explanation-page h3 {{
    font-size: 16pt;
}}

.explanation-page p {{
    margin-bottom: 15px;
    text-align: justify;
    text-justify: inter-word;
}}

.explanation-page ul,
.explanation-page ol {{
    margin-left: 20px;
    margin-bottom: 15px;
}}

.explanation-page li {{
    margin-bottom: 8px;
}}

.explanation-page code {{
    background: #f1f2f6;
    padding: 3px 6px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.9em;
    color: #e74c3c;
}}

.explanation-page pre {{
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 5px;
    padding: 15px;
    overflow-x: auto;
    margin: 15px 0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 11pt;
}}

.explanation-page blockquote {{
    border-left: 4px solid #007bff;
    padding-left: 15px;
    margin: 15px 0;
    font-style: italic;
    color: #6c757d;
    background: #f8f9fa;
    padding: 15px;
    border-radius: 0 5px 5px 0;
}}

.explanation-page .highlight {{
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    border-radius: 5px;
    padding: 15px;
    margin: 15px 0;
}}

.explanation-page .note {{
    background: #d1ecf1;
    border: 1px solid #bee5eb;
    border-radius: 5px;
    padding: 15px;
    margin: 15px 0;
    border-left: 4px solid #17a2b8;
}}

.explanation-page .warning {{
    background: #f8d7da;
    border: 1px solid #f5c6cb;
    border-radius: 5px;
    padding: 15px;
    margin: 15px 0;
    border-left: 4px solid #dc3545;
}}

@keyframes fadeIn {{
    from {{ opacity: 0; transform: translateY(10px); }}
    to {{ opacity: 1; transform: translateY(0); }}
}}

/* 加载指示器 */
.loading {{
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    text-align: center;
    color: #6c757d;
}}

.loading::after {{
    content: '';
    display: inline-block;
    width: 20px;
    height: 20px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #007bff;
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-left: 10px;
}}

@keyframes spin {{
    0% {{ transform: rotate(0deg); }}
    100% {{ transform: rotate(360deg); }}
}}

/* 响应式设计 */
@media (max-width: 1024px) {{
    .sync-container {{
        flex-direction: column;
    }}
    
    .pdf-panel,
    .explanation-panel {{
        max-width: 100%;
        height: 50vh;
    }}
    
    .pdf-controls {{
        bottom: 10px;
        padding: 8px 15px;
    }}
}}

@media (max-width: 768px) {{
    .explanation-header {{
        padding: 15px;
    }}
    
    .explanation-header h2 {{
        font-size: 16pt;
    }}
    
    .explanation-content {{
        padding: 15px;
    }}
    
    .pdf-controls {{
        bottom: 5px;
        padding: 6px 12px;
        gap: 10px;
    }}
    
    .pdf-controls button {{
        padding: 6px 10px;
        font-size: 11pt;
    }}
}}

/* 打印样式 */
@media print {{
    .sync-container {{
        flex-direction: column;
    }}
    
    .pdf-controls,
    .loading {{
        display: none;
    }}
    
    .pdf-panel {{
        max-width: 100%;
        height: 50vh;
        border-right: none;
        border-bottom: 1px solid #e0e0e0;
    }}
    
    .explanation-panel {{
        max-width: 100%;
    }}
}}
"""
        return css
    
    @staticmethod
    def generate_sync_javascript(
        total_pages: int,
        explanations: Dict[int, str]
    ) -> str:
        """生成PDF-讲解同步的JavaScript代码"""
        
        # 将讲解内容转换为JSON，确保正确转义
        explanations_json = json.dumps(explanations, ensure_ascii=False, indent=2)
        
        js = f"""
// PDF-讲解同步功能
class PDFExplanationSync {{
    constructor() {{
        this.currentPage = 1;
        this.totalPages = {total_pages};
        this.explanations = {explanations_json};
        this.pdfViewer = null;
        this.init();
    }}
    
    init() {{
        this.setupPDFViewer();
        this.setupControls();
        this.loadExplanation(this.currentPage);
        this.updateUI();
    }}
    
    setupPDFViewer() {{
        this.pdfViewer = document.querySelector('.pdf-viewer iframe, .pdf-viewer embed');
        if (this.pdfViewer) {{
            // 监听PDF加载完成
            this.pdfViewer.onload = () => {{
                this.detectCurrentPage();
            }};
            
            // 定期检查当前页面（作为备用方案）
            setInterval(() => {{
                this.detectCurrentPage();
            }}, 2000);
        }}
    }}
    
    setupControls() {{
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        const pageInput = document.getElementById('page-input');
        const jumpBtn = document.getElementById('jump-page');
        const wheelToggle = document.getElementById('wheel-toggle');
        const wheelOverlay = document.getElementById('wheel-overlay');
        
        if (prevBtn) {{
            prevBtn.addEventListener('click', () => this.goToPrevPage());
        }}
        
        if (nextBtn) {{
            nextBtn.addEventListener('click', () => this.goToNextPage());
        }}

        if (pageInput && jumpBtn) {{
            jumpBtn.addEventListener('click', () => {{
                const v = parseInt(pageInput.value, 10);
                if (!isNaN(v)) this.goToPage(v);
            }});
            pageInput.addEventListener('keydown', (e) => {{
                if (e.key === 'Enter') {{
                    const v = parseInt(pageInput.value, 10);
                    if (!isNaN(v)) this.goToPage(v);
                }}
            }});
        }}

        // 滚轮切页（使用覆盖层捕获滚轮事件，避免跨域限制）
        if (wheelOverlay) {{
            let lastWheelTs = 0;
            const WHEEL_INTERVAL = 180; // ms
            const onWheel = (e) => {{
                e.preventDefault();
                const now = Date.now();
                if (now - lastWheelTs < WHEEL_INTERVAL) return;
                lastWheelTs = now;
                if (e.deltaY > 0) {{
                    this.goToNextPage();
                }} else if (e.deltaY < 0) {{
                    this.goToPrevPage();
                }}
            }};
            wheelOverlay.addEventListener('wheel', onWheel, {{ passive: false }});

            if (wheelToggle) {{
                const applyToggle = () => {{
                    const enabled = wheelToggle.checked;
                    wheelOverlay.style.display = enabled ? 'block' : 'none';
                }};
                wheelToggle.addEventListener('change', applyToggle);
                applyToggle();
            }}
        }}
    }}
    
    detectCurrentPage() {{
        try {{
            // 尝试从PDF查看器获取当前页面
            let pageNumber = this.currentPage;
            
            // 方法1: 检查URL hash
            if (this.pdfViewer && this.pdfViewer.src) {{
                const hashMatch = this.pdfViewer.src.match(/#page=(\\d+)/);
                if (hashMatch) {{
                    pageNumber = parseInt(hashMatch[1]);
                }}
            }}
            
            // 方法2: 如果是Chrome PDF查看器，尝试从窗口获取页面信息
            if (this.pdfViewer && this.pdfViewer.contentWindow) {{
                try {{
                    const pdfViewer = this.pdfViewer.contentWindow.document.querySelector('.page');
                    if (pdfViewer) {{
                        const pageLabel = pdfViewer.querySelector('.pageNumber');
                        if (pageLabel) {{
                            pageNumber = parseInt(pageLabel.textContent) || pageNumber;
                        }}
                    }}
                }} catch (e) {{
                    // 跨域限制，忽略错误
                }}
            }}
            
            // 更新页面（如果发生变化）
            if (pageNumber !== this.currentPage && pageNumber >= 1 && pageNumber <= this.totalPages) {{
                this.goToPage(pageNumber);
            }}
        }} catch (e) {{
            console.warn('无法检测PDF当前页面:', e);
        }}
    }}
    
    goToPage(pageNumber) {{
        if (pageNumber < 1 || pageNumber > this.totalPages) {{
            return;
        }}
        
        this.currentPage = pageNumber;
        this.updatePDFView();
        this.loadExplanation(pageNumber);
        this.updateUI();
    }}
    
    goToPrevPage() {{
        if (this.currentPage > 1) {{
            this.goToPage(this.currentPage - 1);
        }}
    }}
    
    goToNextPage() {{
        if (this.currentPage < this.totalPages) {{
            this.goToPage(this.currentPage + 1);
        }}
    }}
    
    updatePDFView() {{
        if (this.pdfViewer) {{
            const currentSrc = this.pdfViewer.src;
            const baseUrl = currentSrc.split('#')[0];
            const newSrc = `${{baseUrl}}#page=${{this.currentPage}}`;
            
            if (currentSrc !== newSrc) {{
                this.pdfViewer.src = newSrc;
            }}
        }}
    }}
    
    loadExplanation(pageNumber) {{
        // 隐藏所有讲解页面
        document.querySelectorAll('.explanation-page').forEach(page => {{
            page.classList.remove('active');
        }});
        
        // 显示对应的讲解页面
        const targetPage = document.getElementById(`explanation-page-${{pageNumber}}`);
        if (targetPage) {{
            targetPage.classList.add('active');
        }} else {{
            // 如果没有对应的讲解页面，创建默认页面
            this.createDefaultExplanationPage(pageNumber);
        }}
        
        // 滚动到顶部
        const explanationContent = document.querySelector('.explanation-content');
        if (explanationContent) {{
            explanationContent.scrollTop = 0;
        }}
    }}
    
    createDefaultExplanationPage(pageNumber) {{
        const explanationContent = document.querySelector('.explanation-content');
        if (explanationContent) {{
            // 移除现有的默认页面
            const existingPage = document.getElementById(`explanation-page-${{pageNumber}}`);
            if (existingPage) {{
                existingPage.remove();
            }}
            
            // 创建新的讲解页面
            const pageDiv = document.createElement('div');
            pageDiv.id = `explanation-page-${{pageNumber}}`;
            pageDiv.className = 'explanation-page active';
            
            const explanation = this.explanations[pageNumber] || '暂无讲解内容';
            pageDiv.innerHTML = `
                <h1>第 ${{pageNumber}} 页 讲解</h1>
                <div class="note">
                    <p><strong>注意：</strong> 当前页面暂无详细讲解内容。</p>
                </div>
                ${{explanation ? `<div class="explanation-text">${{this.formatExplanation(explanation)}}</div>` : ''}}
            `;
            
            explanationContent.appendChild(pageDiv);
        }}
    }}
    
    formatExplanation(text) {{
        if (!text) return '';
        
        // 简单的Markdown转HTML（可根据需要扩展）
        return text
            .replace(/\\\\n\\\\n/g, '</p><p>')
            .replace(/\\\\n/g, '<br>')
            .replace(/^/, '<p>')
            .replace(/$/, '</p>');
    }}
    
    updateUI() {{
        // 更新页码显示
        const pageInfo = document.querySelector('.page-info');
        if (pageInfo) {{
            pageInfo.textContent = `${{this.currentPage}} / ${{this.totalPages}}`;
        }}
        
        // 更新按钮状态
        const prevBtn = document.getElementById('prev-page');
        const nextBtn = document.getElementById('next-page');
        
        if (prevBtn) {{
            prevBtn.disabled = this.currentPage <= 1;
        }}
        
        if (nextBtn) {{
            nextBtn.disabled = this.currentPage >= this.totalPages;
        }}
        
        // 更新页面标题
        document.title = `第${{this.currentPage}}页 - PDF讲解`;
    }}
    
    // 键盘导航支持
    setupKeyboardNavigation() {{
        document.addEventListener('keydown', (e) => {{
            switch(e.key) {{
                case 'ArrowLeft':
                case 'ArrowUp':
                    e.preventDefault();
                    this.goToPrevPage();
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                case ' ':
                    e.preventDefault();
                    this.goToNextPage();
                    break;
                case 'Home':
                    e.preventDefault();
                    this.goToPage(1);
                    break;
                case 'End':
                    e.preventDefault();
                    this.goToPage(this.totalPages);
                    break;
            }}
        }});
    }}
}}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {{
    // 移除加载指示器
    const loading = document.querySelector('.loading');
    if (loading) {{
        loading.remove();
    }}
    
    // 初始化同步功能
    window.pdfSync = new PDFExplanationSync();
    
    // 设置键盘导航
    window.pdfSync.setupKeyboardNavigation();
    
    // 处理 URL 参数中的 startPage（用于从目录页跳转时定位）
    try {{
        const params = new URLSearchParams(window.location.search);
        const sp = parseInt(params.get('startPage'), 10);
        if (!isNaN(sp)) {{
            window.pdfSync.goToPage(sp);
            const input = document.getElementById('page-input');
            if (input) input.value = String(sp);
        }}
    }} catch (e) {{}}
    
    console.log('PDF-讲解同步功能已初始化');
}});

// 暴露一些全局方法供外部调用
window.goToPage = function(pageNumber) {{
    if (window.pdfSync) {{
        window.pdfSync.goToPage(pageNumber);
    }}
}};

window.nextPage = function() {{
    if (window.pdfSync) {{
        window.pdfSync.goToNextPage();
    }}
}};

window.prevPage = function() {{
    if (window.pdfSync) {{
        window.pdfSync.goToPrevPage();
    }}
}};
"""
        return js
    
    @staticmethod
    def generate_sync_html(
        pdf_content: str,
        explanations: Dict[int, str],
        total_pages: int = 1,
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_padding: int = 10
    ) -> str:
        """
        生成支持PDF-讲解同步的完整HTML页面
        
        Args:
            pdf_content: PDF文件路径或base64内容
            explanations: 页码到讲解内容的映射
            total_pages: 总页数
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            column_padding: 栏内边距
            
        Returns:
            完整的HTML字符串
        """
        css_styles = EnhancedHTMLGenerator.generate_sync_styles(
            font_name, font_size, line_spacing, column_padding
        )
        
        javascript_code = EnhancedHTMLGenerator.generate_sync_javascript(
            total_pages, explanations
        )
        
        # 生成所有讲解页面的HTML内容
        explanation_pages_html = ""
        for page_num in range(1, total_pages + 1):
            explanation_content = explanations.get(page_num, "")
            
            if not explanation_content:
                explanation_content = f"""
                <div class="note">
                    <p><strong>第{page_num}页暂无讲解内容</strong></p>
                    <p>本页PDF内容较为简单，无需额外解释。如有疑问，请参考相关教材或咨询老师。</p>
                </div>
                """
            else:
                # 简单的Markdown转HTML处理
                explanation_html = explanation_content.replace('\n\n', '</p><p>').replace('\n', '<br>')
                explanation_content = f"<p>{explanation_html}</p>"
            
            explanation_pages_html += f"""
            <div class="explanation-page" id="explanation-page-{page_num}">
                <h1>第 {page_num} 页 讲解</h1>
                {explanation_content}
            </div>
            """
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF讲解 - 第1页</title>
    <style>{css_styles}</style>
</head>
<body>
    <div class="sync-container">
        <!-- PDF显示面板 -->
        <div class="pdf-panel">
            <div class="pdf-viewer">
                <iframe src="{pdf_content}#page=1" 
                        id="pdf-frame"
                        frameborder="0">
                </iframe>
                <div class="wheel-overlay" id="wheel-overlay"></div>
                <div class="loading">正在加载PDF...</div>
            </div>
            
            <!-- PDF控制面板 -->
            <div class="pdf-controls">
                <button id="prev-page" title="上一页 (←)">‹ 上一页</button>
                <span class="page-info">1 / {total_pages}</span>
                <button id="next-page" title="下一页 (→)">下一页 ›</button>
                <label>
                    <input type="checkbox" id="wheel-toggle" checked>
                    滚轮切页
                </label>
                <input type="number" id="page-input" min="1" max="{total_pages}" value="1"/>
                <button id="jump-page" title="输入页码并跳转">跳转</button>
            </div>
        </div>
        
        <!-- 讲解显示面板 -->
        <div class="explanation-panel">
            <div class="explanation-header">
                <h2>📖 页面讲解</h2>
            </div>
            <div class="explanation-content">
                {explanation_pages_html}
            </div>
        </div>
    </div>
    
    <script>
        {javascript_code}
    </script>
</body>
</html>
"""
        return html
    
    @staticmethod
    def create_navigation_html(
        total_pages: int,
        explanations: Dict[int, str],
        pdf_filename: str = "document.pdf",
        font_name: str = "SimHei",
        font_size: int = 14
    ) -> str:
        """创建导航索引页面，包含快速跳转到同步模式"""
        nav_items = ""
        for page_num in range(1, total_pages + 1):
            explanation_content = explanations.get(page_num, "")
            preview = explanation_content[:100] + "..." if len(explanation_content) > 100 else explanation_content
            if not preview:
                preview = "暂无讲解内容"
            
            # 清理预览文本中的HTML标签
            import re
            preview = re.sub(r'<[^>]+>', '', preview)
            
            nav_items += f"""
            <div class="nav-item">
                <div class="nav-content">
                    <h3>第 {page_num} 页</h3>
                    <p>{preview}</p>
                    <button onclick="openSyncMode({page_num})" class="nav-btn">🚀 打开同步模式</button>
                </div>
            </div>
            """
        
        nav_css = f"""
        body {{
            font-family: '{font_name}', 'Microsoft YaHei', 'SimHei', sans-serif;
            font-size: {font_size}pt;
            line-height: 1.4;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 15px;
            font-size: 28pt;
            font-weight: bold;
        }}
        
        .header .subtitle {{
            color: #7f8c8d;
            font-size: 14pt;
            margin-bottom: 20px;
        }}
        
        .sync-btn {{
            background: linear-gradient(45deg, #007bff, #0056b3);
            color: white;
            border: none;
            padding: 15px 30px;
            border-radius: 25px;
            font-size: 16pt;
            font-weight: bold;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(0,123,255,0.3);
        }}
        
        .sync-btn:hover {{
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0,123,255,0.4);
        }}
        
        .nav-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .nav-item {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }}
        
        .nav-item:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }}
        
        .nav-content {{
            padding: 25px;
        }}
        
        .nav-content h3 {{
            color: #2c3e50;
            margin-bottom: 12px;
            font-size: 18pt;
            font-weight: bold;
        }}
        
        .nav-content p {{
            color: #6c757d;
            margin-bottom: 20px;
            line-height: 1.5;
        }}
        
        .nav-btn {{
            background: #28a745;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12pt;
            transition: all 0.2s ease;
            width: 100%;
        }}
        
        .nav-btn:hover {{
            background: #218838;
            transform: translateY(-1px);
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 30px;
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            color: #6c757d;
            backdrop-filter: blur(10px);
        }}
        """
        
        nav_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF讲解文档 - 目录</title>
    <style>{nav_css}</style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📚 PDF讲解文档</h1>
            <p class="subtitle">共 {total_pages} 页 | 点击下方按钮快速跳转到同步模式</p>
            <button class="sync-btn" onclick="openFullSyncMode()">🚀 打开完整同步模式</button>
        </div>
        
        <div class="nav-grid">
            {nav_items}
        </div>
        
        <div class="footer">
            <p>🤖 AI生成讲解 | 📱 支持键盘导航 | 🖨️ 支持打印输出</p>
            <p><small>使用 ← → 方向键或点击按钮切换页面</small></p>
        </div>
    </div>
    
    <script>
        function openSyncMode(pageNumber) {{
            // 在新窗口中打开同步模式，并跳转到指定页面
            const syncWindow = window.open('sync_view.html?startPage=' + pageNumber, '_blank');
            if (syncWindow) {{
                syncWindow.focus();
            }}
        }}
        
        function openFullSyncMode() {{
            // 从第一页开始打开同步模式
            openSyncMode(1);
        }}
        
        // 页面加载完成后的初始化
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('导航页面已加载，共 {total_pages} 页');
        }});
    </script>
</body>
</html>
"""
        return nav_html

    @staticmethod
    def generate_per_page_html(
        page_number: int,
        total_pages: int,
        explanation_content: str,
        pdf_filename: str = "document.pdf",
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        output_folder: str = ""
    ) -> str:
        """
        为单页生成HTML文件，包含完整的导航功能
        
        Args:
            page_number: 当前页面号
            total_pages: 总页数
            explanation_content: 讲解内容
            pdf_filename: PDF文件名
            font_name: 字体名称
            font_size: 字体大小
            line_spacing: 行距倍数
            output_folder: 输出文件夹路径（用于生成相对路径）
            
        Returns:
            生成的HTML文件路径
        """
        # 清理讲解内容中的HTML标签用于导航预览
        import re
        clean_explanation = re.sub(r'<[^>]+>', '', explanation_content)
        clean_explanation = clean_explanation.replace('\n', ' ').replace('\r', ' ')
        
        # 导航按钮状态 - 修复第一页下一页按钮bug
        prev_disabled = "disabled" if page_number == 1 else ""
        next_disabled = "disabled" if page_number >= total_pages else ""
        prev_display = "none" if page_number == 1 else "inline-block"
        next_display = "none" if page_number >= total_pages else "inline-block"
        
        # 构建相对路径：单页HTML与PDF默认在同一输出目录
        if output_folder:
            pdf_path = f"{pdf_filename}"
            base_path = ""
        else:
            pdf_path = pdf_filename
            base_path = ""
        
        # CSS样式
        css = f"""
        /* 单页HTML样式 */
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: '{font_name}', 'Microsoft YaHei', 'SimHei', sans-serif;
            font-size: {font_size}pt;
            line-height: {line_spacing};
            color: #333;
            background-color: #ffffff;
            height: 100vh;
            overflow: hidden;
        }}
        
        .main-container {{
            display: flex;
            height: 100vh;
            width: 100vw;
        }}
        
        /* PDF显示区域 */
        .pdf-section {{
            flex: 1;
            max-width: 50%;
            background: #f8f9fa;
            border-right: 2px solid #e0e0e0;
            display: flex;
            flex-direction: column;
            position: relative;
        }}
        
        .pdf-viewer {{
            flex: 1;
            position: relative;
            overflow: hidden;
        }}
        
        .pdf-viewer embed,
        .pdf-viewer iframe {{
            width: 100%;
            height: 100%;
            border: none;
            background: white;
        }}
        
        /* 讲解显示区域 */
        .explanation-section {{
            flex: 1;
            max-width: 50%;
            background: white;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        
        .explanation-header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .explanation-header h2 {{
            font-size: 18pt;
            font-weight: bold;
            margin: 0;
        }}
        
        .explanation-content {{
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #ffffff;
        }}
        
        .explanation-content h1, 
        .explanation-content h2, 
        .explanation-content h3 {{
            color: #2c3e50;
            margin-bottom: 15px;
        }}
        
        .explanation-content p {{
            margin-bottom: 12px;
            text-align: justify;
        }}
        
        .explanation-content ul, 
        .explanation-content ol {{
            margin-bottom: 15px;
            padding-left: 25px;
        }}
        
        .explanation-content code {{
            background: #f1f2f6;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: 'Consolas', 'Monaco', monospace;
        }}
        
        .explanation-content pre {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            margin: 15px 0;
        }}
        
        /* 导航控制面板 */
        .navigation-panel {{
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(0, 0, 0, 0.85);
            color: white;
            padding: 12px 20px;
            border-radius: 25px;
            display: flex;
            align-items: center;
            gap: 15px;
            z-index: 1000;
            backdrop-filter: blur(10px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }}
        
        .nav-btn {{
            background: #007bff;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 20px;
            cursor: pointer;
            font-size: 12pt;
            font-weight: bold;
            transition: all 0.3s ease;
            text-decoration: none;
            display: {prev_display};
        }}
        
        .nav-btn:hover:not(:disabled) {{
            background: #0056b3;
            transform: translateY(-1px);
        }}
        
        .nav-btn:disabled {{
            background: #6c757d;
            cursor: not-allowed;
            opacity: 0.6;
        }}
        
        .nav-btn.next {{
            background: #28a745;
        }}
        
        .nav-btn.next:hover:not(:disabled) {{
            background: #218838;
        }}
        
        .page-info {{
            color: white;
            font-weight: bold;
            font-size: 14pt;
            min-width: 80px;
            text-align: center;
        }}
        
        .page-jump {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-left: 10px;
        }}
        
        .page-input {{
            width: 60px;
            padding: 4px 8px;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 12pt;
            text-align: center;
        }}
        
        .jump-btn {{
            background: #ffc107;
            color: #212529;
            border: none;
            padding: 4px 8px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 11pt;
            font-weight: bold;
        }}
        
        .jump-btn:hover {{
            background: #e0a800;
        }}
        
        /* 面包屑导航 */
        .breadcrumb {{
            position: absolute;
            top: 10px;
            left: 10px;
            background: rgba(255, 255, 255, 0.9);
            padding: 8px 12px;
            border-radius: 6px;
            font-size: 11pt;
            color: #666;
            z-index: 100;
            backdrop-filter: blur(5px);
        }}
        
        .breadcrumb a {{
            color: #007bff;
            text-decoration: none;
        }}
        
        .breadcrumb a:hover {{
            text-decoration: underline;
        }}
        
        /* 响应式设计 */
        @media (max-width: 768px) {{
            .main-container {{
                flex-direction: column;
            }}
            
            .pdf-section, .explanation-section {{
                max-width: 100%;
                height: 50vh;
            }}
            
            .navigation-panel {{
                position: fixed;
                bottom: 10px;
                left: 10px;
                right: 10px;
                transform: none;
                justify-content: space-between;
            }}
        }}
        """
        
        # JavaScript代码
        javascript = f"""
        // 页面导航功能
        let currentPage = {page_number};
        const totalPages = {total_pages};
        
        // 键盘快捷键支持
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {{
                if (currentPage > 1) {{
                    goToPage(currentPage - 1);
                }}
            }} else if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {{
                if (currentPage < totalPages) {{
                    goToPage(currentPage + 1);
                }}
            }} else if (event.key === 'Home') {{
                goToPage(1);
            }} else if (event.key === 'End') {{
                goToPage(totalPages);
            }}
        }});
        
        // 跳转到指定页面
        function goToPage(pageNumber) {{
            if (pageNumber < 1 || pageNumber > totalPages) {{
                alert(`页面范围: 1 - ${{totalPages}}`);
                return;
            }}
            
            currentPage = pageNumber;
            const pageFileName = `page_${{pageNumber}}.html`;
            window.location.href = pageFileName;
        }}
        
        // 上一页
        function previousPage() {{
            if (currentPage > 1) {{
                goToPage(currentPage - 1);
            }}
        }}
        
        // 下一页
        function nextPage() {{
            if (currentPage < totalPages) {{
                goToPage(currentPage + 1);
            }}
        }}
        
        // 页面跳转输入框
        function jumpToPage() {{
            const pageInput = document.getElementById('pageInput');
            const pageNumber = parseInt(pageInput.value);
            if (!isNaN(pageNumber)) {{
                goToPage(pageNumber);
            }}
        }}
        
        // 回车键跳转
        function handlePageInputKey(event) {{
            if (event.key === 'Enter') {{
                jumpToPage();
            }}
        }}
        
        // 返回主目录
        function goToIndex() {{
            window.location.href = 'index.html';
        }}
        
        // 页面加载完成后的初始化
        document.addEventListener('DOMContentLoaded', function() {{
            console.log(`页面 ${{currentPage}}/${{totalPages}} 已加载`);
            // 聚焦到页面输入框
            const pageInput = document.getElementById('pageInput');
            if (pageInput) {{
                pageInput.focus();
            }}
        }});
        """
        
        # HTML模板
        html_template = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>第 {page_number} 页 / 共 {total_pages} 页 - PDF讲解</title>
    <style>{css}</style>
</head>
<body>
    <!-- 面包屑导航 - 修改为指向第一页 -->
    <div class="breadcrumb">
        <a href="page_1.html">📚 返回第一页</a> 
        > 第 {page_number} 页
    </div>
    
    <div class="main-container">
        <!-- PDF显示区域 -->
        <div class="pdf-section">
            <div class="pdf-viewer">
                <embed src="{pdf_path}#page={page_number}" type="application/pdf" />
                <div class="loading">正在加载PDF...</div>
            </div>
            
            <!-- 导航控制面板 -->
            <div class="navigation-panel">
                <button class="nav-btn" onclick="previousPage()" {prev_disabled}>‹ 上一页</button>
                <span class="page-info">{page_number} / {total_pages}</span>
                <button class="nav-btn next" onclick="nextPage()" {next_disabled}>下一页 ›</button>
                
                <div class="page-jump">
                    <input 
                        type="number" 
                        id="pageInput" 
                        class="page-input" 
                        min="1" 
                        max="{total_pages}" 
                        value="{page_number}"
                        onkeypress="handlePageInputKey(event)"
                    />
                    <button class="jump-btn" onclick="jumpToPage()">跳转</button>
                </div>
            </div>
        </div>
        
        <!-- 讲解显示区域 -->
        <div class="explanation-section">
            <div class="explanation-header">
                <h2>📖 第 {page_number} 页讲解</h2>
            </div>
            <div class="explanation-content">
                {explanation_content}
            </div>
        </div>
    </div>
    
    <script>
        {javascript}
    </script>
</body>
</html>
"""
        return html_template

    @staticmethod
    def generate_complete_per_page_structure(
        explanations: Dict[int, str],
        pdf_filename: str,
        total_pages: int = 1,
        output_dir: str = "per_page_html_output",
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2
    ) -> Dict[str, str]:
        """
        为PDF生成完整的分页HTML结构
        
        Args:
            explanations: 页码到讲解内容的映射
            pdf_filename: PDF文件名
            total_pages: 总页数
            output_dir: 输出目录
            font_name: 字体名称
            font_size: 字体大小
            line_spacing: 行距倍数
            
        Returns:
            包含所有生成文件路径的字典
        """
        import os
        from pathlib import Path
        
        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # 复制PDF文件到输出目录
        pdf_dest_path = output_path / pdf_filename
        try:
            import shutil
            # 假设原PDF文件在同一目录或指定路径
            if os.path.exists(pdf_filename):
                shutil.copy2(pdf_filename, pdf_dest_path)
        except Exception as e:
            print(f"Warning: Cannot copy PDF file: {e}")
        
        # 生成所有页面的HTML文件
        generated_files = {}
        
        for page_num in range(1, total_pages + 1):
            explanation_content = explanations.get(page_num, "暂无讲解内容")
            
            # 渲染Markdown格式的讲解内容为HTML
            explanation_html = EnhancedHTMLGenerator._render_markdown_to_html(explanation_content)
            
            # 生成单页HTML
            html_content = EnhancedHTMLGenerator.generate_per_page_html(
                page_number=page_num,
                total_pages=total_pages,
                explanation_content=explanation_html,
                pdf_filename=pdf_filename,
                font_name=font_name,
                font_size=font_size,
                line_spacing=line_spacing,
                output_folder=str(output_path)
            )
            
            # 保存HTML文件
            page_filename = f"page_{page_num}.html"
            page_path = output_path / page_filename
            
            with open(page_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            generated_files[page_filename] = str(page_path)
            print(f"Generated: {page_filename}")
        
        # 删除index页生成 - 根据用户需求移除
        # index_content = EnhancedHTMLGenerator.create_navigation_html(
        #     total_pages=total_pages,
        #     explanations=explanations,
        #     pdf_filename=pdf_filename,
        #     font_name=font_name,
        #     font_size=font_size
        # )
        # 
        # index_path = output_path / "index.html"
        # with open(index_path, 'w', encoding='utf-8') as f:
        #     f.write(index_content)
        # 
        # generated_files["index.html"] = str(index_path)
        
        print(f"Complete! Generated {total_pages} HTML pages to directory: {output_path}")
        return generated_files

    @staticmethod
    def create_multi_pdf_index(
        pdf_info_list: list,
        output_file: str = "main_index.html"
    ) -> str:
        """
        创建多个PDF的主索引页面
        
        Args:
            pdf_info_list: PDF信息列表，每个元素包含 {name, title, pages, folder}
            output_file: 输出文件名
            
        Returns:
            生成的索引页面路径
        """
        pdf_items = ""
        
        for i, pdf_info in enumerate(pdf_info_list):
            name = pdf_info.get("name", f"PDF_{i+1}")
            title = pdf_info.get("title", name)
            pages = pdf_info.get("pages", 0)
            folder = pdf_info.get("folder", name)
            
            pdf_items += f"""
            <div class="pdf-card">
                <div class="pdf-header">
                    <h2>{title}</h2>
                    <span class="pdf-pages">{pages} 页</span>
                </div>
                <div class="pdf-actions">
                    <a href="{folder}/index.html" class="action-btn primary">📖 开始阅读</a>
                    <a href="{folder}/{folder}.pdf" class="action-btn secondary" download>📄 下载PDF</a>
                </div>
            </div>
            """
        
        index_css = f"""
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'SimHei', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .main-header {{
            text-align: center;
            background: rgba(255, 255, 255, 0.95);
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
        }}
        
        .main-header h1 {{
            color: #2c3e50;
            font-size: 32pt;
            margin-bottom: 15px;
            font-weight: bold;
        }}
        
        .main-header p {{
            color: #7f8c8d;
            font-size: 16pt;
        }}
        
        .pdf-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
            gap: 25px;
            margin-bottom: 40px;
        }}
        
        .pdf-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.1);
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
        }}
        
        .pdf-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.15);
        }}
        
        .pdf-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #f1f2f6;
        }}
        
        .pdf-header h2 {{
            color: #2c3e50;
            font-size: 20pt;
            font-weight: bold;
        }}
        
        .pdf-pages {{
            background: #007bff;
            color: white;
            padding: 5px 12px;
            border-radius: 20px;
            font-size: 12pt;
            font-weight: bold;
        }}
        
        .pdf-actions {{
            display: flex;
            gap: 10px;
        }}
        
        .action-btn {{
            flex: 1;
            padding: 12px 20px;
            border: none;
            border-radius: 8px;
            font-size: 14pt;
            font-weight: bold;
            text-decoration: none;
            text-align: center;
            transition: all 0.3s ease;
            cursor: pointer;
        }}
        
        .action-btn.primary {{
            background: #007bff;
            color: white;
        }}
        
        .action-btn.primary:hover {{
            background: #0056b3;
            transform: translateY(-1px);
        }}
        
        .action-btn.secondary {{
            background: #28a745;
            color: white;
        }}
        
        .action-btn.secondary:hover {{
            background: #218838;
            transform: translateY(-1px);
        }}
        
        .footer {{
            text-align: center;
            background: rgba(255, 255, 255, 0.95);
            padding: 30px;
            border-radius: 15px;
            color: #6c757d;
            backdrop-filter: blur(10px);
        }}
        
        .stats {{
            display: flex;
            justify-content: center;
            gap: 30px;
            margin-bottom: 20px;
        }}
        
        .stat-item {{
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 24pt;
            font-weight: bold;
            color: #007bff;
        }}
        
        .stat-label {{
            font-size: 12pt;
            color: #6c757d;
        }}
        """
        
        stats_info = f"""
        <div class="stats">
            <div class="stat-item">
                <div class="stat-number">{len(pdf_info_list)}</div>
                <div class="stat-label">PDF文档</div>
            </div>
            <div class="stat-item">
                <div class="stat-number">{sum(pdf.get('pages', 0) for pdf in pdf_info_list)}</div>
                <div class="stat-label">总页数</div>
            </div>
        </div>
        """
        
        index_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF讲解文档 - 总目录</title>
    <style>{index_css}</style>
</head>
<body>
    <div class="container">
        <div class="main-header">
            <h1>📚 PDF讲解文档库</h1>
            <p>🤖 AI生成讲解 | 🖱️ 支持鼠标点击 | ⌨️ 支持键盘快捷键 | 🖨️ 支持打印输出</p>
            {stats_info}
        </div>
        
        <div class="pdf-grid">
            {pdf_items}
        </div>
        
        <div class="footer">
            <p><strong>使用说明：</strong></p>
            <p>• 点击"开始阅读"进入PDF的分页浏览模式</p>
            <p>• 使用 ← → 方向键切换页面，输入页码可快速跳转</p>
            <p>• 点击"下载PDF"可获取原始PDF文件</p>
            <p style="margin-top: 15px; font-size: 10pt; color: #999;">
                自动生成时间: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </p>
        </div>
    </div>
    
    <script>
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('主索引页面已加载，共有 {len(pdf_info_list)} 个PDF文档');
        }});
    </script>
</body>
</html>
"""
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(index_html)
        
        return output_file
