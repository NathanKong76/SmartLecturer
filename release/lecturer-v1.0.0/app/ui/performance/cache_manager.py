"""
Cache Manager.

Provides advanced caching strategies for improved performance.
"""

import hashlib
import json
import pickle
import time
from typing import Any, Dict, Optional, Union
from pathlib import Path
import streamlit as st


class CacheManager:
    """Advanced cache manager with multiple storage backends."""

    def __init__(
        self,
        cache_dir: str = ".cache",
        memory_limit: int = 100,
        disk_limit: int = 1000,
        ttl: int = 3600
    ):
        """
        Initialize cache manager.

        Args:
            cache_dir: Directory for disk cache
            memory_limit: Maximum items in memory cache
            disk_limit: Maximum items on disk
            ttl: Time to live in seconds
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.memory_limit = memory_limit
        self.disk_limit = disk_limit
        self.ttl = ttl
        self.memory_cache = {}
        self.cache_index = self._load_cache_index()

    def _load_cache_index(self) -> Dict[str, Dict]:
        """Load cache index from disk."""
        index_file = self.cache_dir / "index.json"
        if index_file.exists():
            try:
                with open(index_file, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_cache_index(self) -> None:
        """Save cache index to disk."""
        index_file = self.cache_dir / "index.json"
        try:
            with open(index_file, 'w') as f:
                json.dump(self.cache_index, f)
        except Exception as e:
            st.warning(f"Failed to save cache index: {e}")

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = {
            "args": args,
            "kwargs": sorted(kwargs.items())
        }
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.md5(key_str.encode()).hexdigest()

    def _is_expired(self, key: str) -> bool:
        """Check if cache entry is expired."""
        if key not in self.cache_index:
            return True

        timestamp = self.cache_index[key].get("timestamp", 0)
        return (time.time() - timestamp) > self.ttl

    def _cleanup_expired(self) -> None:
        """Remove expired cache entries."""
        expired_keys = [
            key for key in self.cache_index
            if self._is_expired(key)
        ]

        for key in expired_keys:
            self._remove(key)

    def _evict_lru(self) -> None:
        """Evict least recently used items."""
        if len(self.memory_cache) >= self.memory_limit:
            # Simple LRU: remove oldest item
            oldest_key = min(
                self.memory_cache.keys(),
                key=lambda k: self.memory_cache[k].get("access_time", 0)
            )
            del self.memory_cache[oldest_key]

    def _remove(self, key: str) -> None:
        """Remove a cache entry."""
        # Remove from memory
        if key in self.memory_cache:
            del self.memory_cache[key]

        # Remove from disk
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists():
            cache_file.unlink()

        # Remove from index
        if key in self.cache_index:
            del self.cache_index[key]

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        # Check memory cache
        if key in self.memory_cache:
            entry = self.memory_cache[key]
            if not self._is_expired(key):
                entry["access_time"] = time.time()
                return entry["value"]
            else:
                self._remove(key)

        # Check disk cache
        cache_file = self.cache_dir / f"{key}.cache"
        if cache_file.exists() and not self._is_expired(key):
            try:
                with open(cache_file, 'rb') as f:
                    value = pickle.load(f)

                # Promote to memory cache
                self.memory_cache[key] = {
                    "value": value,
                    "access_time": time.time()
                }
                self._evict_lru()

                return value
            except Exception:
                # Remove corrupted cache
                self._remove(key)

        return None

    def set(self, key: str, value: Any) -> None:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        # Store in memory cache
        self.memory_cache[key] = {
            "value": value,
            "access_time": time.time()
        }
        self._evict_lru()

        # Store in disk cache (for large values or persistent storage)
        if self._should_persist(value):
            try:
                cache_file = self.cache_dir / f"{key}.cache"
                with open(cache_file, 'wb') as f:
                    pickle.dump(value, f)

                # Update index
                self.cache_index[key] = {
                    "timestamp": time.time(),
                    "size": len(pickle.dumps(value)),
                    "persistent": True
                }
            except Exception as e:
                st.warning(f"Failed to persist cache: {e}")

        # Clean up expired entries
        self._cleanup_expired()

        # Save index
        self._save_cache_index()

    def _should_persist(self, value: Any) -> bool:
        """Determine if value should be persisted to disk."""
        # Persist large objects
        try:
            size = len(pickle.dumps(value))
            return size > 1024 * 1024  # 1MB
        except Exception:
            return True

    def clear(self) -> None:
        """Clear all cache."""
        # Clear memory cache
        self.memory_cache.clear()

        # Clear disk cache
        for cache_file in self.cache_dir.glob("*.cache"):
            cache_file.unlink()

        # Clear index
        self.cache_index = {}
        self._save_cache_index()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        memory_size = sum(
            len(pickle.dumps(v["value"]))
            for v in self.memory_cache.values()
        )

        disk_size = sum(
            meta.get("size", 0)
            for meta in self.cache_index.values()
        )

        return {
            "memory_items": len(self.memory_cache),
            "memory_size_kb": memory_size / 1024,
            "disk_items": len(self.cache_index),
            "disk_size_mb": disk_size / (1024 * 1024),
            "hit_rate": self._calculate_hit_rate()
        }

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        # This is a simplified version
        # In production, you'd track hits and misses
        return 0.0


# Global cache instance
_cache_manager = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(
    ttl: int = 3600,
    key_func: Optional[callable] = None
):
    """
    Decorator for caching function results.

    Args:
        ttl: Time to live in seconds
        key_func: Custom key generation function

    Usage:
        @cached(ttl=3600)
        def expensive_function(x, y):
            return x + y
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            cache = get_cache_manager()

            # Generate key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                # Default key generation
                key_data = {
                    "function": func.__name__,
                    "args": args,
                    "kwargs": sorted(kwargs.items())
                }
                cache_key = hashlib.md5(
                    json.dumps(key_data, sort_keys=True).encode()
                ).hexdigest()

            # Try to get from cache
            result = cache.get(cache_key)

            if result is None:
                # Compute and cache
                result = func(*args, **kwargs)
                cache.set(cache_key, result)

            return result

        return wrapper
    return decorator


# Smart cache decorators for common use cases
@cached(ttl=1800)
def cache_file_hash(file_bytes: bytes) -> str:
    """Cache file hash computation."""
    return hashlib.md5(file_bytes).hexdigest()


@cached(ttl=3600)
def cache_pdf_metadata(pdf_bytes: bytes) -> Dict[str, Any]:
    """Cache PDF metadata extraction."""
    import fitz
    doc = fitz.open(stream=pdf_bytes)
    metadata = {
        "page_count": len(doc),
        "title": doc.metadata.get("title", ""),
        "author": doc.metadata.get("author", ""),
    }
    doc.close()
    return metadata


@cached(ttl=7200)
def cache_font_metrics(font_name: str) -> Dict[str, float]:
    """Cache font metrics."""
    # Return default font metrics
    return {
        "char_width": 10.0,
        "line_height": 12.0,
        "ascent": 8.0,
        "descent": -4.0
    }
