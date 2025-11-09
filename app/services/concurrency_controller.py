"""
Global Concurrency Controller.

Provides centralized concurrency management to prevent resource exhaustion
from concurrent file and page processing.
"""

import asyncio
import time
from typing import Optional
from dataclasses import dataclass, field
from .logger import get_logger

logger = get_logger()


@dataclass
class ConcurrencyStats:
    """Statistics for concurrency usage."""
    current_requests: int = 0
    peak_requests: int = 0
    total_requests: int = 0
    blocked_requests: int = 0
    last_reset: float = field(default_factory=time.time)


class GlobalConcurrencyController:
    """
    Global concurrency controller to prevent resource exhaustion.
    
    This controller manages the total number of concurrent API requests
    across all files and pages to prevent exceeding API limits and
    system resources.
    """
    
    _instance: Optional['GlobalConcurrencyController'] = None
    _lock = asyncio.Lock()
    _adjust_lock = asyncio.Lock()  # Lock for serializing limit adjustments
    
    def __init__(self, max_global_concurrency: int = 200):
        """
        Initialize global concurrency controller.
        
        Args:
            max_global_concurrency: Maximum total concurrent requests across all operations
        """
        self.max_global_concurrency = max_global_concurrency
        self.semaphore: Optional[asyncio.Semaphore] = None
        self._semaphore_loop: Optional[asyncio.AbstractEventLoop] = None
        self.stats = ConcurrencyStats()
        self._active_requests: set[str] = set()
        self._request_counter = 0
    
    @classmethod
    async def get_instance(cls, max_global_concurrency: int = 200) -> 'GlobalConcurrencyController':
        """
        Get or create singleton instance.
        
        Args:
            max_global_concurrency: Maximum global concurrency (only used on first creation)
            
        Returns:
            Global concurrency controller instance
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_global_concurrency)
        return cls._instance
    
    @classmethod
    def get_instance_sync(cls, max_global_concurrency: int = 200) -> 'GlobalConcurrencyController':
        """
        Get or create singleton instance (synchronous version).
        
        Args:
            max_global_concurrency: Maximum global concurrency (only used on first creation)
            
        Returns:
            Global concurrency controller instance
        """
        if cls._instance is None:
            cls._instance = cls(max_global_concurrency)
        return cls._instance
    
    def _ensure_semaphore(self) -> None:
        """
        Ensure semaphore exists and is bound to the current event loop.
        This method should be called from within an async context.
        """
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create one temporarily (shouldn't happen in normal usage)
            current_loop = asyncio.get_event_loop()
        
        # If semaphore doesn't exist or is bound to a different loop, create a new one
        if self.semaphore is None or self._semaphore_loop != current_loop:
            # If we had an old semaphore, we need to account for its current usage
            # Calculate how many slots are currently in use
            if self.semaphore is not None:
                # Get current usage from stats
                current_used = self.stats.current_requests
            else:
                current_used = 0
            
            # Create new semaphore with correct available slots
            available_slots = max(0, self.max_global_concurrency - current_used)
            self.semaphore = asyncio.Semaphore(available_slots)
            self._semaphore_loop = current_loop
    
    async def acquire(self, request_id: Optional[str] = None) -> None:
        """
        Acquire a concurrency slot.
        
        Args:
            request_id: Optional identifier for this request (for tracking)
        """
        # Ensure semaphore is bound to current event loop
        self._ensure_semaphore()
        
        # Check if we need to wait
        if self.semaphore._value <= 0:
            self.stats.blocked_requests += 1
            if self.stats.blocked_requests % 10 == 0:
                logger.warning(
                    f"Global concurrency limit reached ({self.max_global_concurrency}). "
                    f"{self.stats.blocked_requests} requests blocked."
                )
        
        await self.semaphore.acquire()
        
        # Update statistics
        self.stats.current_requests += 1
        self.stats.total_requests += 1
        self.stats.peak_requests = max(
            self.stats.peak_requests,
            self.stats.current_requests
        )
        
        if request_id:
            self._active_requests.add(request_id)
    
    def release(self, request_id: Optional[str] = None) -> None:
        """
        Release a concurrency slot.
        
        Args:
            request_id: Optional identifier for this request
        """
        # Ensure semaphore exists before releasing
        if self.semaphore is not None:
            try:
                self.semaphore.release()
            except RuntimeError:
                # Semaphore might be bound to different loop, ignore
                # The acquire method will recreate it if needed
                pass
        
        self.stats.current_requests = max(0, self.stats.current_requests - 1)
        
        if request_id and request_id in self._active_requests:
            self._active_requests.remove(request_id)
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.release()
    
    def get_stats(self) -> ConcurrencyStats:
        """Get current concurrency statistics."""
        return self.stats
    
    def get_available_slots(self) -> int:
        """Get number of available concurrency slots."""
        if self.semaphore is None:
            return self.max_global_concurrency
        try:
            return self.semaphore._value
        except (AttributeError, RuntimeError):
            # Semaphore might be bound to different loop or not exist
            return self.max_global_concurrency - self.stats.current_requests
    
    def reset_stats(self) -> None:
        """Reset statistics (useful for monitoring periods)."""
        self.stats = ConcurrencyStats()
    
    async def wait_for_all_requests(self, timeout: float = 300.0) -> None:
        """
        Wait for all current requests to complete.
        
        Args:
            timeout: Maximum time to wait in seconds (default 5 minutes)
        """
        start_time = time.time()
        check_interval = 0.1  # Check every 100ms
        
        while self.stats.current_requests > 0:
            if time.time() - start_time > timeout:
                logger.warning(
                    f"Timeout waiting for requests to complete. "
                    f"Still {self.stats.current_requests} active requests."
                )
                break
            await asyncio.sleep(check_interval)
        
        logger.info(
            f"All requests completed. Waited {time.time() - start_time:.2f} seconds."
        )
    
    def adjust_limit(self, new_limit: int) -> None:
        """
        Adjust the global concurrency limit.
        
        Note: This method does NOT wait for current requests to complete.
        Use adjust_limit_async() if you need to wait for requests to finish.
        
        Args:
            new_limit: New maximum concurrency limit
        """
        if new_limit < 1:
            raise ValueError("Concurrency limit must be at least 1")
        
        old_limit = self.max_global_concurrency
        
        # If limit hasn't changed, do nothing
        if new_limit == old_limit:
            return
        
        # Calculate current usage from stats
        current_used = self.stats.current_requests
        
        # If new limit is smaller than current usage, we should wait
        # But this is a sync method, so we just log a warning
        if new_limit < current_used:
            logger.warning(
                f"Adjusting limit from {old_limit} to {new_limit}, but {current_used} "
                f"requests are still active. Consider using adjust_limit_async() to wait."
            )
        
        # Update the limit
        self.max_global_concurrency = new_limit
        
        # Invalidate semaphore so it will be recreated with new limit on next acquire
        # This ensures the new limit is respected in the current event loop
        self.semaphore = None
        self._semaphore_loop = None
        
        logger.info(
            f"Global concurrency limit adjusted from {old_limit} to {new_limit}. "
            f"Current active: {current_used}, New limit will be applied on next acquire"
        )
    
    async def adjust_limit_async(self, new_limit: int, wait_for_completion: bool = True) -> None:
        """
        Adjust the global concurrency limit asynchronously, optionally waiting for current requests.
        This method is serialized using a lock to prevent race conditions.
        
        Args:
            new_limit: New maximum concurrency limit
            wait_for_completion: If True, wait for all current requests to complete before adjusting
        """
        if new_limit < 1:
            raise ValueError("Concurrency limit must be at least 1")
        
        # Serialize limit adjustments to prevent race conditions
        async with self._adjust_lock:
            old_limit = self.max_global_concurrency
            
            # If limit hasn't changed, do nothing
            if new_limit == old_limit:
                return
            
            # Calculate current usage from stats
            current_used = self.stats.current_requests
            
            # If new limit is smaller and we should wait, wait for requests to complete
            if wait_for_completion and new_limit < current_used:
                logger.info(
                    f"New limit {new_limit} is smaller than current active requests ({current_used}). "
                    f"Waiting for requests to complete..."
                )
                await self.wait_for_all_requests()
            
            # Update the limit
            self.max_global_concurrency = new_limit
            
            # Invalidate semaphore so it will be recreated with new limit on next acquire
            self.semaphore = None
            self._semaphore_loop = None
            
            logger.info(
                f"Global concurrency limit adjusted from {old_limit} to {new_limit}. "
                f"Current active: {self.stats.current_requests}, New limit will be applied on next acquire"
            )


def calculate_optimal_concurrency(
    page_concurrency: int,
    file_count: int,
    rpm_limit: int,
    max_global_concurrency: int = 200
) -> tuple[int, int]:
    """
    Calculate optimal concurrency settings considering global limits.
    
    Args:
        page_concurrency: Desired page-level concurrency
        file_count: Number of files being processed
        rpm_limit: API RPM limit
        max_global_concurrency: Maximum global concurrency limit
        
    Returns:
        Tuple of (adjusted_page_concurrency, adjusted_file_concurrency)
    """
    # Calculate theoretical maximum concurrent requests
    theoretical_max = page_concurrency * file_count
    
    # Limit by global concurrency
    if theoretical_max > max_global_concurrency:
        # Scale down proportionally
        scale_factor = max_global_concurrency / theoretical_max
        adjusted_page_concurrency = max(1, int(page_concurrency * scale_factor))
        adjusted_file_concurrency = file_count
    else:
        adjusted_page_concurrency = page_concurrency
        adjusted_file_concurrency = file_count
    
    # Also consider API RPM limit (with safety margin)
    # Assume average request takes 2-3 seconds, so we want to stay under RPM/2
    safe_rpm = max(1, rpm_limit // 2)
    if adjusted_page_concurrency * adjusted_file_concurrency > safe_rpm:
        # Scale down to stay within safe RPM
        scale_factor = safe_rpm / (adjusted_page_concurrency * adjusted_file_concurrency)
        adjusted_page_concurrency = max(1, int(adjusted_page_concurrency * scale_factor))
    
    return adjusted_page_concurrency, adjusted_file_concurrency

