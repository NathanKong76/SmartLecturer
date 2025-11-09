"""
UI helper functions for Streamlit app.

This module contains helper functions to reduce code duplication
and improve maintainability of the main Streamlit app.
"""

from typing import Dict, List, Optional, Tuple, Any, Callable
import logging
import streamlit as st
import threading

from app.services import pdf_processor
from app.services import constants

# Logger for background thread operations
logger = logging.getLogger(__name__)


def _is_main_thread() -> bool:
    """Check if we're in the main thread."""
    try:
        from streamlit.runtime.scriptrunner import get_script_run_ctx
        ctx = get_script_run_ctx()
        return ctx is not None
    except (ImportError, AttributeError, RuntimeError):
        return False


def safe_streamlit_call(func, *args, **kwargs):
    """
    Safely call Streamlit functions only in the main thread.
    In background threads, use logging instead.
    
    Args:
        func: Streamlit function to call (e.g., st.info, st.warning)
        *args: Arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
    """
    if _is_main_thread():
        try:
            return func(*args, **kwargs)
        except (RuntimeError, AttributeError) as e:
            # Fallback to logging if Streamlit call fails
            logger.info(f"Streamlit call failed, using log: {args[0] if args else ''}")
    else:
        # In background thread, use logging
        message = args[0] if args else str(kwargs)
        if func == st.info:
            logger.info(message)
        elif func == st.warning:
            logger.warning(message)
        elif func == st.error:
            logger.error(message)
        elif func == st.success:
            logger.info(f"SUCCESS: {message}")
        else:
            logger.info(message)


class StateManager:
    """Manages Streamlit session state with type safety."""
    
    @staticmethod
    def initialize():
        """Initialize all required session state variables."""
        defaults = {
            "batch_results": {},
            "batch_processing": False,
            "batch_zip_bytes": None,
            "batch_json_results": {},
            "batch_json_processing": False,
            "batch_json_zip_bytes": None,
            "detailed_progress_tracker": None,
        }
        for key, default_value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = default_value
    
    @staticmethod
    def get_batch_results() -> Dict[str, Dict[str, Any]]:
        """Get batch results from session state."""
        return st.session_state.get("batch_results", {})
    
    @staticmethod
    def set_batch_results(value: Dict[str, Dict[str, Any]]):
        """Set batch results in session state."""
        st.session_state["batch_results"] = value
    
    @staticmethod
    def is_processing() -> bool:
        """Check if batch processing is in progress."""
        return st.session_state.get("batch_processing", False)
    
    @staticmethod
    def set_processing(value: bool):
        """Set batch processing status."""
        st.session_state["batch_processing"] = value
    
    @staticmethod
    def get_progress_tracker():
        """Get detailed progress tracker from session state."""
        return st.session_state.get("detailed_progress_tracker")
    
    @staticmethod
    def set_progress_tracker(tracker):
        """Set detailed progress tracker in session state."""
        st.session_state["detailed_progress_tracker"] = tracker


def display_batch_status():
    """Display current batch processing status."""
    batch_results = StateManager.get_batch_results()
    if not batch_results:
        return
    
    total_files = len(batch_results)
    completed_files = sum(1 for r in batch_results.values() if r.get("status") == "completed")
    failed_files = sum(1 for r in batch_results.values() if r.get("status") == "failed")
    processing_files = sum(1 for r in batch_results.values() if r.get("status") == "processing")
    
    if processing_files > 0:
        st.info(f"🔄 正在处理中... 已完成: {completed_files}/{total_files} 个文件")
    elif completed_files > 0:
        st.success(f"✅ 处理完成！成功: {completed_files} 个文件，失败: {failed_files} 个文件")
    elif failed_files > 0:
        st.error(f"❌ 处理失败！失败: {failed_files} 个文件")


def validate_file_upload(uploaded_files: List, params: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate file upload and parameters.
    
    Args:
        uploaded_files: List of uploaded files
        params: Processing parameters
        
    Returns:
        (is_valid, error_message)
    """
    if not uploaded_files:
        return False, "请先上传 PDF 文件"
    
    if len(uploaded_files) > constants.MAX_FILES_PER_BATCH:
        return False, f"最多只能上传{constants.MAX_FILES_PER_BATCH}个文件"
    
    if not params.get("api_key"):
        provider = (params.get("llm_provider") or "gemini").lower()
        if provider == "openai":
            return False, "请在侧边栏填写 OpenAI API Key"
        return False, "请在侧边栏填写 GEMINI_API_KEY"
    
    return True, None


def process_single_file_pdf(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Process a single PDF file in PDF mode.
    
    Args:
        uploaded_file: Uploaded file object (optional, not used if src_bytes provided)
        filename: File name
        src_bytes: PDF file bytes
        params: Processing parameters
        cached_result: Cached result if available
        file_hash: File hash for cache
        on_progress: Progress callback (done, total)
        on_page_status: Page status callback (page_index, status, error)
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import get_file_hash, save_result_to_file, load_result_from_file
    
    column_padding_value = params.get("column_padding", 10)
    
    # Try to use cached result
    if cached_result:
        cache_status = cached_result.get("status")
        
        if cache_status == "completed":
            safe_streamlit_call(st.info, f"📋 {filename} 使用缓存结果")
            try:
                result_bytes = pdf_processor.compose_pdf(
                    src_bytes,
                    cached_result["explanations"],
                    params["right_ratio"],
                    params["font_size"],
                    font_name=(params.get("cjk_font_name") or "SimHei"),
                    render_mode=params.get("render_mode", "markdown"),
                    line_spacing=params["line_spacing"],
                    column_padding=column_padding_value
                )
                return {
                    "status": "completed",
                    "pdf_bytes": result_bytes,
                    "explanations": cached_result["explanations"],
                    "failed_pages": cached_result.get("failed_pages", []),
                    "json_bytes": None
                }
            except Exception as e:
                logger.warning(f"缓存重新合成失败，尝试重新处理: {str(e)}")
                # Fall through to reprocessing
        
        elif cache_status == "partial":
            # Handle partial success - continue processing failed pages
            existing_explanations = cached_result.get("explanations", {})
            failed_pages = cached_result.get("failed_pages", [])
            timestamp = cached_result.get("timestamp", "未知时间")
            
            # Validate and fix cache data
            from app.cache_processor import validate_cache_data
            is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
                src_bytes, existing_explanations, failed_pages
            )
            
            # Display validation warnings if any
            if validation_warnings:
                for warning in validation_warnings:
                    safe_streamlit_call(st.warning, f"⚠️ {warning}")
            
            # If validation failed or no failed pages after fixing, handle accordingly
            if not is_valid and not fixed_failed_pages:
                # Cache data is invalid, reprocess from scratch
                # Fall through to reprocessing section
                pass
            elif fixed_failed_pages and fixed_explanations:
                safe_streamlit_call(st.info, f"📋 {filename} 检测到部分成功状态（保存时间: {timestamp}）")
                safe_streamlit_call(st.info, f"已成功生成 {len(fixed_explanations)} 页讲解，还有 {len(fixed_failed_pages)} 页失败: {', '.join(map(str, fixed_failed_pages))}")
                safe_streamlit_call(st.info, "正在继续处理失败的页面...")
                
                try:
                    # Continue processing failed pages with fixed data
                    merged_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
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
                        on_progress=on_progress,
                        use_context=params.get("use_context", False),
                        context_prompt=params.get("context_prompt", None),
                        llm_provider=params.get("llm_provider", "gemini"),
                        api_base=params.get("api_base"),
                        on_page_status=on_page_status,
                        file_hash=file_hash,
                    )
                    
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
                        column_padding=column_padding_value
                    )
                    
                    result = {
                        "status": final_status,
                        "pdf_bytes": result_bytes,
                        "explanations": merged_explanations,
                        "failed_pages": remaining_failed_pages,
                        "json_bytes": None
                    }
                    
                    # Save updated result to cache
                    save_result_to_file(file_hash, result)
                    
                    if remaining_failed_pages:
                        safe_streamlit_call(st.warning, f"⚠️ {filename} 仍有 {len(remaining_failed_pages)} 页生成失败: {', '.join(map(str, remaining_failed_pages))}")
                    else:
                        safe_streamlit_call(st.success, f"✅ {filename} 所有页面都已成功生成讲解！")
                    
                    return result
                except Exception as e:
                    logger.warning(f"继续处理失败页面时出错: {str(e)}")
                    # Fall through to reprocessing or return partial result
                    safe_streamlit_call(st.error, f"继续处理失败页面时出错: {str(e)}")
                    # Return partial result with fixed explanations
                    try:
                        result_bytes = pdf_processor.compose_pdf(
                            src_bytes,
                            fixed_explanations,
                            params["right_ratio"],
                            params["font_size"],
                            font_name=(params.get("cjk_font_name") or "SimHei"),
                            render_mode=params.get("render_mode", "markdown"),
                            line_spacing=params["line_spacing"],
                            column_padding=column_padding_value
                        )
                        return {
                            "status": "partial",
                            "pdf_bytes": result_bytes,
                            "explanations": fixed_explanations,
                            "failed_pages": fixed_failed_pages,
                            "json_bytes": None
                        }
                    except Exception:
                        # If compose also fails, fall through to reprocessing
                        pass
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
                        column_padding=column_padding_value
                    )
                    result = {
                        "status": "completed",
                        "pdf_bytes": result_bytes,
                        "explanations": fixed_explanations,
                        "failed_pages": [],
                        "json_bytes": None
                    }
                    save_result_to_file(file_hash, result)
                    safe_streamlit_call(st.success, f"✅ {filename} 所有页面都已成功生成讲解！")
                    return result
                except Exception as e:
                    # Failed to regenerate, fall through to reprocessing
                    logger.warning(f"验证后重新生成PDF失败: {str(e)}")
                    pass
    
    # Process from scratch with progress callbacks
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
            on_progress=on_progress,
            use_context=params.get("use_context", False),
            context_prompt=params.get("context_prompt", None),
            llm_provider=params.get("llm_provider", "gemini"),
            api_base=params.get("api_base"),
            on_page_status=on_page_status,
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
            column_padding=column_padding_value
        )
        
        result_status = "completed" if not failed_pages else "partial"
        result = {
            "status": result_status,
            "pdf_bytes": result_bytes,
            "explanations": explanations,
            "failed_pages": failed_pages
        }
        
        # Save to cache file
        save_result_to_file(file_hash, result)
        
        return result
        
    except Exception as e:
        return {
            "status": "failed",
            "pdf_bytes": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def process_single_file_markdown(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Process a single file in Markdown mode.
    
    Args:
        uploaded_file: Uploaded file object (optional, not used if src_bytes provided)
        filename: File name
        src_bytes: PDF file bytes
        params: Processing parameters
        cached_result: Cached result if available
        file_hash: File hash for cache
        on_progress: Progress callback
        on_page_status: Page status callback
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import save_result_to_file
    
    # Try to use cached result
    if cached_result:
        cache_status = cached_result.get("status")
        
        if cache_status == "completed":
            safe_streamlit_call(st.info, f"📋 {filename} 使用缓存结果")
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
                return {
                    "status": "completed",
                    "markdown_content": markdown_content,
                    "explanations": explanations,
                    "failed_pages": failed_pages
                }
            except Exception as e:
                logger.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
                # Fall through to reprocessing
        
        elif cache_status == "partial":
            # Handle partial success for markdown mode
            existing_explanations = cached_result.get("explanations", {})
            failed_pages = cached_result.get("failed_pages", [])
            timestamp = cached_result.get("timestamp", "未知时间")
            
            # Validate and fix cache data
            from app.cache_processor import validate_cache_data
            is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
                src_bytes, existing_explanations, failed_pages
            )
            
            # Display validation warnings if any
            if validation_warnings:
                for warning in validation_warnings:
                    safe_streamlit_call(st.warning, f"⚠️ {warning}")
            
            # If validation failed or no failed pages after fixing, handle accordingly
            if not is_valid and not fixed_failed_pages:
                # Cache data is invalid, reprocess from scratch
                # Fall through to reprocessing section
                pass
            elif fixed_failed_pages and fixed_explanations:
                safe_streamlit_call(st.info, f"📋 {filename} 检测到部分成功状态（保存时间: {timestamp}）")
                safe_streamlit_call(st.info, f"已成功生成 {len(fixed_explanations)} 页讲解，还有 {len(fixed_failed_pages)} 页失败: {', '.join(map(str, fixed_failed_pages))}")
                safe_streamlit_call(st.info, "正在继续处理失败的页面...")
                
                try:
                    # Continue processing failed pages with fixed data
                    merged_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
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
                        on_progress=on_progress,
                        use_context=params.get("use_context", False),
                        context_prompt=params.get("context_prompt", None),
                        llm_provider=params.get("llm_provider", "gemini"),
                        api_base=params.get("api_base"),
                        on_page_status=on_page_status,
                        file_hash=file_hash,
                    )
                    
                    # Generate markdown with merged explanations
                    markdown_content, _images_dir = pdf_processor.generate_markdown_with_screenshots(
                        src_bytes=src_bytes,
                        explanations=merged_explanations,
                        screenshot_dpi=params["screenshot_dpi"],
                        embed_images=params["embed_images"],
                        title=params["markdown_title"],
                    )
                    
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
                    logger.warning(f"继续处理失败页面时出错: {str(e)}")
                    # Fall through to reprocessing
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
                    safe_streamlit_call(st.success, f"✅ {filename} 所有页面都已成功生成讲解！")
                    return result
                except Exception as e:
                    # Failed to regenerate, fall through to reprocessing
                    logger.warning(f"验证后重新生成markdown失败: {str(e)}")
                    pass
    
    # Process from scratch
    logger.info(f"处理 {filename} 中...")
    try:
        # Generate explanations with progress callbacks
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
            on_progress=on_progress,
            use_context=params.get("use_context", False),
            context_prompt=params.get("context_prompt", None),
            llm_provider=params.get("llm_provider", "gemini"),
            api_base=params.get("api_base"),
            on_page_status=on_page_status,
            auto_retry_failed_pages=params.get("auto_retry_failed_pages", True),
            max_auto_retries=params.get("max_auto_retries", 2),
            file_hash=file_hash,
        )
        
        # Generate markdown
        markdown_content, _images_dir = pdf_processor.generate_markdown_with_screenshots(
            src_bytes=src_bytes,
            explanations=explanations,
            screenshot_dpi=params["screenshot_dpi"],
            embed_images=params["embed_images"],
            title=params["markdown_title"],
        )
        
        result = {
            "status": "completed",
            "markdown_content": markdown_content,
            "explanations": explanations,
            "failed_pages": failed_pages
        }
        
        # Save to cache
        save_result_to_file(file_hash, result)
        
        return result
    except Exception as e:
        logger.error(f"处理 {filename} 时发生异常: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "markdown_content": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def process_single_file_html_screenshot(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Process a single file in HTML screenshot mode.
    
    Args:
        uploaded_file: Uploaded file object (optional, not used if src_bytes provided)
        filename: File name
        src_bytes: PDF file bytes
        params: Processing parameters
        cached_result: Cached result if available
        file_hash: File hash for cache
        on_progress: Progress callback
        on_page_status: Page status callback
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import save_result_to_file
    
    # Try to use cached result
    if cached_result:
        cache_status = cached_result.get("status")
        
        if cache_status == "completed":
            safe_streamlit_call(st.info, f"📋 {filename} 使用缓存结果")
            try:
                # Generate HTML from cached explanations
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                # Use user-configured title if provided, otherwise use filename
                title = params.get("markdown_title", "").strip() or base_name
                html_content = pdf_processor.generate_html_screenshot_document(
                    src_bytes=src_bytes,
                    explanations=cached_result["explanations"],
                    screenshot_dpi=params.get("screenshot_dpi", 150),
                    title=title,
                    font_name=params.get("cjk_font_name", "SimHei"),
                    font_size=params.get("font_size", 14),
                    line_spacing=params.get("line_spacing", 1.2),
                    column_count=params.get("html_column_count", 2),
                    column_gap=params.get("html_column_gap", 20),
                    show_column_rule=params.get("html_show_column_rule", True)
                )
                return {
                    "status": "completed",
                    "html_content": html_content,
                    "explanations": cached_result["explanations"],
                    "failed_pages": cached_result.get("failed_pages", [])
                }
            except Exception as e:
                logger.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
                # Fall through to reprocessing
        
        elif cache_status == "partial":
            # Handle partial success for HTML screenshot mode
            existing_explanations = cached_result.get("explanations", {})
            failed_pages = cached_result.get("failed_pages", [])
            timestamp = cached_result.get("timestamp", "未知时间")
            
            # Validate and fix cache data
            from app.cache_processor import validate_cache_data
            is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
                src_bytes, existing_explanations, failed_pages
            )
            
            # Display validation warnings if any
            if validation_warnings:
                for warning in validation_warnings:
                    safe_streamlit_call(st.warning, f"⚠️ {warning}")
            
            # If validation failed or no failed pages after fixing, handle accordingly
            if not is_valid and not fixed_failed_pages:
                # Cache data is invalid, reprocess from scratch
                # Fall through to reprocessing section
                pass
            elif fixed_failed_pages and fixed_explanations:
                safe_streamlit_call(st.info, f"📋 {filename} 检测到部分成功状态（保存时间: {timestamp}）")
                safe_streamlit_call(st.info, f"已成功生成 {len(fixed_explanations)} 页讲解，还有 {len(fixed_failed_pages)} 页失败: {', '.join(map(str, fixed_failed_pages))}")
                safe_streamlit_call(st.info, "正在继续处理失败的页面...")
                
                try:
                    # Continue processing failed pages with fixed data
                    merged_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
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
                        on_progress=on_progress,
                        use_context=params.get("use_context", False),
                        context_prompt=params.get("context_prompt", None),
                        llm_provider=params.get("llm_provider", "gemini"),
                        api_base=params.get("api_base"),
                        on_page_status=on_page_status,
                        file_hash=file_hash,
                    )
                    
                    # Generate HTML with merged explanations
                    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    title = params.get("markdown_title", "").strip() or base_name
                    html_content = pdf_processor.generate_html_screenshot_document(
                        src_bytes=src_bytes,
                        explanations=merged_explanations,
                        screenshot_dpi=params.get("screenshot_dpi", 150),
                        title=title,
                        font_name=params.get("cjk_font_name", "SimHei"),
                        font_size=params.get("font_size", 14),
                        line_spacing=params.get("line_spacing", 1.2),
                        column_count=params.get("html_column_count", 2),
                        column_gap=params.get("html_column_gap", 20),
                        show_column_rule=params.get("html_show_column_rule", True)
                    )
                    
                    final_status = "completed" if not remaining_failed_pages else "partial"
                    result = {
                        "status": final_status,
                        "html_content": html_content,
                        "explanations": merged_explanations,
                        "failed_pages": remaining_failed_pages
                    }
                    
                    # Save updated result to cache
                    save_result_to_file(file_hash, result)
                    
                    return result
                except Exception as e:
                    logger.warning(f"继续处理失败页面时出错: {str(e)}")
                    # Fall through to reprocessing
            else:
                # No failed pages after validation, but status is partial - might be completed now
                # Try to regenerate HTML to verify
                try:
                    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    title = params.get("markdown_title", "").strip() or base_name
                    html_content = pdf_processor.generate_html_screenshot_document(
                        src_bytes=src_bytes,
                        explanations=fixed_explanations,
                        screenshot_dpi=params.get("screenshot_dpi", 150),
                        title=title,
                        font_name=params.get("cjk_font_name", "SimHei"),
                        font_size=params.get("font_size", 14),
                        line_spacing=params.get("line_spacing", 1.2),
                        column_count=params.get("html_column_count", 2),
                        column_gap=params.get("html_column_gap", 20),
                        show_column_rule=params.get("html_show_column_rule", True)
                    )
                    result = {
                        "status": "completed",
                        "html_content": html_content,
                        "explanations": fixed_explanations,
                        "failed_pages": []
                    }
                    save_result_to_file(file_hash, result)
                    safe_streamlit_call(st.success, f"✅ {filename} 所有页面都已成功生成讲解！")
                    return result
                except Exception as e:
                    # Failed to regenerate, fall through to reprocessing
                    logger.warning(f"验证后重新生成HTML失败: {str(e)}")
                    pass
    
    # Process from scratch
    logger.info(f"处理 {filename} 中...")
    try:
        # First get explanations (reuse markdown processing for explanation generation)
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
            on_progress=on_progress,
            use_context=params.get("use_context", False),
            context_prompt=params.get("context_prompt", None),
            llm_provider=params.get("llm_provider", "gemini"),
            api_base=params.get("api_base"),
            on_page_status=on_page_status,
            auto_retry_failed_pages=params.get("auto_retry_failed_pages", True),
            max_auto_retries=params.get("max_auto_retries", 2),
        )
        
        if explanations:
            # Generate HTML screenshot document
            try:
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                # Use user-configured title if provided, otherwise use filename
                title = params.get("markdown_title", "").strip() or base_name
                html_content = pdf_processor.generate_html_screenshot_document(
                    src_bytes=src_bytes,
                    explanations=explanations,
                    screenshot_dpi=params.get("screenshot_dpi", 150),
                    title=title,
                    font_name=params.get("cjk_font_name", "SimHei"),
                    font_size=params.get("font_size", 14),
                    line_spacing=params.get("line_spacing", 1.2),
                    column_count=params.get("html_column_count", 2),
                    column_gap=params.get("html_column_gap", 20),
                    show_column_rule=params.get("html_show_column_rule", True)
                )
                result_status = "completed" if not failed_pages else "partial"
                result = {
                    "status": result_status,
                    "html_content": html_content,
                    "explanations": explanations,
                    "failed_pages": failed_pages
                }
                save_result_to_file(file_hash, result)
                return result
            except Exception as e:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"HTML生成失败: {str(e)}"
                }
        else:
            return {
                "status": "failed",
                "html_content": None,
                "explanations": {},
                "failed_pages": [],
                "error": "生成讲解失败"
            }
    except Exception as e:
        logger.error(f"处理 {filename} 时发生异常: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "html_content": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def process_single_file_html_pdf2htmlex(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str,
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Process a single file in HTML pdf2htmlEX mode.
    
    Args:
        uploaded_file: Uploaded file object (optional, not used if src_bytes provided)
        filename: File name
        src_bytes: PDF file bytes
        params: Processing parameters
        cached_result: Cached result if available
        file_hash: File hash for cache
        on_progress: Progress callback
        on_page_status: Page status callback
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import save_result_to_file
    
    # Try to use cached result
    if cached_result:
        cache_status = cached_result.get("status")
        
        if cache_status == "completed":
            safe_streamlit_call(st.info, f"📋 {filename} 使用缓存结果")
            try:
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                title = params.get("markdown_title", "").strip() or base_name
                html_content = pdf_processor.generate_html_pdf2htmlex_document(
                    src_bytes=src_bytes,
                    explanations=cached_result["explanations"],
                    title=title,
                    font_name=params.get("cjk_font_name", "SimHei"),
                    font_size=params.get("font_size", 14),
                    line_spacing=params.get("line_spacing", 1.2),
                    column_count=params.get("html_column_count", 2),
                    column_gap=params.get("html_column_gap", 20),
                    show_column_rule=params.get("html_show_column_rule", True)
                )
                return {
                    "status": "completed",
                    "html_content": html_content,
                    "explanations": cached_result["explanations"],
                    "failed_pages": cached_result.get("failed_pages", [])
                }
            except Exception as e:
                logger.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
                # Fall through to reprocessing
        
        elif cache_status == "partial":
            # Handle partial success for HTML pdf2htmlEX mode
            existing_explanations = cached_result.get("explanations", {})
            failed_pages = cached_result.get("failed_pages", [])
            timestamp = cached_result.get("timestamp", "未知时间")
            
            # Validate and fix cache data
            from app.cache_processor import validate_cache_data
            is_valid, fixed_explanations, fixed_failed_pages, validation_warnings = validate_cache_data(
                src_bytes, existing_explanations, failed_pages
            )
            
            # Display validation warnings if any
            if validation_warnings:
                for warning in validation_warnings:
                    safe_streamlit_call(st.warning, f"⚠️ {warning}")
            
            # If validation failed or no failed pages after fixing, handle accordingly
            if not is_valid and not fixed_failed_pages:
                # Cache data is invalid, reprocess from scratch
                # Fall through to reprocessing section
                pass
            elif fixed_failed_pages and fixed_explanations:
                safe_streamlit_call(st.info, f"📋 {filename} 检测到部分成功状态（保存时间: {timestamp}）")
                safe_streamlit_call(st.info, f"已成功生成 {len(fixed_explanations)} 页讲解，还有 {len(fixed_failed_pages)} 页失败: {', '.join(map(str, fixed_failed_pages))}")
                safe_streamlit_call(st.info, "正在继续处理失败的页面...")
                
                try:
                    # Continue processing failed pages with fixed data
                    merged_explanations, preview_images, remaining_failed_pages = pdf_processor.retry_failed_pages(
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
                        on_progress=on_progress,
                        use_context=params.get("use_context", False),
                        context_prompt=params.get("context_prompt", None),
                        llm_provider=params.get("llm_provider", "gemini"),
                        api_base=params.get("api_base"),
                        on_page_status=on_page_status,
                        file_hash=file_hash,
                    )
                    
                    # Generate HTML with merged explanations
                    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    title = params.get("markdown_title", "").strip() or base_name
                    html_content = pdf_processor.generate_html_pdf2htmlex_document(
                        src_bytes=src_bytes,
                        explanations=merged_explanations,
                        title=title,
                        font_name=params.get("cjk_font_name", "SimHei"),
                        font_size=params.get("font_size", 14),
                        line_spacing=params.get("line_spacing", 1.2),
                        column_count=params.get("html_column_count", 2),
                        column_gap=params.get("html_column_gap", 20),
                        show_column_rule=params.get("html_show_column_rule", True)
                    )
                    
                    final_status = "completed" if not remaining_failed_pages else "partial"
                    result = {
                        "status": final_status,
                        "html_content": html_content,
                        "explanations": merged_explanations,
                        "failed_pages": remaining_failed_pages
                    }
                    
                    # Save updated result to cache
                    save_result_to_file(file_hash, result)
                    
                    return result
                except Exception as e:
                    logger.warning(f"继续处理失败页面时出错: {str(e)}")
                    # Fall through to reprocessing
            else:
                # No failed pages after validation, but status is partial - might be completed now
                # Try to regenerate HTML to verify
                try:
                    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                    title = params.get("markdown_title", "").strip() or base_name
                    html_content = pdf_processor.generate_html_pdf2htmlex_document(
                        src_bytes=src_bytes,
                        explanations=fixed_explanations,
                        title=title,
                        font_name=params.get("cjk_font_name", "SimHei"),
                        font_size=params.get("font_size", 14),
                        line_spacing=params.get("line_spacing", 1.2),
                        column_count=params.get("html_column_count", 2),
                        column_gap=params.get("html_column_gap", 20),
                        show_column_rule=params.get("html_show_column_rule", True)
                    )
                    result = {
                        "status": "completed",
                        "html_content": html_content,
                        "explanations": fixed_explanations,
                        "failed_pages": []
                    }
                    save_result_to_file(file_hash, result)
                    safe_streamlit_call(st.success, f"✅ {filename} 所有页面都已成功生成讲解！")
                    return result
                except Exception as e:
                    # Failed to regenerate, fall through to reprocessing
                    logger.warning(f"验证后重新生成HTML失败: {str(e)}")
                    pass
    
    # Process from scratch - parallel execution of explanation generation and pdf2htmlEX conversion
    logger.info(f"处理 {filename} 中...")
    try:
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        # Create wrapper functions for parallel execution
        def generate_explanations_task():
            """Generate explanations in a separate thread."""
            return pdf_processor.generate_explanations(
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
                auto_retry_failed_pages=params.get("auto_retry_failed_pages", True),
                max_auto_retries=params.get("max_auto_retries", 2),
                on_progress=on_progress,
                use_context=params.get("use_context", False),
                context_prompt=params.get("context_prompt", None),
                llm_provider=params.get("llm_provider", "gemini"),
                api_base=params.get("api_base"),
                on_page_status=on_page_status,
                file_hash=file_hash,
            )
        
        def convert_pdf_to_html_task():
            """Convert PDF to HTML using pdf2htmlEX in a separate thread."""
            return pdf_processor._convert_pdf_to_html_pdf2htmlex(src_bytes)
        
        # Execute both tasks in parallel
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_explanations = executor.submit(generate_explanations_task)
            future_pdf2html = executor.submit(convert_pdf_to_html_task)
            
            # Wait for both tasks to complete
            explanations_result = None
            pdf2html_result = None
            explanations_error = None
            pdf2html_error = None
            
            # Collect results as they complete
            for future in as_completed([future_explanations, future_pdf2html]):
                try:
                    result = future.result()
                    # Determine which task completed based on which future it is
                    if future == future_explanations:
                        # This is explanations result: (explanations, preview_images, failed_pages)
                        explanations_result = result
                    elif future == future_pdf2html:
                        # This is pdf2htmlEX result: (css_content, page_htmls, error)
                        pdf2html_result = result
                except Exception as e:
                    # Determine which task failed
                    if future == future_explanations:
                        explanations_error = str(e)
                    elif future == future_pdf2html:
                        pdf2html_error = str(e)
            
            # Check for errors
            if explanations_error:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"生成讲解失败: {explanations_error}"
                }
            
            if pdf2html_error or not pdf2html_result:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"PDF转HTML失败: {pdf2html_error or '未知错误'}"
                }
            
            # Unpack results
            explanations, preview_images, failed_pages = explanations_result
            css_content, page_htmls, pdf2html_error = pdf2html_result
            
            if pdf2html_error or not page_htmls:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"PDF转HTML失败: {pdf2html_error or '解析失败'}"
                }
            
            if not explanations:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": "生成讲解失败"
                }
            
            # Generate final HTML document
            try:
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                title = params.get("markdown_title", "").strip() or base_name
                
                # Convert explanations from 0-indexed to 1-indexed
                explanations_1indexed = {
                    page_num + 1: text 
                    for page_num, text in explanations.items()
                }
                
                total_pages = len(page_htmls)
                
                # Generate HTML document
                from app.services.html_pdf2htmlex_generator import HTMLPdf2htmlEXGenerator
                html_content = HTMLPdf2htmlEXGenerator.generate_html_pdf2htmlex_view(
                    page_htmls=page_htmls,
                    pdf2htmlex_css=css_content,
                    explanations=explanations_1indexed,
                    total_pages=total_pages,
                    title=title,
                    font_name=params.get("cjk_font_name", "SimHei"),
                    font_size=params.get("font_size", 14),
                    line_spacing=params.get("line_spacing", 1.2),
                    column_count=params.get("html_column_count", 2),
                    column_gap=params.get("html_column_gap", 20),
                    show_column_rule=params.get("html_show_column_rule", True)
                )
                
                result_status = "completed" if not failed_pages else "partial"
                result = {
                    "status": result_status,
                    "html_content": html_content,
                    "explanations": explanations,
                    "failed_pages": failed_pages
                }
                save_result_to_file(file_hash, result)
                return result
            except Exception as e:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"HTML生成失败: {str(e)}"
                }
    except Exception as e:
        logger.error(f"处理 {filename} 时发生异常: {str(e)}", exc_info=True)
        return {
            "status": "failed",
            "html_content": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def process_single_file(
    src_bytes: bytes,
    filename: str,
    params: Dict[str, Any],
    file_hash: str,
    cached_result: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Process a single uploaded file.
    
    Args:
        src_bytes: PDF file bytes (already read)
        filename: File name
        params: Processing parameters
        file_hash: File hash for cache
        cached_result: Cached result if available
        
    Returns:
        Processing result dictionary
    """
    try:
        # Validate PDF file
        is_valid, validation_error = pdf_processor.validate_pdf_file(src_bytes)
        if not is_valid:
            return {
                "status": "failed",
                "pdf_bytes": None,
                "explanations": {},
                "failed_pages": [],
                "error": f"PDF文件验证失败: {validation_error}"
            }
        
        # Process based on output mode
        output_mode = params.get("output_mode", "PDF讲解版")
        if output_mode == "Markdown截图讲解":
            return process_single_file_markdown(
                None, filename, src_bytes, params, cached_result, file_hash
            )
        elif output_mode == "HTML截图版":
            return process_single_file_html_screenshot(
                None, filename, src_bytes, params, cached_result, file_hash
            )
        elif output_mode == "HTML-pdf2htmlEX版":
            return process_single_file_html_pdf2htmlex(
                None, filename, src_bytes, params, cached_result, file_hash
            )
        else:
            return process_single_file_pdf(
                None, filename, src_bytes, params, cached_result, file_hash
            )
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error processing file {filename}: {e}", exc_info=True)
        return {
            "status": "failed",
            "pdf_bytes": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def process_single_file_with_progress(
    src_bytes: bytes,
    filename: str,
    params: Dict[str, Any],
    file_hash: str,
    cached_result: Optional[Dict[str, Any]],
    on_progress: Optional[Callable[[int, int], None]] = None,
    on_page_status: Optional[Callable[[int, str, Optional[str]], None]] = None,
) -> Dict[str, Any]:
    """
    Process a single uploaded file with progress callbacks.
    
    Args:
        src_bytes: PDF file bytes (already read)
        filename: File name
        params: Processing parameters
        file_hash: File hash for cache
        cached_result: Cached result if available
        on_progress: Progress callback (done, total)
        on_page_status: Page status callback (page_index, status, error)
        
    Returns:
        Processing result dictionary
    """
    try:
        # Validate PDF file
        is_valid, validation_error = pdf_processor.validate_pdf_file(src_bytes)
        if not is_valid:
            return {
                "status": "failed",
                "pdf_bytes": None,
                "explanations": {},
                "failed_pages": [],
                "error": f"PDF文件验证失败: {validation_error}"
            }
        
        # Process based on output mode
        output_mode = params.get("output_mode", "PDF讲解版")
        if output_mode == "Markdown截图讲解":
            return process_single_file_markdown(
                None, filename, src_bytes, params, cached_result, file_hash,
                on_progress=on_progress, on_page_status=on_page_status
            )
        elif output_mode == "HTML截图版":
            return process_single_file_html_screenshot(
                None, filename, src_bytes, params, cached_result, file_hash,
                on_progress=on_progress, on_page_status=on_page_status
            )
        elif output_mode == "HTML-pdf2htmlEX版":
            return process_single_file_html_pdf2htmlex(
                None, filename, src_bytes, params, cached_result, file_hash,
                on_progress=on_progress, on_page_status=on_page_status
            )
        else:
            return process_single_file_pdf(
                None, filename, src_bytes, params, cached_result, file_hash,
                on_progress=on_progress, on_page_status=on_page_status
            )
            
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Error processing file {filename}: {e}", exc_info=True)
        return {
            "status": "failed",
            "pdf_bytes": None,
            "explanations": {},
            "failed_pages": [],
            "error": str(e)
        }


def display_file_result(filename: str, result: Dict[str, Any]):
    """
    Display processing result for a single file.
    
    Args:
        filename: File name
        result: Processing result dictionary
    """
    if result.get("status") == "completed":
        safe_streamlit_call(st.success, f"✅ {filename} 处理完成！")
        if result.get("failed_pages"):
            safe_streamlit_call(st.warning, f"⚠️ {filename} 中 {len(result['failed_pages'])} 页生成讲解失败")
    elif result.get("status") == "failed":
        safe_streamlit_call(st.error, f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")


def build_zip_cache_pdf(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """Build ZIP file containing PDFs and JSONs from batch results."""
    import zipfile
    import io
    import json
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, result in batch_results.items():
            if result.get("status") == "completed":
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                
                # Add PDF
                if result.get("pdf_bytes"):
                    zip_file.writestr(
                        f"{base_name}讲解版.pdf",
                        result["pdf_bytes"]
                    )
                
                # Add JSON
                if result.get("explanations"):
                    json_bytes = json.dumps(
                        result["explanations"],
                        ensure_ascii=False,
                        indent=2
                    ).encode("utf-8")
                    zip_file.writestr(
                        f"{base_name}.json",
                        json_bytes
                    )
    
    zip_buffer.seek(0)
    return zip_buffer.read() if zip_buffer.getvalue() else None


def build_zip_cache_markdown(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """Build ZIP file containing Markdown files and JSONs from batch results."""
    import zipfile
    import io
    import json
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, result in batch_results.items():
            if result.get("status") == "completed":
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                
                # Add Markdown
                if result.get("markdown_content"):
                    zip_file.writestr(
                        f"{base_name}讲解文档.md",
                        result["markdown_content"].encode("utf-8")
                    )
                
                # Add JSON
                if result.get("explanations"):
                    json_bytes = json.dumps(
                        result["explanations"],
                        ensure_ascii=False,
                        indent=2
                    ).encode("utf-8")
                    zip_file.writestr(
                        f"{base_name}.json",
                        json_bytes
                    )
    
    zip_buffer.seek(0)
    return zip_buffer.read() if zip_buffer.getvalue() else None


def build_zip_cache_html_screenshot(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """Build ZIP file containing HTML screenshot files and JSONs from batch results."""
    import zipfile
    import io
    import json
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, result in batch_results.items():
            if result.get("status") == "completed":
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                
                # Add HTML
                if result.get("html_content"):
                    zip_file.writestr(
                        f"{base_name}讲解文档.html",
                        result["html_content"].encode("utf-8")
                    )
                
                # Add JSON
                if result.get("explanations"):
                    json_bytes = json.dumps(
                        result["explanations"],
                        ensure_ascii=False,
                        indent=2
                    ).encode("utf-8")
                    zip_file.writestr(
                        f"{base_name}.json",
                        json_bytes
                    )
    
    zip_buffer.seek(0)
    return zip_buffer.read() if zip_buffer.getvalue() else None


def build_zip_cache_html_pdf2htmlex(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """Build ZIP file containing HTML pdf2htmlEX files and JSONs from batch results."""
    import zipfile
    import io
    import json
    
    zip_buffer = io.BytesIO()
    
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for filename, result in batch_results.items():
            if result.get("status") == "completed":
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                
                # Add HTML
                if result.get("html_content"):
                    zip_file.writestr(
                        f"{base_name}讲解文档.html",
                        result["html_content"].encode("utf-8")
                    )
                
                # Add JSON
                if result.get("explanations"):
                    json_bytes = json.dumps(
                        result["explanations"],
                        ensure_ascii=False,
                        indent=2
                    ).encode("utf-8")
                    zip_file.writestr(
                        f"{base_name}.json",
                        json_bytes
                    )
    
    zip_buffer.seek(0)
    return zip_buffer.read() if zip_buffer.getvalue() else None
