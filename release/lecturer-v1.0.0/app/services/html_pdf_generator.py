#!/usr/bin/env python3
"""
HTML PDF 生成器
生成包含PDF嵌入和AI讲解的HTML页面，支持分栏布局和续页机制
"""

import math
import uuid
from typing import Dict, List, Optional, Tuple


class HtmlPDFGenerator:
    """HTML PDF页面生成器"""
    
    @staticmethod
    def generate_css_styles(
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_padding: int = 10
    ) -> str:
        """
        生成CSS样式，包含三栏布局和响应式设计
        
        Args:
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            column_padding: 栏内边距
            
        Returns:
            CSS样式字符串
        """
        css = f"""
/* HTML PDF布局样式 */
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
}}

.page-container {{
    width: 100%;
    min-height: 100vh;
    display: flex;
    padding: 20px;
    gap: 20px;
}}

.pdf-section {{
    flex: 1;
    max-width: 33.33%;
    display: flex;
    justify-content: center;
    align-items: flex-start;
    background: #f8f9fa;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 15px;
    position: relative;
}}

.pdf-section embed,
.pdf-section iframe {{
    width: 100%;
    height: 90vh;
    border: none;
    border-radius: 4px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}}

.explanation-section {{
    flex: 2;
    max-width: 66.67%;
    background: white;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    position: relative;
}}

.three-column-layout {{
    column-count: 3;
    column-gap: 20px;
    column-fill: balance;
    height: 90vh;
    overflow-y: auto;
}}

.column {{
    break-inside: avoid;
    padding: 0 {column_padding}px;
}}

.column-1, .column-2, .column-3 {{
    width: 100%;
    display: inline-block;
    vertical-align: top;
}}

.explanation-content {{
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-left: 4px solid #007bff;
    border-radius: 4px;
    break-inside: avoid;
}}

.explanation-content h1,
.explanation-content h2,
.explanation-content h3,
.explanation-content h4,
.explanation-content h5,
.explanation-content h6 {{
    color: #2c3e50;
    margin-bottom: 10px;
    line-height: 1.3;
}}

.explanation-content p {{
    margin-bottom: 10px;
    text-align: justify;
    text-justify: inter-word;
}}

.explanation-content ul,
.explanation-content ol {{
    margin-left: 20px;
    margin-bottom: 10px;
}}

.explanation-content li {{
    margin-bottom: 5px;
}}

.explanation-content code {{
    background: #f1f2f6;
    padding: 2px 4px;
    border-radius: 3px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 0.9em;
}}

.explanation-content pre {{
    background: #f1f2f6;
    padding: 10px;
    border-radius: 4px;
    overflow-x: auto;
    margin: 10px 0;
    break-inside: avoid;
}}

.explanation-content blockquote {{
    border-left: 4px solid #bdc3c7;
    padding-left: 15px;
    margin: 15px 0;
    font-style: italic;
    color: #7f8c8d;
}}

/* 页码指示器 */
.page-indicator {{
    position: fixed;
    top: 20px;
    right: 20px;
    background: #007bff;
    color: white;
    padding: 8px 16px;
    border-radius: 20px;
    font-size: 12pt;
    font-weight: bold;
    z-index: 1000;
}}

/* 续页指示器 */
.continuation-indicator {{
    background: #28a745;
    color: white;
    padding: 4px 8px;
    border-radius: 12px;
    font-size: 10pt;
    margin-bottom: 10px;
    display: inline-block;
}}

/* 打印样式 */
@media print {{
    .page-container {{
        padding: 10px;
        gap: 10px;
    }}
    
    .pdf-section {{
        max-width: 40%;
        border: none;
        background: white;
        padding: 10px;
    }}
    
    .explanation-section {{
        max-width: 60%;
        border: none;
        padding: 10px;
    }}
    
    .three-column-layout {{
        height: auto;
        overflow: visible;
    }}
    
    .page-indicator {{
        position: relative;
        top: auto;
        right: auto;
        margin-bottom: 20px;
    }}
}}

/* 响应式设计 */
@media (max-width: 1024px) {{
    .page-container {{
        flex-direction: column;
        padding: 10px;
    }}
    
    .pdf-section,
    .explanation-section {{
        max-width: 100%;
        width: 100%;
    }}
    
    .three-column-layout {{
        column-count: 2;
        height: auto;
    }}
}}

@media (max-width: 768px) {{
    .three-column-layout {{
        column-count: 1;
    }}
    
    .pdf-section embed,
    .pdf-section iframe {{
        height: 60vh;
    }}
}}
"""
        return css
    
    @staticmethod
    def build_page_html(
        pdf_content: str,
        explanation_content: str,
        page_number: int = 1,
        is_continuation: bool = False,
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_padding: int = 10
    ) -> str:
        """
        构建完整的HTML页面
        
        Args:
            pdf_content: PDF文件路径或base64内容
            explanation_content: AI讲解内容
            page_number: 页码
            is_continuation: 是否为续页
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            column_padding: 栏内边距
            
        Returns:
            完整的HTML字符串
        """
        css_styles = HtmlPDFGenerator.generate_css_styles(
            font_name, font_size, line_spacing, column_padding
        )
        
        page_title = f"第{page_number}页" + ("（续）" if is_continuation else "")
        
        html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - PDF讲解</title>
    <style>{css_styles}</style>
</head>
<body>
    <div class="page-indicator">第 {page_number} 页</div>
    
    <div class="page-container">
        <div class="pdf-section">
            <embed src="{pdf_content}" type="application/pdf" />
        </div>
        
        <div class="explanation-section">
            {f'<div class="continuation-indicator">续页 - 第{page_number}页</div>' if is_continuation else ''}
            <div class="three-column-layout">
                <div class="explanation-content">
                    {explanation_content}
                </div>
            </div>
        </div>
    </div>
</body>
</html>
"""
        return html
    
    @staticmethod
    def split_content_to_columns(
        content: str,
        max_chars_per_column: int = 2000
    ) -> List[str]:
        """
        将讲解内容分割成适合三栏布局的部分
        
        Args:
            content: 原始讲解内容
            max_chars_per_column: 每栏最大字符数
            
        Returns:
            分割后的内容列表
        """
        if not content or len(content) <= max_chars_per_column:
            return [content] if content else []
        
        # 按段落分割
        paragraphs = content.split('\n\n')
        columns = []
        current_column = ""
        
        for paragraph in paragraphs:
            # 如果添加这个段落会超出限制，先保存当前栏
            if current_column and len(current_column + '\n\n' + paragraph) > max_chars_per_column:
                columns.append(current_column.strip())
                current_column = paragraph
            else:
                if current_column:
                    current_column += '\n\n' + paragraph
                else:
                    current_column = paragraph
        
        # 添加最后一栏
        if current_column:
            columns.append(current_column.strip())
        
        return columns
    
    @staticmethod
    def generate_explanation_html(
        explanations: Dict[int, str],
        total_pages: int = 1,
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2,
        column_padding: int = 10,
        max_chars_per_column: int = 2000
    ) -> List[Tuple[str, str]]:
        """
        生成所有页面的HTML文件
        
        Args:
            explanations: 页码到讲解内容的映射
            total_pages: 总页数
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            column_padding: 栏内边距
            max_chars_per_column: 每栏最大字符数
            
        Returns:
            (文件名, HTML内容)的列表
        """
        html_files = []
        
        for page_num in range(1, total_pages + 1):
            explanation_content = explanations.get(page_num, "")
            
            if not explanation_content:
                explanation_content = f"<p>第{page_num}页暂无讲解内容</p>"
            else:
                # 将Markdown内容转换为HTML
                try:
                    import markdown
                    explanation_content = markdown.markdown(explanation_content)
                except ImportError:
                    # 如果没有markdown库，使用简单的HTML转换
                    explanation_content = explanation_content.replace('\n', '<br>')
            
            # 将讲解内容分割成适合三栏的段落
            column_contents = HtmlPDFGenerator.split_content_to_columns(
                explanation_content, max_chars_per_column
            )
            
            if len(column_contents) <= 3:
                # 内容适合一页，直接生成
                html = HtmlPDFGenerator.build_page_html(
                    pdf_content=f"document.pdf#page={page_num}",
                    explanation_content=explanation_content,
                    page_number=page_num,
                    font_name=font_name,
                    font_size=font_size,
                    line_spacing=line_spacing,
                    column_padding=column_padding
                )
                filename = f"page_{page_num}.html"
                html_files.append((filename, html))
            else:
                # 内容过多，需要续页
                # 第一页：PDF + 前三栏内容
                first_page_content = '\n'.join(column_contents[:3])
                html = HtmlPDFGenerator.build_page_html(
                    pdf_content=f"document.pdf#page={page_num}",
                    explanation_content=first_page_content,
                    page_number=page_num,
                    font_name=font_name,
                    font_size=font_size,
                    line_spacing=line_spacing,
                    column_padding=column_padding
                )
                filename = f"page_{page_num}.html"
                html_files.append((filename, html))
                
                # 续页：无PDF，只显示后续内容
                continuation_contents = column_contents[3:]
                for i, continuation_content in enumerate(continuation_contents, 1):
                    html = HtmlPDFGenerator.build_page_html(
                        pdf_content="",  # 续页不显示PDF
                        explanation_content=continuation_content,
                        page_number=page_num,
                        is_continuation=True,
                        font_name=font_name,
                        font_size=font_size,
                        line_spacing=line_spacing,
                        column_padding=column_padding
                    )
                    filename = f"page_{page_num}_continuation_{i}.html"
                    html_files.append((filename, html))
        
        return html_files
    
    @staticmethod
    def create_index_html(
        total_pages: int,
        explanations: Dict[int, str],
        font_name: str = "SimHei",
        font_size: int = 14,
        line_spacing: float = 1.2
    ) -> str:
        """
        创建索引页面，便于导航
        
        Args:
            total_pages: 总页数
            explanations: 页码到讲解内容的映射
            font_name: 字体名称
            font_size: 字号大小
            line_spacing: 行距倍数
            
        Returns:
            索引页面的HTML内容
        """
        # 生成页面导航链接
        nav_links = ""
        for page_num in range(1, total_pages + 1):
            explanation_content = explanations.get(page_num, "")
            preview = explanation_content[:100] + "..." if len(explanation_content) > 100 else explanation_content
            if not preview:
                preview = "暂无讲解内容"
            
            nav_links += f"""
            <div class="nav-item">
                <a href="page_{page_num}.html" class="nav-link">
                    <h3>第 {page_num} 页</h3>
                    <p>{preview}</p>
                </a>
            </div>
            """
        
        index_css = f"""
        body {{
            font-family: '{font_name}', 'Microsoft YaHei', 'SimHei', sans-serif;
            font-size: {font_size}pt;
            line-height: {line_spacing};
            color: #333;
            background-color: #f5f5f5;
            margin: 0;
            padding: 20px;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 40px;
            background: white;
            padding: 30px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        
        .header p {{
            color: #7f8c8d;
            font-size: 0.9em;
        }}
        
        .nav-container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .nav-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .nav-item {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transition: transform 0.2s, box-shadow 0.2s;
        }}
        
        .nav-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0,0,0,0.15);
        }}
        
        .nav-link {{
            display: block;
            padding: 20px;
            text-decoration: none;
            color: inherit;
        }}
        
        .nav-link h3 {{
            color: #2c3e50;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        
        .nav-link p {{
            color: #7f8c8d;
            margin: 0;
            line-height: 1.4;
        }}
        
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding: 20px;
            background: white;
            border-radius: 8px;
            color: #7f8c8d;
        }}
        """
        
        index_html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PDF讲解文档 - 目录</title>
    <style>{index_css}</style>
</head>
<body>
    <div class="nav-container">
        <div class="header">
            <h1>📄 PDF讲解文档</h1>
            <p>共 {total_pages} 页 | 点击下方链接查看各页详细内容</p>
        </div>
        
        <div class="nav-grid">
            {nav_links}
        </div>
        
        <div class="footer">
            <p>🤖 AI生成讲解 | 📱 支持移动端查看 | 🖨️ 支持打印输出</p>
        </div>
    </div>
</body>
</html>
"""
        return index_html
