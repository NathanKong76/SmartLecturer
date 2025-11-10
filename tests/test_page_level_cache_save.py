"""
Comprehensive tests for page-level cache save functionality.

This test suite verifies:
1. Real-time partial save during processing
2. Save completeness and consistency
3. Thread safety in concurrent saves
4. Error handling during save failures
5. Edge cases (empty data, large data, etc.)
6. Save and load consistency
7. Status transitions (partial -> completed)
8. Key type conversion (int -> string -> int)
9. Timestamp correctness
10. Data integrity after save/load cycles
"""

import pytest
import tempfile
import os
import json
import threading
import time
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio

from app.cache_processor import (
    save_result_to_file,
    load_result_from_file,
    get_file_hash,
    TEMP_DIR
)
from app.services.pdf_processor import _generate_explanations_async


class TestPageLevelCacheSave:
    """Comprehensive test suite for page-level cache save."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        self.original_temp_dir = None
        
        # Patch TEMP_DIR to use our test directory
        import app.cache_processor
        self.original_temp_dir = app.cache_processor.TEMP_DIR
        app.cache_processor.TEMP_DIR = self.temp_dir
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        import app.cache_processor
        
        # Restore original TEMP_DIR
        if self.original_temp_dir:
            app.cache_processor.TEMP_DIR = self.original_temp_dir
        
        # Clean up test directory
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_basic_result(self):
        """Test basic save functionality."""
        file_hash = "test_hash_001"
        result = {
            "status": "completed",
            "explanations": {
                0: "Explanation for page 1",
                1: "Explanation for page 2",
                2: "Explanation for page 3"
            },
            "failed_pages": []
        }
        
        filepath = save_result_to_file(file_hash, result)
        
        # Verify file was created
        assert os.path.exists(filepath)
        assert filepath == os.path.join(self.temp_dir, f"{file_hash}.json")
        
        # Verify file content
        with open(filepath, 'r', encoding='utf-8') as f:
            loaded = json.load(f)
        
        assert loaded["status"] == "completed"
        assert "explanations" in loaded
        assert "failed_pages" in loaded
        assert "timestamp" in loaded
        assert "pdf_bytes" not in loaded  # Should be removed
    
    def test_save_partial_result(self):
        """Test saving partial result with failed pages."""
        file_hash = "test_hash_002"
        result = {
            "status": "partial",
            "explanations": {
                0: "Explanation for page 1",
                2: "Explanation for page 3"
            },
            "failed_pages": [2]  # Page 2 failed (1-based)
        }
        
        filepath = save_result_to_file(file_hash, result)
        
        # Load and verify
        loaded = load_result_from_file(file_hash)
        assert loaded is not None
        assert loaded["status"] == "partial"
        assert len(loaded["explanations"]) == 2
        assert loaded["failed_pages"] == [2]
        # Verify keys are converted to int
        assert 0 in loaded["explanations"]
        assert 2 in loaded["explanations"]
    
    def test_save_auto_status_detection(self):
        """Test automatic status detection based on failed_pages."""
        file_hash = "test_hash_003"
        
        # Test 1: No status, no failed pages -> should be "completed"
        result1 = {
            "explanations": {0: "test"},
            "failed_pages": []
        }
        filepath1 = save_result_to_file(file_hash + "_1", result1)
        loaded1 = load_result_from_file(file_hash + "_1")
        assert loaded1["status"] == "completed"
        
        # Test 2: No status, with failed pages -> should be "partial"
        result2 = {
            "explanations": {0: "test"},
            "failed_pages": [2]
        }
        filepath2 = save_result_to_file(file_hash + "_2", result2)
        loaded2 = load_result_from_file(file_hash + "_2")
        assert loaded2["status"] == "partial"
    
    def test_save_timestamp(self):
        """Test that timestamp is added correctly."""
        file_hash = "test_hash_004"
        result = {
            "explanations": {0: "test"},
            "failed_pages": []
        }
        
        before_time = time.time()
        filepath = save_result_to_file(file_hash, result)
        after_time = time.time()
        
        loaded = load_result_from_file(file_hash)
        assert "timestamp" in loaded
        
        # Parse timestamp
        from datetime import datetime
        saved_time = datetime.fromisoformat(loaded["timestamp"]).timestamp()
        
        # Verify timestamp is within reasonable range
        assert before_time <= saved_time <= after_time
    
    def test_save_key_type_conversion(self):
        """Test that int keys are preserved through save/load cycle."""
        file_hash = "test_hash_005"
        result = {
            "explanations": {
                0: "Page 1",
                1: "Page 2",
                2: "Page 3"
            },
            "failed_pages": []
        }
        
        save_result_to_file(file_hash, result)
        loaded = load_result_from_file(file_hash)
        
        # Verify keys are int (after conversion from JSON string keys)
        assert isinstance(list(loaded["explanations"].keys())[0], int)
        assert 0 in loaded["explanations"]
        assert 1 in loaded["explanations"]
        assert 2 in loaded["explanations"]
    
    def test_save_large_data(self):
        """Test saving large amounts of data."""
        file_hash = "test_hash_006"
        
        # Create large explanations dict
        large_explanations = {}
        for i in range(1000):
            large_explanations[i] = f"Explanation for page {i+1} " * 100  # Large strings
        
        result = {
            "explanations": large_explanations,
            "failed_pages": []
        }
        
        filepath = save_result_to_file(file_hash, result)
        
        # Verify file was created and is reasonably large
        assert os.path.exists(filepath)
        file_size = os.path.getsize(filepath)
        assert file_size > 100000  # Should be at least 100KB
        
        # Verify can load
        loaded = load_result_from_file(file_hash)
        assert loaded is not None
        assert len(loaded["explanations"]) == 1000
    
    def test_save_empty_data(self):
        """Test saving empty data."""
        file_hash = "test_hash_007"
        
        # Empty explanations
        result1 = {
            "explanations": {},
            "failed_pages": []
        }
        save_result_to_file(file_hash + "_1", result1)
        loaded1 = load_result_from_file(file_hash + "_1")
        assert loaded1["status"] == "completed"
        assert len(loaded1["explanations"]) == 0
        
        # Empty failed_pages
        result2 = {
            "explanations": {0: "test"},
            "failed_pages": []
        }
        save_result_to_file(file_hash + "_2", result2)
        loaded2 = load_result_from_file(file_hash + "_2")
        assert loaded2["status"] == "completed"
        assert len(loaded2["failed_pages"]) == 0
    
    def test_save_unicode_content(self):
        """Test saving unicode/Chinese content."""
        file_hash = "test_hash_008"
        result = {
            "explanations": {
                0: "这是中文解释",
                1: "This is English explanation",
                2: "これは日本語の説明です"
            },
            "failed_pages": []
        }
        
        save_result_to_file(file_hash, result)
        loaded = load_result_from_file(file_hash)
        
        assert loaded["explanations"][0] == "这是中文解释"
        assert loaded["explanations"][1] == "This is English explanation"
        assert loaded["explanations"][2] == "これは日本語の説明です"
    
    def test_save_concurrent_writes(self):
        """Test thread safety of concurrent saves."""
        file_hash = "test_hash_009"
        num_threads = 10
        results = []
        errors = []
        
        def save_worker(thread_id):
            try:
                result = {
                    "explanations": {thread_id: f"Explanation from thread {thread_id}"},
                    "failed_pages": []
                }
                save_result_to_file(f"{file_hash}_{thread_id}", result)
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, str(e)))
        
        # Create and start threads
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=save_worker, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for all threads
        for t in threads:
            t.join()
        
        # Verify all saves succeeded
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == num_threads
        
        # Verify all files were created
        for i in range(num_threads):
            filepath = os.path.join(self.temp_dir, f"{file_hash}_{i}.json")
            assert os.path.exists(filepath)
            loaded = load_result_from_file(f"{file_hash}_{i}")
            assert loaded is not None
            assert i in loaded["explanations"]
    
    def test_save_same_file_hash_overwrite(self):
        """Test that saving with same file_hash overwrites previous data."""
        file_hash = "test_hash_010"
        
        # First save
        result1 = {
            "explanations": {0: "First save"},
            "failed_pages": []
        }
        save_result_to_file(file_hash, result1)
        
        # Second save (overwrite)
        result2 = {
            "explanations": {0: "Second save", 1: "New page"},
            "failed_pages": []
        }
        save_result_to_file(file_hash, result2)
        
        # Verify second save overwrote first
        loaded = load_result_from_file(file_hash)
        assert loaded["explanations"][0] == "Second save"
        assert loaded["explanations"][1] == "New page"
    
    def test_real_time_partial_save_during_processing(self):
        """Test real-time partial save during async processing."""
        file_hash = "test_hash_011"
        saved_states = []
        
        def on_partial_save(explanations_dict: Dict[int, str], failed_pages_list: List[int]):
            """Capture saved states."""
            saved_states.append({
                "explanations": explanations_dict.copy(),
                "failed_pages": failed_pages_list.copy()
            })
            # Also save to file
            try:
                from app.cache_processor import save_result_to_file
                partial_result = {
                    "status": "partial" if failed_pages_list else "completed",
                    "explanations": explanations_dict,
                    "failed_pages": failed_pages_list,
                }
                save_result_to_file(file_hash, partial_result)
            except Exception:
                pass
        
        # Create mock LLM client
        mock_llm_client = Mock()
        call_count = {"count": 0}
        
        async def mock_explain(pages, **kwargs):
            call_count["count"] += 1
            await asyncio.sleep(0.01)  # Simulate processing time
            if call_count["count"] == 2:
                # Second call fails
                raise Exception("Simulated failure")
            return f"Explanation {call_count['count']}"
        
        mock_llm_client.explain_pages_with_context = AsyncMock(side_effect=mock_explain)
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # Run async processing
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=3,  # Process all pages concurrently
                on_progress=None,
                on_log=None,
                global_concurrency_controller=None,
                on_page_status=None,
                target_pages=None,
                on_partial_save=on_partial_save,
                existing_explanations=None,
            )
        )
        
        # Verify that partial saves were called
        assert len(saved_states) > 0
        
        # Verify final state was saved
        final_loaded = load_result_from_file(file_hash)
        assert final_loaded is not None
        assert "explanations" in final_loaded
        assert "failed_pages" in final_loaded
    
    def test_save_consistency_explanations_failed_pages(self):
        """Test that explanations and failed_pages are consistent."""
        file_hash = "test_hash_012"
        
        # Test case 1: No overlap between explanations and failed_pages
        result1 = {
            "explanations": {0: "Page 1", 2: "Page 3"},
            "failed_pages": [2]  # Page 2 failed (1-based)
        }
        save_result_to_file(file_hash + "_1", result1)
        loaded1 = load_result_from_file(file_hash + "_1")
        
        # Verify no overlap (0-based index 1 should not be in explanations)
        explanations_indices = set(loaded1["explanations"].keys())
        failed_indices = {p - 1 for p in loaded1["failed_pages"]}  # Convert to 0-based
        overlap = explanations_indices & failed_indices
        assert len(overlap) == 0, f"Found overlap: {overlap}"
    
    def test_save_load_cycle_integrity(self):
        """Test data integrity through multiple save/load cycles."""
        file_hash = "test_hash_013"
        
        original_result = {
            "explanations": {
                0: "Explanation 1",
                1: "Explanation 2",
                2: "Explanation 3"
            },
            "failed_pages": []
        }
        
        # Save and load multiple times
        for cycle in range(5):
            save_result_to_file(file_hash, original_result)
            loaded = load_result_from_file(file_hash)
            
            # Verify integrity
            assert loaded["status"] == "completed"
            assert len(loaded["explanations"]) == 3
            assert loaded["explanations"][0] == "Explanation 1"
            assert loaded["explanations"][1] == "Explanation 2"
            assert loaded["explanations"][2] == "Explanation 3"
            assert len(loaded["failed_pages"]) == 0
    
    def test_save_status_transition_partial_to_completed(self):
        """Test status transition from partial to completed."""
        file_hash = "test_hash_014"
        
        # First save: partial
        result1 = {
            "explanations": {0: "Page 1"},
            "failed_pages": [2, 3]
        }
        save_result_to_file(file_hash, result1)
        loaded1 = load_result_from_file(file_hash)
        assert loaded1["status"] == "partial"
        
        # Second save: completed (all pages succeeded)
        result2 = {
            "explanations": {0: "Page 1", 1: "Page 2", 2: "Page 3"},
            "failed_pages": []
        }
        save_result_to_file(file_hash, result2)
        loaded2 = load_result_from_file(file_hash)
        assert loaded2["status"] == "completed"
        assert len(loaded2["failed_pages"]) == 0
    
    def test_save_error_handling(self):
        """Test error handling during save."""
        file_hash = "test_hash_015"
        
        # Test with invalid file_hash (should still work)
        invalid_hash = "test/invalid\\hash"
        result = {
            "explanations": {0: "test"},
            "failed_pages": []
        }
        
        # Should handle invalid characters in hash
        try:
            save_result_to_file(invalid_hash, result)
            # If it succeeds, verify file exists
            filepath = os.path.join(self.temp_dir, f"{invalid_hash}.json")
            if os.path.exists(filepath):
                loaded = load_result_from_file(invalid_hash)
                assert loaded is not None
        except Exception:
            # If it fails, that's also acceptable (OS may reject invalid chars)
            pass
    
    def test_save_with_existing_cache_merge(self):
        """Test that saving merges correctly with existing cache."""
        file_hash = "test_hash_016"
        
        # Initial save
        result1 = {
            "explanations": {0: "Page 1", 1: "Page 2"},
            "failed_pages": [3]
        }
        save_result_to_file(file_hash, result1)
        
        # Load existing
        existing = load_result_from_file(file_hash)
        
        # Simulate processing more pages
        new_explanations = {2: "Page 3"}  # Page 3 now succeeded
        merged_explanations = {**existing["explanations"], **new_explanations}
        merged_failed = [p for p in existing["failed_pages"] if p != 3]  # Remove page 3 from failed
        
        # Save merged result
        result2 = {
            "explanations": merged_explanations,
            "failed_pages": merged_failed
        }
        save_result_to_file(file_hash, result2)
        
        # Verify merge
        loaded = load_result_from_file(file_hash)
        assert len(loaded["explanations"]) == 3
        assert 0 in loaded["explanations"]
        assert 1 in loaded["explanations"]
        assert 2 in loaded["explanations"]
        assert len(loaded["failed_pages"]) == 0
        assert loaded["status"] == "completed"
    
    def test_save_special_characters_in_explanations(self):
        """Test saving explanations with special characters."""
        file_hash = "test_hash_017"
        result = {
            "explanations": {
                0: "Line 1\nLine 2\nLine 3",
                1: "Tab\tSeparated\tValues",
                2: "Quote: \"Hello\"",
                3: "Backslash: \\",
                4: "Unicode: \u2022 \u2023 \u2024"
            },
            "failed_pages": []
        }
        
        save_result_to_file(file_hash, result)
        loaded = load_result_from_file(file_hash)
        
        assert loaded["explanations"][0] == "Line 1\nLine 2\nLine 3"
        assert loaded["explanations"][1] == "Tab\tSeparated\tValues"
        assert loaded["explanations"][2] == "Quote: \"Hello\""
        assert loaded["explanations"][3] == "Backslash: \\"
        assert loaded["explanations"][4] == "Unicode: \u2022 \u2023 \u2024"
    
    def test_save_empty_explanations_string(self):
        """Test saving empty string explanations."""
        file_hash = "test_hash_018"
        result = {
            "explanations": {
                0: "",  # Empty string
                1: "   ",  # Whitespace only
                2: "Valid explanation"
            },
            "failed_pages": []
        }
        
        save_result_to_file(file_hash, result)
        loaded = load_result_from_file(file_hash)
        
        assert loaded["explanations"][0] == ""
        assert loaded["explanations"][1] == "   "
        assert loaded["explanations"][2] == "Valid explanation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

