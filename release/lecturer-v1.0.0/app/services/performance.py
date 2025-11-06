"""
Performance monitoring utilities.

This module provides decorators and utilities for measuring
and monitoring function performance.
"""

import time
import functools
from typing import Callable, Any, Optional
from .logger import get_logger

logger = get_logger()


def measure_time(
    func: Optional[Callable] = None,
    log_level: str = "info",
    threshold_seconds: float = 1.0
) -> Callable:
    """
    Decorator to measure function execution time.
    
    Args:
        func: Function to measure (if used as decorator without parentheses)
        log_level: Logging level ("debug", "info", "warning")
        threshold_seconds: Log warning if execution time exceeds this threshold
        
    Example:
        @measure_time
        def my_function():
            pass
        
        @measure_time(threshold_seconds=2.0)
        def slow_function():
            pass
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
                return result
            finally:
                elapsed = time.time() - start_time
                log_message = f"{f.__name__} took {elapsed:.2f}s"
                
                if elapsed > threshold_seconds:
                    log_func = getattr(logger, "warning", logger.info)
                    log_func(f"{log_message} (exceeded threshold of {threshold_seconds}s)")
                else:
                    log_func = getattr(logger, log_level, logger.info)
                    log_func(log_message)
        
        return wrapper
    
    if func is None:
        # Used as @measure_time(threshold_seconds=2.0)
        return decorator
    else:
        # Used as @measure_time
        return decorator(func)


class PerformanceMonitor:
    """Context manager for monitoring code blocks."""
    
    def __init__(self, name: str, threshold_seconds: float = 1.0):
        """
        Initialize performance monitor.
        
        Args:
            name: Name for this monitoring block
            threshold_seconds: Warn if execution exceeds this time
        """
        self.name = name
        self.threshold_seconds = threshold_seconds
        self.start_time: Optional[float] = None
        self.elapsed: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            self.elapsed = time.time() - self.start_time
            log_message = f"{self.name} took {self.elapsed:.2f}s"
            
            if self.elapsed > self.threshold_seconds:
                logger.warning(f"{log_message} (exceeded threshold of {self.threshold_seconds}s)")
            else:
                logger.debug(log_message)
        
        return False  # Don't suppress exceptions
    
    def get_elapsed(self) -> float:
        """Get elapsed time in seconds."""
        if self.elapsed is not None:
            return self.elapsed
        elif self.start_time is not None:
            return time.time() - self.start_time
        else:
            return 0.0


# Example usage:
# with PerformanceMonitor("process_pdf_file"):
#     result = process_file(...)

