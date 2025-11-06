"""
Batch Handler.

Manages batch processing operations.
"""

from typing import Dict, Any, List, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import streamlit as st
from .file_handler import FileHandler
from ..components.progress_tracker import ProgressTracker


class BatchHandler:
    """Handles batch file processing operations."""

    def __init__(self, max_workers: int = 5):
        """
        Initialize batch handler.

        Args:
            max_workers: Maximum number of worker threads
        """
        self.max_workers = max_workers
        self.file_handler = FileHandler()

    def process_batch(
        self,
        files: List,
        params: Dict[str, Any],
        on_progress: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process multiple files in batch.

        Args:
            files: List of uploaded files
            params: Processing parameters
            on_progress: Callback for progress updates

        Returns:
            Dictionary mapping filenames to results
        """
        results = {}
        total_files = len(files)

        # Create progress tracker
        progress_tracker = ProgressTracker(total_files, "批量处理中")
        progress_tracker.render()

        # Process files
        for i, file in enumerate(files):
            # Update progress
            progress_info = progress_tracker.update(i, "正在处理文件", "processing")

            # Process file
            file.seek(0)  # Reset file pointer
            file_bytes = file.read()

            try:
                result = self.file_handler.process_file(
                    file_bytes,
                    file.name,
                    params
                )
                results[file.name] = result

                # Update progress to completed
                progress_info = progress_tracker.update(i, "处理完成", "completed")

            except Exception as e:
                results[file.name] = {
                    "status": "failed",
                    "error": str(e)
                }
                progress_info = progress_tracker.update(i, "处理失败", "failed")

            # Call progress callback if provided
            if on_progress:
                on_progress(i + 1, file.name)

        return results

    def process_batch_concurrent(
        self,
        files: List,
        params: Dict[str, Any],
        on_progress: Optional[Callable[[int, str], None]] = None,
        max_workers: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process multiple files concurrently.

        Args:
            files: List of uploaded files
            params: Processing parameters
            on_progress: Callback for progress updates
            max_workers: Maximum worker threads (overrides instance default)

        Returns:
            Dictionary mapping filenames to results
        """
        if max_workers is None:
            max_workers = self.max_workers

        results = {}
        total_files = len(files)

        # Create progress tracker
        progress_tracker = ProgressTracker(total_files, "批量并发处理中")
        progress_tracker.render()

        # Submit all tasks
        future_to_file = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for file in files:
                file.seek(0)
                file_bytes = file.read()
                future = executor.submit(
                    self._process_single_file_safe,
                    file_bytes,
                    file.name,
                    params
                )
                future_to_file[future] = file.name

            # Collect results as they complete
            completed_count = 0
            for future in as_completed(future_to_file):
                filename = future_to_file[future]
                completed_count += 1

                try:
                    result = future.result()
                    results[filename] = result

                    # Update progress
                    status = result.get("status", "unknown")
                    if status == "completed":
                        progress_tracker.update(
                            completed_count - 1,
                            f"已完成 {filename}",
                            "completed"
                        )
                    else:
                        progress_tracker.update(
                            completed_count - 1,
                            f"失败 {filename}",
                            "failed"
                        )

                except Exception as e:
                    results[filename] = {
                        "status": "failed",
                        "error": str(e)
                    }
                    progress_tracker.update(
                        completed_count - 1,
                        f"异常 {filename}",
                        "failed"
                    )

                # Call progress callback
                if on_progress:
                    on_progress(completed_count, filename)

        return results

    def _process_single_file_safe(
        self,
        file_bytes: bytes,
        filename: str,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process a single file safely (for threading).

        Args:
            file_bytes: File bytes
            filename: File name
            params: Processing parameters

        Returns:
            Processing result
        """
        try:
            return self.file_handler.process_file(file_bytes, filename, params)
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }

    def retry_failed_files(
        self,
        batch_results: Dict[str, Any],
        original_files: List,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retry processing of failed files.

        Args:
            batch_results: Previous batch results
            original_files: Original uploaded files
            params: Processing parameters

        Returns:
            Updated results dictionary
        """
        # Find failed files
        failed_files = [
            filename
            for filename, result in batch_results.items()
            if result.get("status") == "failed"
        ]

        if not failed_files:
            return batch_results

        # Find corresponding file objects
        file_map = {f.name: f for f in original_files}
        files_to_retry = [file_map[fname] for fname in failed_files if fname in file_map]

        # Process failed files
        st.info(f"开始重试 {len(files_to_retry)} 个失败的文件...")

        retry_results = self.process_batch(files_to_retry, params)

        # Update results
        updated_results = batch_results.copy()
        for filename, result in retry_results.items():
            updated_results[filename] = result

        return updated_results


class SmartBatchHandler(BatchHandler):
    """Smart batch handler with optimization features."""

    def __init__(self, max_workers: int = 5):
        """Initialize smart batch handler."""
        super().__init__(max_workers)
        self.adaptive_workers = True

    def process_with_optimization(
        self,
        files: List,
        params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process batch with automatic optimization.

        Args:
            files: List of uploaded files
            params: Processing parameters

        Returns:
            Processing results
        """
        # Adapt worker count based on system and file size
        file_sizes = [len(f.read()) for f in files]
        f.seek(0) for f in files  # Reset all file pointers

        # Calculate average file size
        avg_size_mb = sum(file_sizes) / (1024 * 1024 * len(files))

        # Adjust worker count based on file size
        if avg_size_mb > 20:  # Large files
            max_workers = 2
        elif avg_size_mb > 10:  # Medium files
            max_workers = 3
        else:  # Small files
            max_workers = min(10, len(files))

        st.info(f"优化设置: {max_workers} 个并发工作线程 (平均文件大小: {avg_size_mb:.1f}MB)")

        # Choose processing method based on file count
        if len(files) <= 3:
            # Few files, use sequential processing
            return self.process_batch(files, params)
        else:
            # Many files, use concurrent processing
            return self.process_batch_concurrent(files, params, max_workers=max_workers)
