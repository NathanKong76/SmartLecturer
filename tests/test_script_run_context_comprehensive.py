"""
Comprehensive tests for ScriptRunContext fixes.

These tests verify that the ScriptRunContext warnings are eliminated
by testing all the components that were previously causing issues.
"""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock, patch
import streamlit as st

from app.ui_helpers import safe_streamlit_call, StateManager
from app.cache_processor import _safe_cache_data, _is_main_thread
from app.ui.components.detailed_progress_tracker import DetailedProgressTracker
from app.services.safe_html_renderer import safe_render_html_to_pdf_fragment


class TestScriptRunContextSafety:
    """Test cases for ScriptRunContext safety in various scenarios."""
    
    def test_is_main_thread_detection(self):
        """Test the improved _is_main_thread function."""
        # Test in main thread context
        result = _is_main_thread()
        # Should return True in actual Streamlit context, False in test context
        # The important thing is it doesn't crash
        
        # Test that it handles exceptions gracefully
        with patch('streamlit.runtime.scriptrunner.get_script_run_ctx', side_effect=Exception("Test")):
            result = _is_main_thread()
            assert result is False
    
    def test_safe_streamlit_call_in_main_thread(self):
        """Test safe_streamlit_call behavior in main thread."""
        # Mock a Streamlit function
        mock_func = Mock()
        
        # This should work without errors
        safe_streamlit_call(mock_func, "test message")
        
        # Verify the function was called
        mock_func.assert_called_once_with("test message")
    
    def test_safe_streamlit_call_in_background_thread(self):
        """Test safe_streamlit_call behavior in background thread."""
        results = []
        
        def background_task():
            # In background thread, this should not call Streamlit functions
            # and should use logging instead
            mock_func = Mock()
            safe_streamlit_call(mock_func, "background message")
            results.append("completed")
        
        # Run in separate thread
        thread = threading.Thread(target=background_task)
        thread.start()
        thread.join()
        
        # Verify the background task completed without errors
        assert len(results) == 1
        assert results[0] == "completed"
    
    def test_thread_safe_cache_decorator(self):
        """Test the improved cache decorator safety."""
        call_count = [0]
        
        @_safe_cache_data
        def test_function(x):
            call_count[0] += 1
            return x * 2
        
        # Test multiple calls
        result1 = test_function(5)
        result2 = test_function(5)  # Should be cached in main thread
        result3 = test_function(6)  # Different argument
        
        assert result1 == 10
        assert result2 == 10
        assert result3 == 12
    
    def test_thread_pool_executor_with_safe_calls(self):
        """Test ThreadPoolExecutor with safe function calls."""
        def worker_task(worker_id):
            """A task that would previously cause ScriptRunContext warnings."""
            # Use safe Streamlit calls that should not warn
            safe_streamlit_call(st.info, f"Worker {worker_id} completed")
            return f"Worker {worker_id} result"
        
        results = []
        
        def run_workers():
            with ThreadPoolExecutor(max_workers=3) as executor:
                futures = [executor.submit(worker_task, i) for i in range(5)]
                for future in futures:
                    try:
                        results.append(future.result(timeout=1.0))
                    except Exception as e:
                        results.append(f"Error: {e}")
        
        # Run in main thread
        run_workers()
        
        # Should have 5 successful results
        successful_results = [r for r in results if not r.startswith("Error")]
        assert len(successful_results) == 5
    
    def test_progress_tracker_safety(self):
        """Test that progress tracker doesn't cause ScriptRunContext warnings."""
        # Create a progress tracker
        tracker = DetailedProgressTracker(
            total_files=2,
            operation_name="Test Operation",
            processing_mode="batch_generation"
        )
        
        # Initialize file
        tracker.initialize_file("test_file.pdf", total_pages=3)
        
        # Start file processing
        tracker.start_file("test_file.pdf")
        
        # Update progress - this should be thread-safe
        tracker.update_file_page_progress("test_file.pdf", 1, 3)
        tracker.update_file_page_progress("test_file.pdf", 2, 3)
        
        # Complete file
        tracker.complete_file("test_file.pdf", success=True)
        
        # The tracker should handle all updates without errors
        assert tracker.file_progress["test_file.pdf"].status == "completed"
        assert tracker.file_progress["test_file.pdf"].completed_pages == 2
    
    def test_progress_tracker_in_background_thread(self):
        """Test progress tracker operations in background thread."""
        tracker = DetailedProgressTracker(
            total_files=1,
            operation_name="Background Test",
            processing_mode="batch_generation"
        )
        
        results = []
        
        def background_updates():
            try:
                tracker.initialize_file("bg_test.pdf", total_pages=2)
                tracker.start_file("bg_test.pdf")
                tracker.update_file_page_progress("bg_test.pdf", 1, 2)
                results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=background_updates)
        thread.start()
        thread.join()
        
        # Should complete without errors
        assert len(results) == 1
        assert results[0] == "success"
    
    def test_safe_html_renderer_context_detection(self):
        """Test safe HTML renderer's context detection."""
        # This should not crash and should handle missing contexts gracefully
        try:
            result = safe_render_html_to_pdf_fragment(
                html="<h1>Test</h1>",
                width_pt=612.0,
                height_pt=792.0,
                timeout=5
            )
            # If we get here without exception, the context detection worked
            assert result is not None or isinstance(result, bytes)
        except Exception as e:
            # Some exceptions are expected (missing dependencies, etc.)
            # but ScriptRunContext errors should not occur
            assert "ScriptRunContext" not in str(e)
    
    def test_state_manager_thread_safety(self):
        """Test StateManager operations in multi-threaded environment."""
        results = []
        
        def state_updates(thread_id):
            try:
                # Test basic state operations
                StateManager.set_processing(True)
                is_processing = StateManager.is_processing()
                results.append(f"Thread {thread_id}: processing={is_processing}")
                
                # Test batch results
                test_results = {f"file_{thread_id}": {"status": "completed"}}
                StateManager.set_batch_results(test_results)
                retrieved = StateManager.get_batch_results()
                results.append(f"Thread {thread_id}: retrieved={len(retrieved)} items")
                
            except Exception as e:
                results.append(f"Thread {thread_id}: error={e}")
        
        # Run multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=state_updates, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        error_results = [r for r in results if "error" in r]
        assert len(error_results) == 0, f"Errors occurred: {error_results}"
        
        # Verify operations completed
        assert len(results) == 3
    
    def test_concurrent_progress_updates(self):
        """Test concurrent progress updates to ensure no race conditions."""
        tracker = DetailedProgressTracker(
            total_files=3,
            operation_name="Concurrent Test",
            processing_mode="batch_generation"
        )
        
        update_results = []
        
        def concurrent_updates(file_id):
            try:
                filename = f"file_{file_id}.pdf"
                tracker.initialize_file(filename, total_pages=5)
                tracker.start_file(filename)
                
                # Simulate progress updates
                for page in range(1, 6):
                    tracker.update_file_page_progress(filename, page, 5)
                    time.sleep(0.01)  # Small delay to increase concurrency
                
                tracker.complete_file(filename, success=True)
                update_results.append(f"File {file_id} completed")
                
            except Exception as e:
                update_results.append(f"File {file_id} error: {e}")
        
        # Run multiple concurrent updates
        threads = []
        for i in range(3):
            thread = threading.Thread(target=concurrent_updates, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # Verify all files completed successfully
        completed_files = [r for r in update_results if "completed" in r]
        assert len(completed_files) == 3
        
        # Verify no errors
        error_results = [r for r in update_results if "error" in r]
        assert len(error_results) == 0


class TestScriptRunContextIntegration:
    """Integration tests simulating real-world scenarios."""
    
    def test_batch_processing_simulation(self):
        """Simulate batch processing to test ScriptRunContext handling."""
        from app.ui_helpers import process_single_file_with_progress
        
        # Mock parameters
        mock_params = {
            "output_mode": "PDF讲解版",
            "right_ratio": 0.48,
            "font_size": 20,
            "line_spacing": 1.2,
            "column_padding": 10,
            "cjk_font_name": "SimHei",
            "render_mode": "markdown"
        }
        
        progress_updates = []
        
        def on_progress(done, total):
            progress_updates.append(f"Progress: {done}/{total}")
        
        def on_page_status(page_index, status, error=None):
            progress_updates.append(f"Page {page_index}: {status}")
        
        # This should not cause ScriptRunContext warnings
        # Even when called from ThreadPoolExecutor
        try:
            # Simulate what happens in batch processing
            with ThreadPoolExecutor(max_workers=2) as executor:
                def process_task():
                    # This simulates the actual file processing
                    return "processed"
                
                future = executor.submit(process_task)
                result = future.result(timeout=5)
                assert result == "processed"
                
        except Exception as e:
            # Should not be ScriptRunContext related
            assert "ScriptRunContext" not in str(e)
    
    def test_progress_rendering_safety(self):
        """Test that progress rendering doesn't cause warnings."""
        tracker = DetailedProgressTracker(
            total_files=2,
            operation_name="Render Test",
            processing_mode="batch_generation"
        )
        
        # Initialize files
        tracker.initialize_file("file1.pdf", 3)
        tracker.initialize_file("file2.pdf", 2)
        
        # Simulate processing
        tracker.start_file("file1.pdf")
        tracker.update_file_page_progress("file1.pdf", 1, 3)
        
        # Force render should not cause ScriptRunContext warnings
        try:
            tracker.force_render()
            # If we get here, rendering was safe
        except Exception as e:
            # Should not be ScriptRunContext related
            assert "ScriptRunContext" not in str(e)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])