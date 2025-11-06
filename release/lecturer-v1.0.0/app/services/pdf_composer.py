from __future__ import annotations

import io
import os
from contextlib import contextmanager
from typing import Dict, Iterator, List, Optional, Tuple

import fitz  # PyMuPDF
from PIL import Image
from markdown import markdown

from .text_layout import _smart_text_layout
from .logger import get_logger
from .pandoc_pdf_generator import PandocPDFGenerator
from . import constants
from .validators import validate_compose_params

logger = get_logger()


@contextmanager
def open_pdf_document(pdf_bytes: bytes, filetype: str = "pdf") -> Iterator[fitz.Document]:
    """
    Context manager for safely opening PDF documents.
    
    Args:
        pdf_bytes: PDF file bytes
        filetype: File type (default: "pdf")
        
    Yields:
        Opened PDF document
        
    Example:
        with open_pdf_document(pdf_bytes) as doc:
            # Use doc here
            pass
    """
    doc = None
    try:
        doc = fitz.open(stream=pdf_bytes, filetype=filetype)
        yield doc
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception as e:
                logger.warning(f"Error closing PDF document: {e}")


def _page_png_bytes(doc: fitz.Document, pno: int, dpi: int) -> bytes:
    """
    Convert PDF page to PNG bytes.
    
    Args:
        doc: PyMuPDF document
        pno: Page number (0-indexed)
        dpi: Resolution in DPI
        
    Returns:
        PNG image bytes
    """
    page = doc.load_page(pno)
    mat = fitz.Matrix(dpi / 72.0, dpi / 72.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    try:
        png_bytes = pix.tobytes("png")
        return png_bytes
    finally:
        # Clean up pixmap to free memory
        try:
            del pix
        except Exception:
            pass


def _compose_vector(dst_doc: fitz.Document, src_doc: fitz.Document, pno: int,
                    right_ratio: float, font_size: int, explanation: str,
                    font_name: Optional[str] = None,
                    render_mode: str = "text", line_spacing: float = 1.4, column_padding: int = 10) -> None:
    spage = src_doc.load_page(pno)
    w, h = spage.rect.width, spage.rect.height

    # Normalize rotation so layout calculation always works in page coordinates
    rotation = spage.rotation
    if rotation != 0:
        original_rotation = rotation
        spage.set_rotation(0)
        w, h = spage.rect.width, spage.rect.height

    new_w, new_h = int(w * constants.PDF_WIDTH_MULTIPLIER), h
    dpage = dst_doc.new_page(width=new_w, height=new_h)
    dpage.show_pdf_page(fitz.Rect(0, 0, w, h), src_doc, pno)

    if rotation != 0:
        spage.set_rotation(original_rotation)

    if render_mode == "empty_right":
        return

    # Try to use pandoc to generate explanation PDF
    explanation_text = explanation or ""
    # 使用 Pandoc 生成 PDF（markdown 和 pandoc 模式都使用）
    if explanation_text.strip() and render_mode in ("markdown", "pandoc"):
        margin_x, margin_y = constants.DEFAULT_MARGIN_X_PT, constants.DEFAULT_MARGIN_Y_PT
        right_start = w + margin_x
        right_end = new_w - margin_x
        available_width = max(right_end - right_start, 1)
        
        # Calculate explanation area dimensions
        expl_width_pt = available_width
        expl_height_pt = h - 2 * margin_y
        
        # Try to generate PDF using pandoc
        # 将字体名称转换为 LaTeX 字体名称
        latex_font_name = None
        if font_name:
            from app.services.font_helper import get_latex_font_name
            latex_font_name = get_latex_font_name(font_name)
        
        pdf_bytes, success = PandocPDFGenerator.generate_pdf(
            markdown_content=explanation_text,
            width_pt=expl_width_pt,
            height_pt=expl_height_pt,
            font_name=latex_font_name,
            font_size=font_size,
            line_spacing=line_spacing,
            column_padding=column_padding
        )
        
        if success and pdf_bytes:
            expl_doc = None
            try:
                # Open the generated PDF
                expl_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                expl_page_count = expl_doc.page_count
                
                # Merge explanation pages
                for expl_page_idx in range(expl_page_count):
                    if expl_page_idx > 0:
                        # Create continuation page
                        cont_page = dst_doc.new_page(width=new_w, height=new_h)
                        # Show original PDF on left
                        cont_page.show_pdf_page(fitz.Rect(0, 0, w, h), src_doc, pno)
                        dpage = cont_page
                    else:
                        # Use the last page (which was just created)
                        dpage = dst_doc[-1]
                    
                    # Calculate target rectangle for explanation (right side)
                    target_rect = fitz.Rect(right_start, margin_y, right_end, h - margin_y)
                    
                    # Show explanation page on right side
                    dpage.show_pdf_page(target_rect, expl_doc, expl_page_idx)
                
                expl_doc.close()
                logger.info(f"Page {pno + 1}: Successfully merged {expl_page_count} explanation page(s) using pandoc")
                return
            except Exception as e:
                if render_mode == "pandoc":
                    # pandoc 模式下，如果失败则报错，不回退
                    logger.error(f"Page {pno + 1}: Pandoc PDF generation failed in pandoc mode: {e}")
                    raise
                else:
                    # markdown 模式下，失败则回退到默认方法
                    logger.warning(f"Page {pno + 1}: Failed to merge pandoc PDF, falling back to default method: {e}")
                    if expl_doc:
                        try:
                            expl_doc.close()
                        except Exception:
                            pass
                    # Fall through to default method
        else:
            if render_mode == "pandoc":
                # pandoc 模式下，如果不可用则报错，提供更详细的错误信息
                error_details = []
                if not success:
                    error_details.append("Pandoc PDF generation returned failure")
                if not pdf_bytes:
                    error_details.append("No PDF bytes generated")
                
                # 获取详细的错误信息
                last_error = PandocPDFGenerator.get_last_error()
                if last_error:
                    error_details.append(f"Details: {last_error}")
                
                error_msg = f"Page {pno + 1}: Pandoc PDF generation failed or unavailable in pandoc mode"
                if error_details:
                    error_msg += f" - {', '.join(error_details)}"
                
                logger.error(error_msg)
                logger.error(f"Page {pno + 1}: Check logs for detailed error information")
                
                # 抛出包含详细信息的错误
                raise RuntimeError(error_msg)
            else:
                logger.debug(f"Page {pno + 1}: Pandoc PDF generation failed or unavailable, using default method")

    # Default method: use existing textbox/htmlbox approach
    margin_x, margin_y = constants.DEFAULT_MARGIN_X_PT, constants.DEFAULT_MARGIN_Y_PT
    right_start = w + margin_x
    right_end = new_w - margin_x
    available_width = max(right_end - right_start, 1)
    column_spacing = constants.COLUMN_SPACING_PT
    max_columns = constants.MAX_COLUMNS

    # 将字体名称转换为字体文件路径（用于 PyMuPDF）
    fontname = "china"
    fontfile = None
    font_available = False

    if font_name:
        from app.services.font_helper import get_font_file_path
        font_path = get_font_file_path(font_name)
        if font_path:
            import os
            try:
                if os.path.exists(font_path) and os.access(font_path, os.R_OK):
                    fontfile = font_path
                    font_available = True
                else:
                    logger.warning(f"字体文件不存在或不可读: {font_path}，将使用默认字体")
            except Exception as e:
                logger.warning(f"字体文件验证失败: {e}，将使用默认字体")
        else:
            logger.warning(f"无法找到字体 {font_name} 的文件路径，将使用默认字体")
    else:
        logger.debug("未指定字体名称，将使用默认字体")

    if not font_available:
        fontname = "helv"
        fontfile = None

    initial_text = explanation or ""
    # Validate font_size and line_spacing
    if font_size <= 0:
        logger.warning(f"Invalid font_size in _compose_vector: {font_size}, using default 12")
        font_size = 12
    if line_spacing <= 0:
        logger.warning(f"Invalid line_spacing in _compose_vector: {line_spacing}, using default 1.4")
        line_spacing = 1.4
    
    line_height = font_size * max(1.0, line_spacing)
    # Calculate actual_line_height for overflow calculations (used in HTML rendering check)
    actual_line_height = font_size * max(1.0, line_spacing)
    if render_mode in ("markdown", "pandoc"):
        actual_line_height *= 1.1  # Add 10% buffer for markdown/pandoc elements
    
    # Ensure actual_line_height is positive to avoid division by zero
    actual_line_height = max(actual_line_height, font_size * 0.5) if font_size > 0 else 1.0
    
    # Optimized bottom_safe: reduced from 16-36px to 8-20px for markdown/pandoc mode
    # Text mode uses minimal safe margin (half line height) to maximize usable space
    if render_mode in ("markdown", "pandoc"):
        # Markdown needs some space for potential table/list overflow
        bottom_core = int(line_height * 0.8)
        bottom_safe = min(max(8, bottom_core), 20)  # Reduced from 16-36 to 8-20
    else:
        # Text mode: use minimal margin (half line height)
        bottom_safe = max(int(line_height * 0.5), 4)
    
    # Optimized internal margins: reduce excessive padding
    # Left margin: enough for readability but not excessive
    left_internal_margin = max(column_padding, int(font_size * 1.2))  # Reduced from 1.6
    # Right margin: minimal, just for spacing
    right_internal_margin = max(column_padding, int(font_size * 0.6))  # Reduced from 0.8
    
    total_spacing = column_spacing * (max_columns - 1)
    column_width = max(1.0, (available_width - total_spacing) / max(max_columns, 1))

    def build_rects(count: int, top_offset: float = 0.0):
        if count <= 0:
            return []
        top = margin_y + top_offset
        # Reduced the extra -2 offset, use bottom_safe only
        bottom = new_h - margin_y - bottom_safe
        if bottom <= top:
            # Ensure minimum rect height (at least 3 lines)
            bottom = top + max(line_height * 3, font_size * 3)
        rects = []
        for idx in range(count):
            x_left = right_start + idx * (column_width + column_spacing)
            x_right = x_left + column_width
            x0 = x_left + left_internal_margin
            x1 = min(x_right, right_end) - right_internal_margin
            if x1 <= x0:
                # Ensure minimum width for at least one character
                x1 = x0 + max(font_size, 20)  # Increased from 0.75 * font_size
            rects.append(fitz.Rect(x0, top, x1, bottom))
        return rects

    def estimated_capacity(rects):
        total = 0
        # ENHANCED: Use same improved estimation as _smart_text_layout with better safety
        char_width_factor = 0.55 if fontname != "helv" else 0.45  # Reduced from 0.65/0.5 to match _smart_text_layout
        actual_line_height = font_size * max(1.0, line_spacing)
        if render_mode in ("markdown", "pandoc"):
            actual_line_height *= 1.15  # Increased from 1.1 to match _smart_text_layout

        char_width_divisor = font_size * char_width_factor

        for rect in rects:
            rect_width = max(rect.width, 1)
            rect_height = max(rect.height, 1)

            if char_width_divisor > 0:
                chars_per_line = max(int(rect_width / char_width_divisor), 1)
            else:
                chars_per_line = 1  # Fallback if font_size is 0

            if actual_line_height > 0:
                lines = max(int(rect_height / actual_line_height), 1)
            else:
                lines = 1  # Fallback if line height is invalid

            # OPTIMIZED: Use the same adaptive logic as _smart_text_layout
            rect_capacity = chars_per_line * lines * 0.5
            if rect_capacity < 50:
                # For small spaces, be less conservative
                total += max(int(chars_per_line * lines * 0.7), 1)
            else:
                total += int(rect_capacity)

        return total

    effective_length = len(initial_text.strip()) or len(initial_text)
    column_count = max_columns
    all_rects = build_rects(max_columns)

    # ENHANCED: More conservative column count selection with better safety
    for num_columns in range(1, max_columns + 1):
        capacity = estimated_capacity(all_rects[:num_columns])
        # ENHANCED: Much more conservative fudge factor: 0.5 for markdown/pandoc, 0.6 for text (reduced from 0.65/0.75)
        fudge = 0.5 if render_mode in ("markdown", "pandoc") else 0.6
        if effective_length <= capacity * fudge:
            column_count = num_columns
            break

    # ADDITIONAL SAFETY: Even if we found a column count, ensure we have enough capacity
    # If text is very long, consider adding one more column for safety
    final_capacity = estimated_capacity(all_rects[:column_count])
    if effective_length > final_capacity * 0.8 and column_count < max_columns:  # If already at 80% of capacity
        column_count += 1
        logger.debug(f"Page {pno + 1}: Added extra column for safety, text length {effective_length}, capacity {final_capacity}")

    column_rects = all_rects[:column_count]

    text_parts = _smart_text_layout(initial_text, column_rects, font_size, fontfile, fontname, render_mode, line_spacing)

    # Process overflow for each column
    leftovers = []
    for rect, text_part in zip(column_rects, text_parts):
        if not text_part.strip():
            leftovers.append("")
            continue

        if render_mode == "markdown":
            try:
                import re as _re

                def protect_latex(s: str) -> str:
                    s = _re.sub(r"\$\$(.+?)\$\$", r"\n```\n\\1\n```\n", s, flags=_re.S)
                    s = _re.sub(r"\$(.+?)\$", r"`\\1`", s, flags=_re.S)
                    return s

                md_text = protect_latex(text_part)
                html = markdown(md_text, extensions=["fenced_code", "tables", "toc", "codehilite"])
                css = f"""
                /* base reset */
                body {{ font-size: {font_size}pt; line-height: {line_spacing}; font-family: 'SimHei','Noto Sans SC','Microsoft YaHei',sans-serif; color: #000000; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; white-space: normal; }}
                pre, code {{ font-family: 'Consolas','Fira Code',monospace; font-size: {max(8, font_size-1)}pt; color: #000000; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ccc; padding: 2pt 4pt; color: #000000; }}
                body, p, h1, h2, h3, h4, h5, h6, ul, ol, pre, table {{ margin: 0; padding: 0; color: #000000; }}
                ul, ol {{ padding-left: 0; list-style-position: inside; }}
                p {{ margin-bottom: 1pt; }}
                """
                
                # Insert HTML - use conservative approach since insert_htmlbox doesn't return overflow
                # CRITICAL FIX: Completely remove max-height constraint to allow full content rendering
                # PyMuPDF may clip content even with overflow:visible if max-height is set
                # Render everything and detect overflow afterward
                constrained_html = html
                
                try:
                    dpage.insert_htmlbox(rect, constrained_html, css=css)
                    
                    # Post-render check: verify if text actually fits by checking rendered blocks
                    # Get text blocks that might belong to this column
                    # Note: get_text("blocks") returns blocks from the entire page, so we need to filter carefully
                    page_blocks = []
                    try:
                        page_blocks = dpage.get_text("blocks")
                    except Exception as e:
                        # If get_text fails, log warning and use conservative overflow detection
                        logger.warning(f"get_text('blocks') failed for page {pno + 1}, using conservative overflow detection: {e}")
                        # More conservative: if detection fails, estimate based on capacity
                        # Check if text length suggests overflow risk
                        char_width_factor = 0.65 if fontname != "helv" else 0.5
                        # Enhanced safety checks for division
                        font_width_product = font_size * char_width_factor
                        if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                            estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.65)
                        else:
                            estimated_capacity_chars = 0
                        # CRITICAL FIX: More aggressive overflow detection when get_text fails
                        # If text length exceeds estimated capacity by ANY amount, assume overflow
                        # Use lower threshold (1.0 instead of 1.05) and higher overflow ratio
                        if estimated_capacity_chars > 0 and len(text_part) > estimated_capacity_chars * 1.0:
                            # Text exceeds estimated capacity, assume overflow (more conservative)
                            overflow_ratio = min((len(text_part) - estimated_capacity_chars * 0.9) / len(text_part), 0.5)  # Increased from 0.4 to 0.5
                            overflow_chars = int(len(text_part) * overflow_ratio)
                            if overflow_chars > 0 and overflow_chars < len(text_part):
                                # Try to preserve word boundaries
                                overflow_text = text_part[-overflow_chars:]
                                boundary_adjust = min(overflow_chars // 10, 50)
                                for boundary in [' ', '，', '。', '！', '？', '\n']:
                                    pos = text_part[:-overflow_chars].rfind(boundary, max(0, len(text_part) - overflow_chars - boundary_adjust))
                                    if pos >= len(text_part) - overflow_chars - boundary_adjust:
                                        overflow_text = text_part[pos + 1:]
                                        break
                                leftovers.append(overflow_text)
                                logger.debug(f"get_text failed for page {pno + 1}, estimated overflow: {overflow_chars} chars (text_part: {len(text_part)}, capacity: {estimated_capacity_chars})")
                            else:
                                # Even if calculation fails, if text is significantly longer, mark some as overflow
                                if len(text_part) > estimated_capacity_chars * 1.2:
                                    overflow_text = text_part[-int(len(text_part) * 0.2):]
                                    leftovers.append(overflow_text)
                                    logger.debug(f"get_text failed for page {pno + 1}, forced overflow: {len(overflow_text)} chars")
                                else:
                                    leftovers.append("")
                        elif estimated_capacity_chars == 0:
                            # If capacity estimation failed, and get_text also failed, use defensive approach
                            # If text is substantial, assume there might be overflow
                            if len(text_part) > 100:  # Arbitrary threshold for substantial text
                                overflow_text = text_part[-int(len(text_part) * 0.1):]  # Take last 10% as overflow
                                leftovers.append(overflow_text)
                                logger.warning(f"get_text and capacity estimation both failed for page {pno + 1}, using defensive overflow: {len(overflow_text)} chars")
                            else:
                                leftovers.append("")
                        else:
                            # Text within capacity, but get_text failed - still check if text is very long
                            if len(text_part) > 500:  # If text is very long, assume potential overflow
                                overflow_text = text_part[-int(len(text_part) * 0.05):]  # Take last 5% as potential overflow
                                leftovers.append(overflow_text)
                                logger.debug(f"get_text failed but text is long ({len(text_part)} chars), defensive overflow: {len(overflow_text)} chars")
                            else:
                                leftovers.append("")
                        # Skip block-based detection since get_text failed, but continue processing next column
                        page_blocks = []  # Ensure page_blocks is empty to skip block processing
                    
                    column_blocks = []
                    # Only process blocks if we successfully got them
                    if page_blocks:
                        for block in page_blocks:
                            if len(block) >= 5:  # Ensure block has coordinates
                                block_x0, block_y0, block_x1, block_y1 = block[0], block[1], block[2], block[3]
                                # Check if block is within column x bounds and near column y region
                                # More strict filtering: block must be primarily within column bounds
                                # Improved block filtering: check if block is primarily within column bounds
                                # Block center should be within column x bounds, and block should be in reasonable y range
                                block_center_x = (block_x0 + block_x1) / 2
                                if (block_center_x >= rect.x0 - 10 and block_center_x <= rect.x1 + 10 and 
                                    block_y0 >= rect.y0 - line_height * 2 and block_y1 <= rect.y1 + line_height * 5):
                                    column_blocks.append(block)
                    
                    # Check for significant overflow with lower threshold (more sensitive)
                    # Only check if we have valid blocks
                    significant_overflow = False
                    if column_blocks:
                        # EXTREMELY SENSITIVE: Lower threshold from 0.5 to 0.05 line_height for maximum sensitivity
                        # This detects even tiny overflows
                        significant_overflow = any(
                            block[3] > rect.y1 + line_height * 0.05 
                            for block in column_blocks 
                            if len(block) >= 5
                        )
                    
                    # CRITICAL DEFENSIVE CHECK: Always check by capacity, regardless of block detection result
                    # This is the last line of defense - PyMuPDF HTML rendering may not respect overflow settings
                    if not significant_overflow:  # Always check, not just when we have blocks
                        # ENHANCED: Use more conservative capacity calculation with dynamic thresholds
                        char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match improved estimate_text_capacity
                        font_width_product = font_size * char_width_factor
                        if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                            estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)  # Match 0.5 factor

                            # DYNAMIC THRESHOLD: Adaptive threshold based on content length
                            if estimated_capacity_chars > 0:
                                # For small capacities, use more sensitive detection
                                if estimated_capacity_chars < 100:
                                    overflow_threshold = 0.80  # 80% for small spaces
                                elif estimated_capacity_chars < 300:
                                    overflow_threshold = 0.85  # 85% for medium spaces
                                else:
                                    overflow_threshold = 0.90  # 90% for large spaces

                                if len(text_part) > estimated_capacity_chars * overflow_threshold:
                                    significant_overflow = True
                                    logger.info(f"CRITICAL: Dynamic threshold overflow detection for page {pno + 1}: text_part ({len(text_part)} chars) exceeds {overflow_threshold:.0%} of capacity ({estimated_capacity_chars} chars)")
                        # Also check if text is very long even if capacity check passes - ADAPTIVE threshold
                        if not significant_overflow:
                            # Dynamic long text threshold based on font size
                            long_text_threshold = max(150, font_size * 10)  # At least 150, or 10x font size
                            if len(text_part) > long_text_threshold:
                                significant_overflow = True
                                logger.info(f"CRITICAL: Dynamic long text overflow detection for page {pno + 1}: {len(text_part)} chars (threshold: {long_text_threshold})")
                    
                    if significant_overflow:
                        # Estimate overflow amount based on bottom-most block
                        block_bottoms = [block[3] for block in column_blocks if len(block) >= 5]
                        max_bottom = max(block_bottoms + [rect.y1]) if block_bottoms else rect.y1
                        overflow_height = max(0, max_bottom - rect.y1)
                        # Lower threshold from 0.3 to 0.05 for much more sensitive detection
                        if overflow_height > line_height * 0.05 and actual_line_height > 0:  # Much more sensitive overflow detection
                            # Improved overflow text estimation: account for font rendering variations
                            overflow_lines = max(1, int(overflow_height / actual_line_height))
                            char_width_factor = 0.65 if fontname != "helv" else 0.5
                            overflow_chars = int(overflow_lines * rect.width / (font_size * char_width_factor))
                            if overflow_chars > 0 and overflow_chars < len(text_part):
                                # Try to preserve word boundaries
                                overflow_text = text_part[-overflow_chars:]
                                boundary_adjust = min(overflow_chars // 10, 50)
                                for boundary in [' ', '，', '。', '！', '？', '\n']:
                                    pos = text_part[:-overflow_chars].rfind(boundary, max(0, len(text_part) - overflow_chars - boundary_adjust))
                                    if pos >= len(text_part) - overflow_chars - boundary_adjust:
                                        overflow_text = text_part[pos + 1:]
                                        break
                                leftovers.append(overflow_text)
                                logger.debug(f"Estimated overflow: {overflow_chars} chars (text_part: {len(text_part)}, capacity: {estimated_capacity_chars})")
                            else:
                                leftovers.append("")
                        else:
                            leftovers.append("")
                    else:
                        leftovers.append("")
                except Exception as e:
                    logger.error(f"Error inserting HTML box for page {pno + 1}: {e}")
                    leftovers.append("")
            except Exception as e:
                logger.error(f"Error processing text part for page {pno + 1}: {e}")
                leftovers.append("")
        else:
            # Text mode: use textbox
            text_len = dpage.insert_textbox(rect, text_part, fontsize=font_size, fontname=fontname, fontfile=fontfile, align=0)
            if isinstance(text_len, (int, float)) and text_len > 0:
                # Text didn't fit, calculate overflow
                char_width_factor = 0.55 if fontname != "helv" else 0.45
                divisor = font_size * char_width_factor
                if divisor > 0:
                    remaining_chars = int(text_len / divisor * 1.2)  # Add buffer for font rendering variations
                    remaining_chars = max(0, min(remaining_chars, len(text_part)))
                    if remaining_chars > 0 and remaining_chars < len(text_part):
                        # Try to preserve word boundaries
                        overflow_text = text_part[-remaining_chars:]
                        boundary_adjust = min(remaining_chars // 10, 50)
                        for boundary in [' ', '，', '。', '！', '？', '\n']:
                            pos = text_part[:-remaining_chars].rfind(boundary, max(0, len(text_part) - remaining_chars - boundary_adjust))
                            if pos >= len(text_part) - remaining_chars - boundary_adjust:
                                overflow_text = text_part[pos + 1:]
                                break
                        leftovers.append(overflow_text)
                    else:
                        leftovers.append("")
                else:
                    leftovers.append("")
            else:
                leftovers.append("")

    # Process any overflow text in continuation pages
    if any(len(leftover) > 0 for leftover in leftovers):
        process_continuation_page(
            dst_doc, src_doc, pno, 
            leftovers, "续", 5, set(),
            font_size, font_name, render_mode, line_spacing, column_padding
        )  # max depth of 5 continuation pages with text tracker


def process_continuation_page(
    dst_doc: fitz.Document, 
    src_doc: fitz.Document, 
    pno: int,
    current_leftovers: List[str], 
    page_suffix: str, 
    max_depth: int = 5, 
    processed_text_tracker: Optional[set] = None,
    font_size: int = 12,
    font_name: Optional[str] = None,
    render_mode: str = "text",
    line_spacing: float = 1.4,
    column_padding: int = 10
):
    """
    Process continuation pages for overflow text.
    
    Args:
        dst_doc: Destination PDF document to add pages to
        src_doc: Source PDF document
        pno: Original page number
        current_leftovers: List of overflow text for each column
        page_suffix: Suffix for page title (e.g., "续", "续2", etc.)
        max_depth: Maximum recursion depth to prevent infinite loops
        processed_text_tracker: Set to track text that has already been processed to avoid duplication
        font_size: Font size for continuation pages
        font_path: Font file path
        render_mode: Rendering mode
        line_spacing: Line spacing
        column_padding: Column padding
    """
    if max_depth <= 0 or not any(len(lo) > 0 for lo in current_leftovers):
        return

    # Initialize the text tracker if not provided
    if processed_text_tracker is None:
        processed_text_tracker = set()
    
    # Get page dimensions from source document
    spage = src_doc.load_page(pno)
    w, h = spage.rect.width, spage.rect.height
    new_w, new_h = int(w * constants.PDF_WIDTH_MULTIPLIER), h
    
    # Create continuation page in destination document
    cpage = dst_doc.new_page(width=new_w, height=new_h)
    
    # Copy original page content to first third of continuation page
    cpage.show_pdf_page(fitz.Rect(0, 0, w, h), src_doc, pno)
    
    # Set up right-side columns for overflow text
    margin_x, margin_y = constants.DEFAULT_MARGIN_X_PT, constants.DEFAULT_MARGIN_Y_PT
    right_start = w + margin_x
    right_end = new_w - margin_x
    available_width = max(right_end - right_start, 1)
    column_spacing = constants.COLUMN_SPACING_PT
    max_columns = constants.MAX_COLUMNS

    # Use font settings from parameters
    fontname = "china"
    fontfile = None
    font_available = False

    if font_name:
        from app.services.font_helper import get_font_file_path
        font_path = get_font_file_path(font_name)
        if font_path:
            try:
                if os.path.exists(font_path) and os.access(font_path, os.R_OK):
                    fontfile = font_path
                    font_available = True
            except Exception:
                pass

    if not font_available:
        fontname = "helv"
        fontfile = None

    line_height = font_size * max(1.0, line_spacing)
    bottom_safe = max(int(line_height * 0.5), 4)

    # Optimized internal margins
    left_internal_margin = max(column_padding, int(font_size * 1.2))
    right_internal_margin = max(column_padding, int(font_size * 0.6))

    total_spacing = column_spacing * (max_columns - 1)
    column_width = max(1.0, (available_width - total_spacing) / max(max_columns, 1))

    def build_rects(count: int, top_offset: float = 0.0):
        if count <= 0:
            return []
        top = margin_y + top_offset
        bottom = new_h - margin_y - bottom_safe
        if bottom <= top:
            bottom = top + max(line_height * 3, font_size * 3)
        rects = []
        for idx in range(count):
            x_left = right_start + idx * (column_width + column_spacing)
            x_right = x_left + column_width
            x0 = x_left + left_internal_margin
            x1 = min(x_right, right_end) - right_internal_margin
            if x1 <= x0:
                x1 = x0 + max(font_size, 20)
            rects.append(fitz.Rect(x0, top, x1, bottom))
        return rects

    continue_rects = build_rects(max_columns)

    # Process each column's leftover text
    continue_leftovers = []
    
    for rect, leftover_text in zip(continue_rects, current_leftovers):
        if leftover_text:
            # Hash the text content to avoid duplication
            text_hash = hash(leftover_text)
            
            # Check if this text has already been processed to prevent duplication
            if text_hash in processed_text_tracker:
                logger.warning(f"Continuation page '{page_suffix}' detected duplicate text, skipping")
                continue_leftovers.append("")
                continue
                
            # Add this text to the tracker
            processed_text_tracker.add(text_hash)
            
            # Render the leftover text in the continuation page
            # Use the same render_mode as the main page
            actual_line_height = font_size * max(1.0, line_spacing)
            
            if render_mode == "markdown":
                # Use same markdown rendering for continuation pages
                try:
                    import re as _re
                    def protect_latex(s: str) -> str:
                        s = _re.sub(r"\$\$(.+?)\$\$", r"\n```\n\\1\n```\n", s, flags=_re.S)
                        s = _re.sub(r"\$(.+?)\$", r"`\\1`", s, flags=_re.S)
                        return s
                    md_text = protect_latex(leftover_text)
                    html = markdown(md_text, extensions=["fenced_code", "tables", "toc", "codehilite"])
                    css = f"""
                    body {{ font-size: {font_size}pt; line-height: 1.4; font-family: 'Helvetica','Arial',sans-serif; color: #000000; word-wrap: break-word; overflow-wrap: break-word; word-break: break-word; white-space: normal; }}
                    pre, code {{ font-family: 'Courier','monospace'; font-size: {max(8, font_size-1)}pt; color: #000000; }}
                    table {{ border-collapse: collapse; width: 100%; }}
                    th, td {{ border: 1px solid #ccc; padding: 2pt 4pt; color: #000000; }}
                    body, p, h1, h2, h3, h4, h5, h6, ul, ol, pre, table {{ margin: 0; padding: 0; color: #000000; }}
                    ul, ol {{ padding-left: 0; list-style-position: inside; }}
                    p {{ margin-bottom: 1pt; }}
                    """
                    # CRITICAL: Completely remove max-height constraint for continuation pages
                    constrained_html = html
                    try:
                        cpage.insert_htmlbox(rect, constrained_html, css=css)
                        # Check for overflow in continuation page
                        page_blocks = []
                        try:
                            page_blocks = cpage.get_text("blocks")
                        except Exception as e:
                            # If get_text fails, use conservative overflow detection
                            logger.warning(f"get_text('blocks') failed in continuation page, using conservative overflow detection: {e}")
                            # More conservative: if detection fails, estimate based on capacity
                            char_width_factor = 0.65 if fontname != "helv" else 0.5
                            font_width_product = font_size * char_width_factor
                            if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.65)
                            else:
                                estimated_capacity_chars = 0
                            # CRITICAL: Use same aggressive threshold as main page (1.0 instead of 1.05)
                            if estimated_capacity_chars > 0 and len(leftover_text) > estimated_capacity_chars * 1.0:
                                # Text exceeds estimated capacity, assume overflow (more aggressive)
                                overflow_ratio = max(0.1, min((len(leftover_text) - estimated_capacity_chars * 0.9) / len(leftover_text), 0.5))
                                overflow_chars = int(len(leftover_text) * overflow_ratio)
                                if overflow_chars > 0 and overflow_chars < len(leftover_text):
                                    # Try to preserve word boundaries
                                    overflow_text = leftover_text[-overflow_chars:]
                                    boundary_adjust = min(overflow_chars // 10, 50)
                                    for boundary in [' ', '，', '。', '！', '？', '\n']:
                                        pos = leftover_text[:-overflow_chars].rfind(boundary, max(0, len(leftover_text) - overflow_chars - boundary_adjust))
                                        if pos >= len(leftover_text) - overflow_chars - boundary_adjust:
                                            overflow_text = leftover_text[pos + 1:]
                                            break
                                    continue_leftovers.append(overflow_text)
                                else:
                                    continue_leftovers.append("")
                            else:
                                continue_leftovers.append("")
                            # Skip block-based detection since get_text failed
                            continue
                        
                        column_blocks = []
                        # Use improved block filtering consistent with main page
                        for block in page_blocks:
                            if len(block) >= 5:
                                block_x0, block_y0, block_x1, block_y1 = block[0], block[1], block[2], block[3]
                                # Improved block filtering: check if block is primarily within column bounds
                                # Block center should be within column x bounds, and block should be in reasonable y range
                                block_center_x = (block_x0 + block_x1) / 2
                                if (block_center_x >= rect.x0 - 10 and block_center_x <= rect.x1 + 10 and 
                                    block_y0 >= rect.y0 - line_height * 2 and block_y1 <= rect.y1 + line_height * 5):
                                    column_blocks.append(block)
                        
                        significant_overflow = False
                        if column_blocks:
                            # EXTREMELY SENSITIVE: Use same threshold as main page (0.05 line_height)
                            significant_overflow = any(
                                block[3] > rect.y1 + line_height * 0.05 
                                for block in column_blocks 
                                if len(block) >= 5
                            )
                        
                        # ENHANCED: CRITICAL DEFENSIVE CHECK - Match main page improvements
                        # This ensures we catch overflow even if block detection fails in continuation pages
                        if not significant_overflow:  # Always check, not just when we have blocks
                            char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                            font_width_product = font_size * char_width_factor
                            if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)  # Match main page
                                # ULTRA AGGRESSIVE: Match main page threshold of 0.85
                                if len(leftover_text) > estimated_capacity_chars * 0.85:
                                    significant_overflow = True
                                    logger.info(f"ENHANCED: Defensive overflow detection in continuation page: leftover_text ({len(leftover_text)} chars) exceeds 85% of capacity ({estimated_capacity_chars} chars)")
                            # Also check if text is very long - LOWERED threshold to match main page
                            if not significant_overflow and len(leftover_text) > 200:  # Reduced from 400 to 200
                                significant_overflow = True
                                logger.info(f"ENHANCED: Long text defensive overflow in continuation page: {len(leftover_text)} chars")
                        
                        if significant_overflow:
                            block_bottoms = [block[3] for block in column_blocks if len(block) >= 5] if column_blocks else []
                            max_bottom = max(block_bottoms + [rect.y1]) if block_bottoms else rect.y1
                            overflow_height = max(0, max_bottom - rect.y1)
                            if overflow_height > line_height * 0.05 and actual_line_height > 0:  # Enhanced threshold
                                # ENHANCED: Improved overflow text estimation with better safety
                                overflow_lines = max(1, int(overflow_height / actual_line_height))
                                char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                                divisor = font_size * char_width_factor
                                chars_per_line = max(int(rect.width / divisor), 1) if divisor > 0 else 1
                                # Add 25% buffer for font rendering variations (increased from 20%)
                                overflow_chars = int(min(overflow_lines * chars_per_line * 1.25, len(leftover_text)))
                                overflow_chars = min(overflow_chars, len(leftover_text))
                                if overflow_chars > 0:
                                    # Extract overflow text, try to preserve word boundaries with enhanced adjustment
                                    overflow_text = leftover_text[-overflow_chars:]
                                    # Try to adjust to nearest word/sentence boundary if close
                                    boundary_adjust = min(overflow_chars // 8, 60)  # Enhanced from 10% to 12.5% and 50 to 60
                                    for boundary in [' ', '，', '。', '！', '？', '\n']:
                                        pos = leftover_text[:-overflow_chars].rfind(boundary, max(0, len(leftover_text) - overflow_chars - boundary_adjust))
                                        if pos >= len(leftover_text) - overflow_chars - boundary_adjust:
                                            overflow_text = leftover_text[pos + 1:]
                                            break
                                    continue_leftovers.append(overflow_text)
                                else:
                                    # If block-based calculation failed, use capacity-based estimation with enhanced thresholds
                                    char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                                    font_width_product = font_size * char_width_factor
                                    if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                        estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)  # Match main page
                                        if len(leftover_text) > estimated_capacity_chars * 0.85:  # Match main page
                                            overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))  # Enhanced
                                            overflow_chars = int(len(leftover_text) * overflow_ratio)
                                            overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 else ""
                                            boundary_adjust = min(overflow_chars // 8, 60)  # Enhanced
                                            for boundary in [' ', '，', '。', '！', '？', '\n']:
                                                pos = leftover_text[:-len(overflow_text)].rfind(boundary, max(0, len(leftover_text) - len(overflow_text) - boundary_adjust))
                                                if pos >= len(leftover_text) - len(overflow_text) - boundary_adjust:
                                                    overflow_text = leftover_text[pos + 1:]
                                                    break
                                            continue_leftovers.append(overflow_text)
                                        else:
                                            continue_leftovers.append("")
                                    else:
                                        continue_leftovers.append("")
                            else:
                                # ENHANCED: Even if overflow_height is small, check by capacity with improved thresholds
                                char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                                font_width_product = font_size * char_width_factor
                                if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                    estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)  # Match main page
                                    if len(leftover_text) > estimated_capacity_chars * 0.85:  # Match main page
                                        overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))  # Enhanced
                                        overflow_chars = int(len(leftover_text) * overflow_ratio)
                                        overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 and overflow_chars < len(leftover_text) else leftover_text[-int(len(leftover_text) * 0.15):]  # Enhanced
                                        boundary_adjust = min(overflow_chars // 8, 60)  # Enhanced
                                        for boundary in [' ', '，', '。', '！', '？', '\n']:
                                            pos = leftover_text[:-len(overflow_text)].rfind(boundary, max(0, len(leftover_text) - len(overflow_text) - boundary_adjust))
                                            if pos >= len(leftover_text) - len(overflow_text) - boundary_adjust:
                                                overflow_text = leftover_text[pos + 1:]
                                                break
                                        continue_leftovers.append(overflow_text)
                                    else:
                                        # Even if within capacity, if text is very long, mark some as potential overflow - LOWERED threshold
                                        if len(leftover_text) > 150:  # Reduced from 300 to 150
                                            overflow_text = leftover_text[-int(len(leftover_text) * 0.12):]  # Increased from 8% to 12%
                                            continue_leftovers.append(overflow_text)
                                        else:
                                            continue_leftovers.append("")
                                else:
                                    # If capacity calculation failed, use absolute length threshold - LOWERED
                                    if len(leftover_text) > 100:  # Reduced from 200 to 100
                                        overflow_text = leftover_text[-int(len(leftover_text) * 0.15):]  # Increased from 10% to 15%
                                        continue_leftovers.append(overflow_text)
                                    else:
                                        continue_leftovers.append("")
                        else:
                            # ENHANCED: Even if no overflow detected by blocks, always verify by capacity with improved thresholds
                            char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                            font_width_product = font_size * char_width_factor
                            if actual_line_height > 0 and font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)  # Match main page
                                if len(leftover_text) > estimated_capacity_chars * 0.85:  # Match main page
                                    overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))  # Enhanced
                                    overflow_chars = int(len(leftover_text) * overflow_ratio)
                                    overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 and overflow_chars < len(leftover_text) else leftover_text[-int(len(leftover_text) * 0.15):]  # Enhanced
                                    boundary_adjust = min(overflow_chars // 8, 60)  # Enhanced
                                    for boundary in [' ', '，', '。', '！', '？', '\n']:
                                        pos = leftover_text[:-len(overflow_text)].rfind(boundary, max(0, len(leftover_text) - len(overflow_text) - boundary_adjust))
                                        if pos >= len(leftover_text) - len(overflow_text) - boundary_adjust:
                                            overflow_text = leftover_text[pos + 1:]
                                            break
                                    continue_leftovers.append(overflow_text)
                                else:
                                    # Even if within capacity, if text is very long, mark some as potential overflow - LOWERED threshold
                                    if len(leftover_text) > 150:  # Reduced from 300 to 150
                                        overflow_text = leftover_text[-int(len(leftover_text) * 0.12):]  # Increased from 8% to 12%
                                        continue_leftovers.append(overflow_text)
                                    else:
                                        continue_leftovers.append("")
                            else:
                                # If capacity calculation failed, use absolute length threshold - LOWERED
                                if len(leftover_text) > 100:  # Reduced from 200 to 100
                                    overflow_text = leftover_text[-int(len(leftover_text) * 0.15):]  # Increased from 10% to 15%
                                    continue_leftovers.append(overflow_text)
                                else:
                                    continue_leftovers.append("")
                    except Exception as html_err:
                        logger.warning(f"HTML box insertion failed in continuation page, using textbox: {html_err}")
                        try:
                            leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname=fontname, fontfile=fontfile, align=0)
                        except Exception as font_err:
                            logger.warning(f"Font insertion failed, falling back to default font: {font_err}")
                            leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname="helv", fontfile=None, align=0)
                        if isinstance(leftover_len, (int, float)) and leftover_len > 0:
                            # ENHANCED: Match main page improvements
                            char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                            divisor = font_size * char_width_factor
                            if divisor > 0:
                                # Improved calculation with better buffer
                                remaining_chars = int(leftover_len / divisor * 1.2)  # Increased from 1.1 to 1.2
                                remaining_chars = max(0, min(remaining_chars, len(leftover_text)))
                                if remaining_chars > 0 and remaining_chars < len(leftover_text):
                                    # Try to preserve word boundaries with enhanced adjustment
                                    overflow_text = leftover_text[-remaining_chars:]
                                    boundary_adjust = min(remaining_chars // 8, 60)  # Enhanced from 10% to 12.5% and 50 to 60
                                    for boundary in [' ', '，', '。', '！', '？', '\n']:
                                        pos = leftover_text[:-remaining_chars].rfind(boundary, max(0, len(leftover_text) - remaining_chars - boundary_adjust))
                                        if pos >= len(leftover_text) - remaining_chars - boundary_adjust:
                                            overflow_text = leftover_text[pos + 1:]
                                            break
                                    continue_leftovers.append(overflow_text)
                                else:
                                    continue_leftovers.append("")
                            else:
                                continue_leftovers.append("")
                        else:
                            # ENHANCED: Add capacity-based fallback
                            char_width_factor = 0.55 if fontname != "helv" else 0.45
                            font_width_product = font_size * char_width_factor
                            if font_width_product > 0 and rect.width > 0 and rect.height > 0:
                                actual_line_height = font_size * 1.4  # Default line spacing
                                actual_line_height = max(actual_line_height, font_size * 0.6)
                                if actual_line_height > 0:
                                    estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)
                                    if len(leftover_text) > estimated_capacity_chars * 0.85:
                                        overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))
                                        overflow_chars = int(len(leftover_text) * overflow_ratio)
                                        overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 else ""
                                        continue_leftovers.append(overflow_text)
                                    else:
                                        continue_leftovers.append("")
                                else:
                                    continue_leftovers.append("")
                            else:
                                continue_leftovers.append("")
                except Exception as e:
                    logger.warning(f"HTML rendering failed in continuation page, falling back to textbox: {e}")
                    try:
                        leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname=fontname, fontfile=fontfile, align=0)
                    except Exception as font_err:
                        logger.warning(f"Font insertion failed, falling back to default font: {font_err}")
                        leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname="helv", fontfile=None, align=0)
                    if isinstance(leftover_len, (int, float)) and leftover_len > 0:
                        # ENHANCED: Match main page improvements
                        char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                        divisor = font_size * char_width_factor
                        if divisor > 0:
                            # Improved calculation with better buffer
                            remaining_chars = int(leftover_len / divisor * 1.2)  # Increased from 1.1 to 1.2
                            remaining_chars = max(0, min(remaining_chars, len(leftover_text)))
                            if remaining_chars > 0 and remaining_chars < len(leftover_text):
                                # Try to preserve word boundaries with enhanced adjustment
                                overflow_text = leftover_text[-remaining_chars:]
                                boundary_adjust = min(remaining_chars // 8, 60)  # Enhanced from 10% to 12.5% and 50 to 60
                                for boundary in [' ', '，', '。', '！', '？', '\n']:
                                    pos = leftover_text[:-remaining_chars].rfind(boundary, max(0, len(leftover_text) - remaining_chars - boundary_adjust))
                                    if pos >= len(leftover_text) - remaining_chars - boundary_adjust:
                                        overflow_text = leftover_text[pos + 1:]
                                        break
                                continue_leftovers.append(overflow_text)
                            else:
                                continue_leftovers.append("")
                        else:
                            continue_leftovers.append("")
                    else:
                        # ENHANCED: Add capacity-based fallback
                        char_width_factor = 0.55 if fontname != "helv" else 0.45
                        font_width_product = font_size * char_width_factor
                        if font_width_product > 0 and rect.width > 0 and rect.height > 0:
                            actual_line_height = font_size * 1.4  # Default line spacing
                            actual_line_height = max(actual_line_height, font_size * 0.6)
                            if actual_line_height > 0:
                                estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)
                                if len(leftover_text) > estimated_capacity_chars * 0.85:
                                    overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))
                                    overflow_chars = int(len(leftover_text) * overflow_ratio)
                                    overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 else ""
                                    continue_leftovers.append(overflow_text)
                                else:
                                    continue_leftovers.append("")
                            else:
                                continue_leftovers.append("")
                        else:
                            continue_leftovers.append("")
            else:
                # Text mode: use textbox with enhanced overflow detection
                try:
                    leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname=fontname, fontfile=fontfile, align=0)
                except Exception as font_err:
                    logger.warning(f"Font insertion failed, falling back to default font: {font_err}")
                    leftover_len = cpage.insert_textbox(rect, leftover_text, fontsize=font_size, fontname="helv", fontfile=None, align=0)
                if isinstance(leftover_len, (int, float)) and leftover_len > 0:
                    # ENHANCED: Match main page improvements
                    char_width_factor = 0.55 if fontname != "helv" else 0.45  # Match main page
                    divisor = font_size * char_width_factor
                    if divisor > 0:
                        # Improved calculation with better buffer for font rendering variations
                        remaining_chars = int(leftover_len / divisor * 1.2)  # Increased from 1.1 to 1.2
                        remaining_chars = max(0, min(remaining_chars, len(leftover_text)))
                        if remaining_chars > 0 and remaining_chars < len(leftover_text):
                            # Try to preserve word boundaries for better readability with enhanced adjustment
                            overflow_text = leftover_text[-remaining_chars:]
                            boundary_adjust = min(remaining_chars // 8, 60)  # Enhanced from 10% to 12.5% and 50 to 60
                            for boundary in [' ', '，', '。', '！', '？', '\n']:
                                pos = leftover_text[:-remaining_chars].rfind(boundary, max(0, len(leftover_text) - remaining_chars - boundary_adjust))
                                if pos >= len(leftover_text) - remaining_chars - boundary_adjust:
                                    overflow_text = leftover_text[pos + 1:]
                                    break
                            continue_leftovers.append(overflow_text)
                        else:
                            continue_leftovers.append("")
                    else:
                        continue_leftovers.append("")
                else:
                    # ENHANCED: Add capacity-based fallback for textbox mode
                    char_width_factor = 0.55 if fontname != "helv" else 0.45
                    font_width_product = font_size * char_width_factor
                    if font_width_product > 0 and rect.width > 0 and rect.height > 0:
                        actual_line_height = font_size * 1.4  # Default line spacing
                        actual_line_height = max(actual_line_height, font_size * 0.6)
                        if actual_line_height > 0:
                            estimated_capacity_chars = int((rect.width / font_width_product) * (rect.height / actual_line_height) * 0.5)
                            if len(leftover_text) > estimated_capacity_chars * 0.85:
                                overflow_ratio = max(0.15, min((len(leftover_text) - estimated_capacity_chars * 0.85) / len(leftover_text), 0.4))
                                overflow_chars = int(len(leftover_text) * overflow_ratio)
                                overflow_text = leftover_text[-overflow_chars:] if overflow_chars > 0 else ""
                                continue_leftovers.append(overflow_text)
                            else:
                                continue_leftovers.append("")
                        else:
                            continue_leftovers.append("")
                    else:
                        continue_leftovers.append("")
        else:
            continue_leftovers.append("")

    # Recursively process further overflow
    continue_summary = [len(lo) for lo in continue_leftovers]
    total_continue = sum(continue_summary)
    logger.info(f"Continuation page '{page_suffix}' processed: continue_leftovers={continue_summary}, total={total_continue} chars")
    
    if any(len(lo) > 0 for lo in continue_leftovers):
        # Determine next page suffix with safer logic
        try:
            if page_suffix == "续":
                next_suffix = "续2"
            elif page_suffix.startswith("续") and len(page_suffix) > 1:
                # Extract number after "续"
                try:
                    current_num = int(page_suffix[1:])
                    next_suffix = f"续{current_num + 1}"
                except (ValueError, IndexError):
                    # Fallback if parsing fails
                    next_suffix = "续2"
            else:
                # Fallback for unexpected suffix format
                next_suffix = "续2"
        except Exception as e:
            logger.warning(f"Error determining next page suffix, using default: {e}")
            next_suffix = "续2"
        
        # Recursively process with decreased depth counter and pass the text tracker
        process_continuation_page(
            dst_doc, src_doc, pno,
            continue_leftovers, next_suffix, max_depth - 1, processed_text_tracker,
            font_size, font_name, render_mode, line_spacing, column_padding
        )


def compose_pdf(src_bytes: bytes, explanations: Dict[int, str], right_ratio: float, font_size: int,
                font_name: Optional[str] = None,
                render_mode: str = "text", line_spacing: float = 1.4, column_padding: int = 10) -> bytes:
    """
    Compose PDF with explanations added to right side.
    
    Args:
        src_bytes: Source PDF bytes
        explanations: Dictionary mapping page number (0-indexed) to explanation text
        right_ratio: Right side ratio (unused, kept for compatibility)
        font_size: Font size for explanations
        render_mode: Rendering mode ("text", "markdown", or "empty_right")
        line_spacing: Line spacing multiplier
        column_padding: Column internal padding
        
    Returns:
        Composed PDF bytes
        
    Raises:
        ValueError: If any parameter is invalid
    """
    # Validate input parameters
    is_valid, error_msg = validate_compose_params(font_size, line_spacing, right_ratio, column_padding)
    if not is_valid:
        raise ValueError(f"Invalid parameter: {error_msg}")
    
    if render_mode not in ("text", "markdown", "pandoc", "empty_right"):
        raise ValueError(f"Invalid render_mode: {render_mode}. Must be 'text', 'markdown', 'pandoc', or 'empty_right'")
    
    with open_pdf_document(src_bytes) as src_doc:
        dst_doc = fitz.open()
        try:
            for pno in range(src_doc.page_count):
                expl = explanations.get(pno, "")
                _compose_vector(dst_doc, src_doc, pno, right_ratio, font_size, expl, 
                               font_name=font_name, render_mode=render_mode, 
                               line_spacing=line_spacing, column_padding=column_padding)
            bout = io.BytesIO()
            # 优化PDF保存参数，减小文件大小
            dst_doc.save(bout, deflate=True, clean=True, garbage=4, deflate_images=True, deflate_fonts=True)
            return bout.getvalue()
        finally:
            # Ensure destination document is closed even if error occurs
            try:
                dst_doc.close()
            except Exception as e:
                logger.warning(f"Error closing destination document: {e}")