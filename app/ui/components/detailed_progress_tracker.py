"""
Detailed Progress Tracker Component.

Provides comprehensive progress tracking with file-level, page-level,
stage tracking, and performance metrics.
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable, Tuple
import streamlit as st

from app.services.concurrency_controller import ConcurrencyStats, GlobalConcurrencyController


@dataclass
class FileProgress:
    """Progress information for a single file."""
    filename: str
    status: str  # waiting/processing/completed/failed
    current_page: int = 0
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: List[int] = field(default_factory=list)
    current_stage: str = "waiting"  # waiting/rendering/generating/composing/completed
    start_time: Optional[float] = None
    elapsed_time: float = 0.0
    pages_per_second: float = 0.0
    error: Optional[str] = None
    page_statuses: Dict[int, str] = field(default_factory=dict)  # page_index -> status


@dataclass
class OverallProgress:
    """Overall progress information."""
    total_files: int = 0
    completed_files: int = 0
    failed_files: int = 0
    processing_files: int = 0
    waiting_files: int = 0
    total_pages: int = 0
    completed_pages: int = 0
    failed_pages: int = 0
    current_stage: str = "准备中"
    overall_speed: float = 0.0  # pages per second
    elapsed_time: float = 0.0
    remaining_time: float = 0.0
    concurrency_stats: Optional[ConcurrencyStats] = None
    processing_mode: str = "batch_generation"  # batch_generation or json_regeneration


class DetailedProgressTracker:
    """
    Comprehensive progress tracker with file-level, page-level,
    stage tracking, and performance metrics.
    """

    def __init__(
        self,
        total_files: int,
        operation_name: str = "处理中",
        processing_mode: str = "batch_generation"
    ):
        """
        Initialize detailed progress tracker.

        Args:
            total_files: Total number of files to process
            operation_name: Name of the operation
            processing_mode: "batch_generation" or "json_regeneration"
        """
        self.total_files = total_files
        self.operation_name = operation_name
        self.processing_mode = processing_mode
        self.start_time = time.time()
        
        # File progress tracking
        self.file_progress: Dict[str, FileProgress] = {}
        
        # Thread safety for concurrent updates
        self._lock = threading.Lock()
        
        # Overall statistics
        self.total_pages = 0
        self.completed_pages = 0
        self.failed_pages_count = 0
        
        # Stage definitions based on mode
        if processing_mode == "batch_generation":
            self.stages = ["给PDF页面截图", "用LLM生成讲解（html也会在此阶段生成）", "合成文档"]
        else:  # json_regeneration
            self.stages = ["匹配和解析JSON", "合成文档"]
        
        # UI placeholders - use single containers to avoid duplication
        tracker_key = f"progress_tracker_ui_{self.operation_name}"
        if tracker_key not in st.session_state:
            st.session_state[tracker_key] = {
                "overview": st.empty(),
                "details": st.empty()
            }
        self.ui_containers = st.session_state[tracker_key]
        
        # Render throttling - limit render frequency to avoid performance issues
        render_throttle_key = f"progress_tracker_render_{self.operation_name}"
        if render_throttle_key not in st.session_state:
            st.session_state[render_throttle_key] = {
                "last_render_time": 0.0,
                "pending_render": False,
                "min_render_interval": 0.3  # Minimum seconds between renders (300ms)
            }
        self._render_throttle = st.session_state[render_throttle_key]
        
        # Initialize session state
        if "detailed_progress_tracker" not in st.session_state:
            st.session_state.detailed_progress_tracker = self._get_state()

    def _get_state(self) -> Dict[str, Any]:
        """Get current state dictionary."""
        return {
            "total_files": self.total_files,
            "file_progress": {k: {
                "filename": v.filename,
                "status": v.status,
                "current_page": v.current_page,
                "total_pages": v.total_pages,
                "completed_pages": v.completed_pages,
                "failed_pages": v.failed_pages,
                "current_stage": v.current_stage,
                "elapsed_time": v.elapsed_time,
                "pages_per_second": v.pages_per_second,
                "error": v.error
            } for k, v in self.file_progress.items()},
            "total_pages": self.total_pages,
            "completed_pages": self.completed_pages,
            "failed_pages_count": self.failed_pages_count,
            "start_time": self.start_time
        }

    def initialize_file(self, filename: str, total_pages: int = 0) -> None:
        """
        Initialize progress tracking for a file.

        Args:
            filename: File name
            total_pages: Total number of pages in the file
        """
        if filename not in self.file_progress:
            self.file_progress[filename] = FileProgress(
                filename=filename,
                status="waiting",
                total_pages=total_pages,
                start_time=None
            )
            self.total_pages += total_pages

    def start_file(self, filename: str) -> None:
        """
        Mark a file as started processing.

        Args:
            filename: File name
        """
        if filename in self.file_progress:
            self.file_progress[filename].status = "processing"
            self.file_progress[filename].start_time = time.time()
            self.file_progress[filename].current_stage = self.stages[0]

    def update_file_stage(self, filename: str, stage_index: int) -> None:
        """
        Update the current stage for a file.

        Args:
            filename: File name
            stage_index: Index of the current stage
        """
        if filename in self.file_progress and 0 <= stage_index < len(self.stages):
            self.file_progress[filename].current_stage = self.stages[stage_index]

    def update_file_page_progress(
        self,
        filename: str,
        current_page: int,
        total_pages: Optional[int] = None
    ) -> None:
        """
        Update page progress for a file (thread-safe).

        Args:
            filename: File name
            current_page: Current page index (1-based)
            total_pages: Total pages (if different from initialized)
        """
        with self._lock:
            if filename in self.file_progress:
                file_prog = self.file_progress[filename]
                file_prog.current_page = current_page
                file_prog.completed_pages = current_page
                
                if total_pages is not None:
                    file_prog.total_pages = total_pages
                
                # Update elapsed time and speed
                if file_prog.start_time:
                    file_prog.elapsed_time = time.time() - file_prog.start_time
                    if file_prog.elapsed_time > 0:
                        file_prog.pages_per_second = current_page / file_prog.elapsed_time
                
                # Update total completed pages
                self.completed_pages = sum(f.completed_pages for f in self.file_progress.values())

    def update_page_status(
        self,
        filename: str,
        page_index: int,
        status: str,
        error: Optional[str] = None,
        is_retry: bool = False
    ) -> None:
        """
        Update status for a specific page (thread-safe).

        Args:
            filename: File name
            page_index: Page index (0-based)
            status: Status (processing/completed/failed/retrying)
            error: Error message if failed
            is_retry: Whether this is a retry attempt
        """
        with self._lock:
            if filename in self.file_progress:
                file_prog = self.file_progress[filename]
                # Use "retrying" status if it's a retry attempt and status is processing
                if is_retry and status == "processing":
                    file_prog.page_statuses[page_index] = "retrying"
                else:
                    file_prog.page_statuses[page_index] = status
                
                if status == "completed":
                    # Remove from failed pages if it was previously failed
                    if page_index in file_prog.failed_pages:
                        file_prog.failed_pages.remove(page_index)
                        self.failed_pages_count = max(0, self.failed_pages_count - 1)
                    # Update completed pages count
                    if page_index + 1 > file_prog.completed_pages:
                        file_prog.completed_pages = page_index + 1
                    # Recalculate total completed pages
                    self.completed_pages = sum(f.completed_pages for f in self.file_progress.values())
                elif status == "failed":
                    if page_index not in file_prog.failed_pages:
                        file_prog.failed_pages.append(page_index)
                        self.failed_pages_count += 1

    def complete_file(self, filename: str, success: bool = True, error: Optional[str] = None) -> None:
        """
        Mark a file as completed or failed.

        Args:
            filename: File name
            success: Whether processing succeeded
            error: Error message if failed
        """
        if filename in self.file_progress:
            file_prog = self.file_progress[filename]
            if success:
                file_prog.status = "completed"
                file_prog.current_stage = "完成"
            else:
                file_prog.status = "failed"
                file_prog.error = error
                file_prog.current_stage = "失败"
            
            # Update elapsed time
            if file_prog.start_time:
                file_prog.elapsed_time = time.time() - file_prog.start_time

    def get_overall_progress(self) -> OverallProgress:
        """
        Get overall progress information.

        Returns:
            OverallProgress object
        """
        completed = sum(1 for f in self.file_progress.values() if f.status == "completed")
        failed = sum(1 for f in self.file_progress.values() if f.status == "failed")
        processing = sum(1 for f in self.file_progress.values() if f.status == "processing")
        waiting = sum(1 for f in self.file_progress.values() if f.status == "waiting")
        
        elapsed = time.time() - self.start_time
        
        # Calculate overall speed
        if elapsed > 0:
            overall_speed = self.completed_pages / elapsed
        else:
            overall_speed = 0.0
        
        # Calculate remaining time
        remaining_pages = self.total_pages - self.completed_pages
        if overall_speed > 0:
            remaining_time = remaining_pages / overall_speed
        else:
            remaining_time = 0.0
        
        # Get concurrency stats
        try:
            controller = GlobalConcurrencyController.get_instance_sync()
            concurrency_stats = controller.get_stats()
        except Exception:
            concurrency_stats = None
        
        # Determine current stage
        current_stage = "准备中"
        for file_prog in self.file_progress.values():
            if file_prog.status == "processing":
                current_stage = file_prog.current_stage
                break
        
        return OverallProgress(
            total_files=self.total_files,
            completed_files=completed,
            failed_files=failed,
            processing_files=processing,
            waiting_files=waiting,
            total_pages=self.total_pages,
            completed_pages=self.completed_pages,
            failed_pages=self.failed_pages_count,
            current_stage=current_stage,
            overall_speed=overall_speed,
            elapsed_time=elapsed,
            remaining_time=remaining_time,
            concurrency_stats=concurrency_stats,
            processing_mode=self.processing_mode
        )

    def render_overview(self) -> None:
        """Render overview panel with key metrics."""
        overall = self.get_overall_progress()
        
        # Render all content in a single container to avoid duplication
        with self.ui_containers["overview"].container():
            # Overall progress bar
            file_progress_pct = (
                (overall.completed_files + overall.failed_files) / self.total_files * 100
                if self.total_files > 0 else 0
            )
            st.progress(file_progress_pct / 100)
            
            # Key metrics in columns
            col1, col2, col3, col4, col5 = st.columns(5)
            
            with col1:
                st.metric(
                    "总体进度",
                    f"{overall.completed_files + overall.failed_files}/{self.total_files}",
                    f"{file_progress_pct:.1f}%"
                )
            
            with col2:
                st.metric("✅ 成功", overall.completed_files)
            
            with col3:
                st.metric("❌ 失败", overall.failed_files)
            
            with col4:
                st.metric("🔄 处理中", overall.processing_files)
            
            with col5:
                # Format remaining time
                if overall.remaining_time > 0:
                    mins = int(overall.remaining_time // 60)
                    secs = int(overall.remaining_time % 60)
                    remaining_str = f"{mins}:{secs:02d}"
                else:
                    remaining_str = "计算中..."
                st.metric("⏱️ 剩余时间", remaining_str)
            
            # Current file and stage
            current_file = None
            for file_prog in self.file_progress.values():
                if file_prog.status == "processing":
                    current_file = file_prog
                    break
            
            if current_file:
                page_progress_pct = (
                    current_file.completed_pages / current_file.total_pages * 100
                    if current_file.total_pages > 0 else 0
                )
                
                st.info(
                    f"**当前文件**: {current_file.filename} | "
                    f"**阶段**: {current_file.current_stage} | "
                    f"**页面进度**: {current_file.completed_pages}/{current_file.total_pages} "
                    f"({page_progress_pct:.1f}%)"
                )
                
                # Page-level progress bar
                st.progress(page_progress_pct / 100)
            else:
                st.info(f"**{self.operation_name}** - {overall.current_stage}")
            
            # Performance metrics
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("处理速度", f"{overall.overall_speed:.2f} 页/秒")
            with col2:
                elapsed_mins = int(overall.elapsed_time // 60)
                elapsed_secs = int(overall.elapsed_time % 60)
                st.metric("已用时间", f"{elapsed_mins}:{elapsed_secs:02d}")
            with col3:
                if overall.concurrency_stats:
                    st.metric(
                        "并发请求",
                        f"{overall.concurrency_stats.current_requests}/{overall.concurrency_stats.peak_requests}"
                    )
                else:
                    st.metric("并发请求", "N/A")

    def render_details(self) -> None:
        """Render detailed information in expandable panel."""
        overall = self.get_overall_progress()
        
        # Render in a container to avoid duplication
        with self.ui_containers["details"].container():
            with st.expander("📊 详细信息", expanded=False):
                # File list table
                st.subheader("文件处理状态")
                
                if self.file_progress:
                    # Create table data
                    table_data = []
                    for filename, file_prog in self.file_progress.items():
                        status_icon = {
                            "waiting": "⏳",
                            "processing": "🔄",
                            "completed": "✅",
                            "failed": "❌"
                        }.get(file_prog.status, "❓")
                        
                        progress_pct = (
                            file_prog.completed_pages / file_prog.total_pages * 100
                            if file_prog.total_pages > 0 else 0
                        )
                        
                        elapsed_str = f"{int(file_prog.elapsed_time // 60)}:{int(file_prog.elapsed_time % 60):02d}" if file_prog.elapsed_time > 0 else "-"
                        
                        table_data.append({
                            "文件": filename,
                            "状态": f"{status_icon} {file_prog.status}",
                            "阶段": file_prog.current_stage,
                            "页面": f"{file_prog.completed_pages}/{file_prog.total_pages}",
                            "进度": f"{progress_pct:.1f}%",
                            "速度": f"{file_prog.pages_per_second:.2f} 页/秒" if file_prog.pages_per_second > 0 else "-",
                            "耗时": elapsed_str
                        })
                    
                    st.dataframe(table_data, use_container_width=True)
                
                # Current processing file details
                current_file = None
                for file_prog in self.file_progress.values():
                    if file_prog.status == "processing":
                        current_file = file_prog
                        break
                
                if current_file:
                    st.subheader(f"当前处理文件: {current_file.filename}")
                    
                    # Page status list
                    if current_file.page_statuses:
                        st.write("**页面处理状态:**")
                        cols = st.columns(min(10, current_file.total_pages))
                        for page_idx in range(current_file.total_pages):
                            col_idx = page_idx % len(cols)
                            with cols[col_idx]:
                                status = current_file.page_statuses.get(page_idx, "waiting")
                                if status == "completed":
                                    st.write(f"✅ {page_idx + 1}")
                                elif status == "failed":
                                    st.write(f"❌ {page_idx + 1}")
                                elif status == "retrying":
                                    st.write(f"🔄 {page_idx + 1} (重试)")
                                elif status == "processing":
                                    st.write(f"🔄 {page_idx + 1}")
                                else:
                                    st.write(f"⏳ {page_idx + 1}")
                
                # Performance metrics
                st.subheader("性能指标")
                perf_col1, perf_col2, perf_col3 = st.columns(3)
                
                with perf_col1:
                    st.write(f"**总页数**: {overall.total_pages}")
                    st.write(f"**已完成页数**: {overall.completed_pages}")
                    st.write(f"**失败页数**: {overall.failed_pages}")
                
                with perf_col2:
                    st.write(f"**处理速度**: {overall.overall_speed:.2f} 页/秒")
                    if overall.total_files > 0:
                        avg_file_time = overall.elapsed_time / overall.total_files
                        st.write(f"**平均文件耗时**: {int(avg_file_time // 60)}:{int(avg_file_time % 60):02d}")
                    if overall.completed_pages > 0:
                        avg_page_time = overall.elapsed_time / overall.completed_pages
                        st.write(f"**平均页面耗时**: {avg_page_time:.2f} 秒")
                
                with perf_col3:
                    if overall.concurrency_stats:
                        st.write(f"**当前并发**: {overall.concurrency_stats.current_requests}")
                        st.write(f"**峰值并发**: {overall.concurrency_stats.peak_requests}")
                        st.write(f"**阻塞请求**: {overall.concurrency_stats.blocked_requests}")
                        st.write(f"**总请求数**: {overall.concurrency_stats.total_requests}")
                    else:
                        st.write("**并发统计**: 不可用")
                
                # Failed files/pages
                failed_files = [f for f in self.file_progress.values() if f.status == "failed"]
                if failed_files:
                    st.subheader("失败文件")
                    for file_prog in failed_files:
                        st.error(f"❌ {file_prog.filename}: {file_prog.error or '未知错误'}")

    def render(self, force: bool = False) -> None:
        """
        Render both overview and details with throttling.
        
        Args:
            force: If True, render immediately regardless of throttle
        """
        current_time = time.time()
        last_render_time = self._render_throttle["last_render_time"]
        min_interval = self._render_throttle["min_render_interval"]
        
        # Check if we should render (throttle check)
        time_since_last_render = current_time - last_render_time
        should_render = force or time_since_last_render >= min_interval
        
        if not should_render:
            # Mark that we have pending updates
            self._render_throttle["pending_render"] = True
            return
        
        # Perform the actual render
        self._do_render()
        
        # Update throttle state
        self._render_throttle["last_render_time"] = current_time
        self._render_throttle["pending_render"] = False
    
    def _do_render(self) -> None:
        """Internal method to perform the actual rendering."""
        try:
            # Only render if we're in the main thread (Streamlit requirement)
            # Check if we have a valid Streamlit context
            try:
                from streamlit.runtime.scriptrunner import get_script_run_ctx
                ctx = get_script_run_ctx()
                if ctx is None:
                    # Not in main thread or no context, skip rendering
                    return
            except (ImportError, AttributeError, RuntimeError):
                # Can't determine context, skip rendering to be safe
                return
            
            # Ensure containers exist and are valid
            if "overview" not in self.ui_containers or "details" not in self.ui_containers:
                return
            
            self.render_overview()
            self.render_details()
            
            # Update session state
            st.session_state.detailed_progress_tracker = self._get_state()
        except (RuntimeError, AttributeError) as e:
            # Silently ignore rendering errors in background threads or invalid contexts
            # This prevents "setIn cannot be called on an ElementNode" errors
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Render skipped (likely in background thread or invalid context): {e}")
        except Exception as e:
            # Log other unexpected errors but don't crash
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"Unexpected error during render: {e}", exc_info=True)
    
    def force_render(self) -> None:
        """Force immediate render, bypassing throttle."""
        self.render(force=True)
    
    def create_thread_safe_callbacks(self, filename: str) -> Tuple[Callable, Callable]:
        """
        Create thread-safe progress callbacks for concurrent processing.
        
        Args:
            filename: File name
            
        Returns:
            Tuple of (on_progress, on_page_status) callbacks
        """
        def on_progress(done: int, total: int):
            """Thread-safe progress callback."""
            self.update_file_page_progress(filename, done, total)
            self.update_file_stage(filename, 1)  # Stage 1: Composing
            # Note: render() is not thread-safe, so we skip it here
            # The main thread will call render() periodically
        
        def on_page_status(page_index: int, status: str, error: Optional[str]):
            """Thread-safe page status callback."""
            self.update_page_status(filename, page_index, status, error)
            # Note: render() is not thread-safe, so we skip it here
            # The main thread will call render() periodically
        
        return on_progress, on_page_status

    def reset(self) -> None:
        """Reset the tracker."""
        self.__init__(self.total_files, self.operation_name, self.processing_mode)


