from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .pdf_composer import compose_pdf
from .pdf_validator import safe_utf8_loads
from .logger import get_logger

logger = get_logger()


def match_pdf_json_files(pdf_files: List[str], json_files: List[str]) -> Dict[str, Optional[str]]:
    """
    智能匹配PDF文件和JSON文件
    匹配规则：
    1. 移除文件扩展名
    2. 移除常见的序号模式如 (1), (2)等
    3. 完全匹配文件名

    Args:
        pdf_files: PDF文件名列表
        json_files: JSON文件名列表

    Returns:
        字典：PDF文件名 -> 匹配的JSON文件名（如果没有匹配则为None）
    """
    def normalize_filename(filename: str) -> str:
        """标准化文件名用于匹配"""
        # 移除扩展名
        name = filename.rsplit('.', 1)[0] if '.' in filename else filename
        # 移除序号模式如 (1), (2)等
        name = re.sub(r'\s*\(\d+\)\s*$', '', name)
        # 移除多余空格
        name = name.strip()
        return name.lower()

    # 创建标准化名称到原始文件名的映射
    pdf_normalized = {normalize_filename(pdf): pdf for pdf in pdf_files}
    json_normalized = {normalize_filename(json): json for json in json_files}

    # 匹配结果
    matches = {}
    for norm_name, pdf_file in pdf_normalized.items():
        matched_json = json_normalized.get(norm_name)
        matches[pdf_file] = matched_json

    return matches


def batch_recompose_from_json(pdf_files: List[Tuple[str, bytes]], json_files: List[Tuple[str, bytes]],
                            right_ratio: float, font_size: int,
                            font_name: Optional[str] = None,
                            render_mode: str = "text", line_spacing: float = 1.4, column_padding: int = 10) -> Dict[str, Dict]:
    """
    批量根据JSON文件重新合成PDF

    Args:
        pdf_files: [(filename, bytes), ...] PDF文件列表
        json_files: [(filename, bytes), ...] JSON文件列表
        right_ratio: 右侧留白比例
        font_size: 字体大小
        font_name: 字体名称（如 "SimHei"）
        render_mode: 渲染模式
        line_spacing: 行间距

    Returns:
        处理结果字典
    """
    logger.info('开始批量重新合成PDF，PDF文件数: %d, JSON文件数: %d, 字体大小: %d',
                len(pdf_files), len(json_files), font_size)

    # 提取文件名列表用于匹配
    pdf_filenames = [name for name, _ in pdf_files]
    json_filenames = [name for name, _ in json_files]

    logger.debug('PDF文件名列表: %s', pdf_filenames)
    logger.debug('JSON文件名列表: %s', json_filenames)

    # 智能匹配文件
    matches = match_pdf_json_files(pdf_filenames, json_filenames)
    logger.info('文件匹配完成，匹配对数: %d', len(matches))

    # 创建文件名到内容的映射
    pdf_content_map = {name: content for name, content in pdf_files}
    json_content_map = {name: content for name, content in json_files}

    results = {}
    completed_count = 0
    failed_count = 0

    for pdf_filename, matched_json in matches.items():
        logger.debug('处理PDF文件: %s', pdf_filename)

        result = {
            "status": "pending",
            "pdf_bytes": None,
            "explanations": {},
            "error": None
        }

        try:
            pdf_bytes = pdf_content_map[pdf_filename]

            if matched_json is None:
                logger.warning('PDF文件 %s 未找到匹配的JSON文件', pdf_filename)
                result["status"] = "failed"
                result["error"] = "未找到匹配的JSON文件"
                failed_count += 1
            else:
                logger.debug('为PDF文件 %s 找到匹配的JSON文件: %s', pdf_filename, matched_json)
                json_bytes = json_content_map[matched_json]

                # 解析JSON
                try:
                    json_data = safe_utf8_loads(json_bytes, source=matched_json)
                    # 转换键为整数
                    explanations = {int(k): str(v) for k, v in json_data.items()}
                    logger.debug('JSON文件 %s 解析成功，包含 %d 个讲解条目', matched_json, len(explanations))

                    # 重新合成PDF
                    logger.debug('开始重新合成PDF文件: %s', pdf_filename)
                    result_pdf = compose_pdf(
                        pdf_bytes,
                        explanations,
                        right_ratio,
                        font_size,
                        font_name=font_name,
                        render_mode=render_mode,
                        line_spacing=line_spacing,
                        column_padding=column_padding
                    )

                    logger.debug('PDF文件 %s 重新合成成功，大小: %d bytes', pdf_filename, len(result_pdf))
                    result["status"] = "completed"
                    result["pdf_bytes"] = result_pdf
                    result["explanations"] = explanations
                    completed_count += 1

                except json.JSONDecodeError as e:
                    logger.error('JSON文件 %s 解析失败: %s', matched_json, e)
                    result["status"] = "failed"
                    result["error"] = f"JSON解析失败: {str(e)}"
                    failed_count += 1
                except Exception as e:
                    logger.error('PDF文件 %s 合成失败: %s', pdf_filename, e, exc_info=True)
                    result["status"] = "failed"
                    result["error"] = f"PDF合成失败: {str(e)}"
                    failed_count += 1

        except Exception as e:
            logger.error('处理PDF文件 %s 时发生未知错误: %s', pdf_filename, e, exc_info=True)
            result["status"] = "failed"
            result["error"] = f"处理失败: {str(e)}"
            failed_count += 1

        results[pdf_filename] = result

    logger.info('批量重新合成PDF完成，成功: %d, 失败: %d, 总计: %d',
                completed_count, failed_count, len(results))
    return results


async def batch_recompose_from_json_async(pdf_files: List[Tuple[str, bytes]], json_files: List[Tuple[str, bytes]],
                                        right_ratio: float, font_size: int,
                                        font_name: Optional[str] = None,
                                        render_mode: str = "text", line_spacing: float = 1.4, column_padding: int = 10) -> Dict[str, Dict]:
    """
    异步批量根据JSON文件重新合成PDF

    Args:
        pdf_files: [(filename, bytes), ...] PDF文件列表
        json_files: [(filename, bytes), ...] JSON文件列表
        right_ratio: 右侧留白比例
        font_size: 字体大小
        font_name: 字体名称
        render_mode: 渲染模式
        line_spacing: 行间距

    Returns:
        处理结果字典
    """
    logger.info('开始异步批量重新合成PDF，PDF文件数: %d, JSON文件数: %d, 字体大小: %d',
                len(pdf_files), len(json_files), font_size)

    # 提取文件名列表用于匹配
    pdf_filenames = [name for name, _ in pdf_files]
    json_filenames = [name for name, _ in json_files]

    logger.debug('PDF文件名列表: %s', pdf_filenames)
    logger.debug('JSON文件名列表: %s', json_filenames)

    # 智能匹配文件
    matches = match_pdf_json_files(pdf_filenames, json_filenames)
    logger.info('文件匹配完成，匹配对数: %d', len(matches))

    # 创建文件名到内容的映射
    pdf_content_map = {name: content for name, content in pdf_files}
    json_content_map = {name: content for name, content in json_files}

    results = {}
    completed_count = 0
    failed_count = 0

    for pdf_filename, matched_json in matches.items():
        logger.debug('处理PDF文件: %s', pdf_filename)

        result = {
            "status": "pending",
            "pdf_bytes": None,
            "explanations": {},
            "error": None
        }

        try:
            pdf_bytes = pdf_content_map[pdf_filename]

            if matched_json is None:
                logger.warning('PDF文件 %s 未找到匹配的JSON文件', pdf_filename)
                result["status"] = "failed"
                result["error"] = "未找到匹配的JSON文件"
                failed_count += 1
            else:
                logger.debug('为PDF文件 %s 找到匹配的JSON文件: %s', pdf_filename, matched_json)
                json_bytes = json_content_map[matched_json]

                # 解析JSON
                try:
                    json_data = safe_utf8_loads(json_bytes, source=matched_json)
                    # 转换键为整数
                    explanations = {int(k): str(v) for k, v in json_data.items()}
                    logger.debug('JSON文件 %s 解析成功，包含 %d 个讲解条目', matched_json, len(explanations))

                    # 重新合成PDF
                    logger.debug('开始重新合成PDF文件: %s', pdf_filename)
                    result_pdf = compose_pdf(
                        pdf_bytes,
                        explanations,
                        right_ratio,
                        font_size,
                        font_name=font_name,
                        render_mode=render_mode,
                        line_spacing=line_spacing,
                        column_padding=column_padding
                    )

                    logger.debug('PDF文件 %s 重新合成成功，大小: %d bytes', pdf_filename, len(result_pdf))
                    result["status"] = "completed"
                    result["pdf_bytes"] = result_pdf
                    result["explanations"] = explanations
                    completed_count += 1

                except json.JSONDecodeError as e:
                    logger.error('JSON文件 %s 解析失败: %s', matched_json, e)
                    result["status"] = "failed"
                    result["error"] = f"JSON解析失败: {str(e)}"
                    failed_count += 1
                except Exception as e:
                    logger.error('PDF文件 %s 合成失败: %s', pdf_filename, e, exc_info=True)
                    result["status"] = "failed"
                    result["error"] = f"PDF合成失败: {str(e)}"
                    failed_count += 1

        except Exception as e:
            logger.error('处理PDF文件 %s 时发生未知错误: %s', pdf_filename, e, exc_info=True)
            result["status"] = "failed"
            result["error"] = f"处理失败: {str(e)}"
            failed_count += 1

        results[pdf_filename] = result

    logger.info('异步批量重新合成PDF完成，成功: %d, 失败: %d, 总计: %d',
                completed_count, failed_count, len(results))
    return results