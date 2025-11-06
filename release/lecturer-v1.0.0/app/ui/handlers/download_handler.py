"""
Download Handler.

Manages file downloads and packaging.
"""

from typing import Dict, Any, Optional
import io
import zipfile
import json
import os
import streamlit as st


class DownloadHandler:
    """Handles file downloads and packaging."""

    def __init__(self):
        """Initialize download handler."""
        pass

    def build_zip_package(
        self,
        batch_results: Dict[str, Any],
        output_mode: str = "PDF讲解版"
    ) -> Optional[bytes]:
        """
        Build ZIP package from batch results.

        Args:
            batch_results: Dictionary of batch results
            output_mode: Output mode (PDF or Markdown)

        Returns:
            ZIP file bytes or None
        """
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for filename, result in batch_results.items():
                    if result.get("status") != "completed":
                        continue

                    base_name = os.path.splitext(filename)[0]

                    # Add PDF
                    if result.get("pdf_bytes") and output_mode == "PDF讲解版":
                        pdf_filename = f"{base_name}讲解版.pdf"
                        zip_file.writestr(pdf_filename, result["pdf_bytes"])

                    # Add Markdown
                    if result.get("markdown_content") and output_mode == "Markdown截图讲解":
                        md_filename = f"{base_name}讲解文档.md"
                        zip_file.writestr(md_filename, result["markdown_content"])

                    # Add JSON (always)
                    if result.get("explanations"):
                        json_filename = f"{base_name}.json"
                        json_bytes = json.dumps(
                            result["explanations"],
                            ensure_ascii=False,
                            indent=2
                        ).encode("utf-8")
                        zip_file.writestr(json_filename, json_bytes)

            zip_buffer.seek(0)
            return zip_buffer.getvalue()

        except Exception as e:
            st.error(f"构建ZIP包失败: {str(e)}")
            return None

    def create_download_button(
        self,
        data: bytes,
        filename: str,
        label: str,
        mime: str,
        key: Optional[str] = None,
        use_container_width: bool = True
    ) -> None:
        """
        Create a download button.

        Args:
            data: File data
            filename: Download filename
            label: Button label
            mime: MIME type
            key: Unique key
            use_container_width: Whether to use container width
        """
        st.download_button(
            label=label,
            data=data,
            file_name=filename,
            mime=mime,
            key=key,
            use_container_width=use_container_width
        )

    def get_file_size_str(self, size_bytes: int) -> str:
        """
        Convert bytes to human-readable string.

        Args:
            size_bytes: Size in bytes

        Returns:
            Human-readable size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


class BatchDownloadHandler(DownloadHandler):
    """Specialized handler for batch downloads."""

    def __init__(self):
        """Initialize batch download handler."""
        super().__init__()

    def render_download_interface(
        self,
        batch_results: Dict[str, Any],
        output_mode: str = "PDF讲解版"
    ) -> None:
        """
        Render complete download interface.

        Args:
            batch_results: Batch processing results
            output_mode: Output mode
        """
        st.subheader("📥 下载结果")

        # Check if there are completed files
        completed_files = [
            filename
            for filename, result in batch_results.items()
            if result.get("status") == "completed"
        ]

        if not completed_files:
            st.warning("没有完成处理的文件")
            return

        # Download mode selection
        download_mode = st.radio(
            "选择下载方式",
            ["分别下载", "打包下载"],
            help="分别下载：每个文件一个下载按钮\n打包下载：所有文件打包成一个ZIP"
        )

        if download_mode == "打包下载":
            self._render_zip_download(batch_results, output_mode)
        else:
            self._render_individual_downloads(batch_results, output_mode)

    def _render_zip_download(
        self,
        batch_results: Dict[str, Any],
        output_mode: str
    ) -> None:
        """
        Render ZIP download option.

        Args:
            batch_results: Batch results
            output_mode: Output mode
        """
        # Show summary
        total_size = 0
        file_count = 0

        for filename, result in batch_results.items():
            if result.get("status") != "completed":
                continue

            file_count += 1
            if result.get("pdf_bytes"):
                total_size += len(result["pdf_bytes"])
            if result.get("markdown_content"):
                total_size += len(result["markdown_content"])

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 文件数", file_count)
        with col2:
            st.metric("💾 总大小", self.get_file_size_str(total_size))
        with col3:
            avg_size = total_size / file_count if file_count > 0 else 0
            st.metric("📊 平均大小", self.get_file_size_str(int(avg_size)))

        # ZIP filename
        col1, col2 = st.columns([2, 1])
        with col1:
            zip_filename = st.text_input(
                "ZIP文件名",
                value=f"批量处理结果_{output_mode}.zip",
                key="zip_filename"
            )
        with col2:
            st.write("")  # Spacer

        # Build and download ZIP
        if st.button("📦 生成并下载ZIP", type="primary", use_container_width=True):
            with st.spinner("正在构建ZIP包..."):
                zip_bytes = self.build_zip_package(batch_results, output_mode)

                if zip_bytes:
                    self.create_download_button(
                        data=zip_bytes,
                        filename=zip_filename,
                        label="📥 下载 ZIP 压缩包",
                        mime="application/zip",
                        key="download_zip_button"
                    )

                    st.success("ZIP包构建完成！")
                else:
                    st.error("ZIP包构建失败")

    def _render_individual_downloads(
        self,
        batch_results: Dict[str, Any],
        output_mode: str
    ) -> None:
        """
        Render individual download buttons.

        Args:
            batch_results: Batch results
            output_mode: Output mode
        """
        st.write("**分别下载每个文件:**")

        # Separate PDF and Markdown files
        pdf_files = []
        md_files = []

        for filename, result in batch_results.items():
            if result.get("status") != "completed":
                continue

            base_name = os.path.splitext(filename)[0]

            if result.get("pdf_bytes") and output_mode == "PDF讲解版":
                pdf_files.append((filename, base_name, result))

            if result.get("markdown_content") and output_mode == "Markdown截图讲解":
                md_files.append((filename, base_name, result))

        # Render PDF downloads
        if pdf_files:
            st.markdown("### 📄 PDF 文件")
            for filename, base_name, result in pdf_files:
                pdf_filename = f"{base_name}讲解版.pdf"
                json_filename = f"{base_name}.json"

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.text(f"  {pdf_filename}")

                with col2:
                    self.create_download_button(
                        data=result["pdf_bytes"],
                        filename=pdf_filename,
                        label="📄 PDF",
                        mime="application/pdf",
                        key=f"pdf_{filename}",
                        use_container_width=False
                    )

                with col3:
                    if result.get("explanations"):
                        json_bytes = json.dumps(
                            result["explanations"],
                            ensure_ascii=False,
                            indent=2
                        ).encode("utf-8")

                        self.create_download_button(
                            data=json_bytes,
                            filename=json_filename,
                            label="📝 JSON",
                            mime="application/json",
                            key=f"json_{filename}",
                            use_container_width=False
                        )

        # Render Markdown downloads
        if md_files:
            st.markdown("### 📝 Markdown 文件")
            for filename, base_name, result in md_files:
                md_filename = f"{base_name}讲解文档.md"
                json_filename = f"{base_name}.json"

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.text(f"  {md_filename}")

                with col2:
                    self.create_download_button(
                        data=result["markdown_content"],
                        filename=md_filename,
                        label="📄 MD",
                        mime="text/markdown",
                        key=f"md_{filename}",
                        use_container_width=False
                    )

                with col3:
                    if result.get("explanations"):
                        json_bytes = json.dumps(
                            result["explanations"],
                            ensure_ascii=False,
                            indent=2
                        ).encode("utf-8")

                        self.create_download_button(
                            data=json_bytes,
                            filename=json_filename,
                            label="📝 JSON",
                            mime="application/json",
                            key=f"json_{filename}",
                            use_container_width=False
                        )
