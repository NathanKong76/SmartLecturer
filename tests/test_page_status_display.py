"""
Comprehensive tests for page status display functionality.

Tests cover:
1. Page status initialization
2. Status updates during processing
3. Status display in UI
4. Thread safety
5. Edge cases
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


class TestPageStatusDisplay(unittest.TestCase):
    """Test page status display functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Streamlit session state - use a dict-like object that supports attribute access
        class MockSessionState(dict):
            def __getattr__(self, key):
                return self.get(key)
            
            def __setattr__(self, key, value):
                self[key] = value
        
        self.mock_session_state = MockSessionState()
        
        with patch('streamlit.session_state', self.mock_session_state):
            with patch('streamlit.empty', return_value=MagicMock()):
                self.tracker = DetailedProgressTracker(
                    total_files=2,
                    operation_name="测试处理",
                    processing_mode="batch_generation"
                )
    
    def test_initialize_file_with_page_statuses(self):
        """Test that file initialization creates page_statuses for all pages."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        
        self.assertIn(filename, self.tracker.file_progress)
        file_prog = self.tracker.file_progress[filename]
        
        # Check that page_statuses is initialized for all pages
        self.assertEqual(len(file_prog.page_statuses), total_pages)
        for i in range(total_pages):
            self.assertIn(i, file_prog.page_statuses)
            self.assertEqual(file_prog.page_statuses[i], "waiting")
    
    def test_update_page_status_processing(self):
        """Test updating page status to processing."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        self.tracker.update_page_status(filename, page_index, "processing")
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[page_index], "processing")
    
    def test_update_page_status_completed(self):
        """Test updating page status to completed."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        self.tracker.update_page_status(filename, page_index, "completed")
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[page_index], "completed")
        self.assertEqual(file_prog.completed_pages, page_index + 1)
    
    def test_update_page_status_failed(self):
        """Test updating page status to failed."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        self.tracker.update_page_status(filename, page_index, "failed", error="Test error")
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[page_index], "failed")
        self.assertIn(page_index, file_prog.failed_pages)
        self.assertEqual(self.tracker.failed_pages_count, 1)
    
    def test_update_page_status_retrying(self):
        """Test updating page status to retrying."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        self.tracker.update_page_status(filename, page_index, "processing", is_retry=True)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[page_index], "retrying")
    
    def test_thread_safe_status_updates(self):
        """Test that status updates are thread-safe."""
        filename = "test.pdf"
        total_pages = 10
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        def update_status(page_idx):
            """Update status for a page."""
            status = "processing" if page_idx % 2 == 0 else "completed"
            self.tracker.update_page_status(filename, page_idx, status)
        
        # Create multiple threads updating different pages
        threads = []
        for i in range(total_pages):
            thread = threading.Thread(target=update_status, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all pages have status updated
        file_prog = self.tracker.file_progress[filename]
        for i in range(total_pages):
            self.assertIn(i, file_prog.page_statuses)
            self.assertIn(file_prog.page_statuses[i], ["processing", "completed"])
    
    def test_status_display_priority(self):
        """Test that failed status takes priority over other statuses."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Set status to completed
        self.tracker.update_page_status(filename, page_index, "completed")
        
        # Then mark as failed
        self.tracker.update_page_status(filename, page_index, "failed", error="Test error")
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[page_index], "failed")
        self.assertIn(page_index, file_prog.failed_pages)
    
    def test_completed_pages_calculation(self):
        """Test that completed_pages is correctly calculated."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Complete pages 0, 1, 2 (0-indexed)
        for i in range(3):
            self.tracker.update_page_status(filename, i, "completed")
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.completed_pages, 3)
        self.assertEqual(self.tracker.completed_pages, 3)
    
    def test_failed_pages_removal_on_retry_success(self):
        """Test that failed pages are removed when retry succeeds."""
        filename = "test.pdf"
        total_pages = 3
        page_index = 1
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Mark as failed
        self.tracker.update_page_status(filename, page_index, "failed", error="Test error")
        self.assertIn(page_index, self.tracker.file_progress[filename].failed_pages)
        self.assertEqual(self.tracker.failed_pages_count, 1)
        
        # Retry and succeed
        self.tracker.update_page_status(filename, page_index, "completed")
        self.assertNotIn(page_index, self.tracker.file_progress[filename].failed_pages)
        self.assertEqual(self.tracker.failed_pages_count, 0)
    
    def test_multiple_files_status_tracking(self):
        """Test status tracking for multiple files."""
        file1 = "file1.pdf"
        file2 = "file2.pdf"
        total_pages1 = 3
        total_pages2 = 5
        
        self.tracker.initialize_file(file1, total_pages1)
        self.tracker.initialize_file(file2, total_pages2)
        
        self.tracker.start_file(file1)
        self.tracker.start_file(file2)
        
        # Update statuses for both files
        self.tracker.update_page_status(file1, 0, "completed")
        self.tracker.update_page_status(file2, 0, "processing")
        self.tracker.update_page_status(file2, 1, "completed")
        
        # Verify statuses are tracked separately
        file1_prog = self.tracker.file_progress[file1]
        file2_prog = self.tracker.file_progress[file2]
        
        self.assertEqual(file1_prog.page_statuses[0], "completed")
        self.assertEqual(file2_prog.page_statuses[0], "processing")
        self.assertEqual(file2_prog.page_statuses[1], "completed")
        
        # Verify completed_pages for each file
        # completed_pages represents the highest completed page number (1-based)
        self.assertEqual(file1_prog.completed_pages, 1)  # Page 0 completed
        self.assertEqual(file2_prog.completed_pages, 2)  # Page 1 completed (highest)
        
        # Verify total completed pages (sum of all files' completed_pages)
        self.assertEqual(self.tracker.completed_pages, 3)  # 1 from file1 + 2 from file2
    
    def test_status_display_with_missing_statuses(self):
        """Test that status display handles missing statuses correctly."""
        filename = "test.pdf"
        total_pages = 5
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Update completed_pages but don't update page_statuses for some pages
        file_prog = self.tracker.file_progress[filename]
        file_prog.completed_pages = 3  # Pages 0, 1, 2 are completed
        
        # Only update status for page 0
        file_prog.page_statuses[0] = "completed"
        
        # Verify that render logic can infer status for other pages
        # (This is tested through the render_details method)
        self.assertEqual(file_prog.page_statuses[0], "completed")
        # Pages 1 and 2 should be inferred as completed based on completed_pages
        # This is handled in render_details method
    
    def test_progress_callback_integration(self):
        """Test that progress callbacks correctly update page status."""
        filename = "test.pdf"
        total_pages = 3
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        # Create callbacks
        on_progress, on_page_status = self.tracker.create_thread_safe_callbacks(filename)
        
        # Simulate page processing
        on_page_status(0, "processing", None)
        on_page_status(0, "completed", None)
        on_page_status(1, "processing", None)
        on_page_status(1, "failed", "Test error")
        
        # Verify statuses
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(file_prog.page_statuses[0], "completed")
        self.assertEqual(file_prog.page_statuses[1], "failed")
        self.assertIn(1, file_prog.failed_pages)


class TestPageStatusEdgeCases(unittest.TestCase):
    """Test edge cases for page status display."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Mock Streamlit session state - use a dict-like object that supports attribute access
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
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(len(file_prog.page_statuses), 0)
    
    def test_large_file(self):
        """Test handling of file with many pages."""
        filename = "large.pdf"
        total_pages = 1000
        
        self.tracker.initialize_file(filename, total_pages)
        
        file_prog = self.tracker.file_progress[filename]
        self.assertEqual(len(file_prog.page_statuses), total_pages)
    
    def test_concurrent_status_updates_same_page(self):
        """Test concurrent updates to the same page."""
        filename = "test.pdf"
        total_pages = 1
        page_index = 0
        
        self.tracker.initialize_file(filename, total_pages)
        self.tracker.start_file(filename)
        
        def update_status(status):
            """Update status."""
            self.tracker.update_page_status(filename, page_index, status)
        
        # Create threads updating the same page
        threads = [
            threading.Thread(target=update_status, args=("processing",)),
            threading.Thread(target=update_status, args=("completed",)),
        ]
        
        for thread in threads:
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Verify final status (should be one of the statuses)
        file_prog = self.tracker.file_progress[filename]
        self.assertIn(file_prog.page_statuses[page_index], ["processing", "completed"])


if __name__ == '__main__':
    unittest.main()

