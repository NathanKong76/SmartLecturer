"""
File Uploader Component.

Enhanced file upload with validation and preview.
"""

from typing import List, Tuple, Optional, Dict, Any
import os
import streamlit as st
from .error_handler import validate_file_size, validate_file_type


class FileUploader:
    """Enhanced file uploader with validation and preview."""

    def __init__(
        self,
        label: str = "上传 PDF 文件",
        max_files: int = 20,
        max_file_size_mb: int = 50,
        allowed_types: List[str] = ["pdf"],
        key: Optional[str] = None
    ):
        """
        Initialize file uploader.

        Args:
            label: Label for the uploader
            max_files: Maximum number of files
            max_file_size_mb: Maximum file size in MB
            allowed_types: List of allowed file extensions
            key: Unique key for the component
        """
        self.label = label
        self.max_files = max_files
        self.max_file_size_mb = max_file_size_mb
        self.allowed_types = allowed_types
        self.key = key or "file_uploader"

    def render(self) -> List:
        """
        Render the file uploader.

        Returns:
            List of uploaded files
        """
        # File uploader with enhanced label
        uploaded_files = st.file_uploader(
            self.label,
            type=self.allowed_types,
            accept_multiple_files=True,
            key=self.key,
            help=f"最多上传 {self.max_files} 个文件，每个文件最大 {self.max_file_size_mb}MB"
        )

        # Validate and show results
        if uploaded_files:
            valid_files, warnings, errors = self._validate_files(uploaded_files)

            # Show warnings
            if warnings:
                for warning in warnings:
                    st.warning(warning)

            # Show errors
            if errors:
                for error in errors:
                    st.error(error)

            # Show file summary
            if valid_files:
                self._render_file_summary(valid_files)

            return valid_files

        return []

    def _validate_files(self, uploaded_files: List) -> Tuple[List, List[str], List[str]]:
        """
        Validate all uploaded files.

        Args:
            uploaded_files: List of uploaded files

        Returns:
            Tuple of (valid_files, warnings, errors)
        """
        valid_files = []
        warnings = []
        errors = []

        # Check file count
        if len(uploaded_files) > self.max_files:
            errors.append(f"文件数量 ({len(uploaded_files)}) 超过限制 ({self.max_files})")
            uploaded_files = uploaded_files[:self.max_files]
            warnings.append(f"已自动截取前 {self.max_files} 个文件")

        # Validate each file
        for file in uploaded_files:
            # Validate file type
            is_valid_type, type_error = validate_file_type(file, self.allowed_types)
            if not is_valid_type:
                errors.append(f"{file.name}: {type_error}")
                continue

            # Validate file size
            is_valid_size, size_error = validate_file_size(file, self.max_file_size_mb)
            if not is_valid_size:
                errors.append(f"{file.name}: {size_error}")
                continue

            # Additional validations
            if file.size == 0:
                errors.append(f"{file.name}: 文件为空")
                continue

            valid_files.append(file)

        return valid_files, warnings, errors

    def _render_file_summary(self, files: List) -> None:
        """
        Render summary of uploaded files.

        Args:
            files: List of valid files
        """
        total_size = sum(f.size for f in files)
        total_size_mb = total_size / (1024 * 1024)

        # File summary in columns
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📄 文件数量", len(files))

        with col2:
            st.metric("💾 总大小", f"{total_size_mb:.1f} MB")

        with col3:
            avg_size = total_size_mb / len(files) if files else 0
            st.metric("📊 平均大小", f"{avg_size:.1f} MB")

        # File list with details
        with st.expander("📋 文件列表", expanded=False):
            for i, file in enumerate(files, 1):
                size_kb = file.size / 1024
                st.write(f"{i}. **{file.name}** - {size_kb:.1f} KB")

        # Show top 3 files as preview (simulated)
        if len(files) > 0:
            with st.expander("👁️ 预览", expanded=False):
                st.info("前几个文件预览")
                for file in files[:3]:
                    st.write(f"- {file.name}")


class DragDropFileUploader(FileUploader):
    """File uploader with drag-and-drop support (Streamlit native)."""

    def __init__(self, **kwargs):
        """Initialize with drag-drop enabled."""
        super().__init__(**kwargs)
        # Streamlit's file_uploader supports drag-and-drop by default
        # This is a placeholder for future enhancements


class BatchFileUploader:
    """Batch file uploader for different file types."""

    def __init__(
        self,
        pdf_label: str = "上传 PDF 文件",
        json_label: str = "上传 JSON 文件 (可选)",
        max_files: int = 20,
        key: Optional[str] = None
    ):
        """
        Initialize batch file uploader.

        Args:
            pdf_label: Label for PDF uploader
            json_label: Label for JSON uploader
            max_files: Maximum files per type
            key: Unique key
        """
        self.pdf_uploader = FileUploader(
            label=pdf_label,
            max_files=max_files,
            allowed_types=["pdf"],
            key=f"{key}_pdf" if key else "pdf_uploader"
        )
        self.json_uploader = FileUploader(
            label=json_label,
            max_files=max_files,
            allowed_types=["json"],
            key=f"{key}_json" if key else "json_uploader"
        )

    def render(self) -> Tuple[List, List]:
        """
        Render both uploaders.

        Returns:
            Tuple of (pdf_files, json_files)
        """
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📄 PDF 文件")
            pdf_files = self.pdf_uploader.render()

        with col2:
            st.subheader("📝 JSON 文件")
            json_files = self.json_uploader.render()

        return pdf_files, json_files
