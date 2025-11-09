"""
Cache processing functions.

This module contains cached processing functions to avoid circular imports
between streamlit_app and ui_helpers.
"""

from typing import Dict, Any, Optional, Tuple, List
import streamlit as st
import os
import json
import hashlib
import tempfile

# Cache utilities (moved from streamlit_app to avoid circular import)
TEMP_DIR = os.path.join(tempfile.gettempdir(), "pdf_processor_cache")
os.makedirs(TEMP_DIR, exist_ok=True)


def get_file_hash(file_bytes: bytes, params: dict) -> str:
	"""Generate hash based on file content and parameters."""
	content = file_bytes + json.dumps(params, sort_keys=True).encode('utf-8')
	return hashlib.md5(content).hexdigest()


def save_result_to_file(file_hash: str, result: dict) -> str:
	"""Save processing result to temporary file."""
	filepath = os.path.join(TEMP_DIR, f"{file_hash}.json")
	with open(filepath, 'w', encoding='utf-8') as f:
		# Don't save pdf_bytes to file, only save other information
		result_copy = result.copy()
		result_copy.pop('pdf_bytes', None)
		
		# If status is not explicitly set, determine it based on failed_pages
		if "status" not in result_copy:
			failed_pages = result_copy.get("failed_pages", [])
			if failed_pages:
				result_copy["status"] = "partial"
			else:
				result_copy["status"] = "completed"
		
		# Add timestamp for tracking
		from datetime import datetime
		result_copy["timestamp"] = datetime.now().isoformat()
		
		json.dump(result_copy, f, ensure_ascii=False, indent=2)
	return filepath


def load_result_from_file(file_hash: str) -> Optional[Dict[str, Any]]:
	"""Load processing result from temporary file."""
	filepath = os.path.join(TEMP_DIR, f"{file_hash}.json")
	if not os.path.exists(filepath):
		return None
	try:
		with open(filepath, 'r', encoding='utf-8') as f:
			result = json.load(f)
			
			# Convert explanations dict keys from string to int (JSON always uses string keys)
			if "explanations" in result and isinstance(result["explanations"], dict):
				explanations = result["explanations"]
				# Check if keys are strings (from JSON) and convert to int
				if explanations:
					first_key = next(iter(explanations.keys()))
					if isinstance(first_key, str):
						try:
							result["explanations"] = {int(k): v for k, v in explanations.items()}
						except (ValueError, TypeError):
							# If conversion fails, keep original (shouldn't happen normally)
							pass
			
			return result
	except (json.JSONDecodeError, UnicodeDecodeError) as e:
		# Log warning but don't raise - corrupted cache should be handled gracefully
		try:
			import logging
			logging.getLogger(__name__).warning(f"Failed to load cache file {filepath}: {e}")
			# Try to remove corrupted cache file
			os.remove(filepath)
		except OSError:
			pass
		return None
	except Exception as e:
		# Log unexpected errors but don't crash
		try:
			import logging
			logging.getLogger(__name__).error(f"Unexpected error loading cache file {filepath}: {e}", exc_info=True)
		except Exception:
			pass
		return None


def get_cache_stats() -> Dict[str, Any]:
	"""Get cache statistics."""
	if not os.path.exists(TEMP_DIR):
		return {
			"file_count": 0,
			"total_size": 0,
			"total_size_mb": 0.0
		}
	
	cache_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.json')]
	total_size = 0
	
	for filename in cache_files:
		filepath = os.path.join(TEMP_DIR, filename)
		try:
			total_size += os.path.getsize(filepath)
		except OSError:
			pass
	
	return {
		"file_count": len(cache_files),
		"total_size": total_size,
		"total_size_mb": round(total_size / (1024 * 1024), 2)
	}


def clear_cache() -> Dict[str, Any]:
	"""Clear all cache files and Streamlit memory cache."""
	if not os.path.exists(TEMP_DIR):
		return {
			"success": True,
			"deleted_count": 0,
			"deleted_size_mb": 0.0
		}
	
	cache_files = [f for f in os.listdir(TEMP_DIR) if f.endswith('.json')]
	deleted_count = 0
	deleted_size = 0
	
	for filename in cache_files:
		filepath = os.path.join(TEMP_DIR, filename)
		try:
			file_size = os.path.getsize(filepath)
			os.remove(filepath)
			deleted_count += 1
			deleted_size += file_size
		except OSError as e:
			import logging
			logging.getLogger(__name__).warning(f"Failed to delete cache file {filepath}: {e}")
	
	# Clear Streamlit memory cache for cached functions
	try:
		cached_process_pdf.clear()
		cached_process_markdown.clear()
	except Exception:
		# If cache clearing fails, continue anyway
		pass
	
	return {
		"success": True,
		"deleted_count": deleted_count,
		"deleted_size_mb": round(deleted_size / (1024 * 1024), 2)
	}


def validate_cache_data(
	src_bytes: bytes,
	existing_explanations: Dict[int, str],
	failed_pages: List[int]
) -> Tuple[bool, Dict[int, str], List[int], List[str]]:
	"""
	Validate cache data consistency and fix issues if found.
	
	Args:
		src_bytes: Source PDF bytes
		existing_explanations: Existing explanations dict (0-indexed page -> explanation)
		failed_pages: List of failed page numbers (1-based)
		
	Returns:
		Tuple of (is_valid, fixed_explanations, fixed_failed_pages, warnings)
		- is_valid: Whether cache data is valid (after fixing)
		- fixed_explanations: Fixed explanations dict
		- fixed_failed_pages: Fixed failed pages list
		- warnings: List of warning messages about issues found and fixed
	"""
	import fitz
	
	warnings = []
	
	# Get PDF page count
	try:
		pdf_doc = fitz.open(stream=src_bytes, filetype="pdf")
		page_count = pdf_doc.page_count
		pdf_doc.close()
	except Exception as e:
		warnings.append(f"无法读取PDF页数: {str(e)}")
		return False, {}, [], warnings
	
	# Convert explanations keys to ensure they are int (0-based)
	fixed_explanations = {}
	for page_idx, explanation in existing_explanations.items():
		try:
			page_idx_int = int(page_idx)
			if 0 <= page_idx_int < page_count:
				fixed_explanations[page_idx_int] = explanation
			else:
				warnings.append(f"移除无效的页面索引 {page_idx_int} (PDF只有 {page_count} 页)")
		except (ValueError, TypeError):
			warnings.append(f"移除无效的页面索引: {page_idx}")
	
	# Convert failed_pages to ensure they are int (1-based) and valid
	fixed_failed_pages = []
	seen_failed = set()
	for page_num in failed_pages:
		try:
			page_num_int = int(page_num)
			if 1 <= page_num_int <= page_count:
				if page_num_int not in seen_failed:
					fixed_failed_pages.append(page_num_int)
					seen_failed.add(page_num_int)
			else:
				warnings.append(f"移除无效的失败页面编号 {page_num_int} (PDF只有 {page_count} 页)")
		except (ValueError, TypeError):
			warnings.append(f"移除无效的失败页面编号: {page_num}")
	
	# Check for conflicts: pages that are both in explanations and failed_pages
	conflict_pages = []
	for page_num in fixed_failed_pages:
		page_idx = page_num - 1  # Convert 1-based to 0-based
		if page_idx in fixed_explanations:
			conflict_pages.append(page_num)
	
	if conflict_pages:
		# Remove conflicts from failed_pages (assume explanations are correct)
		fixed_failed_pages = [p for p in fixed_failed_pages if p not in conflict_pages]
		warnings.append(f"发现冲突: 页面 {', '.join(map(str, conflict_pages))} 既在成功列表又在失败列表中，已从失败列表移除")
	
	# Check for missing pages: pages that are neither in explanations nor failed_pages
	success_page_indices = set(fixed_explanations.keys())
	failed_page_indices = {p - 1 for p in fixed_failed_pages}  # Convert to 0-based
	all_page_indices = set(range(page_count))
	missing_page_indices = all_page_indices - success_page_indices - failed_page_indices
	
	if missing_page_indices:
		# Add missing pages to failed_pages (1-based)
		missing_pages = sorted([idx + 1 for idx in missing_page_indices])
		fixed_failed_pages.extend(missing_pages)
		fixed_failed_pages.sort()
		warnings.append(f"发现遗漏的页面: {', '.join(map(str, missing_pages))}，已添加到失败列表")
	
	# Determine if cache is valid
	# Cache is valid if all pages are accounted for (either in explanations or failed_pages)
	# Recalculate failed_page_indices after all fixes
	final_failed_page_indices = {p - 1 for p in fixed_failed_pages}  # Convert to 0-based
	all_accounted = len(success_page_indices) + len(final_failed_page_indices) == page_count
	is_valid = all_accounted and len(conflict_pages) == 0
	
	return is_valid, fixed_explanations, fixed_failed_pages, warnings


@st.cache_data
def cached_process_pdf(src_bytes: bytes, params: dict) -> dict:
	"""Cached PDF processing function."""
	from app.services import pdf_processor
	
	file_hash = get_file_hash(src_bytes, params)
	column_padding = params.get("column_padding", 10)
	
	# Try to load from cache file
	cached_result = load_result_from_file(file_hash)
	if cached_result:
		cache_status = cached_result.get("status")
		
		# Handle completed cache
		if cache_status == "completed":
			# If cached, need to regenerate PDF bytes (bytes can't be serialized to JSON)
			try:
				result_bytes = pdf_processor.compose_pdf(
					src_bytes,
					cached_result["explanations"],
					params["right_ratio"],
					params["font_size"],
					font_name=(params.get("cjk_font_name") or "SimHei"),
					render_mode=params.get("render_mode", "markdown"),
					line_spacing=params["line_spacing"],
					column_padding=column_padding
				)
				cached_result["pdf_bytes"] = result_bytes
				return cached_result
			except Exception as e:
				# Failed to regenerate PDF from cache, return error result
				return {
					"status": "failed",
					"pdf_bytes": None,
					"explanations": {},
					"failed_pages": [],
					"error": f"从缓存重新合成PDF失败: {str(e)}"
				}
		
		# Handle partial cache - continue processing failed pages
		elif cache_status == "partial":
			existing_explanations = cached_result.get("explanations", {})
			failed_pages = cached_result.get("failed_pages", [])
			
			# Validate and fix cache data
			is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
				src_bytes, existing_explanations, failed_pages
			)
			
			# Log validation warnings if any
			if validation_warnings:
				try:
					import logging
					logger = logging.getLogger(__name__)
					for warning in validation_warnings:
						logger.warning(f"Cache validation warning: {warning}")
				except Exception:
					pass
			
			# If validation failed or no failed pages after fixing, handle accordingly
			if not is_valid and not fixed_failed_pages:
				# Cache data is invalid, reprocess from scratch
				# Fall through to reprocessing section
				pass
			elif fixed_failed_pages and fixed_explanations:
				# Continue processing with fixed data
				try:
					new_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
						src_bytes=src_bytes,
						existing_explanations=fixed_explanations,
						failed_page_numbers=fixed_failed_pages,
						api_key=params["api_key"],
						model_name=params["model_name"],
						user_prompt=params["user_prompt"],
						temperature=params["temperature"],
						max_tokens=params["max_tokens"],
						dpi=params["dpi"],
						concurrency=params["concurrency"],
						rpm_limit=params["rpm_limit"],
						tpm_budget=params["tpm_budget"],
						rpd_limit=params["rpd_limit"],
						use_context=params.get("use_context", False),
						context_prompt=params.get("context_prompt", None),
						llm_provider=params.get("llm_provider", "gemini"),
						api_base=params.get("api_base"),
						file_hash=file_hash,
					)
					
					# Merge explanations
					merged_explanations = {**fixed_explanations, **new_explanations}
					
					# Determine final status
					final_status = "completed" if not remaining_failed_pages else "partial"
					
					result_bytes = pdf_processor.compose_pdf(
						src_bytes,
						merged_explanations,
						params["right_ratio"],
						params["font_size"],
						font_name=(params.get("cjk_font_name") or "SimHei"),
						render_mode=params.get("render_mode", "markdown"),
						line_spacing=params["line_spacing"],
						column_padding=column_padding
					)
					
					result = {
						"status": final_status,
						"pdf_bytes": result_bytes,
						"explanations": merged_explanations,
						"failed_pages": remaining_failed_pages
					}
					
					# Save updated result to cache
					save_result_to_file(file_hash, result)
					
					return result
				except Exception as e:
					# If retry fails, return partial result with error info
					return {
						"status": "partial",
						"pdf_bytes": None,
						"explanations": fixed_explanations,
						"failed_pages": fixed_failed_pages,
						"error": f"继续处理失败页面时出错: {str(e)}"
					}
			else:
				# No failed pages after validation, but status is partial - might be completed now
				# Try to regenerate PDF to verify
				try:
					result_bytes = pdf_processor.compose_pdf(
						src_bytes,
						fixed_explanations,
						params["right_ratio"],
						params["font_size"],
						font_name=(params.get("cjk_font_name") or "SimHei"),
						render_mode=params.get("render_mode", "markdown"),
						line_spacing=params["line_spacing"],
						column_padding=column_padding
					)
					result = {
						"status": "completed",
						"pdf_bytes": result_bytes,
						"explanations": fixed_explanations,
						"failed_pages": []
					}
					save_result_to_file(file_hash, result)
					return result
				except Exception as e:
					# Failed to regenerate, fall through to reprocessing
					pass
	
	# No cache or invalid cache, reprocess
	try:
		explanations, preview_images, failed_pages = pdf_processor.generate_explanations(
			src_bytes=src_bytes,
			api_key=params["api_key"],
			model_name=params["model_name"],
			user_prompt=params["user_prompt"],
			temperature=params["temperature"],
			max_tokens=params["max_tokens"],
			dpi=params["dpi"],
			concurrency=params["concurrency"],
			rpm_limit=params["rpm_limit"],
			tpm_budget=params["tpm_budget"],
			rpd_limit=params["rpd_limit"],
			use_context=params.get("use_context", False),
			context_prompt=params.get("context_prompt", None),
			llm_provider=params.get("llm_provider", "gemini"),
			api_base=params.get("api_base"),
			auto_retry_failed_pages=params.get("auto_retry_failed_pages", True),
			max_auto_retries=params.get("max_auto_retries", 2),
			file_hash=file_hash,
		)
		
		result_bytes = pdf_processor.compose_pdf(
			src_bytes,
			explanations,
			params["right_ratio"],
			params["font_size"],
			font_name=(params.get("cjk_font_name") or "SimHei"),
			render_mode=params.get("render_mode", "markdown"),
			line_spacing=params["line_spacing"],
			column_padding=column_padding
		)
		
		# Determine status based on failed pages
		result_status = "completed" if not failed_pages else "partial"
		
		result = {
			"status": result_status,
			"pdf_bytes": result_bytes,
			"explanations": explanations,
			"failed_pages": failed_pages
		}
		
		# Save to cache file (will set status correctly if not set)
		save_result_to_file(file_hash, result)
		
		return result
		
	except Exception as e:
		result = {
			"status": "failed",
			"pdf_bytes": None,
			"explanations": {},
			"failed_pages": [],
			"error": str(e)
		}
		return result


@st.cache_data
def cached_process_markdown(src_bytes: bytes, params: dict) -> dict:
	"""Cached markdown processing function."""
	from app.services import pdf_processor
	
	file_hash = get_file_hash(src_bytes, params)
	
	# Try to load from cache file
	cached_result = load_result_from_file(file_hash)
	if cached_result:
		cache_status = cached_result.get("status")
		
		if cache_status == "completed":
			# If cached, need to regenerate markdown content
			try:
				markdown_content, explanations, failed_pages, _ = pdf_processor.process_markdown_mode(
					src_bytes=src_bytes,
					api_key=params["api_key"],
					model_name=params["model_name"],
					user_prompt=params["user_prompt"],
					temperature=params["temperature"],
					max_tokens=params["max_tokens"],
					dpi=params["dpi"],
					screenshot_dpi=params["screenshot_dpi"],
					concurrency=params["concurrency"],
					rpm_limit=params["rpm_limit"],
					tpm_budget=params["tpm_budget"],
					rpd_limit=params["rpd_limit"],
					embed_images=params["embed_images"],
					title=params["markdown_title"],
					use_context=params.get("use_context", False),
					context_prompt=params.get("context_prompt", None),
					llm_provider=params.get("llm_provider", "gemini"),
					api_base=params.get("api_base"),
				)
				cached_result["markdown_content"] = markdown_content
				return cached_result
			except Exception as e:
				# Failed to regenerate markdown from cache, return error result
				return {
					"status": "failed",
					"markdown_content": "",
					"explanations": {},
					"failed_pages": [],
					"error": f"从缓存重新生成markdown失败: {str(e)}"
				}
		
		elif cache_status == "partial":
			# Handle partial success - continue processing failed pages
			existing_explanations = cached_result.get("explanations", {})
			failed_pages = cached_result.get("failed_pages", [])
			
			# Validate and fix cache data
			is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
				src_bytes, existing_explanations, failed_pages
			)
			
			# Log validation warnings if any
			if validation_warnings:
				try:
					import logging
					logger = logging.getLogger(__name__)
					for warning in validation_warnings:
						logger.warning(f"Cache validation warning: {warning}")
				except Exception:
					pass
			
			# If validation failed or no failed pages after fixing, handle accordingly
			if not is_valid and not fixed_failed_pages:
				# Cache data is invalid, reprocess from scratch
				# Fall through to reprocessing section
				pass
			elif fixed_failed_pages and fixed_explanations:
				# Continue processing with fixed data
				try:
					new_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
						src_bytes=src_bytes,
						existing_explanations=fixed_explanations,
						failed_page_numbers=fixed_failed_pages,
						api_key=params["api_key"],
						model_name=params["model_name"],
						user_prompt=params["user_prompt"],
						temperature=params["temperature"],
						max_tokens=params["max_tokens"],
						dpi=params["dpi"],
						concurrency=params["concurrency"],
						rpm_limit=params["rpm_limit"],
						tpm_budget=params["tpm_budget"],
						rpd_limit=params["rpd_limit"],
						use_context=params.get("use_context", False),
						context_prompt=params.get("context_prompt", None),
						llm_provider=params.get("llm_provider", "gemini"),
						api_base=params.get("api_base"),
						file_hash=file_hash,
					)
					
					# Merge explanations
					merged_explanations = {**fixed_explanations, **new_explanations}
					
					# Generate markdown with merged explanations
					from app.services.markdown_generator import generate_markdown_with_screenshots
					markdown_content, _ = generate_markdown_with_screenshots(
						src_bytes=src_bytes,
						explanations=merged_explanations,
						screenshot_dpi=params["screenshot_dpi"],
						embed_images=params["embed_images"],
						title=params["markdown_title"],
					)
					
					# Determine final status
					final_status = "completed" if not remaining_failed_pages else "partial"
					
					result = {
						"status": final_status,
						"markdown_content": markdown_content,
						"explanations": merged_explanations,
						"failed_pages": remaining_failed_pages
					}
					
					# Save updated result to cache
					save_result_to_file(file_hash, result)
					
					return result
				except Exception as e:
					# If retry fails, return partial result with error info
					return {
						"status": "partial",
						"markdown_content": "",
						"explanations": fixed_explanations,
						"failed_pages": fixed_failed_pages,
						"error": f"继续处理失败页面时出错: {str(e)}"
					}
			else:
				# No failed pages after validation, but status is partial - might be completed now
				# Try to regenerate markdown to verify
				try:
					from app.services.markdown_generator import generate_markdown_with_screenshots
					markdown_content, _ = generate_markdown_with_screenshots(
						src_bytes=src_bytes,
						explanations=fixed_explanations,
						screenshot_dpi=params["screenshot_dpi"],
						embed_images=params["embed_images"],
						title=params["markdown_title"],
					)
					result = {
						"status": "completed",
						"markdown_content": markdown_content,
						"explanations": fixed_explanations,
						"failed_pages": []
					}
					save_result_to_file(file_hash, result)
					return result
				except Exception as e:
					# Failed to regenerate, fall through to reprocessing
					pass
	
	# No cache or invalid cache, reprocess
	try:
		markdown_content, explanations, failed_pages, _ = pdf_processor.process_markdown_mode(
			src_bytes=src_bytes,
			api_key=params["api_key"],
			model_name=params["model_name"],
			user_prompt=params["user_prompt"],
			temperature=params["temperature"],
			max_tokens=params["max_tokens"],
			dpi=params["dpi"],
			screenshot_dpi=params["screenshot_dpi"],
			concurrency=params["concurrency"],
			rpm_limit=params["rpm_limit"],
			tpm_budget=params["tpm_budget"],
			rpd_limit=params["rpd_limit"],
			embed_images=params["embed_images"],
			title=params["markdown_title"],
			use_context=params.get("use_context", False),
			context_prompt=params.get("context_prompt", None),
		llm_provider=params.get("llm_provider", "gemini"),
		api_base=params.get("api_base"),
		)
		
		# Determine status based on failed pages
		result_status = "completed" if not failed_pages else "partial"
		
		result = {
			"status": result_status,
			"markdown_content": markdown_content,
			"explanations": explanations,
			"failed_pages": failed_pages
		}
		
		# Save to cache file (will set status correctly if not set)
		save_result_to_file(file_hash, result)
		
		return result
		
	except Exception as e:
		result = {
			"status": "failed",
			"markdown_content": "",
			"explanations": {},
			"failed_pages": [],
			"error": str(e)
		}
		return result

