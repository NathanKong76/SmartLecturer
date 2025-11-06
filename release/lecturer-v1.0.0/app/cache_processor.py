"""
Cache processing functions.

This module contains cached processing functions to avoid circular imports
between streamlit_app and ui_helpers.
"""

from typing import Dict, Any, Optional
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
		json.dump(result_copy, f, ensure_ascii=False, indent=2)
	return filepath


def load_result_from_file(file_hash: str) -> Optional[Dict[str, Any]]:
	"""Load processing result from temporary file."""
	filepath = os.path.join(TEMP_DIR, f"{file_hash}.json")
	if not os.path.exists(filepath):
		return None
	try:
		with open(filepath, 'r', encoding='utf-8') as f:
			return json.load(f)
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


@st.cache_data
def cached_process_pdf(src_bytes: bytes, params: dict) -> dict:
	"""Cached PDF processing function."""
	from app.services import pdf_processor
	
	file_hash = get_file_hash(src_bytes, params)
	column_padding = params.get("column_padding", 10)
	
	# Try to load from cache file
	cached_result = load_result_from_file(file_hash)
	if cached_result and cached_result.get("status") == "completed":
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
		
		result = {
			"status": "completed",
			"pdf_bytes": result_bytes,
			"explanations": explanations,
			"failed_pages": failed_pages
		}
		
		# Save to cache file
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
	if cached_result and cached_result.get("status") == "completed":
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
		)
		
		result = {
			"status": "completed",
			"markdown_content": markdown_content,
			"explanations": explanations,
			"failed_pages": failed_pages
		}
		
		# Save to cache file
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

