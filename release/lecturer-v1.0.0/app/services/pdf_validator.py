from __future__ import annotations

import json
import re
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from .logger import get_logger

logger = get_logger()

def safe_utf8_loads(json_bytes: bytes, source: str = "unknown") -> dict:
    """
    安全地从字节数据加载JSON，处理UTF-8编码问题

    Args:
        json_bytes: JSON文件的字节数据
        source: 数据源描述，用于错误信息

    Returns:
        解析后的JSON数据字典

    Raises:
        json.JSONDecodeError: JSON解析失败
    """
    try:
        # 尝试直接解析
        return json.loads(json_bytes)
    except json.JSONDecodeError:
        # 如果失败，尝试使用UTF-8解码
        try:
            json_str = json_bytes.decode('utf-8')
            return json.loads(json_str)
        except UnicodeDecodeError:
            # 如果UTF-8解码失败，尝试其他常见编码
            for encoding in ['utf-8-sig', 'gbk', 'gb2312', 'latin1']:
                try:
                    json_str = json_bytes.decode(encoding)
                    return json.loads(json_str)
                except (UnicodeDecodeError, json.JSONDecodeError):
                    continue
            # 所有编码都失败，抛出原始错误
            raise json.JSONDecodeError(f"无法使用任何编码解析JSON文件: {source}", json_bytes, 0)


# 判空：去除空白与标点等装饰字符后长度是否小于阈值
_BLANK_RE = re.compile(r"[\s`~!@#$%^&*()\-_=.\[\]{}|;:'\",.<>/?，。？！、·—【】（）《》“”‘’\\]+")

def is_blank_explanation(text: Optional[str], min_chars: int = 10) -> bool:
    if text is None:
        return True
    s = _BLANK_RE.sub("", str(text))
    return len(s.strip()) < min_chars


def validate_pdf_file(pdf_bytes: bytes) -> Tuple[bool, str]:
    """
    验证PDF文件是否有效

    Args:
        pdf_bytes: PDF文件字节数据

    Returns:
        (bool, str): (是否有效, 错误信息)
    """
    doc = None
    try:
        # 尝试打开PDF文件
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")

        # 检查页数
        if doc.page_count == 0:
            return False, "PDF文件没有页面"

        # 检查第一页是否可以正常访问
        try:
            page = doc.load_page(0)
            if page.rect.width <= 0 or page.rect.height <= 0:
                return False, "PDF页面尺寸无效"
        except Exception as e:
            return False, f"无法读取PDF页面: {str(e)}"

        return True, ""

    except Exception as e:
        return False, f"PDF文件无效或已损坏: {str(e)}"
    finally:
        # Ensure document is closed even if error occurs
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def pages_with_blank_explanations(explanations: Dict[int, str], min_chars: int = 10) -> List[int]:
    return [p for p, t in explanations.items() if is_blank_explanation(t, min_chars)]