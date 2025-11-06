"""
File Handler.

Manages file processing operations.
"""

from typing import Dict, Any, Optional, Tuple
import hashlib
from app.cache_processor import get_file_hash, load_result_from_file


class FileHandler:
    """Handles individual file processing operations."""

    def __init__(self):
        """Initialize file handler."""
        pass

    def process_file(
        self,
        file_bytes: bytes,
        filename: str,
        params: Dict[str, Any],
        cached_result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Process a single file.

        Args:
            file_bytes: File content as bytes
            filename: Name of the file
            params: Processing parameters
            cached_result: Cached result if available

        Returns:
            Processing result dictionary
        """
        try:
            # Validate PDF file
            from app.services.pdf_processor import validate_pdf_file

            is_valid, validation_error = validate_pdf_file(file_bytes)
            if not is_valid:
                return {
                    "status": "failed",
                    "error": f"PDF文件验证失败: {validation_error}"
                }

            # Get file hash for caching
            file_hash = get_file_hash(file_bytes, params)

            # Try to use cached result
            if cached_result and cached_result.get("status") == "completed":
                # Verify cache is still valid
                if self._is_cache_valid(cached_result, params):
                    return self._use_cached_result(file_bytes, cached_result, params)
                else:
                    # Cache invalid, process fresh
                    pass

            # Process based on output mode
            output_mode = params.get("output_mode", "PDF讲解版")
            if output_mode == "Markdown截图讲解":
                return self._process_markdown_mode(file_bytes, filename, params, file_hash)
            else:
                return self._process_pdf_mode(file_bytes, filename, params, file_hash)

        except Exception as e:
            return self._handle_error(e, filename)

    def _is_cache_valid(self, cached_result: Dict[str, Any], params: Dict[str, Any]) -> bool:
        """
        Check if cached result is still valid.

        Args:
            cached_result: Cached result
            params: Current parameters

        Returns:
            True if cache is valid
        """
        # Check if any relevant parameters changed
        relevant_params = [
            "right_ratio", "font_size", "line_spacing",
            "column_padding", "render_mode", "cjk_font_name"
        ]

        cached_params = cached_result.get("params", {})
        for param in relevant_params:
            if cached_params.get(param) != params.get(param):
                return False

        return True

    def _use_cached_result(
        self,
        file_bytes: bytes,
        cached_result: Dict[str, Any],
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use cached result to generate output.

        Args:
            file_bytes: Original file bytes
            cached_result: Cached result
            params: Processing parameters

        Returns:
            Processing result
        """
        from app.services.pdf_processor import compose_pdf

        try:
            result_bytes = compose_pdf(
                file_bytes,
                cached_result["explanations"],
                params["right_ratio"],
                params["font_size"],
                font_name=(params.get("cjk_font_name") or "SimHei"),
                render_mode=params.get("render_mode", "markdown"),
                line_spacing=params["line_spacing"],
                column_padding=params.get("column_padding", 10)
            )

            return {
                "status": "completed",
                "pdf_bytes": result_bytes,
                "explanations": cached_result["explanations"],
                "failed_pages": cached_result.get("failed_pages", []),
                "from_cache": True
            }

        except Exception as e:
            # Cache use failed, need to reprocess
            return {
                "status": "failed",
                "error": f"使用缓存失败，需要重新处理: {str(e)}",
                "from_cache": True
            }

    def _process_pdf_mode(
        self,
        file_bytes: bytes,
        filename: str,
        params: Dict[str, Any],
        file_hash: str
    ) -> Dict[str, Any]:
        """
        Process file in PDF mode.

        Args:
            file_bytes: File bytes
            filename: File name
            params: Processing parameters
            file_hash: File hash

        Returns:
            Processing result
        """
        from app.cache_processor import cached_process_pdf

        return cached_process_pdf(file_bytes, params)

    def _process_markdown_mode(
        self,
        file_bytes: bytes,
        filename: str,
        params: Dict[str, Any],
        file_hash: str
    ) -> Dict[str, Any]:
        """
        Process file in Markdown mode.

        Args:
            file_bytes: File bytes
            filename: File name
            params: Processing parameters
            file_hash: File hash

        Returns:
            Processing result
        """
        from app.cache_processor import cached_process_markdown

        return cached_process_markdown(file_bytes, params)

    def _handle_error(self, error: Exception, filename: str) -> Dict[str, Any]:
        """
        Handle processing error.

        Args:
            error: Exception that occurred
            filename: Name of the file being processed

        Returns:
            Error result dictionary
        """
        import logging

        logger = logging.getLogger(__name__)
        logger.error(f"Error processing file {filename}: {error}", exc_info=True)

        return {
            "status": "failed",
            "error": str(error),
            "filename": filename
        }

    @staticmethod
    def get_file_info(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Get basic information about a file.

        Args:
            file_bytes: File content as bytes
            filename: File name

        Returns:
            Dictionary with file information
        """
        file_size_kb = len(file_bytes) / 1024

        # Try to get page count for PDF
        page_count = None
        try:
            import fitz
            doc = fitz.open(stream=file_bytes)
            page_count = len(doc)
            doc.close()
        except Exception:
            pass

        return {
            "filename": filename,
            "size_bytes": len(file_bytes),
            "size_kb": file_size_kb,
            "page_count": page_count
        }


class FileValidator:
    """Validates files before processing."""

    def __init__(self):
        """Initialize file validator."""
        pass

    def validate_file(self, file_bytes: bytes, filename: str) -> Tuple[bool, Optional[str]]:
        """
        Validate a file before processing.

        Args:
            file_bytes: File content
            filename: File name

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check file signature (magic bytes)
        if not self._is_pdf(file_bytes):
            return False, "文件不是有效的PDF格式"

        # Check file size (minimum)
        if len(file_bytes) < 100:
            return False, "PDF文件太小或为空"

        # Try to open with PyMuPDF
        try:
            import fitz
            doc = fitz.open(stream=file_bytes)

            # Check if document has pages
            if len(doc) == 0:
                doc.close()
                return False, "PDF文件没有页面"

            doc.close()

        except Exception as e:
            return False, f"无法打开PDF文件: {str(e)}"

        return True, None

    def _is_pdf(self, file_bytes: bytes) -> bool:
        """
        Check if file is PDF by signature.

        Args:
            file_bytes: File content

        Returns:
            True if file appears to be PDF
        """
        return file_bytes.startswith(b"%PDF")
