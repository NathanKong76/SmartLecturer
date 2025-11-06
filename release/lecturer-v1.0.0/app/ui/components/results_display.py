"""
Results Display Component.

Displays processing results with download options and statistics.
"""

from typing import Dict, Any, List, Optional
import json
import io
import zipfile
import streamlit as st
import os


class ResultsDisplay:
    """Displays batch processing results with download options."""

    def __init__(self, batch_results_key: str = "batch_results"):
        """
        Initialize results display.

        Args:
            batch_results_key: Key for batch results in session state
        """
        self.batch_results_key = batch_results_key

    def render(self, batch_results: Optional[Dict[str, Any]] = None) -> None:
        """
        Render results display.

        Args:
            batch_results: Dictionary of batch results
        """
        if batch_results is None:
            batch_results = st.session_state.get(self.batch_results_key, {})

        if not batch_results:
            st.info("暂无处理结果")
            return

        # Calculate statistics
        total_files = len(batch_results)
        completed_files = sum(
            1 for r in batch_results.values()
            if r.get("status") == "completed"
        )
        failed_files = total_files - completed_files

        # Header with statistics
        st.subheader("📊 处理结果")

        # Statistics columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("📄 总文件数", total_files)

        with col2:
            st.metric("✅ 成功", completed_files, delta=completed_files)

        with col3:
            st.metric("❌ 失败", failed_files, delta=-failed_files)

        with col4:
            success_rate = (completed_files / total_files * 100) if total_files > 0 else 0
            st.metric("📈 成功率", f"{success_rate:.1f}%")

        # Detailed results
        with st.expander("📋 详细结果", expanded=False):
            for filename, result in batch_results.items():
                status = result.get("status", "unknown")

                if status == "completed":
                    st.success(f"✅ {filename} - 处理成功")

                    # Show failed pages if any
                    failed_pages = result.get("failed_pages", [])
                    if failed_pages:
                        st.warning(
                            f"  ⚠️ {len(failed_pages)} 页生成讲解失败: "
                            f"{', '.join(map(str, failed_pages))}"
                        )

                    # Show file info
                    pdf_bytes = result.get("pdf_bytes")
                    markdown_content = result.get("markdown_content")

                    if pdf_bytes:
                        size_kb = len(pdf_bytes) / 1024
                        st.caption(f"  📄 PDF大小: {size_kb:.1f} KB")

                    if markdown_content:
                        size_kb = len(markdown_content) / 1024
                        st.caption(f"  📝 Markdown大小: {size_kb:.1f} KB")

                elif status == "failed":
                    error_msg = result.get("error", "未知错误")
                    st.error(f"❌ {filename} - 处理失败: {error_msg}")

                elif status == "processing":
                    st.info(f"🔄 {filename} - 正在处理中...")

        # Download section
        if completed_files > 0:
            self._render_download_section(batch_results)

        # Retry section
        if failed_files > 0:
            self._render_retry_section(batch_results)

    def _render_download_section(self, batch_results: Dict[str, Any]) -> None:
        """Render download section."""
        st.subheader("📥 下载结果")

        # Download mode selection
        download_mode = st.radio(
            "下载方式",
            ["分别下载", "打包下载"],
            help="分别下载：为每个文件生成单独的下载按钮\n打包下载：将所有文件打包成ZIP下载"
        )

        if download_mode == "打包下载":
            # Build ZIP
            zip_bytes = self._build_zip(batch_results)
            if zip_bytes:
                zip_filename = st.text_input(
                    "ZIP文件名",
                    value=f"批量处理结果_{st.session_state.get('timestamp', 'now')}.zip"
                )

                st.download_button(
                    label="📦 下载 ZIP 压缩包",
                    data=zip_bytes,
                    file_name=zip_filename,
                    mime="application/zip",
                    use_container_width=True,
                    key="download_zip"
                )
        else:
            # Individual downloads
            self._render_individual_downloads(batch_results)

    def _render_individual_downloads(self, batch_results: Dict[str, Any]) -> None:
        """Render individual download buttons."""
        st.write("**分别下载每个文件:**")

        # Group by output type
        pdf_results = {
            fname: result
            for fname, result in batch_results.items()
            if result.get("status") == "completed" and result.get("pdf_bytes")
        }

        md_results = {
            fname: result
            for fname, result in batch_results.items()
            if result.get("status") == "completed" and result.get("markdown_content")
        }

        # PDF downloads
        if pdf_results:
            st.write("📄 **PDF 文件:**")
            for filename, result in pdf_results.items():
                base_name = os.path.splitext(filename)[0]
                pdf_filename = f"{base_name}讲解版.pdf"

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"  {pdf_filename}")

                with col2:
                    st.download_button(
                        "下载",
                        data=result["pdf_bytes"],
                        file_name=pdf_filename,
                        mime="application/pdf",
                        key=f"download_pdf_{filename}"
                    )

        # Markdown downloads
        if md_results:
            st.write("📝 **Markdown 文件:**")
            for filename, result in md_results.items():
                base_name = os.path.splitext(filename)[0]
                md_filename = f"{base_name}讲解文档.md"

                col1, col2 = st.columns([3, 1])
                with col1:
                    st.text(f"  {md_filename}")

                with col2:
                    st.download_button(
                        "下载",
                        data=result["markdown_content"],
                        file_name=md_filename,
                        mime="text/markdown",
                        key=f"download_md_{filename}"
                    )

    def _render_retry_section(self, batch_results: Dict[str, Any]) -> None:
        """Render retry section for failed files."""
        failed_files = [
            filename
            for filename, result in batch_results.items()
            if result.get("status") == "failed"
        ]

        if failed_files:
            st.subheader("🔄 重试失败的文件")
            st.info(f"有 {len(failed_files)} 个文件处理失败")

            if st.button(
                f"重试 {len(failed_files)} 个文件",
                use_container_width=True,
                key="retry_failed"
            ):
                # Trigger retry logic
                st.session_state.retry_files = failed_files
                st.rerun()

    def _build_zip(self, batch_results: Dict[str, Any]) -> Optional[bytes]:
        """
        Build ZIP file from results.

        Args:
            batch_results: Dictionary of batch results

        Returns:
            ZIP file bytes or None
        """
        zip_buffer = io.BytesIO()

        try:
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                # Add PDF files
                for filename, result in batch_results.items():
                    if result.get("status") != "completed":
                        continue

                    base_name = os.path.splitext(filename)[0]

                    # Add PDF
                    if result.get("pdf_bytes"):
                        pdf_filename = f"{base_name}讲解版.pdf"
                        zip_file.writestr(pdf_filename, result["pdf_bytes"])

                    # Add Markdown
                    if result.get("markdown_content"):
                        md_filename = f"{base_name}讲解文档.md"
                        zip_file.writestr(md_filename, result["markdown_content"])

                    # Add JSON
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
            st.error(f"构建ZIP文件失败: {str(e)}")
            return None


class ComparisonView:
    """View for comparing results."""

    def __init__(self):
        """Initialize comparison view."""
        pass

    def render(
        self,
        results_a: Dict[str, Any],
        results_b: Dict[str, Any],
        label_a: str = "结果 A",
        label_b: str = "结果 B"
    ) -> None:
        """
        Render comparison view.

        Args:
            results_a: First set of results
            results_b: Second set of results
            label_a: Label for first results
            label_b: Label for second results
        """
        st.subheader("📊 结果对比")

        # Compare statistics
        col1, col2 = st.columns(2)

        with col1:
            st.markdown(f"### {label_a}")
            self._render_stats(results_a)

        with col2:
            st.markdown(f"### {label_b}")
            self._render_stats(results_b)

    def _render_stats(self, results: Dict[str, Any]) -> None:
        """Render statistics for a result set."""
        total = len(results)
        completed = sum(1 for r in results.values() if r.get("status") == "completed")
        failed = total - completed

        col1, col2, col3 = st.columns(3)
        col1.metric("总数", total)
        col2.metric("成功", completed)
        col3.metric("失败", failed)
