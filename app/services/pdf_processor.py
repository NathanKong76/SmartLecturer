from __future__ import annotations

import asyncio
import base64
import sys
from typing import Any, Callable, Dict, List, Optional, Tuple

import fitz

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

from .gemini_client import GeminiClient
from .openai_client import OpenAIClient
from .logger import get_logger

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


logger = get_logger()


def _create_llm_client(
	llm_provider: str,
	api_key: str,
	model_name: str,
	temperature: float,
	max_tokens: int,
	rpm_limit: int,
	tpm_budget: int,
	rpd_limit: int,
	api_base: Optional[str],
) -> Any:
	provider = (llm_provider or "gemini").lower()
	if provider == "openai":
		return OpenAIClient(
			api_key=api_key,
			model_name=model_name,
			temperature=temperature,
			max_output_tokens=max_tokens,
			rpm_limit=rpm_limit,
			tpm_budget=tpm_budget,
			rpd_limit=rpd_limit,
			api_base=api_base,
			logger=logger.info,
		)
	return GeminiClient(
		api_key=api_key,
		model_name=model_name,
		temperature=temperature,
		max_output_tokens=max_tokens,
		rpm_limit=rpm_limit,
		tpm_budget=tpm_budget,
		rpd_limit=rpd_limit,
		logger=logger.info,
	)


def _run_async(coro: asyncio.Future) -> Any:
	if sys.platform.startswith("win"):
		try:
			asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
		except Exception:
			pass
	loop = asyncio.new_event_loop()
	try:
		asyncio.set_event_loop(loop)
		return loop.run_until_complete(coro)
	finally:
		asyncio.set_event_loop(None)
		loop.close()


async def _generate_explanations_async(
	llm_client,
	page_images: List[bytes],
	user_prompt: str,
	context_prompt: Optional[str],
	use_context: bool,
	concurrency: int,
	on_progress: Optional[Callable[[int, int], None]],
	on_log: Optional[Callable[[str], None]],
) -> Tuple[Dict[int, str], Dict[int, str], List[int]]:
	total_pages = len(page_images)
	if total_pages == 0:
		return {}, {}, []

	semaphore = asyncio.Semaphore(max(1, concurrency))
	progress_lock = asyncio.Lock()
	completed = {"count": 0}
	preview_images: Dict[int, str] = {
		idx + 1: base64.b64encode(img).decode("utf-8")
		for idx, img in enumerate(page_images)
	}

	async def process_page(page_index: int) -> Tuple[int, str, Optional[Exception]]:
		async with semaphore:
			current_image = page_images[page_index]
			error: Optional[Exception] = None
			result = ""

			if current_image:
				images_with_labels: List[Tuple[str, bytes]] = []
				if use_context and page_index > 0 and page_images[page_index - 1]:
					images_with_labels.append(("前一页", page_images[page_index - 1]))
				images_with_labels.append(("当前页", current_image))
				if use_context and page_index < total_pages - 1 and page_images[page_index + 1]:
					images_with_labels.append(("后一页", page_images[page_index + 1]))

				try:
					result = await llm_client.explain_pages_with_context(
						images_with_labels,
						system_prompt=user_prompt,
						context_prompt=context_prompt,
					)
				except Exception as exc:  # noqa: BLE001
					error = exc
			else:
				error = RuntimeError("页面截图生成失败，跳过 LLM 调用")

			async with progress_lock:
				completed["count"] += 1
				if on_progress:
					try:
						on_progress(completed["count"], total_pages)
					except Exception:
						pass

			if error:
				if on_log:
					try:
						on_log(f"第 {page_index + 1} 页生成失败: {error}")
					except Exception:
						pass
			else:
				if on_log:
					try:
						on_log(f"第 {page_index + 1} 页生成完成")
					except Exception:
						pass

			return page_index, result.strip(), error

	tasks = [asyncio.create_task(process_page(idx)) for idx in range(total_pages)]
	results = await asyncio.gather(*tasks, return_exceptions=False)
	explanations: Dict[int, str] = {}
	failed_pages: List[int] = []
	for page_index, text, error in results:
		if error:
			failed_pages.append(page_index + 1)
		else:
			explanations[page_index] = text

	return explanations, preview_images, failed_pages


def generate_explanations(
	src_bytes: bytes,
	api_key: str,
	model_name: str,
	user_prompt: str,
	temperature: float,
	max_tokens: int,
	dpi: int,
	concurrency: int,
	rpm_limit: int,
	tpm_budget: int,
	rpd_limit: int,
	on_progress: Optional[Callable[[int, int], None]] = None,
	on_log: Optional[Callable[[str], None]] = None,
	use_context: bool = False,
	context_prompt: Optional[str] = None,
	llm_provider: str = "gemini",
	api_base: Optional[str] = None,
) -> Tuple[Dict[int, str], Dict[int, str], List[int]]:
	if not api_key:
		raise ValueError("api_key is required to generate explanations")
	if not model_name:
		raise ValueError("model_name is required to generate explanations")

	llm_client = _create_llm_client(
		llm_provider=llm_provider,
		api_key=api_key,
		model_name=model_name,
		temperature=temperature,
		max_tokens=max_tokens,
		rpm_limit=rpm_limit,
		tpm_budget=tpm_budget,
		rpd_limit=rpd_limit,
		api_base=api_base,
	)

	pdf_doc = fitz.open(stream=src_bytes, filetype="pdf")
	try:
		page_images: List[bytes] = []
		for page_index in range(pdf_doc.page_count):
			try:
				page_images.append(_page_png_bytes(pdf_doc, page_index, dpi))
			except Exception as exc:  # noqa: BLE001
				logger.warning("Failed to render page %s at %s DPI: %s", page_index + 1, dpi, exc)
				page_images.append(b"")
	finally:
		pdf_doc.close()

	filtered_images = [img for img in page_images if img]
	if len(filtered_images) != len(page_images):
		missing_pages = [idx + 1 for idx, data in enumerate(page_images) if not data]
		if on_log and missing_pages:
			try:
				on_log(f"以下页面无法渲染截图: {', '.join(map(str, missing_pages))}")
			except Exception:
				pass

	return _run_async(
		_generate_explanations_async(
			llm_client=llm_client,
			page_images=[img if img else b"" for img in page_images],
			user_prompt=user_prompt,
			context_prompt=context_prompt,
			use_context=use_context,
			concurrency=max(1, concurrency),
			on_progress=on_progress,
			on_log=on_log,
		)
	)


def process_markdown_mode(
	src_bytes: bytes,
	api_key: str,
	model_name: str,
	user_prompt: str,
	temperature: float,
	max_tokens: int,
	dpi: int,
	screenshot_dpi: int,
	concurrency: int,
	rpm_limit: int,
	tpm_budget: int,
	rpd_limit: int,
	embed_images: bool,
	title: str,
	use_context: bool = False,
	context_prompt: Optional[str] = None,
	llm_provider: str = "gemini",
	api_base: Optional[str] = None,
) -> Tuple[str, Dict[int, str], List[int], Dict[int, str]]:
	explanations, preview_images, failed_pages = generate_explanations(
		src_bytes=src_bytes,
		api_key=api_key,
		model_name=model_name,
		user_prompt=user_prompt,
		temperature=temperature,
		max_tokens=max_tokens,
		dpi=dpi,
		concurrency=concurrency,
		rpm_limit=rpm_limit,
		tpm_budget=tpm_budget,
		rpd_limit=rpd_limit,
		on_progress=None,
		on_log=None,
		use_context=use_context,
		context_prompt=context_prompt,
		llm_provider=llm_provider,
		api_base=api_base,
	)

	markdown_content, _images_dir = generate_markdown_with_screenshots(
		src_bytes=src_bytes,
		explanations=explanations,
		screenshot_dpi=screenshot_dpi,
		embed_images=embed_images,
		title=title,
	)

	return markdown_content, explanations, failed_pages, preview_images

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
    "generate_html_pdf2htmlex_document",
    "generate_explanations",
    "process_markdown_mode",
]