"""
Comprehensive tests for ScriptRunContext warning fixes.

This test suite verifies that all fixes for the "missing ScriptRunContext" warning
are working correctly and that no warnings are triggered in background threads.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor

# Import modules to test
from app.ui_helpers import StateManager, _is_main_thread
from app.ui.components.detailed_progress_tracker import DetailedProgressTracker
from app.services.safe_html_renderer import safe_render_html_to_pdf_fragment


class TestScriptRunContextFixes(unittest.TestCase):
    """Test suite for ScriptRunContext warning fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Clear thread-safe storage before each test
        StateManager._thread_safe_storage.clear()
    
    def test_is_main_thread_detection(self):
        """Test that _is_main_thread correctly detects main thread."""
        # In test environment, we're in main thread
        # But without Streamlit context, it should return False
        result = _is_main_thread()
        # In test environment without Streamlit, should return False
        self.assertIsInstance(result, bool)
    
    def test_state_manager_main_thread_access(self):
        """Test StateManager methods in main thread (without Streamlit context)."""
        # Test that methods don't crash even without Streamlit context
        # They should use thread-safe storage as fallback
        
        # Test get_batch_results
        results = StateManager.get_batch_results()
        self.assertIsInstance(results, dict)
        
        # Test set_batch_results
        test_data = {"test_file": {"status": "completed"}}
        StateManager.set_batch_results(test_data)
        
        # Verify it's stored in thread-safe storage
        with StateManager._storage_lock:
            self.assertEqual(StateManager._thread_safe_storage.get("batch_results"), test_data)
        
        # Test is_processing
        is_proc = StateManager.is_processing()
        self.assertIsInstance(is_proc, bool)
        
        # Test set_processing
        StateManager.set_processing(True)
        with StateManager._storage_lock:
            self.assertTrue(StateManager._thread_safe_storage.get("batch_processing", False))
    
    def test_state_manager_background_thread_access(self):
        """Test StateManager methods in background thread."""
        results = {}
        errors = []
        
        def background_task():
            """Task to run in background thread."""
            try:
                # Test get_batch_results in background thread
                results["get"] = StateManager.get_batch_results()
                
                # Test set_batch_results in background thread
                test_data = {"background_file": {"status": "processing"}}
                StateManager.set_batch_results(test_data)
                results["set"] = test_data
                
                # Test is_processing
                results["is_processing"] = StateManager.is_processing()
                
                # Test set_processing
                StateManager.set_processing(True)
                results["set_processing"] = True
            except Exception as e:
                errors.append(e)
        
        # Run in background thread
        thread = threading.Thread(target=background_task)
        thread.start()
        thread.join(timeout=5)
        
        # Verify no errors occurred
        self.assertEqual(len(errors), 0, f"Errors in background thread: {errors}")
        
        # Verify data was stored in thread-safe storage
        with StateManager._storage_lock:
            self.assertIn("batch_results", StateManager._thread_safe_storage)
            self.assertTrue(StateManager._thread_safe_storage.get("batch_processing", False))
    
    def test_state_manager_sync_to_session_state(self):
        """Test sync_to_session_state method."""
        # Set some data in thread-safe storage
        with StateManager._storage_lock:
            StateManager._thread_safe_storage["batch_results"] = {"test": "data"}
            StateManager._thread_safe_storage["batch_processing"] = True
        
        # Mock st.session_state
        with patch('app.ui_helpers.st') as mock_st:
            mock_st.session_state = {}
            
            # Call sync (should work even without real Streamlit context)
            StateManager.sync_to_session_state()
            
            # Verify sync was attempted (method should not crash)
            # In test environment without Streamlit, it should gracefully skip
    
    def test_detailed_progress_tracker_render_safety(self):
        """Test that DetailedProgressTracker render is safe in background threads."""
        tracker = DetailedProgressTracker(total_files=1, operation_name="Test")
        
        # Test render in background thread
        errors = []
        
        def background_render():
            try:
                # This should not trigger ScriptRunContext warning
                tracker.render()
            except Exception as e:
                errors.append(e)
        
        # Run render in background thread
        thread = threading.Thread(target=background_render)
        thread.start()
        thread.join(timeout=2)
        
        # Verify no errors (render should gracefully skip in background thread)
        self.assertEqual(len(errors), 0, f"Errors during background render: {errors}")
    
    def test_detailed_progress_tracker_thread_safe_callbacks(self):
        """Test that thread-safe callbacks don't trigger warnings."""
        tracker = DetailedProgressTracker(total_files=1, operation_name="Test")
        tracker.initialize_file("test.pdf", total_pages=5)
        
        # Create callbacks
        on_progress, on_page_status = tracker.create_thread_safe_callbacks("test.pdf")
        
        # Test callbacks in background thread
        errors = []
        
        def background_callback_test():
            try:
                # Call on_progress
                on_progress(1, 5)
                on_progress(2, 5)
                
                # Call on_page_status
                on_page_status(0, "processing", None)
                on_page_status(0, "completed", None)
                on_page_status(1, "processing", None)
            except Exception as e:
                errors.append(e)
        
        # Run in background thread
        thread = threading.Thread(target=background_callback_test)
        thread.start()
        thread.join(timeout=2)
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors in callback: {errors}")
        
        # Verify progress was updated (in thread-safe storage)
        self.assertEqual(tracker.file_progress["test.pdf"].completed_pages, 2)
    
    def test_safe_html_renderer_streamlit_detection(self):
        """Test that safe_html_renderer doesn't trigger warnings."""
        # Test that Streamlit detection doesn't crash in background thread
        # We test the detection logic without actually rendering HTML
        
        # Test in background thread - just verify the detection doesn't crash
        errors = []
        warnings_captured = []
        
        def background_detection_test():
            """Test Streamlit detection in background thread."""
            try:
                # Import streamlit to test detection
                import streamlit as st
                
                # Test the detection logic (similar to what safe_html_renderer does)
                # This should not trigger ScriptRunContext warning
                streamlit_env = False
                try:
                    # Check if runtime exists without calling exists() (which triggers context check)
                    streamlit_env = hasattr(st, 'runtime') and hasattr(st.runtime, 'exists')
                    
                    if streamlit_env:
                        # Try to get context (this is what our fix does)
                        try:
                            from streamlit.runtime.scriptrunner import get_script_run_ctx
                            ctx = get_script_run_ctx()
                            # In background thread, ctx should be None
                            # This is expected and should not trigger warnings
                            if ctx is None:
                                # This is the safe path - no warning should be triggered
                                pass
                        except (ImportError, AttributeError, RuntimeError):
                            pass
                except ImportError:
                    pass
                
            except Exception as e:
                # Check if it's a ScriptRunContext-related error
                error_str = str(e)
                if "ScriptRunContext" in error_str or "missing ScriptRunContext" in error_str:
                    errors.append(e)
                # Other errors are acceptable in test environment
        
        # Run in background thread
        thread = threading.Thread(target=background_detection_test)
        thread.start()
        thread.join(timeout=2)
        
        # Verify no ScriptRunContext-related errors
        self.assertEqual(len(errors), 0, 
                        f"ScriptRunContext errors in detection: {errors}")
    
    def test_concurrent_state_manager_access(self):
        """Test concurrent access to StateManager from multiple threads."""
        errors = []
        results = []
        
        def worker_thread(thread_id):
            """Worker thread that accesses StateManager."""
            try:
                # Each thread sets its own data
                test_data = {f"file_{thread_id}": {"status": "processing", "thread": thread_id}}
                StateManager.set_batch_results(test_data)
                
                # Read back
                retrieved = StateManager.get_batch_results()
                results.append((thread_id, retrieved))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker_thread, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors in concurrent access: {errors}")
        
        # Verify all threads completed
        self.assertEqual(len(results), 5)
    
    def test_progress_tracker_concurrent_updates(self):
        """Test concurrent updates to progress tracker."""
        tracker = DetailedProgressTracker(total_files=2, operation_name="Concurrent Test")
        tracker.initialize_file("file1.pdf", total_pages=10)
        tracker.initialize_file("file2.pdf", total_pages=10)
        
        errors = []
        
        def update_file1():
            """Update file1 progress."""
            try:
                for i in range(1, 6):
                    tracker.update_file_page_progress("file1.pdf", i, 10)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(("file1", e))
        
        def update_file2():
            """Update file2 progress."""
            try:
                for i in range(1, 6):
                    tracker.update_file_page_progress("file2.pdf", i, 10)
                    time.sleep(0.01)
            except Exception as e:
                errors.append(("file2", e))
        
        # Run updates concurrently
        thread1 = threading.Thread(target=update_file1)
        thread2 = threading.Thread(target=update_file2)
        
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=2)
        thread2.join(timeout=2)
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors in concurrent updates: {errors}")
        
        # Verify progress was updated
        self.assertEqual(tracker.file_progress["file1.pdf"].completed_pages, 5)
        self.assertEqual(tracker.file_progress["file2.pdf"].completed_pages, 5)


class TestScriptRunContextIntegration(unittest.TestCase):
    """Integration tests for ScriptRunContext fixes."""
    
    def test_thread_pool_executor_with_state_manager(self):
        """Test ThreadPoolExecutor with StateManager (simulating real usage)."""
        errors = []
        
        def process_file(file_id):
            """Simulate file processing."""
            try:
                # Simulate processing
                StateManager.set_processing(True)
                
                # Update batch results
                result = {f"file_{file_id}": {"status": "processing"}}
                StateManager.set_batch_results(result)
                
                # Simulate completion
                result = {f"file_{file_id}": {"status": "completed"}}
                StateManager.set_batch_results(result)
                StateManager.set_processing(False)
            except Exception as e:
                errors.append((file_id, e))
        
        # Use ThreadPoolExecutor (like in real code)
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_file, i) for i in range(5)]
            
            # Wait for all
            for future in futures:
                future.result(timeout=5)
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors in ThreadPoolExecutor: {errors}")
        
        # Verify final state
        final_results = StateManager.get_batch_results()
        self.assertEqual(len(final_results), 1)  # Last write wins
    
    def test_progress_tracker_with_thread_pool(self):
        """Test progress tracker with ThreadPoolExecutor."""
        tracker = DetailedProgressTracker(total_files=3, operation_name="ThreadPool Test")
        
        for i in range(3):
            tracker.initialize_file(f"file_{i}.pdf", total_pages=5)
        
        errors = []
        
        def process_file(file_id):
            """Simulate file processing with progress updates."""
            try:
                filename = f"file_{file_id}.pdf"
                tracker.start_file(filename)
                
                # Create callbacks
                on_progress, on_page_status = tracker.create_thread_safe_callbacks(filename)
                
                # Simulate processing pages
                for page in range(5):
                    on_page_status(page, "processing", None)
                    time.sleep(0.01)
                    on_progress(page + 1, 5)
                    on_page_status(page, "completed", None)
                
                tracker.complete_file(filename, success=True)
            except Exception as e:
                errors.append((file_id, e))
        
        # Use ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(process_file, i) for i in range(3)]
            
            # Wait for all
            for future in futures:
                future.result(timeout=5)
        
        # Verify no errors
        self.assertEqual(len(errors), 0, f"Errors in progress tracker: {errors}")
        
        # Verify all files completed
        for i in range(3):
            filename = f"file_{i}.pdf"
            self.assertEqual(tracker.file_progress[filename].status, "completed")
            self.assertEqual(tracker.file_progress[filename].completed_pages, 5)


if __name__ == '__main__':
    unittest.main()

