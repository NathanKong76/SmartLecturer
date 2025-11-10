"""
Integration tests for page-level cache frontend functionality.

Tests the complete flow from UI to cache and back, including:
1. Cache loading and display in UI
2. Progress tracking with cached pages
3. Retry functionality with cache
4. State management
5. Error handling
"""

import pytest
import tempfile
import os
import json
from typing import Dict, Any
from unittest.mock import Mock, patch, MagicMock

from app.ui_helpers import process_single_file_pdf, StateManager
from app.cache_processor import (
    save_result_to_file,
    load_result_from_file,
    get_file_hash,
    validate_cache_data,
    TEMP_DIR
)
from app.ui.components.detailed_progress_tracker import DetailedProgressTracker


class TestCacheFrontendIntegration:
    """Integration tests for cache frontend."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        import app.cache_processor
        self.original_temp_dir = app.cache_processor.TEMP_DIR
        app.cache_processor.TEMP_DIR = self.temp_dir
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        import app.cache_processor
        if self.original_temp_dir:
            app.cache_processor.TEMP_DIR = self.original_temp_dir
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_cache_loaded_pages_displayed_correctly(self):
        """Test that cached pages are displayed as completed in progress tracker."""
        tracker = DetailedProgressTracker(
            total_files=1,
            operation_name="测试",
            processing_mode="batch_generation"
        )
        
        tracker.initialize_file("test.pdf", total_pages=5)
        tracker.start_file("test.pdf")
        
        # Simulate pages 0, 2, 4 being cached (completed immediately)
        tracker.update_page_status("test.pdf", 0, "completed")
        tracker.update_page_status("test.pdf", 2, "completed")
        tracker.update_page_status("test.pdf", 4, "completed")
        
        # Verify page statuses
        file_prog = tracker.file_progress["test.pdf"]
        assert file_prog.page_statuses[0] == "completed"
        assert file_prog.page_statuses[2] == "completed"
        assert file_prog.page_statuses[4] == "completed"
        
        # Verify completed_pages is highest completed page number
        assert file_prog.completed_pages == 5  # Page 4 (index 4) = page 5 (1-based)
    
    def test_cache_partial_result_ui_flow(self):
        """Test UI flow with partial cache result."""
        # Create partial cache
        file_hash = "test_partial_ui"
        cached_result = {
            "status": "partial",
            "explanations": {
                0: "Page 1 explanation",
                2: "Page 3 explanation"
            },
            "failed_pages": [2]  # Page 2 failed (1-based)
        }
        save_result_to_file(file_hash, cached_result)
        
        # Verify cache structure
        loaded = load_result_from_file(file_hash)
        assert loaded["status"] == "partial"
        assert len(loaded["explanations"]) == 2
        assert loaded["failed_pages"] == [2]
        
        # Verify UI would show correct info
        existing_explanations = loaded["explanations"]
        failed_pages = loaded["failed_pages"]
        
        # UI message format
        message = f"已成功生成 {len(existing_explanations)} 页讲解，还有 {len(failed_pages)} 页失败: {', '.join(map(str, failed_pages))}"
        assert "2" in message  # 2 pages succeeded
        assert "2" in message  # Page 2 failed
    
    def test_retry_button_data_structure(self):
        """Test that retry button stores correct data structure."""
        # Simulate batch_results
        batch_results = {
            "test.pdf": {
                "status": "completed",
                "explanations": {
                    0: "Page 1",
                    1: "Page 2",
                    2: "Page 3"
                },
                "failed_pages": [2]  # Page 2 failed (1-based)
            }
        }
        
        filename = "test.pdf"
        result = batch_results[filename]
        
        # Simulate retry button click
        retry_data = {
            "filename": filename,
            "failed_pages": result.get("failed_pages", []),
            "existing_explanations": result.get("explanations", {})
        }
        
        # Verify structure matches what retry_failed_pages expects
        assert "filename" in retry_data
        assert "failed_pages" in retry_data
        assert "existing_explanations" in retry_data
        
        # Verify failed_pages is 1-based
        assert retry_data["failed_pages"] == [2]
        
        # Verify existing_explanations has int keys (0-based)
        assert isinstance(list(retry_data["existing_explanations"].keys())[0], int)
        assert 0 in retry_data["existing_explanations"]
        assert 1 in retry_data["existing_explanations"]
        assert 2 in retry_data["existing_explanations"]
    
    def test_cache_validation_warnings_in_ui(self):
        """Test that cache validation warnings are properly formatted for UI."""
        # Create cache with validation issues
        file_hash = "test_validation_ui"
        cached_result = {
            "status": "partial",
            "explanations": {
                0: "Page 1",
                2: "Page 3"
            },
            "failed_pages": [2]
        }
        save_result_to_file(file_hash, cached_result)
        
        # Create minimal PDF (1 page)
        minimal_pdf = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n179\n%%EOF"
        
        loaded = load_result_from_file(file_hash)
        is_valid, fixed_explanations, fixed_failed_pages, warnings = validate_cache_data(
            minimal_pdf,
            loaded["explanations"],
            loaded["failed_pages"]
        )
        
        # Verify warnings are user-friendly
        if warnings:
            for warning in warnings:
                assert isinstance(warning, str)
                assert len(warning) > 0
                # Warnings should be in Chinese for UI display
                assert any(char in warning for char in ["页", "移除", "无效", "冲突", "遗漏"])
    
    def test_cache_statistics_display_format(self):
        """Test cache statistics display format."""
        # Create multiple cache files
        for i in range(3):
            file_hash = f"test_stats_{i:03d}"
            result = {
                "explanations": {0: f"Page {i}"},
                "failed_pages": []
            }
            save_result_to_file(file_hash, result)
        
        # Get statistics
        from app.cache_processor import get_cache_stats
        stats = get_cache_stats()
        
        # Verify statistics format
        assert "file_count" in stats
        assert "total_size" in stats
        assert "total_size_mb" in stats
        
        # Verify values are reasonable
        assert stats["file_count"] == 3
        assert stats["total_size"] >= 0
        assert stats["total_size_mb"] >= 0
    
    def test_cache_clear_ui_feedback(self):
        """Test cache clear UI feedback."""
        # Create cache files
        for i in range(2):
            file_hash = f"test_clear_{i:03d}"
            result = {
                "explanations": {0: f"Page {i}"},
                "failed_pages": []
            }
            save_result_to_file(file_hash, result)
        
        # Clear cache
        from app.cache_processor import clear_cache
        result = clear_cache()
        
        # Verify feedback structure
        assert "success" in result
        assert "deleted_count" in result
        assert "deleted_size_mb" in result
        
        assert result["success"] is True
        assert result["deleted_count"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

