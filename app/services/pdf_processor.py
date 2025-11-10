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
	global_concurrency_controller=None,
	on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
	target_pages: Optional[List[int]] = None,
	on_partial_save: Optional[Callable[[Dict[int, str], List[int]], None]] = None,
	existing_explanations: Optional[Dict[int, str]] = None,
) -> Tuple[Dict[int, str], Dict[int, str], List[int]]:
	total_pages = len(page_images)
	if total_pages == 0:
		return {}, {}, []

	# Initialize existing_explanations if not provided
	if existing_explanations is None:
		existing_explanations = {}
	
	# Filter pages to process if target_pages is specified
	# target_pages contains 0-based indices
	pages_to_process = list(range(total_pages))
	if target_pages is not None:
		# Filter to only process specified pages (0-based)
		pages_to_process = [idx for idx in target_pages if 0 <= idx < total_pages]
		if not pages_to_process:
			return {}, {}, []
	
	# Skip pages that already have explanations in cache (page-level cache recall)
	# Only skip if the explanation is not empty/blank
	# Note: Failed pages are NOT in existing_explanations, so they will be reprocessed
	# This is correct behavior - failed pages should be retried, not skipped
	pages_to_process = [
		idx for idx in pages_to_process 
		if idx not in existing_explanations or not existing_explanations.get(idx, "").strip()
	]
	
	# If all pages are already cached, return early
	if not pages_to_process:
		# All pages are cached, return existing explanations
		# Update page status for all cached pages
		if on_page_status:
			for page_idx in range(total_pages):
				if page_idx in existing_explanations and existing_explanations[page_idx] and existing_explanations[page_idx].strip():
					try:
						on_page_status(page_idx, "completed", None)
					except Exception:
						pass
		
		# Update progress to show all pages completed
		if on_progress:
			try:
				on_progress(total_pages, total_pages)
			except Exception:
				pass
		
		# Return existing explanations (filtered to only include pages in target_pages if specified)
		if target_pages is not None:
			cached_explanations = {idx: existing_explanations[idx] for idx in target_pages if idx in existing_explanations}
		else:
			cached_explanations = existing_explanations.copy()
		
		# Generate preview images for all pages
		preview_images: Dict[int, str] = {
			idx + 1: base64.b64encode(img).decode("utf-8")
			for idx, img in enumerate(page_images)
		}
		
		return cached_explanations, preview_images, []

	# Remove local semaphore limit - use global concurrency controller only
	# Set to a very large value so global controller truly controls all concurrency
	local_semaphore = asyncio.Semaphore(10000)  # Large value, not a real limit
	progress_lock = asyncio.Lock()
	completed = {"count": 0}
	preview_images: Dict[int, str] = {
		idx + 1: base64.b64encode(img).decode("utf-8")
		for idx, img in enumerate(page_images)
	}
	
	# Track current explanations and failed pages for real-time saving
	# Start with existing cached explanations
	current_explanations: Dict[int, str] = existing_explanations.copy() if existing_explanations else {}
	current_failed_pages: List[int] = []
	
	# Count of pages that were skipped (already cached)
	skipped_count = len([idx for idx in range(total_pages) if idx in existing_explanations and existing_explanations.get(idx, "").strip()])
	
	# Update progress for skipped pages
	if skipped_count > 0 and on_progress:
		try:
			on_progress(skipped_count, total_pages)
		except Exception:
			pass
	
	# Update page status for cached pages
	if on_page_status:
		for page_idx in range(total_pages):
			if page_idx in existing_explanations and existing_explanations[page_idx] and existing_explanations[page_idx].strip():
				if target_pages is None or page_idx in target_pages:
					try:
						on_page_status(page_idx, "completed", None)
					except Exception:
						pass
	
	# Log skipped pages
	if skipped_count > 0 and on_log:
		try:
			skipped_pages = [idx + 1 for idx in range(total_pages) if idx in existing_explanations and existing_explanations.get(idx, "").strip()]
			on_log(f"跳过 {skipped_count} 个已缓存的页面: {', '.join(map(str, skipped_pages))}")
		except Exception:
			pass

	async def process_page(page_index: int) -> Tuple[int, str, Optional[Exception]]:
		# Notify that page processing has started
		if on_page_status:
			try:
				on_page_status(page_index, "processing", None)
			except Exception as e:
				# Log the error but don't break processing
				logger.warning(f"Failed to update page status to 'processing' for page {page_index + 1}: {e}", exc_info=True)
		
		# Acquire both local and global semaphores
		async with local_semaphore:
			# Use global concurrency controller if available
			if global_concurrency_controller:
				request_id = f"page_{page_index}"
				async with global_concurrency_controller:
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
			else:
				# No global controller, just use local semaphore
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
				
				# Update current state for real-time saving
				if error:
					current_failed_pages.append(page_index + 1)
					# Remove from explanations if it was there
					current_explanations.pop(page_index, None)
				else:
					current_explanations[page_index] = result.strip()
					# Remove from failed pages if it was there
					if (page_index + 1) in current_failed_pages:
						current_failed_pages.remove(page_index + 1)
				
				# Update page status after processing
				if on_page_status:
					try:
						if error:
							on_page_status(page_index, "failed", str(error))
						else:
							on_page_status(page_index, "completed", None)
					except Exception as e:
						# Log the error but don't break processing
						status = "failed" if error else "completed"
						logger.warning(f"Failed to update page status to '{status}' for page {page_index + 1}: {e}", exc_info=True)
				
				if on_progress:
					try:
						on_progress(completed["count"], total_pages)
					except Exception:
						pass
				
				# Trigger real-time save after each page
				if on_partial_save:
					try:
						# Create a copy to avoid race conditions
						explanations_copy = current_explanations.copy()
						failed_pages_copy = current_failed_pages.copy()
						on_partial_save(explanations_copy, failed_pages_copy)
					except Exception:
						# Don't let save errors break the processing
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

	tasks = [asyncio.create_task(process_page(idx)) for idx in pages_to_process]
	results = await asyncio.gather(*tasks, return_exceptions=False)
	
	# Start with existing cached explanations
	explanations: Dict[int, str] = existing_explanations.copy() if existing_explanations else {}
	failed_pages: List[int] = []
	
	for page_index, text, error in results:
		if error:
			failed_pages.append(page_index + 1)
			# Remove from explanations if it was there (in case of retry failure)
			explanations.pop(page_index, None)
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
	on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
	target_pages: Optional[List[int]] = None,
	auto_retry_failed_pages: bool = True,
	max_auto_retries: int = 2,
	file_hash: Optional[str] = None,
	existing_explanations: Optional[Dict[int, str]] = None,
) -> Tuple[Dict[int, str], Dict[int, str], List[int]]:
	"""
	Generate explanations for PDF pages with page-level cache recall support.
	
	Args:
		existing_explanations: Existing explanations dict (0-indexed page -> explanation).
			Pages with non-empty explanations will be skipped (page-level cache recall).
		file_hash: File hash for cache. If provided, will try to load existing explanations
			from cache if existing_explanations is not provided.
		... (other parameters same as before)
	"""
	if not api_key:
		raise ValueError("api_key is required to generate explanations")
	if not model_name:
		raise ValueError("model_name is required to generate explanations")
	
	# Load existing explanations from cache if file_hash is provided and existing_explanations is not
	# Note: Only successful pages are loaded from cache (explanations dict)
	# Failed pages are stored separately in failed_pages list and are NOT recalled
	# This ensures failed pages are always reprocessed, which is the correct behavior
	if existing_explanations is None and file_hash:
		try:
			from app.cache_processor import load_result_from_file
			cached_result = load_result_from_file(file_hash)
			if cached_result:
				# Only load successful pages (explanations), not failed pages
				existing_explanations = cached_result.get("explanations", {})
				# Convert keys to int if they are strings (JSON always uses string keys)
				if existing_explanations:
					first_key = next(iter(existing_explanations.keys()), None)
					if first_key is not None and isinstance(first_key, str):
						try:
							existing_explanations = {int(k): v for k, v in existing_explanations.items()}
						except (ValueError, TypeError):
							# If conversion fails, keep original
							pass
				if on_log and existing_explanations:
					try:
						on_log(f"从缓存加载了 {len(existing_explanations)} 个页面的讲解")
					except Exception:
						pass
		except Exception as e:
			# Log but don't fail - cache loading is optional
			logger.debug(f"Failed to load cache for file_hash {file_hash}: {e}")
	
	# Initialize existing_explanations if still None
	if existing_explanations is None:
		existing_explanations = {}

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

	# Get global concurrency controller if available
	from .concurrency_controller import GlobalConcurrencyController
	global_controller = GlobalConcurrencyController.get_instance_sync()
	
	# Convert target_pages from 1-based to 0-based if provided
	target_pages_0based = None
	if target_pages is not None:
		# Assume input is 1-based, convert to 0-based
		target_pages_0based = [p - 1 for p in target_pages if p > 0]
	
	# Create real-time save callback if needed
	# This will be used to save partial progress
	on_partial_save_callback = None
	if file_hash:
		# Use provided file_hash for real-time saving
		try:
			from app.cache_processor import save_result_to_file
			
			def save_partial_state(explanations_dict: Dict[int, str], failed_pages_list: List[int]) -> None:
				"""Save partial state to cache file."""
				try:
					partial_result = {
						"status": "partial" if failed_pages_list else "completed",
						"explanations": explanations_dict,
						"failed_pages": failed_pages_list,
					}
					save_result_to_file(file_hash, partial_result)
				except Exception:
					# Silently fail - don't break processing if save fails
					pass
			
			on_partial_save_callback = save_partial_state
		except Exception:
			# If cache processor is not available, skip real-time saving
			pass
	
	# Define async function that adjusts limit and then processes
	async def _process_with_limit_adjustment():
		# Adjust global concurrency limit to user-specified value
		# This makes "concurrency" parameter control total LLM concurrent pages across all files
		# Wait for completion if new limit is smaller than current active requests
		await global_controller.adjust_limit_async(
			max(1, concurrency),
			wait_for_completion=True  # Wait for current requests to complete
		)
		
		# Now process with the adjusted limit
		return await _generate_explanations_async(
			llm_client=llm_client,
			page_images=[img if img else b"" for img in page_images],
			user_prompt=user_prompt,
			context_prompt=context_prompt,
			use_context=use_context,
			concurrency=max(1, concurrency),
			on_progress=on_progress,
			on_log=on_log,
			global_concurrency_controller=global_controller,
			on_page_status=on_page_status,
			target_pages=target_pages_0based,
			on_partial_save=on_partial_save_callback,
			existing_explanations=existing_explanations,
		)
	
	# Initial processing
	explanations, preview_images, failed_pages = _run_async(_process_with_limit_adjustment())
	
	# Auto-retry failed pages if enabled
	if auto_retry_failed_pages and failed_pages and max_auto_retries > 0:
		if on_log:
			try:
				on_log(f"开始自动重试 {len(failed_pages)} 个失败页面（最多重试 {max_auto_retries} 次）")
			except Exception:
				pass
		
		for retry_attempt in range(max_auto_retries):
			if not failed_pages:
				break
			
			if on_log:
				try:
					on_log(f"自动重试第 {retry_attempt + 1} 次，剩余失败页面: {', '.join(map(str, failed_pages))}")
				except Exception:
					pass
			
			# Retry failed pages (convert 1-based to 0-based)
			failed_pages_0based = [p - 1 for p in failed_pages]
			new_explanations, _, new_failed_pages = _run_async(
				_generate_explanations_async(
					llm_client=llm_client,
					page_images=[img if img else b"" for img in page_images],
					user_prompt=user_prompt,
					context_prompt=context_prompt,
					use_context=use_context,
					concurrency=max(1, concurrency),
					on_progress=on_progress,
					on_log=on_log,
					global_concurrency_controller=global_controller,
					on_page_status=on_page_status,
					target_pages=failed_pages_0based,
					on_partial_save=on_partial_save_callback,
					existing_explanations=existing_explanations,
				)
			)
			
			# Merge new explanations with existing ones
			explanations.update(new_explanations)
			
			# Update failed pages list (only keep pages that still failed)
			failed_pages = new_failed_pages
			
			if on_log:
				try:
					if failed_pages:
						on_log(f"自动重试第 {retry_attempt + 1} 次完成，仍有 {len(failed_pages)} 页失败")
					else:
						on_log(f"自动重试第 {retry_attempt + 1} 次完成，所有页面已成功")
				except Exception:
					pass
		
		if on_log and failed_pages:
			try:
				on_log(f"自动重试完成，仍有 {len(failed_pages)} 页失败: {', '.join(map(str, failed_pages))}")
			except Exception:
				pass
	
	return explanations, preview_images, failed_pages


def retry_failed_pages(
	src_bytes: bytes,
	existing_explanations: Dict[int, str],
	failed_page_numbers: List[int],  # 1-based page numbers
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
	on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
	file_hash: Optional[str] = None,
) -> Tuple[Dict[int, str], Dict[int, str], List[int]]:
	"""
	Retry generating explanations for failed pages only.
	
	Args:
		src_bytes: Source PDF bytes
		existing_explanations: Existing explanations dict (0-indexed page -> explanation)
		failed_page_numbers: List of failed page numbers (1-based)
		... (other parameters same as generate_explanations)
		
	Returns:
		Tuple of (merged_explanations, preview_images, remaining_failed_pages)
		- merged_explanations: Combined dict with existing and new explanations (0-indexed)
		- preview_images: Preview images dict (1-indexed page -> base64 string)
		- remaining_failed_pages: List of page numbers that still failed (1-based)
	"""
	if not failed_page_numbers:
		# No failed pages to retry, return existing data
		# Generate preview images for all pages
		pdf_doc = fitz.open(stream=src_bytes, filetype="pdf")
		try:
			preview_images: Dict[int, str] = {}
			for page_index in range(pdf_doc.page_count):
				try:
					img_bytes = _page_png_bytes(pdf_doc, page_index, dpi)
					preview_images[page_index + 1] = base64.b64encode(img_bytes).decode("utf-8")
				except Exception:
					pass
		finally:
			pdf_doc.close()
		return existing_explanations, preview_images, []
	
	# Generate explanations only for failed pages
	# Pass existing_explanations to enable page-level cache recall
	# This ensures that if any failed pages are already in cache, they will be skipped
	new_explanations, preview_images, new_failed_pages = generate_explanations(
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
		on_progress=on_progress,
		on_log=on_log,
		use_context=use_context,
		context_prompt=context_prompt,
		llm_provider=llm_provider,
		api_base=api_base,
		on_page_status=on_page_status,
		target_pages=failed_page_numbers,
		auto_retry_failed_pages=False,  # Don't auto-retry in manual retry
		max_auto_retries=0,
		file_hash=file_hash,
		existing_explanations=existing_explanations,  # Pass existing explanations for cache recall
	)
	
	# Merge existing explanations with new ones
	merged_explanations = {**existing_explanations, **new_explanations}
	
	return merged_explanations, preview_images, new_failed_pages


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
    show_column_rule: bool = True,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None
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
        # 更新页面状态：开始处理
        if on_page_status:
            try:
                on_page_status(page_num, "processing", None)
            except Exception:
                pass
        
        try:
            screenshot_bytes = _page_png_bytes(src_doc, page_num, screenshot_dpi)
            screenshot_data.append({
                'page_num': page_num + 1,  # Convert to 1-indexed
                'image_bytes': screenshot_bytes
            })
            
            # 更新页面状态：完成
            if on_page_status:
                try:
                    on_page_status(page_num, "completed", None)
                except Exception:
                    pass
            
            # 更新进度
            if on_progress:
                try:
                    on_progress(page_num + 1, total_pages)
                except Exception:
                    pass
        except Exception as e:
            # 更新页面状态：失败
            if on_page_status:
                try:
                    on_page_status(page_num, "failed", str(e))
                except Exception:
                    pass
            
            # 更新进度
            if on_progress:
                try:
                    on_progress(page_num + 1, total_pages)
                except Exception:
                    pass
            raise
    
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

# Helper function to convert PDF to HTML using pdf2htmlEX (can be run in parallel)
def _convert_pdf_to_html_pdf2htmlex(
    src_bytes: bytes
) -> Tuple[Optional[str], Optional[List[str]], Optional[str]]:
    """
    Convert PDF to HTML using pdf2htmlEX (internal helper for parallel execution).
    
    Args:
        src_bytes: Source PDF file bytes
        
    Returns:
        (css_content, page_htmls_list, error_message)
    """
    import tempfile
    import os
    
    # Check if pdf2htmlEX is installed
    is_installed, message = HTMLPdf2htmlEXGenerator.check_pdf2htmlex_installed()
    if not is_installed:
        return None, None, f"pdf2htmlEX not available: {message}"
    
    # Create temporary directory for pdf2htmlEX output
    temp_dir = tempfile.mkdtemp()
    try:
        # Call pdf2htmlEX to convert PDF
        success, html_path, error = HTMLPdf2htmlEXGenerator.call_pdf2htmlex(
            src_bytes, temp_dir
        )
        
        if not success:
            return None, None, f"pdf2htmlEX conversion failed: {error}"
        
        # Parse pdf2htmlEX output
        css_content, page_htmls, error = HTMLPdf2htmlEXGenerator.parse_pdf2htmlex_html(html_path)
        
        if error or not page_htmls:
            return None, None, f"Failed to parse pdf2htmlEX output: {error}"
        
        return css_content, page_htmls, None
    finally:
        # Clean up temporary directory
        try:
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)
        except Exception:
            pass


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
    show_column_rule: bool = True,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None
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
    
    # Use helper function to get pdf2htmlEX conversion result
    # (This can be called in parallel with explanation generation)
    css_content, page_htmls, error = _convert_pdf_to_html_pdf2htmlex(src_bytes)
    
    if error or not page_htmls:
        raise RuntimeError(f"pdf2htmlEX conversion failed: {error}")
    
    total_pages = len(page_htmls)
    
    # 更新进度：pdf2htmlEX 转换完成，开始解析页面
    if on_progress:
        try:
            on_progress(0, total_pages)  # 转换完成，开始处理页面
        except Exception:
            pass
    
    # Convert explanations from 0-indexed to 1-indexed
    explanations_1indexed = {
        page_num + 1: text 
        for page_num, text in explanations.items()
    }
    
    # 更新每个页面的状态（解析阶段）
    for page_num in range(total_pages):
        if on_page_status:
            try:
                on_page_status(page_num, "processing", None)
            except Exception:
                pass
        
        if on_progress:
            try:
                on_progress(page_num + 1, total_pages)
            except Exception:
                pass
        
        if on_page_status:
            try:
                on_page_status(page_num, "completed", None)
            except Exception:
                pass
    
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
    "retry_failed_pages",
    "process_markdown_mode",
]