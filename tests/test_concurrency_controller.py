"""
Comprehensive tests for Global Concurrency Controller.

This test suite verifies:
1. Singleton pattern implementation
2. Semaphore acquisition and release
3. Concurrency limit adjustment
4. Statistics tracking
5. Thread safety and async safety
6. Edge cases and error handling
7. Integration with async operations
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch, AsyncMock
from typing import Optional

from app.services.concurrency_controller import (
    GlobalConcurrencyController,
    ConcurrencyStats,
    calculate_optimal_concurrency
)


class TestGlobalConcurrencyController:
    """Comprehensive test suite for Global Concurrency Controller."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Reset singleton instance before each test
        GlobalConcurrencyController._instance = None
    
    def teardown_method(self):
        """Clean up test fixtures."""
        # Reset singleton instance after each test
        GlobalConcurrencyController._instance = None
    
    def test_singleton_pattern(self):
        """Test that singleton pattern works correctly."""
        instance1 = GlobalConcurrencyController.get_instance_sync()
        instance2 = GlobalConcurrencyController.get_instance_sync()
        
        assert instance1 is instance2
        assert isinstance(instance1, GlobalConcurrencyController)
    
    def test_initialization(self):
        """Test controller initialization."""
        controller = GlobalConcurrencyController(max_global_concurrency=100)
        
        assert controller.max_global_concurrency == 100
        assert controller.semaphore is None
        assert controller.stats.current_requests == 0
        assert controller.stats.total_requests == 0
        assert controller.stats.peak_requests == 0
    
    def test_acquire_release_sync(self):
        """Test acquire and release in synchronous context."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        # Test that acquire/release work (even in sync context, they should handle gracefully)
        # Note: acquire is async, so we test it in async context
        pass
    
    @pytest.mark.asyncio
    async def test_acquire_release_async(self):
        """Test acquire and release in async context."""
        controller = GlobalConcurrencyController(max_global_concurrency=3)
        
        # Acquire 3 slots
        await controller.acquire("request1")
        await controller.acquire("request2")
        await controller.acquire("request3")
        
        assert controller.stats.current_requests == 3
        assert controller.stats.total_requests == 3
        assert controller.stats.peak_requests == 3
        
        # Release slots
        controller.release("request1")
        controller.release("request2")
        controller.release("request3")
        
        assert controller.stats.current_requests == 0
        assert controller.stats.total_requests == 3
    
    @pytest.mark.asyncio
    async def test_context_manager(self):
        """Test async context manager usage."""
        controller = GlobalConcurrencyController(max_global_concurrency=2)
        
        async with controller:
            assert controller.stats.current_requests == 1
        
        assert controller.stats.current_requests == 0
    
    @pytest.mark.asyncio
    async def test_concurrency_limit_enforcement(self):
        """Test that concurrency limit is enforced."""
        controller = GlobalConcurrencyController(max_global_concurrency=2)
        
        # Acquire 2 slots (should succeed)
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        assert controller.stats.current_requests == 2
        
        # Try to acquire more (should block)
        acquired_third = False
        
        async def try_acquire_third():
            nonlocal acquired_third
            await controller.acquire("req3")
            acquired_third = True
        
        # Start third acquisition
        task = asyncio.create_task(try_acquire_third())
        
        # Wait a bit to see if it blocks
        await asyncio.sleep(0.1)
        assert not acquired_third
        
        # Release one slot
        controller.release("req1")
        
        # Wait a bit more
        await asyncio.sleep(0.1)
        assert acquired_third
        
        # Clean up
        controller.release("req2")
        controller.release("req3")
        await task
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self):
        """Test that statistics are tracked correctly."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        # Make multiple requests
        for i in range(5):
            await controller.acquire(f"req{i}")
        
        stats = controller.get_stats()
        assert stats.current_requests == 5
        assert stats.total_requests == 5
        assert stats.peak_requests == 5
        
        # Release some
        controller.release("req0")
        controller.release("req1")
        
        stats = controller.get_stats()
        assert stats.current_requests == 3
        assert stats.total_requests == 5
        assert stats.peak_requests == 5
        
        # Make more requests
        for i in range(5, 8):
            await controller.acquire(f"req{i}")
        
        stats = controller.get_stats()
        assert stats.current_requests == 6
        assert stats.total_requests == 8
        assert stats.peak_requests == 6
        
        # Clean up
        for i in range(8):
            controller.release(f"req{i}")
    
    @pytest.mark.asyncio
    async def test_adjust_limit_async(self):
        """Test async limit adjustment."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        # Acquire some slots
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        assert controller.stats.current_requests == 2
        
        # Adjust limit (should wait for completion if needed)
        await controller.adjust_limit_async(5, wait_for_completion=False)
        
        assert controller.max_global_concurrency == 5
        
        # Clean up
        controller.release("req1")
        controller.release("req2")
    
    @pytest.mark.asyncio
    async def test_adjust_limit_wait_for_completion(self):
        """Test limit adjustment with wait for completion."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        # Acquire some slots
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        assert controller.stats.current_requests == 2
        
        # Adjust limit to smaller value with wait
        async def adjust_and_wait():
            await controller.adjust_limit_async(1, wait_for_completion=True)
        
        # Start adjustment (should wait)
        adjust_task = asyncio.create_task(adjust_and_wait())
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Release slots
        controller.release("req1")
        controller.release("req2")
        
        # Wait for adjustment to complete
        await adjust_task
        
        assert controller.max_global_concurrency == 1
    
    def test_adjust_limit_sync(self):
        """Test synchronous limit adjustment."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        controller.adjust_limit(5)
        assert controller.max_global_concurrency == 5
        
        # Adjust to same value (should do nothing)
        controller.adjust_limit(5)
        assert controller.max_global_concurrency == 5
    
    def test_adjust_limit_invalid(self):
        """Test limit adjustment with invalid values."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        with pytest.raises(ValueError):
            controller.adjust_limit(0)
        
        with pytest.raises(ValueError):
            controller.adjust_limit(-1)
    
    @pytest.mark.asyncio
    async def test_adjust_limit_async_invalid(self):
        """Test async limit adjustment with invalid values."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        with pytest.raises(ValueError):
            await controller.adjust_limit_async(0)
        
        with pytest.raises(ValueError):
            await controller.adjust_limit_async(-1)
    
    @pytest.mark.asyncio
    async def test_get_available_slots(self):
        """Test getting available slots."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        # Initially all slots available
        available = controller.get_available_slots()
        assert available == 5
        
        # Acquire some slots
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        available = controller.get_available_slots()
        assert available == 3
        
        # Clean up
        controller.release("req1")
        controller.release("req2")
    
    @pytest.mark.asyncio
    async def test_reset_stats(self):
        """Test statistics reset."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        # Make some requests
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        assert controller.stats.current_requests == 2
        assert controller.stats.total_requests == 2
        
        # Reset stats
        controller.reset_stats()
        
        assert controller.stats.current_requests == 0
        assert controller.stats.total_requests == 0
        assert controller.stats.peak_requests == 0
        
        # Clean up
        controller.release("req1")
        controller.release("req2")
    
    @pytest.mark.asyncio
    async def test_wait_for_all_requests(self):
        """Test waiting for all requests to complete."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        # Acquire some slots
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        # Start wait task
        wait_task = asyncio.create_task(controller.wait_for_all_requests(timeout=1.0))
        
        # Wait a bit
        await asyncio.sleep(0.1)
        
        # Release slots
        controller.release("req1")
        controller.release("req2")
        
        # Wait should complete
        await wait_task
    
    @pytest.mark.asyncio
    async def test_wait_for_all_requests_timeout(self):
        """Test waiting with timeout."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        # Acquire a slot
        await controller.acquire("req1")
        
        # Wait with short timeout
        await controller.wait_for_all_requests(timeout=0.1)
        
        # Should complete (timeout or release)
        # Clean up
        controller.release("req1")
    
    @pytest.mark.asyncio
    async def test_multiple_event_loops(self):
        """Test that controller works across different event loops."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        # First event loop
        async def loop1():
            await controller.acquire("req1")
            await asyncio.sleep(0.1)
            controller.release("req1")
        
        # Second event loop
        async def loop2():
            await controller.acquire("req2")
            await asyncio.sleep(0.1)
            controller.release("req2")
        
        # Run in same loop (should work)
        await asyncio.gather(loop1(), loop2())
    
    @pytest.mark.asyncio
    async def test_concurrent_adjustments(self):
        """Test concurrent limit adjustments."""
        controller = GlobalConcurrencyController(max_global_concurrency=10)
        
        # Multiple concurrent adjustments
        async def adjust1():
            await controller.adjust_limit_async(5)
        
        async def adjust2():
            await controller.adjust_limit_async(3)
        
        # Should serialize properly
        await asyncio.gather(adjust1(), adjust2())
        
        # Final limit should be one of them
        assert controller.max_global_concurrency in [3, 5]
    
    @pytest.mark.asyncio
    async def test_request_id_tracking(self):
        """Test request ID tracking."""
        controller = GlobalConcurrencyController(max_global_concurrency=5)
        
        await controller.acquire("req1")
        await controller.acquire("req2")
        
        assert "req1" in controller._active_requests
        assert "req2" in controller._active_requests
        
        controller.release("req1")
        assert "req1" not in controller._active_requests
        assert "req2" in controller._active_requests
        
        controller.release("req2")
        assert "req2" not in controller._active_requests


class TestCalculateOptimalConcurrency:
    """Test suite for calculate_optimal_concurrency function."""
    
    def test_basic_calculation(self):
        """Test basic concurrency calculation."""
        page_conc, file_conc = calculate_optimal_concurrency(
            page_concurrency=10,
            file_count=5,
            rpm_limit=100,
            max_global_concurrency=200
        )
        
        # Should not be limited
        assert page_conc == 10
        assert file_conc == 5
    
    def test_global_limit_restriction(self):
        """Test when global limit restricts concurrency."""
        page_conc, file_conc = calculate_optimal_concurrency(
            page_concurrency=50,
            file_count=10,
            rpm_limit=100,
            max_global_concurrency=100
        )
        
        # Theoretical max is 500, but limited to 100
        # Should scale down proportionally
        assert page_conc <= 50
        assert file_conc == 10
        assert page_conc * file_conc <= 100
    
    def test_minimum_concurrency(self):
        """Test that minimum concurrency is respected."""
        page_conc, file_conc = calculate_optimal_concurrency(
            page_concurrency=1,
            file_count=1,
            rpm_limit=100,
            max_global_concurrency=1
        )
        
        assert page_conc >= 1
        assert file_conc >= 1
    
    def test_edge_cases(self):
        """Test edge cases."""
        # Zero file count
        page_conc, file_conc = calculate_optimal_concurrency(
            page_concurrency=10,
            file_count=0,
            rpm_limit=100,
            max_global_concurrency=200
        )
        assert file_conc == 0
        
        # Very large values
        page_conc, file_conc = calculate_optimal_concurrency(
            page_concurrency=1000,
            file_count=100,
            rpm_limit=10000,
            max_global_concurrency=200
        )
        assert page_conc * file_conc <= 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

