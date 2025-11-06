#!/usr/bin/env python3
"""
批量重新生成服务
根据JSON数据重新生成PDF/Markdown/HTML，支持三种输出格式
"""

import os
import io
import json
import zipfile
import tempfile
import shutil
from typing import Dict, List, Tuple, Optional, Any
from pathlib import Path

import fitz

from app.services.enhanced_html_generator import EnhancedHTMLGenerator


class BatchRegenerationService:
    """批量重新生成服务类"""
    
    @staticmethod
    def match_pdf_json_files(pdf_names: List[str], json_names: List[str]) -> Dict[str, Optional[str]]:
        """
        智能匹配PDF和JSON文件
        基于文件名匹配，返回 {pdf_name: json_name or None}
        """
        matches = {}
        
        for pdf_name in pdf_names:
            pdf_base = os.path.splitext(pdf_name)[0]
            matched_json = None
            
            # 优先查找完全匹配（基础名称.json）
            for json_name in json_names:
                if os.path.splitext(json_name)[0] == pdf_base:
                    matched_json = json_name
                    break
            
            # 如果没有完全匹配，查找包含关系的
            if not matched_json:
                for json_name in json_names:
                    json_base = os.path.splitext(json_name)[0]
                    if pdf_base in json_base or json_base in pdf_base:
                        matched_json = json_name
                        break
            
            matches[pdf_name] = matched_json
        
        return matches
    
    @staticmethod
    def regenerate_pdf_batch(
        pdf_json_pairs: List[Tuple[bytes, bytes, str]],
        output_mode: str = "PDF讲解版",
        params: Dict[str, Any] = None
    ) -> Dict[str, Dict[str, Any]]:
        """
        批量重新生成PDF/Markdown/HTML
        
        Args:
            pdf_json_pairs: [(pdf_bytes, json_bytes, pdf_name), ...]
            output_mode: 输出模式
            params: 生成参数
            
        Returns:
            {pdf_name: result_dict}
        """
        results = {}
        params = params or {}
        
        if output_mode == "分页HTML版":
            return BatchRegenerationService._regenerate_per_page_html_batch(pdf_json_pairs, params)
        elif output_mode == "Markdown截图讲解":
            return BatchRegenerationService._regenerate_markdown_batch(pdf_json_pairs, params)
        else:
            return BatchRegenerationService._regenerate_pdf_batch(pdf_json_pairs, params)
    
    @staticmethod
    def _regenerate_per_page_html_batch(
        pdf_json_pairs: List[Tuple[bytes, bytes, str]], 
        params: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """批量重新生成分页HTML版"""
        results = {}
        
        for pdf_bytes, json_bytes, pdf_name in pdf_json_pairs:
            try:
                # 解析JSON数据
                explanations_data = json.loads(json_bytes.decode('utf-8'))
                explanations = {int(k): str(v) for k, v in explanations_data.items()}
                
                # 获取PDF总页数
                with fitz.open(stream=pdf_bytes, filetype="pdf") as pdf_doc:
                    total_pages = pdf_doc.page_count
                
                # 创建临时目录
                base_name = os.path.splitext(pdf_name)[0]
                temp_dir = tempfile.mkdtemp(prefix=f"regenerate_{base_name}_")
                
                try:
                    # 生成完整的分页HTML结构
                    generated_files = EnhancedHTMLGenerator.generate_complete_per_page_structure(
                        explanations=explanations,
                        pdf_filename=base_name + ".pdf",
                        total_pages=total_pages,
                        output_dir=temp_dir,
                        font_name=params.get("html_font_name", "SimHei"),
                        font_size=params.get("html_font_size", 14),
                        line_spacing=params.get("html_line_spacing", 1.2)
                    )
                    
                    # 复制PDF文件到同一目录
                    pdf_dest_path = os.path.join(temp_dir, base_name + ".pdf")
                    with open(pdf_dest_path, 'wb') as f:
                        f.write(pdf_bytes)
                    
                    # 创建解压后的文件结构到ZIP
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        # 将临时目录中的所有文件添加到ZIP，保持文件夹结构
                        for root, dirs, files in os.walk(temp_dir):
                            for file in files:
                                file_path = os.path.join(root, file)
                                # 计算相对路径并保持结构
                                arc_name = os.path.relpath(file_path, temp_dir)
                                zip_file.write(file_path, arc_name)
                    
                    zip_buffer.seek(0)
                    
                    results[pdf_name] = {
                        "status": "completed",
                        "zip_bytes": zip_buffer.getvalue(),
                        "explanations": explanations,
                        "pdf_bytes": pdf_bytes,
                        "generated_files": generated_files,
                        "total_pages": total_pages
                    }
                    
                finally:
                    # 清理临时目录
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir, ignore_errors=True)
                        
            except Exception as e:
                results[pdf_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    @staticmethod
    def _regenerate_markdown_batch(
        pdf_json_pairs: List[Tuple[bytes, bytes, str]], 
        params: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """批量重新生成Markdown版"""
        from app.services.pdf_processor import PDFProcessor
        
        results = {}
        
        for pdf_bytes, json_bytes, pdf_name in pdf_json_pairs:
            try:
                # 解析JSON数据
                explanations_data = json.loads(json_bytes.decode('utf-8'))
                explanations = {int(k): str(v) for k, v in explanations_data.items()}
                
                # 创建临时图片目录
                base_name = os.path.splitext(pdf_name)[0]
                embed_images = params.get("embed_images", True)
                images_dir = None
                
                if not embed_images:
                    images_dir = tempfile.mkdtemp(prefix=f"{base_name}_images_")
                
                # 生成Markdown文档
                markdown_content, images_dir_return = PDFProcessor.generate_markdown_with_screenshots(
                    src_bytes=pdf_bytes,
                    explanations=explanations,
                    screenshot_dpi=params.get("screenshot_dpi", 150),
                    embed_images=embed_images,
                    title=params.get("markdown_title", "PDF文档讲解"),
                    images_dir=images_dir
                )
                
                results[pdf_name] = {
                    "status": "completed",
                    "markdown_content": markdown_content,
                    "explanations": explanations,
                    "images_dir": images_dir_return
                }
                
                # 清理临时目录
                if images_dir and os.path.exists(images_dir):
                    shutil.rmtree(images_dir, ignore_errors=True)
                    
            except Exception as e:
                results[pdf_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    @staticmethod
    def _regenerate_pdf_batch(
        pdf_json_pairs: List[Tuple[bytes, bytes, str]], 
        params: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """批量重新生成PDF版"""
        from app.services.pdf_processor import PDFProcessor
        
        results = {}
        
        for pdf_bytes, json_bytes, pdf_name in pdf_json_pairs:
            try:
                # 解析JSON数据
                explanations_data = json.loads(json_bytes.decode('utf-8'))
                explanations = {int(k): str(v) for k, v in explanations_data.items()}
                
                # 重新合成PDF
                result_bytes = PDFProcessor.compose_pdf(
                    src_bytes=pdf_bytes,
                    explanations=explanations,
                    right_ratio=params.get("right_ratio", 0.48),
                    font_size=params.get("font_size", 20),
                    font_name=params.get("cjk_font_name", "SimHei"),
                    render_mode=params.get("render_mode", "markdown"),
                    line_spacing=params.get("line_spacing", 1.2),
                    column_padding=params.get("column_padding", 10)
                )
                
                results[pdf_name] = {
                    "status": "completed",
                    "pdf_bytes": result_bytes,
                    "explanations": explanations
                }
                
            except Exception as e:
                results[pdf_name] = {
                    "status": "failed",
                    "error": str(e)
                }
        
        return results
    
    @staticmethod
    def create_flattened_zip_for_per_page_html(
        batch_results: Dict[str, Dict[str, Any]],
        output_filename: str = "batch_per_page_html.zip"
    ) -> bytes:
        """
        为分页HTML版创建扁平化的ZIP文件，避免嵌套压缩包
        
        Args:
            batch_results: 批量处理结果
            output_filename: 输出文件名
            
        Returns:
            ZIP文件的字节数据
        """
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, result in batch_results.items():
                if result["status"] == "completed" and result.get("zip_bytes"):
                    base_name = os.path.splitext(filename)[0]
                    
                    try:
                        # 创建临时目录来解包
                        temp_dir = tempfile.mkdtemp()
                        
                        with zipfile.ZipFile(io.BytesIO(result["zip_bytes"]), 'r') as inner_zip:
                            # 先解包到临时目录
                            inner_zip.extractall(temp_dir)
                            
                            # 重新组织文件结构，避免嵌套压缩包
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    # 计算相对路径
                                    rel_path = os.path.relpath(file_path, temp_dir)
                                    
                                    # 将每个PDF的文件放在单独的子文件夹中，避免冲突
                                    # 格式：PDF文件名/子文件夹/文件名
                                    arc_name = f"{base_name}/{rel_path}"
                                    zip_file.write(file_path, arc_name)
                            
                            # 清理临时目录
                            shutil.rmtree(temp_dir, ignore_errors=True)
                            
                    except Exception as e:
                        print(f"处理文件 {filename} 时出错: {e}")
                        # 如果解压失败，尝试直接复制（可能已经是扁平结构）
                        try:
                            zip_file.writestr(f"{base_name}/error.txt", f"处理此PDF时出错: {e}")
                        except:
                            pass
            
            # 添加JSON文件到json子目录（便于复现）
            for filename, result in batch_results.items():
                if result["status"] == "completed" and result.get("explanations"):
                    base_name = os.path.splitext(filename)[0]
                    try:
                        json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
                        json_filename = f"json/{base_name}.json"
                        zip_file.writestr(json_filename, json_bytes)
                    except Exception:
                        pass
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
    
    @staticmethod
    def create_zip_for_other_modes(
        batch_results: Dict[str, Dict[str, Any]],
        output_mode: str,
        output_filename: str = None
    ) -> bytes:
        """
        为其他模式创建ZIP文件
        
        Args:
            batch_results: 批量处理结果
            output_mode: 输出模式
            output_filename: 输出文件名
            
        Returns:
            ZIP文件的字节数据
        """
        if not output_filename:
            if output_mode == "Markdown截图讲解":
                output_filename = "batch_markdown_docs.zip"
            elif output_mode == "PDF讲解版":
                output_filename = "batch_pdf_docs.zip"
            else:
                output_filename = "batch_docs.zip"
        
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            if output_mode == "Markdown截图讲解":
                for filename, result in batch_results.items():
                    if result["status"] == "completed" and result.get("markdown_content"):
                        base_name = os.path.splitext(filename)[0]
                        markdown_filename = f"{base_name}讲解文档.md"
                        zip_file.writestr(markdown_filename, result["markdown_content"])
                        
                        # 添加JSON到json子目录
                        if result.get("explanations"):
                            try:
                                json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
                                json_filename = f"json/{base_name}.json"
                                zip_file.writestr(json_filename, json_bytes)
                            except Exception:
                                pass
                        
                        # 添加图片文件夹
                        images_dir = result.get("images_dir")
                        if images_dir and os.path.exists(images_dir):
                            for img_file in os.listdir(images_dir):
                                img_path = os.path.join(images_dir, img_file)
                                if os.path.isfile(img_path):
                                    zip_img_path = f"{base_name}_images/{img_file}"
                                    zip_file.write(img_path, zip_img_path)
            
            elif output_mode == "PDF讲解版":
                for filename, result in batch_results.items():
                    if result["status"] == "completed" and result.get("pdf_bytes"):
                        base_name = os.path.splitext(filename)[0]
                        new_filename = f"{base_name}讲解版.pdf"
                        zip_file.writestr(new_filename, result["pdf_bytes"])
                        
                        # 添加JSON到json子目录
                        if result.get("explanations"):
                            try:
                                json_bytes = json.dumps(result["explanations"], ensure_ascii=False, indent=2).encode("utf-8")
                                json_filename = f"json/{base_name}.json"
                                zip_file.writestr(json_filename, json_bytes)
                            except Exception:
                                pass
        
        zip_buffer.seek(0)
        return zip_buffer.getvalue()
