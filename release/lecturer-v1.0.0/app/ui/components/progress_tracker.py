"""
Progress Tracker Component.

Provides detailed progress tracking and status updates for long-running operations.
"""

import time
from typing import Dict, Any, Optional
import streamlit as st


class ProgressTracker:
    """Tracks and displays progress for batch operations."""

    def __init__(self, total_items: int, operation_name: str = "处理中"):
        """
        Initialize progress tracker.

        Args:
            total_items: Total number of items to process
            operation_name: Name of the operation being tracked
        """
        self.total = total_items
        self.current = 0
        self.completed = 0
        self.failed = 0
        self.operation_name = operation_name
        self.start_time = time.time()
        self.stage = "准备中"
        self.failed_items = []

        # Initialize session state
        if "progress_tracker" not in st.session_state:
            st.session_state.progress_tracker = self._get_state()

    def _get_state(self) -> Dict[str, Any]:
        """Get current state dictionary."""
        return {
            "total": self.total,
            "current": self.current,
            "completed": self.completed,
            "failed": self.failed,
            "stage": self.stage,
            "start_time": self.start_time,
            "failed_items": self.failed_items
        }

    def update(self, item_index: int, stage: str, status: str = "processing") -> Dict[str, Any]:
        """
        Update progress.

        Args:
            item_index: Current item index (0-based)
            stage: Current operation stage
            status: Status of the item (processing, completed, failed)

        Returns:
            Dictionary with progress information
        """
        self.current = item_index + 1
        self.stage = stage

        if status == "completed":
            self.completed += 1
        elif status == "failed":
            self.failed += 1
            self.failed_items.append({
                "index": item_index,
                "time": time.time()
            })

        # Update state
        st.session_state.progress_tracker = self._get_state()

        return self.get_progress_info()

    def get_progress_info(self) -> Dict[str, Any]:
        """
        Get current progress information.

        Returns:
            Dictionary with progress details
        """
        elapsed = time.time() - self.start_time

        if self.current > 0:
            rate = self.current / elapsed if elapsed > 0 else 0
            estimated_total = (self.total * elapsed) / self.current
            remaining = max(0, estimated_total - elapsed)
        else:
            rate = 0
            remaining = 0

        progress_pct = (self.current / self.total) * 100 if self.total > 0 else 0

        return {
            "total": self.total,
            "current": self.current,
            "completed": self.completed,
            "failed": self.failed,
            "progress_pct": progress_pct,
            "stage": self.stage,
            "elapsed": elapsed,
            "remaining": remaining,
            "rate": rate,
            "failed_items": self.failed_items
        }

    def render(self) -> None:
        """Render progress indicators in Streamlit."""
        info = self.get_progress_info()

        # Overall progress bar
        progress_bar = st.progress(0)
        progress_bar.progress(info["progress_pct"] / 100)

        # Status columns
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "总体进度",
                f"{info['current']}/{info['total']}",
                f"{info['progress_pct']:.1f}%"
            )

        with col2:
            st.metric("✅ 成功", info["completed"])

        with col3:
            st.metric("❌ 失败", info["failed"])

        with col4:
            # Format remaining time
            if info["remaining"] > 0:
                mins = int(info["remaining"] // 60)
                secs = int(info["remaining"] % 60)
                remaining_str = f"{mins}:{secs:02d}"
            else:
                remaining_str = "计算中..."

            st.metric("⏱️ 剩余时间", remaining_str)

        # Current stage
        st.info(f"**{self.operation_name}** - {info['stage']}")

        # Failed items
        if info["failed_items"]:
            with st.expander(f"⚠️ 失败项目 ({len(info['failed_items'])})", expanded=False):
                for item in info["failed_items"]:
                    st.error(f"项目 {item['index'] + 1} 处理失败")

    def reset(self) -> None:
        """Reset the tracker."""
        self.__init__(self.total, self.operation_name)


class MultiStageProgressTracker:
    """Tracks progress across multiple stages of an operation."""

    def __init__(self, stages: list[str]):
        """
        Initialize multi-stage tracker.

        Args:
            stages: List of stage names
        """
        self.stages = stages
        self.current_stage_index = 0
        self.start_time = time.time()
        self.stage_start_time = time.time()

    def set_stage(self, stage_index: int) -> None:
        """Set current stage."""
        if 0 <= stage_index < len(self.stages):
            self.current_stage_index = stage_index
            self.stage_start_time = time.time()

    def get_current_stage(self) -> str:
        """Get current stage name."""
        return self.stages[self.current_stage_index] if self.stages else ""

    def render(self) -> None:
        """Render multi-stage progress."""
        total_stages = len(self.stages)
        overall_progress = (self.current_stage_index / total_stages) * 100

        # Show stage progress
        st.progress(overall_progress / 100)

        # Stage indicator
        st.info(f"阶段 {self.current_stage_index + 1}/{total_stages}: **{self.get_current_stage()}**")

        # Show all stages with current highlighted
        for i, stage in enumerate(self.stages):
            if i == self.current_stage_index:
                st.write(f"🔄 **{stage}** (当前)")
            elif i < self.current_stage_index:
                st.write(f"✅ {stage} (已完成)")
            else:
                st.write(f"⏳ {stage} (等待中)")
