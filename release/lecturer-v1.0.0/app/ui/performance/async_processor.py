"""
Async Processor.

Provides asynchronous processing capabilities.
"""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from typing import List, Callable, Any, Dict, Optional, Iterator
import streamlit as st


class AsyncProcessor:
    """Asynchronous processor for concurrent operations."""

    def __init__(
        self,
        max_workers: int = 5,
        use_threads: bool = True
    ):
        """
        Initialize async processor.

        Args:
            max_workers: Maximum number of worker threads/processes
            use_threads: Whether to use threads (True) or processes (False)
        """
        self.max_workers = max_workers
        self.use_threads = use_threads

    def execute_in_parallel(
        self,
        func: Callable,
        items: List[Any],
        show_progress: bool = True,
        progress_label: str = "处理中"
    ) -> List[Any]:
        """
        Execute function in parallel across items.

        Args:
            func: Function to execute
            items: List of items to process
            show_progress: Whether to show progress
            progress_label: Label for progress bar

        Returns:
            List of results
        """
        results = []
        total = len(items)

        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()

        # Choose executor type
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_item = {
                executor.submit(func, item): item
                for item in items
            }

            # Collect results
            for i, future in enumerate(as_completed(future_to_item)):
                item = future_to_item[future]

                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "error": str(e),
                        "item": item
                    })

                # Update progress
                if show_progress:
                    progress = (i + 1) / total
                    progress_bar.progress(progress)
                    status_text.text(f"{progress_label}: {i + 1}/{total}")

        return results

    def execute_with_batch_updates(
        self,
        func: Callable,
        items: List[Any],
        batch_size: int = 10,
        callback: Optional[Callable] = None
    ) -> Iterator[Dict[str, Any]]:
        """
        Execute function with batch updates.

        Args:
            func: Function to execute
            items: Items to process
            batch_size: Size of each batch
            callback: Callback for each batch completion

        Yields:
            Dictionary with batch results
        """
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor

        with executor_class(max_workers=self.max_workers) as executor:
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]

                future_to_item = {
                    executor.submit(func, item): item
                    for item in batch
                }

                batch_results = []
                for future in as_completed(future_to_item):
                    item = future_to_item[future]
                    try:
                        result = future.result()
                        batch_results.append(result)
                    except Exception as e:
                        batch_results.append({
                            "error": str(e),
                            "item": item
                        })

                yield {
                    "batch_index": i // batch_size,
                    "items": batch,
                    "results": batch_results,
                    "completed": min(i + batch_size, len(items)),
                    "total": len(items)
                }

                if callback:
                    callback(batch_results)

    def map_with_timeout(
        self,
        func: Callable,
        items: List[Any],
        timeout: Optional[float] = None
    ) -> List[Any]:
        """
        Map function over items with timeout.

        Args:
            func: Function to apply
            items: Items to process
            timeout: Timeout per item in seconds

        Returns:
            List of results with timeout handling
        """
        executor_class = ThreadPoolExecutor if self.use_threads else ProcessPoolExecutor

        results = []
        with executor_class(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(func, item): item
                for item in items
            }

            for future in as_completed(futures, timeout=timeout):
                item = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    results.append({
                        "error": str(e),
                        "item": item
                    })

        return results


class BatchAsyncProcessor:
    """Batch asynchronous processor with queue management."""

    def __init__(
        self,
        max_workers: int = 5,
        max_queue_size: int = 100
    ):
        """
        Initialize batch processor.

        Args:
            max_workers: Maximum worker threads
            max_queue_size: Maximum queue size
        """
        self.max_workers = max_workers
        self.max_queue_size = max_queue_size
        self.queue = asyncio.Queue(maxsize=max_queue_size)
        self.results = []
        self.active = False

    async def process_batch(
        self,
        items: List[Any],
        process_func: Callable,
        result_handler: Optional[Callable] = None
    ) -> List[Any]:
        """
        Process items in batch asynchronously.

        Args:
            items: Items to process
            process_func: Processing function
            result_handler: Optional result handler

        Returns:
            List of processed results
        """
        self.active = True
        self.results = []

        # Start workers
        workers = [
            asyncio.create_task(self._worker(process_func))
            for _ in range(self.max_workers)
        ]

        # Queue items
        for item in items:
            await self.queue.put(item)

        # Wait for all items to be processed
        await self.queue.join()

        # Cancel workers
        for worker in workers:
            worker.cancel()

        # Wait for workers to finish
        await asyncio.gather(*workers, return_exceptions=True)

        self.active = False
        return self.results

    async def _worker(self, process_func: Callable):
        """Worker coroutine."""
        while self.active:
            try:
                # Get item from queue
                item = await asyncio.wait_for(
                    self.queue.get(),
                    timeout=1.0
                )

                # Process item
                try:
                    result = process_func(item)
                    self.results.append(result)
                except Exception as e:
                    self.results.append({
                        "error": str(e),
                        "item": item
                    })

                # Mark task as done
                self.queue.task_done()

            except asyncio.TimeoutError:
                # No more items
                continue


# Helper functions
def run_async_in_thread(coro):
    """
    Run async coroutine in a thread.

    Args:
        coro: Coroutine to run

    Returns:
        Result of the coroutine
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def create_task_tracker(total_tasks: int):
    """
    Create a task tracker for async operations.

    Args:
        total_tasks: Total number of tasks

    Returns:
        Dictionary with tracking methods
    """
    completed = 0
    failed = 0
    start_time = None

    def update_completed():
        nonlocal completed
        completed += 1

    def update_failed():
        nonlocal failed
        failed += 1

    def get_progress():
        nonlocal start_time
        if start_time is None:
            start_time = time.time()

        elapsed = time.time() - start_time
        progress_pct = (completed + failed) / total_tasks * 100

        if completed + failed > 0:
            rate = (completed + failed) / elapsed
            estimated_total = total_tasks / rate if rate > 0 else 0
            remaining = max(0, estimated_total - elapsed)
        else:
            remaining = 0

        return {
            "completed": completed,
            "failed": failed,
            "progress_pct": progress_pct,
            "remaining": remaining
        }

    return {
        "update_completed": update_completed,
        "update_failed": update_failed,
        "get_progress": get_progress
    }
