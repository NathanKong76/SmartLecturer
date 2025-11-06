#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Markdown 生成服务
生成包含页面截图和讲解的 Markdown 文档
"""

import base64
import os
from typing import Optional, Tuple, Dict
from .pdf_composer import _page_png_bytes
from .logger import get_logger
import fitz

logger = get_logger()


def create_page_screenshot_markdown(
    page_num: int,
    screenshot_bytes: bytes,
    explanation: str,
    embed_images: bool = True,
    image_path: Optional[str] = None
) -> str:
    """
    创建单页的 Markdown 内容（包含截图和讲解）
    
    Args:
        page_num: 页码（从1开始）
        screenshot_bytes: 页面截图的 PNG 字节数据
        explanation: 该页的讲解文本
        embed_images: 是否将图片嵌入到 Markdown（base64编码）
        image_path: 外部图片文件的路径（仅在 embed_images=False 时使用）
    
    Returns:
        Markdown 格式的字符串
    """
    markdown_content = f"## 第 {page_num} 页\n\n"
    
    if embed_images:
        # 将图片 base64 编码嵌入到 Markdown
        base64_data = base64.b64encode(screenshot_bytes).decode('utf-8')
        markdown_content += f"![第{page_num}页截图](data:image/png;base64,{base64_data})\n\n"
    else:
        # 使用外部图片路径
        if image_path:
            # 提取文件名（相对于 Markdown 文件，使用文件名即可）
            filename = os.path.basename(image_path)
            markdown_content += f"![第{page_num}页截图]({filename})\n\n"
        else:
            # 如果没有提供路径，使用默认格式
            markdown_content += f"![第{page_num}页截图](page_{page_num}.png)\n\n"
    
    # 添加讲解内容
    if explanation.strip():
        markdown_content += f"{explanation.strip()}\n\n"
    else:
        markdown_content += "*（无讲解内容）*\n\n"
    
    return markdown_content


def generate_markdown_with_screenshots(
    src_bytes: bytes,
    explanations: Dict[int, str],
    screenshot_dpi: int = 150,
    embed_images: bool = True,
    title: str = "PDF文档讲解",
    images_dir: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    生成包含页面截图和讲解的完整 Markdown 文档
    
    Args:
        src_bytes: 源 PDF 文件的字节数据
        explanations: 页码（0-indexed）到讲解文本的字典
        screenshot_dpi: 截图 DPI
        embed_images: 是否将图片嵌入到 Markdown（base64编码）
        title: 文档标题
        images_dir: 外部图片保存目录（仅在 embed_images=False 时使用）
    
    Returns:
        (markdown_content, images_dir) 元组
        - markdown_content: 完整的 Markdown 文档内容
        - images_dir: 如果使用外部图片，返回图片目录路径；否则返回 None
    """
    try:
        # 打开 PDF 文档
        src_doc = fitz.open(stream=src_bytes, filetype="pdf")
        total_pages = src_doc.page_count
        
        # 如果使用外部图片，确保图片目录存在
        actual_images_dir = None
        if not embed_images:
            if images_dir:
                actual_images_dir = images_dir
            else:
                # 如果没有提供目录，创建一个临时目录
                import tempfile
                actual_images_dir = tempfile.mkdtemp(prefix="pdf_images_")
                logger.debug(f"Created temporary images directory: {actual_images_dir}")
            
            os.makedirs(actual_images_dir, exist_ok=True)
            logger.debug(f"Using images directory: {actual_images_dir}")
        
        # 构建 Markdown 文档
        markdown_lines = [f"# {title}\n\n"]
        
        # 遍历每一页
        for page_num in range(total_pages):
            # 获取该页的讲解
            explanation = explanations.get(page_num, "")
            
            # 生成页面截图
            try:
                screenshot_bytes = _page_png_bytes(src_doc, page_num, screenshot_dpi)
            except Exception as e:
                logger.warning(f"Failed to generate screenshot for page {page_num + 1}: {e}")
                # 如果截图失败，仍然添加讲解内容
                markdown_lines.append(f"## 第 {page_num + 1} 页\n\n")
                if explanation.strip():
                    markdown_lines.append(f"{explanation.strip()}\n\n")
                else:
                    markdown_lines.append("*（截图生成失败）*\n\n")
                continue
            
            # 如果使用外部图片，保存图片文件
            image_path = None
            if not embed_images and actual_images_dir:
                image_filename = f"page_{page_num + 1}.png"
                image_path = os.path.join(actual_images_dir, image_filename)
                try:
                    with open(image_path, 'wb') as f:
                        f.write(screenshot_bytes)
                    logger.debug(f"Saved screenshot to: {image_path}")
                except Exception as e:
                    logger.error(f"Failed to save screenshot to {image_path}: {e}")
                    # 如果保存失败，回退到嵌入模式
                    embed_images = True
            
            # 创建该页的 Markdown 内容
            page_markdown = create_page_screenshot_markdown(
                page_num=page_num + 1,
                screenshot_bytes=screenshot_bytes,
                explanation=explanation,
                embed_images=embed_images,
                image_path=image_path
            )
            markdown_lines.append(page_markdown)
        
        # 关闭文档
        src_doc.close()
        
        # 组合完整的 Markdown 内容
        markdown_content = "".join(markdown_lines)
        
        # 返回结果
        return_images_dir = actual_images_dir if not embed_images else None
        logger.info(f"Generated markdown document with {total_pages} pages, embed_images={embed_images}")
        return markdown_content, return_images_dir
        
    except Exception as e:
        logger.error(f"Failed to generate markdown with screenshots: {e}", exc_info=True)
        raise

