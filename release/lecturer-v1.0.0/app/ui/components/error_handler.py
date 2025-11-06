"""
Error Handler Component.

Provides structured error handling and user-friendly error messages.
"""

from typing import Callable, Optional, Any
import traceback
import streamlit as st


class ErrorHandler:
    """Handles errors with user-friendly messages and recovery options."""

    def __init__(self):
        """Initialize error handler."""
        self.error_counts = {}

    def handle_error(
        self,
        error: Exception,
        context: str,
        on_retry: Optional[Callable] = None,
        show_traceback: bool = False,
        key: Optional[str] = None
    ) -> None:
        """
        Handle and display an error.

        Args:
            error: The exception that occurred
            context: Context where the error occurred
            on_retry: Callback function for retry action
            show_traceback: Whether to show the full traceback
            key: Unique key for this error (for session state)
        """
        # Count errors for this context
        error_key = key or context
        self.error_counts[error_key] = self.error_counts.get(error_key, 0) + 1

        # Create columns for error and action
        col1, col2 = st.columns([3, 1])

        with col1:
            # Error message with emoji
            st.error(f"❌ **{context}** - {self._get_error_message(error)}")

            # Error details in expander
            with st.expander("📋 错误详情", expanded=show_traceback):
                st.write(f"**错误类型**: {type(error).__name__}")
                st.write(f"**错误信息**: {str(error)}")

                if show_traceback:
                    st.code(traceback.format_exc())

                # Suggestion based on error type
                suggestion = self._get_suggestion(error)
                if suggestion:
                    st.info(f"💡 **建议**: {suggestion}")

        with col2:
            st.write("")  # Spacer
            st.write("")  # Spacer

            # Retry button
            if on_retry:
                if st.button("🔄 重试", key=f"retry_{error_key}"):
                    on_retry()

            # Show error count
            count = self.error_counts[error_key]
            if count > 1:
                st.caption(f"失败次数: {count}")

    def _get_error_message(self, error: Exception) -> str:
        """
        Get user-friendly error message.

        Args:
            error: The exception

        Returns:
            User-friendly error message
        """
        error_messages = {
            "FileNotFoundError": "文件未找到，请检查文件路径",
            "PermissionError": "没有权限访问文件，请检查文件权限",
            "ValueError": "文件格式无效，请上传正确的PDF文件",
            "TypeError": "参数类型错误，请检查输入参数",
            "ConnectionError": "网络连接失败，请检查网络连接",
            "TimeoutError": "操作超时，请重试或检查网络",
            "MemoryError": "内存不足，请尝试处理较小的文件",
        }

        error_type = type(error).__name__
        return error_messages.get(error_type, str(error))

    def _get_suggestion(self, error: Exception) -> str:
        """
        Get suggestion for resolving the error.

        Args:
            error: The exception

        Returns:
            Suggestion string
        """
        suggestions = {
            "FileNotFoundError": "请确保文件路径正确且文件存在",
            "PermissionError": "请检查文件是否被其他程序占用，或尝试以管理员身份运行",
            "ValueError": "请检查PDF文件是否损坏，或尝试使用其他PDF文件",
            "ConnectionError": "请检查网络连接，或稍后重试",
            "TimeoutError": "文件可能过大，请尝试降低DPI或并发数",
            "MemoryError": "请关闭其他应用程序，或处理较小的文件",
        }

        error_type = type(error).__name__
        return suggestions.get(error_type, "")

    def reset(self) -> None:
        """Reset error counts."""
        self.error_counts = {}


class ValidationError(Exception):
    """Custom validation error."""
    pass


def validate_file_size(uploaded_file, max_size_mb: int = 50) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file size.

    Args:
        uploaded_file: Streamlit uploaded file
        max_size_mb: Maximum file size in MB

    Returns:
        Tuple of (is_valid, error_message)
    """
    if uploaded_file is None:
        return True, None

    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > max_size_mb:
        return False, f"文件大小 ({file_size_mb:.1f}MB) 超过限制 ({max_size_mb}MB)"

    return True, None


def validate_file_type(uploaded_file, allowed_types: list[str] = ["pdf"]) -> tuple[bool, Optional[str]]:
    """
    Validate uploaded file type.

    Args:
        uploaded_file: Streamlit uploaded file
        allowed_types: List of allowed file extensions

    Returns:
        Tuple of (is_valid, error_message)
    """
    if uploaded_file is None:
        return True, None

    file_name = uploaded_file.name.lower()
    is_valid = any(file_name.endswith(f".{ext}") for ext in allowed_types)

    if not is_valid:
        allowed_str = ", ".join(allowed_types)
        return False, f"不支持的文件类型。请上传 {allowed_str} 格式的文件"

    return True, None
