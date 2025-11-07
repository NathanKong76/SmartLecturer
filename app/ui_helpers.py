"""
UI helper functions for Streamlit app.

This module contains helper functions to reduce code duplication
and improve maintainability of the main Streamlit app.
"""

from typing import Dict, List, Optional, Tuple, Any
import streamlit as st

from app.services import pdf_processor
from app.services import constants


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
        return False, "请在侧边栏填写 GEMINI_API_KEY"
    
    return True, None


def process_single_file_pdf(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str
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
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import cached_process_pdf
    
    column_padding_value = params.get("column_padding", 10)
    
    # Try to use cached result
    if cached_result and cached_result.get("status") == "completed":
        st.info(f"📋 {filename} 使用缓存结果")
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
                "failed_pages": cached_result["failed_pages"],
                "json_bytes": None
            }
        except Exception as e:
            st.warning(f"缓存重新合成失败，尝试重新处理: {str(e)}")
            # Fall through to reprocessing
    
    # Process from scratch
    with st.spinner(f"处理 {filename} 中..."):
        result = cached_process_pdf(src_bytes, params)
        return result


def process_single_file_markdown(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str
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
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import cached_process_markdown
    
    # Try to use cached result
    if cached_result and cached_result.get("status") == "completed":
        st.info(f"📋 {filename} 使用缓存结果")
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
            st.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
            # Fall through to reprocessing
    
    # Process from scratch
    with st.spinner(f"处理 {filename} 中..."):
        result = cached_process_markdown(src_bytes, params)
        return result


def process_single_file_html_screenshot(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str
) -> Dict[str, Any]:
    """
    Process a single file in HTML Screenshot mode.
    
    Args:
        uploaded_file: Uploaded file object (optional, not used if src_bytes provided)
        filename: File name
        src_bytes: PDF file bytes
        params: Processing parameters
        cached_result: Cached result if available
        file_hash: File hash for cache
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import cached_process_markdown
    
    # Try to use cached result
    if cached_result and cached_result.get("status") == "completed":
        st.info(f"📋 {filename} 使用缓存结果")
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
                "failed_pages": cached_result["failed_pages"]
            }
        except Exception as e:
            st.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
            # Fall through to reprocessing
    
    # Process from scratch
    with st.spinner(f"处理 {filename} 中..."):
        # First get explanations (reuse markdown processing for explanation generation)
        markdown_result = cached_process_markdown(src_bytes, params)
        
        if markdown_result.get("status") == "completed":
            # Generate HTML screenshot document
            try:
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                # Use user-configured title if provided, otherwise use filename
                title = params.get("markdown_title", "").strip() or base_name
                html_content = pdf_processor.generate_html_screenshot_document(
                    src_bytes=src_bytes,
                    explanations=markdown_result["explanations"],
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
                    "explanations": markdown_result["explanations"],
                    "failed_pages": markdown_result.get("failed_pages", [])
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"HTML生成失败: {str(e)}"
                }
        else:
            return markdown_result


def process_single_file_html_pdf2htmlex(
    uploaded_file: Optional[Any],
    filename: str,
    src_bytes: bytes,
    params: Dict[str, Any],
    cached_result: Optional[Dict[str, Any]],
    file_hash: str
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
        
    Returns:
        Processing result dictionary
    """
    from app.cache_processor import cached_process_markdown
    
    # Try to use cached result
    if cached_result and cached_result.get("status") == "completed":
        st.info(f"📋 {filename} 使用缓存结果")
        try:
            # Generate HTML from cached explanations
            base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
            # Use user-configured title if provided, otherwise use filename
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
                "failed_pages": cached_result["failed_pages"]
            }
        except Exception as e:
            st.warning(f"缓存重新生成失败，尝试重新处理: {str(e)}")
            # Fall through to reprocessing
    
    # Process from scratch
    with st.spinner(f"处理 {filename} 中 (使用pdf2htmlEX转换)..."):
        # First get explanations (reuse markdown processing for explanation generation)
        markdown_result = cached_process_markdown(src_bytes, params)
        
        if markdown_result.get("status") == "completed":
            # Generate HTML pdf2htmlEX document
            try:
                base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
                # Use user-configured title if provided, otherwise use filename
                title = params.get("markdown_title", "").strip() or base_name
                html_content = pdf_processor.generate_html_pdf2htmlex_document(
                    src_bytes=src_bytes,
                    explanations=markdown_result["explanations"],
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
                    "explanations": markdown_result["explanations"],
                    "failed_pages": markdown_result.get("failed_pages", [])
                }
            except Exception as e:
                return {
                    "status": "failed",
                    "html_content": None,
                    "explanations": {},
                    "failed_pages": [],
                    "error": f"HTML-pdf2htmlEX生成失败: {str(e)}"
                }
        else:
            return markdown_result


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


def display_file_result(filename: str, result: Dict[str, Any]):
    """
    Display processing result for a single file.
    
    Args:
        filename: File name
        result: Processing result dictionary
    """
    if result.get("status") == "completed":
        st.success(f"✅ {filename} 处理完成！")
        if result.get("failed_pages"):
            st.warning(f"⚠️ {filename} 中 {len(result['failed_pages'])} 页生成讲解失败")
    elif result.get("status") == "failed":
        st.error(f"❌ {filename} 处理失败: {result.get('error', '未知错误')}")


def build_zip_cache_pdf(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """
    Build ZIP cache for PDF mode results.
    
    Args:
        batch_results: Batch processing results
        
    Returns:
        ZIP file bytes or None
    """
    import io
    import zipfile
    import json
    import os
    
    completed_any = any(
        r.get("status") == "completed" and r.get("pdf_bytes") 
        for r in batch_results.values()
    )
    
    if not completed_any:
        return None
    
    # Pre-generate JSON bytes for each file
    for fname, res in batch_results.items():
        if res.get("status") == "completed" and res.get("explanations"):
            try:
                res["json_bytes"] = json.dumps(
                    res["explanations"], 
                    ensure_ascii=False, 
                    indent=2
                ).encode("utf-8")
            except Exception:
                res["json_bytes"] = None
    
    # Build ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for fname, res in batch_results.items():
            if res.get("status") == "completed" and res.get("pdf_bytes"):
                base_name = os.path.splitext(fname)[0]
                new_filename = f"{base_name}讲解版.pdf"
                zip_file.writestr(new_filename, res["pdf_bytes"])
                if res.get("json_bytes"):
                    json_filename = f"{base_name}.json"
                    zip_file.writestr(json_filename, res["json_bytes"])
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def build_zip_cache_markdown(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """
    Build ZIP cache for Markdown mode results.
    
    Args:
        batch_results: Batch processing results
        
    Returns:
        ZIP file bytes or None
    """
    import io
    import zipfile
    import json
    import os
    
    completed_any = any(
        r.get("status") == "completed" and r.get("markdown_content")
        for r in batch_results.values()
    )
    
    if not completed_any:
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for fname, res in batch_results.items():
            if res.get("status") == "completed" and res.get("markdown_content"):
                base_name = os.path.splitext(fname)[0]
                markdown_filename = f"{base_name}讲解文档.md"
                zip_file.writestr(markdown_filename, res["markdown_content"])
                if res.get("explanations"):
                    try:
                        json_bytes = json.dumps(
                            res["explanations"], 
                            ensure_ascii=False, 
                            indent=2
                        ).encode("utf-8")
                        json_filename = f"{base_name}.json"
                        zip_file.writestr(json_filename, json_bytes)
                    except Exception:
                        pass
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def build_zip_cache_html_screenshot(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """
    Build ZIP cache for HTML Screenshot mode results.
    
    Args:
        batch_results: Batch processing results
        
    Returns:
        ZIP file bytes or None
    """
    import io
    import zipfile
    import json
    import os
    
    completed_any = any(
        r.get("status") == "completed" and r.get("html_content")
        for r in batch_results.values()
    )
    
    if not completed_any:
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for fname, res in batch_results.items():
            if res.get("status") == "completed" and res.get("html_content"):
                base_name = os.path.splitext(fname)[0]
                html_filename = f"{base_name}讲解文档.html"
                zip_file.writestr(html_filename, res["html_content"])
                if res.get("explanations"):
                    try:
                        json_bytes = json.dumps(
                            res["explanations"], 
                            ensure_ascii=False, 
                            indent=2
                        ).encode("utf-8")
                        json_filename = f"{base_name}.json"
                        zip_file.writestr(json_filename, json_bytes)
                    except Exception:
                        pass
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()


def build_zip_cache_html_pdf2htmlex(batch_results: Dict[str, Dict[str, Any]]) -> Optional[bytes]:
    """
    Build ZIP cache for HTML pdf2htmlEX mode results.
    
    Args:
        batch_results: Batch processing results
        
    Returns:
        ZIP file bytes or None
    """
    import io
    import zipfile
    import json
    import os
    
    completed_any = any(
        r.get("status") == "completed" and r.get("html_content")
        for r in batch_results.values()
    )
    
    if not completed_any:
        return None
    
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for fname, res in batch_results.items():
            if res.get("status") == "completed" and res.get("html_content"):
                base_name = os.path.splitext(fname)[0]
                html_filename = f"{base_name}讲解文档.html"
                zip_file.writestr(html_filename, res["html_content"])
                if res.get("explanations"):
                    try:
                        json_bytes = json.dumps(
                            res["explanations"], 
                            ensure_ascii=False, 
                            indent=2
                        ).encode("utf-8")
                        json_filename = f"{base_name}.json"
                        zip_file.writestr(json_filename, json_bytes)
                    except Exception:
                        pass
    
    zip_buffer.seek(0)
    return zip_buffer.getvalue()

