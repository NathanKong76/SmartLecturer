from __future__ import annotations

# Import all functions from the modularized components
from .pdf_validator import (
    safe_utf8_loads,
    is_blank_explanation,
    validate_pdf_file,
    pages_with_blank_explanations
)

from .text_layout import (
    _smart_text_layout
)

from .pdf_composer import (
    _page_png_bytes,
    _compose_vector,
    compose_pdf
)

from .batch_processor import (
    match_pdf_json_files,
    batch_recompose_from_json,
    batch_recompose_from_json_async
)

from .markdown_generator import (
    create_page_screenshot_markdown,
    generate_markdown_with_screenshots
)

from .html_screenshot_generator import (
    HTMLScreenshotGenerator
)

from .html_pdf2htmlex_generator import (
    HTMLPdf2htmlEXGenerator
)

# HTML screenshot document generation function
def generate_html_screenshot_document(
    src_bytes: bytes,
    explanations: dict,
    screenshot_dpi: int = 150,
    title: str = "PDF文档讲解",
    font_name: str = "SimHei",
    font_size: int = 14,
    line_spacing: float = 1.2,
    column_count: int = 2,
    column_gap: int = 20,
    show_column_rule: bool = True
) -> str:
    """
    Generate HTML screenshot document with PDF screenshots and explanations
    
    Args:
        src_bytes: Source PDF file bytes
        explanations: Dict mapping page numbers (0-indexed) to explanation text
        screenshot_dpi: Screenshot DPI
        title: Document title
        font_name: Font family name
        font_size: Font size in pt
        line_spacing: Line height multiplier
        column_count: Number of columns for explanation text
        column_gap: Gap between columns in px
        show_column_rule: Whether to show column separator line
        
    Returns:
        Complete HTML document string
    """
    import fitz
    
    # Open PDF document
    src_doc = fitz.open(stream=src_bytes, filetype="pdf")
    total_pages = src_doc.page_count
    
    # Generate screenshots for all pages
    screenshot_data = []
    for page_num in range(total_pages):
        screenshot_bytes = _page_png_bytes(src_doc, page_num, screenshot_dpi)
        screenshot_data.append({
            'page_num': page_num + 1,  # Convert to 1-indexed
            'image_bytes': screenshot_bytes
        })
    
    src_doc.close()
    
    # Convert explanations from 0-indexed to 1-indexed
    explanations_1indexed = {
        page_num + 1: text 
        for page_num, text in explanations.items()
    }
    
    # Generate HTML document
    html_content = HTMLScreenshotGenerator.generate_html_screenshot_view(
        screenshot_data=screenshot_data,
        explanations=explanations_1indexed,
        total_pages=total_pages,
        title=title,
        font_name=font_name,
        font_size=font_size,
        line_spacing=line_spacing,
        column_count=column_count,
        column_gap=column_gap,
        show_column_rule=show_column_rule
    )
    
    return html_content

# HTML pdf2htmlEX document generation function
def generate_html_pdf2htmlex_document(
    src_bytes: bytes,
    explanations: dict,
    title: str = "PDF文档讲解",
    font_name: str = "SimHei",
    font_size: int = 14,
    line_spacing: float = 1.2,
    column_count: int = 2,
    column_gap: int = 20,
    show_column_rule: bool = True
) -> str:
    """
    Generate HTML pdf2htmlEX document with pdf2htmlEX converted PDF and explanations
    
    Args:
        src_bytes: Source PDF file bytes
        explanations: Dict mapping page numbers (0-indexed) to explanation text
        title: Document title
        font_name: Font family name
        font_size: Font size in pt
        line_spacing: Line height multiplier
        column_count: Number of columns for explanation text
        column_gap: Gap between columns in px
        show_column_rule: Whether to show column separator line
        
    Returns:
        Complete HTML document string
    """
    import tempfile
    import os
    
    # Check if pdf2htmlEX is installed
    is_installed, message = HTMLPdf2htmlEXGenerator.check_pdf2htmlex_installed()
    if not is_installed:
        raise RuntimeError(f"pdf2htmlEX not available: {message}")
    
    # Create temporary directory for pdf2htmlEX output
    with tempfile.TemporaryDirectory() as temp_dir:
        # Call pdf2htmlEX to convert PDF
        success, html_path, error = HTMLPdf2htmlEXGenerator.call_pdf2htmlex(
            src_bytes, temp_dir
        )
        
        if not success:
            raise RuntimeError(f"pdf2htmlEX conversion failed: {error}")
        
        # Parse pdf2htmlEX output
        css_content, page_htmls, error = HTMLPdf2htmlEXGenerator.parse_pdf2htmlex_html(html_path)
        
        if error or not page_htmls:
            raise RuntimeError(f"Failed to parse pdf2htmlEX output: {error}")
        
        total_pages = len(page_htmls)
        
        # Convert explanations from 0-indexed to 1-indexed
        explanations_1indexed = {
            page_num + 1: text 
            for page_num, text in explanations.items()
        }
        
        # Generate HTML document
        html_content = HTMLPdf2htmlEXGenerator.generate_html_pdf2htmlex_view(
            page_htmls=page_htmls,
            pdf2htmlex_css=css_content,
            explanations=explanations_1indexed,
            total_pages=total_pages,
            title=title,
            font_name=font_name,
            font_size=font_size,
            line_spacing=line_spacing,
            column_count=column_count,
            column_gap=column_gap,
            show_column_rule=show_column_rule
        )
        
        return html_content

# For backward compatibility, import everything into this namespace
__all__ = [
    "safe_utf8_loads",
    "is_blank_explanation",
    "validate_pdf_file",
    "pages_with_blank_explanations",
    "_smart_text_layout",
    "_page_png_bytes",
    "_compose_vector",
    "compose_pdf",
    "match_pdf_json_files",
    "batch_recompose_from_json",
    "batch_recompose_from_json_async",
    "create_page_screenshot_markdown",
    "generate_markdown_with_screenshots",
    "generate_html_screenshot_document",
    "generate_html_pdf2htmlex_document"
]