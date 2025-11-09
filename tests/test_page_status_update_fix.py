"""
Comprehensive tests for page status update fixes.

Tests cover:
1. Page status updates when on_page_status callback is called
2. Page status updates when on_page_status callback is NOT called (fallback to completed_pages)
3. Concurrent status updates
4. Status synchronization between update_file_page_progress and update_page_status
5. Render logic with status inference
"""

import os
import sys

# Add project root to path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import unittest
from unittest.mock import Mock, patch, MagicMock
import threading
import time

from app.ui.components.detailed_progress_tracker import DetailedProgressTracker, FileProgress


class TestPageStatusUpdateFix(unittest.TestCase):
    """Test page status update fixes."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Streamlit session state
        class MockSessionState(dict):
            def __getattr__(self, key):
                return self.get(key)
            
            def __setattr__(self, key, value):
                self[key] = value
        
        self.mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', self.mock_session_state):
            with patch('streamlit.empty', return_value=MagicMock()):
                self.tracker = DetailedProgressTracker(
                    total_files=1,
                    operation_name="测试处理",
                    processing_mode="batch_generation"
                )
    
    def test_page_status_update_with_callback(self):
        """Test that page status is updated when on_page_status callback is called."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Simulate page processing with callback
        on_progress, on_page_status = self.tracker.create_thread_safe_callbacks(filename)
        
        # Update status for page 0 (processing)
        on_page_status(0, "processing", None)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[0], "processing")
        
        # Update status for page 0 (completed)
        on_page_status(0, "completed", None)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[0], "completed")
        self.assertEqual(file_prog.completed_pages, 1)
    
    def test_page_status_update_without_callback_fallback(self):
        """Test that page status is inferred from completed_pages when callback is not called."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update progress without calling on_page_status
        # This simulates the case where on_page_status callback fails or is not called
        self.tracker.update_file_page_progress(filename, 3, total_pages)  # 3 pages completed
        
        file_prog = self.tracker.file_progress[filename]
        
        # Pages 0, 1, 2 should be marked as completed
        self.assertEqual(file_prog.completed_pages, 3)
        self.assertEqual(file_prog.page_statuses[0], "completed")
        self.assertEqual(file_prog.page_statuses[1], "completed")
        self.assertEqual(file_prog.page_statuses[2], "completed")
        # Page 3 should still be waiting (since completed_pages is 1-based)
        # Actually, if completed_pages=3, it means pages 0,1,2 are completed (0-based)
        self.assertEqual(file_prog.page_statuses.get(3, "waiting"), "waiting")
    
    def test_concurrent_status_updates(self):
        """Test that concurrent status updates work correctly."""
        filename = "test.pdf"
        total_pages = 10
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        on_progress, on_page_status = self.tracker.create_thread_safe_callbacks(filename)
        
        def update_page(page_idx):
            """Update status for a page."""
            on_page_status(page_idx, "processing", None)
            time.sleep(0.01)  # Simulate processing
            on_page_status(page_idx, "completed", None)
        
        # Create multiple threads updating different pages
        threads = []
        for i in range(total_pages):
            thread = threading.Thread(target=update_page, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all pages have correct status
        file_prog = self.tracker.file_progress[filename]
        for i in range(total_pages):
            self.assertEqual(file_prog.page_statuses[i], "completed")
        
        self.assertEqual(file_prog.completed_pages, total_pages)
    
    def test_status_sync_between_progress_and_status(self):
        """Test that update_file_page_progress and update_page_status stay in sync."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update progress first
        self.tracker.update_file_page_progress(filename, 3, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.completed_pages, 3)
        self.assertEqual(file_prog.page_statuses[0], "completed")
        self.assertEqual(file_prog.page_statuses[1], "completed")
        self.assertEqual(file_prog.page_statuses[2], "completed")
        
        # Now update status explicitly for page 4
        self.tracker.update_page_status(filename, 3, "processing")
        self.assertEqual(file_prog.page_statuses[3], "processing")
        
        # Update status to completed
        self.tracker.update_page_status(filename, 3, "completed")
        self.assertEqual(file_prog.page_statuses[3], "completed")
        self.assertEqual(file_prog.completed_pages, 4)  # Should be updated
    
    def test_status_inference_in_render(self):
        """Test that render correctly infers status from completed_pages."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update progress without calling on_page_status
        self.tracker.update_file_page_progress(filename, 3, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        
        # Manually check render logic
        # Pages 0, 1, 2 should be inferred as completed
        for page_idx in range(3):
            status = file_prog.page_statuses.get(page_idx, "waiting")
            if status in ("waiting", "processing", "retrying") and (page_idx + 1) <= file_prog.completed_pages:
                status = "completed"
            self.assertEqual(status, "completed", f"Page {page_idx + 1} should be completed")
    
    def test_failed_page_status_priority(self):
        """Test that failed page status takes priority over completed inference."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Mark page 2 as failed
        self.tracker.update_page_status(filename, 1, "failed", error="Test error")
        
        # Update progress to 3 (which would normally mark page 2 as completed)
        self.tracker.update_file_page_progress(filename, 3, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        
        # Page 2 (index 1) should still be failed, not completed
        self.assertEqual(file_prog.page_statuses[1], "failed")
        self.assertIn(1, file_prog.failed_pages)
    
    def test_retry_status_update(self):
        """Test that retry status is correctly handled."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Mark page as failed
        self.tracker.update_page_status(filename, 2, "failed", error="Test error")
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[2], "failed")
        self.assertIn(2, file_prog.failed_pages)
        
        # Retry the page
        self.tracker.update_page_status(filename, 2, "processing", is_retry=True)
        self.assertEqual(file_prog.page_statuses[2], "retrying")
        
        # Complete the retry
        self.tracker.update_page_status(filename, 2, "completed")
        self.assertEqual(file_prog.page_statuses[2], "completed")
        self.assertNotIn(2, file_prog.failed_pages)
    
    def test_multiple_files_status_tracking(self):
        """Test status tracking for multiple files concurrently."""
        file1 = "file1.pdf"
        file2 = "file2.pdf"
        total_pages1 = 3
        total_pages2 = 5
        
        self.tracker.initialize_file(file1, total_pages1)
        self.tracker.initialize_file(file2, total_pages2)
        
        self.tracker.start_file(file1)
        self.tracker.start_file(file2)
        
        # Update statuses for both files
        on_progress1, on_page_status1 = self.tracker.create_thread_safe_callbacks(file1)
        on_progress2, on_page_status2 = self.tracker.create_thread_safe_callbacks(file2)
        
        on_page_status1(0, "completed", None)
        on_page_status2(0, "processing", None)
        on_page_status2(1, "completed", None)
        
        # Verify statuses are tracked separately
        file1_prog = self.tracker.file_progress[file1]
        file2_prog = self.tracker.file_progress[file2]
        
        self.assertEqual(file1_prog.page_statuses[0], "completed")
        self.assertEqual(file2_prog.page_statuses[0], "processing")
        self.assertEqual(file2_prog.page_statuses[1], "completed")
        
        # Verify completed_pages for each file
        self.assertEqual(file1_prog.completed_pages, 1)
        self.assertEqual(file2_prog.completed_pages, 2)


class TestPageStatusEdgeCases(unittest.TestCase):
    """Test edge cases for page status updates."""
    
    def setUp(self):
        """Set up test fixtures."""
        class MockSessionState(dict):
            def __getattr__(self, key):
                return self.get(key)
            
            def __setattr__(self, key, value):
                self[key] = value
        
        self.mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', self.mock_session_state):
            with patch('streamlit.empty', return_value=MagicMock()):
                self.tracker = DetailedProgressTracker(
                    total_files=1,
                    operation_name="测试处理",
                    processing_mode="batch_generation"
                )
    
    def test_empty_file(self):
        """Test handling of file with 0 pages."""
        filename = "empty.pdf"
        total_pages = 0
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Should not crash
        self.tracker.update_file_page_progress(filename, 0, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(len(file_prog.page_statuses), 0)
    
    def test_large_file(self):
        """Test handling of file with many pages."""
        filename = "large.pdf"
        total_pages = 100
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update progress for all pages
        self.tracker.update_file_page_progress(filename, total_pages, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(len(file_prog.page_statuses), total_pages)
        # All pages should be marked as completed
        for i in range(total_pages):
            self.assertEqual(file_prog.page_statuses[i], "completed")
    
    def test_out_of_order_status_updates(self):
        """Test handling of out-of-order status updates."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update pages out of order
        self.tracker.update_page_status(filename, 3, "completed")
        self.tracker.update_page_status(filename, 1, "completed")
        self.tracker.update_page_status(filename, 2, "processing")
        
        file_prog = self.tracker.file_progress[filename]
        
        self.assertEqual(file_prog.page_statuses[1], "completed")
        self.assertEqual(file_prog.page_statuses[2], "processing")
        self.assertEqual(file_prog.page_statuses[3], "completed")
        
        # completed_pages should be the highest completed page (1-based)
        self.assertEqual(file_prog.completed_pages, 4)  # Page 4 (index 3) is completed


if __name__ == '__main__':
    unittest.main()

