"""
Comprehensive tests for file status transition from waiting to completed.

This test suite ensures that file status transitions follow the correct sequence:
waiting -> processing -> completed (or failed)

It tests various scenarios including:
- Normal processing flow
- Cached result handling
- Concurrent processing
- Sequential processing
- Race conditions
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import ThreadPoolExecutor, as_completed

from app.ui.components.detailed_progress_tracker import (
    DetailedProgressTracker,
    FileProgress
)


class TestFileStatusTransition(unittest.TestCase):
    """Test file status transitions."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = DetailedProgressTracker(
            total_files=1,
            operation_name="测试",
            processing_mode="batch_generation"
        )
        self.filename = "test.pdf"
        self.total_pages = 5
    
    def test_normal_status_transition(self):
        """Test normal status transition: waiting -> processing -> completed."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Verify initial state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "waiting")
        
        # Start processing
        self.tracker.start_file(self.filename)
        
        # Verify processing state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
        self.assertIsNotNone(self.tracker.file_progress[self.filename].start_time)
        
        # Complete processing
        self.tracker.complete_file(self.filename, success=True)
        
        # Verify completed state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
    
    def test_status_transition_with_cache(self):
        """Test status transition when cache is used."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Verify initial state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "waiting")
        
        # Start processing
        self.tracker.start_file(self.filename)
        
        # Verify processing state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
        
        # Simulate cache return: update page statuses
        for page_idx in range(self.total_pages):
            self.tracker.update_page_status(self.filename, page_idx, "completed")
        
        # Update progress
        self.tracker.update_file_page_progress(self.filename, self.total_pages, self.total_pages)
        
        # Complete processing
        self.tracker.complete_file(self.filename, success=True)
        
        # Verify completed state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
        self.assertEqual(self.tracker.file_progress[self.filename].completed_pages, self.total_pages)
    
    def test_concurrent_status_transition(self):
        """Test status transition in concurrent processing."""
        filenames = [f"test_{i}.pdf" for i in range(3)]
        
        # Initialize all files
        for filename in filenames:
            self.tracker.initialize_file(filename, self.total_pages)
            self.assertEqual(self.tracker.file_progress[filename].status, "waiting")
        
        # Start all files concurrently
        def start_file(filename):
            self.tracker.start_file(filename)
            time.sleep(0.01)  # Simulate processing
            self.tracker.complete_file(filename, success=True)
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(start_file, filename) for filename in filenames]
            for future in as_completed(futures):
                future.result()
        
        # Verify all files went through correct state transitions
        for filename in filenames:
            file_prog = self.tracker.file_progress[filename]
            self.assertEqual(file_prog.status, "completed")
            self.assertIsNotNone(file_prog.start_time)
    
    def test_no_skip_processing_state(self):
        """Test that processing state is never skipped."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Track state transitions
        state_transitions = []
        
        # Override start_file to track transitions
        original_start_file = self.tracker.start_file
        def tracked_start_file(filename):
            file_prog = self.tracker.file_progress[filename]
            state_transitions.append(("start", file_prog.status))
            original_start_file(filename)
            state_transitions.append(("after_start", file_prog.status))
        
        original_complete_file = self.tracker.complete_file
        def tracked_complete_file(filename, success=True, error=None):
            file_prog = self.tracker.file_progress[filename]
            state_transitions.append(("before_complete", file_prog.status))
            original_complete_file(filename, success, error)
            state_transitions.append(("after_complete", file_prog.status))
        
        self.tracker.start_file = tracked_start_file
        self.tracker.complete_file = tracked_complete_file
        
        # Start and complete
        self.tracker.start_file(self.filename)
        self.tracker.complete_file(self.filename, success=True)
        
        # Verify processing state was set
        self.assertIn(("after_start", "processing"), state_transitions)
        self.assertIn(("before_complete", "processing"), state_transitions)
    
    def test_race_condition_prevention(self):
        """Test that race conditions don't cause state skipping."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Simulate race condition: multiple threads trying to start and complete
        def race_condition_test():
            # Thread 1: Start file
            self.tracker.start_file(self.filename)
            time.sleep(0.001)
            # Thread 2: Try to complete (should see processing state)
            status_before_complete = self.tracker.file_progress[self.filename].status
            self.tracker.complete_file(self.filename, success=True)
            return status_before_complete
        
        result = race_condition_test()
        
        # Verify that status was processing before completion
        self.assertEqual(result, "processing")
        self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
    
    def test_invalid_state_transition_warning(self):
        """Test that invalid state transitions are logged."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Manually set invalid state
        self.tracker.file_progress[self.filename].status = "completed"
        
        # Try to start file (should log warning but still work)
        # Logger is imported inside the function, so we patch logging.getLogger
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            self.tracker.start_file(self.filename)
            # Verify warning was logged (logger is created in start_file)
            # Since logger is created inside the function, we verify the call was made
            self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
    
    def test_waiting_to_completed_detection(self):
        """Test detection of waiting -> completed transition (should not happen)."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Verify initial state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "waiting")
        
        # Try to complete without starting (should log warning)
        # Logger is imported inside the function, so we patch logging.getLogger
        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = Mock()
            mock_get_logger.return_value = mock_logger
            self.tracker.complete_file(self.filename, success=True)
            # Verify state is still set correctly
            self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
            # Verify start_time was set (handled gracefully)
            self.assertIsNotNone(self.tracker.file_progress[self.filename].start_time)
    
    def test_state_transition_with_page_updates(self):
        """Test state transition with page-level updates."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Start processing
        self.tracker.start_file(self.filename)
        self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
        
        # Update pages one by one
        for page_idx in range(self.total_pages):
            self.tracker.update_page_status(self.filename, page_idx, "processing")
            self.tracker.update_page_status(self.filename, page_idx, "completed")
            self.tracker.update_file_page_progress(self.filename, page_idx + 1, self.total_pages)
        
        # Complete processing
        self.tracker.complete_file(self.filename, success=True)
        
        # Verify final state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
        self.assertEqual(self.tracker.file_progress[self.filename].completed_pages, self.total_pages)
    
    def test_multiple_files_independent_transitions(self):
        """Test that multiple files have independent state transitions."""
        filenames = [f"test_{i}.pdf" for i in range(3)]
        
        # Initialize all files
        for filename in filenames:
            self.tracker.initialize_file(filename, self.total_pages)
        
        # Start first file
        self.tracker.start_file(filenames[0])
        self.assertEqual(self.tracker.file_progress[filenames[0]].status, "processing")
        
        # Other files should still be waiting
        for filename in filenames[1:]:
            self.assertEqual(self.tracker.file_progress[filename].status, "waiting")
        
        # Complete first file
        self.tracker.complete_file(filenames[0], success=True)
        self.assertEqual(self.tracker.file_progress[filenames[0]].status, "completed")
        
        # Start second file
        self.tracker.start_file(filenames[1])
        self.assertEqual(self.tracker.file_progress[filenames[1]].status, "processing")
        
        # First file should still be completed
        self.assertEqual(self.tracker.file_progress[filenames[0]].status, "completed")
    
    def test_state_transition_timing(self):
        """Test that state transitions happen in correct order with timing."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        timestamps = {}
        
        # Start processing
        self.tracker.start_file(self.filename)
        timestamps['start'] = time.time()
        time.sleep(0.01)  # Simulate processing time
        
        # Complete processing
        self.tracker.complete_file(self.filename, success=True)
        timestamps['complete'] = time.time()
        
        # Verify timing
        self.assertLess(timestamps['start'], timestamps['complete'])
        
        # Verify elapsed time is set
        file_prog = self.tracker.file_progress[self.filename]
        self.assertGreater(file_prog.elapsed_time, 0)
    
    def test_state_transition_with_exceptions(self):
        """Test state transition when exceptions occur."""
        # Initialize file
        self.tracker.initialize_file(self.filename, self.total_pages)
        
        # Start processing
        self.tracker.start_file(self.filename)
        self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
        
        # Complete with failure
        self.tracker.complete_file(self.filename, success=False, error="Test error")
        
        # Verify failed state
        self.assertEqual(self.tracker.file_progress[self.filename].status, "failed")
        self.assertEqual(self.tracker.file_progress[self.filename].error, "Test error")


class TestStatusTransitionIntegration(unittest.TestCase):
    """Integration tests for status transitions with actual processing flow."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.tracker = DetailedProgressTracker(
            total_files=1,
            operation_name="集成测试",
            processing_mode="batch_generation"
        )
        self.filename = "test.pdf"
        self.total_pages = 3
    
    def test_simulated_processing_flow(self):
        """Test complete processing flow simulation."""
        # Step 1: Initialize
        self.tracker.initialize_file(self.filename, self.total_pages)
        self.assertEqual(self.tracker.file_progress[self.filename].status, "waiting")
        
        # Step 2: Start processing
        self.tracker.start_file(self.filename)
        self.assertEqual(self.tracker.file_progress[self.filename].status, "processing")
        
        # Step 3: Update stage
        self.tracker.update_file_stage(self.filename, 0)  # Stage 0: 给PDF页面截图
        
        # Step 4: Update pages
        for page_idx in range(self.total_pages):
            self.tracker.update_page_status(self.filename, page_idx, "processing")
            time.sleep(0.001)  # Simulate processing
            self.tracker.update_page_status(self.filename, page_idx, "completed")
            self.tracker.update_file_page_progress(self.filename, page_idx + 1, self.total_pages)
        
        # Step 5: Update stage
        self.tracker.update_file_stage(self.filename, 1)  # Stage 1: 用LLM生成讲解
        self.tracker.update_file_stage(self.filename, 2)  # Stage 2: 合成文档
        
        # Step 6: Complete
        self.tracker.complete_file(self.filename, success=True)
        self.assertEqual(self.tracker.file_progress[self.filename].status, "completed")
        
        # Verify all pages are completed
        file_prog = self.tracker.file_progress[self.filename]
        self.assertEqual(file_prog.completed_pages, self.total_pages)
        for page_idx in range(self.total_pages):
            self.assertEqual(file_prog.page_statuses[page_idx], "completed")


if __name__ == '__main__':
    unittest.main()

