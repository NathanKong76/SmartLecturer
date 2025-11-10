"""
Comprehensive tests for page-level cache recall functionality.

This test suite verifies that:
1. Pages with existing explanations in cache are skipped
2. Only pages without explanations are processed
3. Cached pages are correctly merged with newly processed pages
4. Progress tracking correctly reflects skipped pages
5. Page status updates correctly for cached pages
"""

import pytest
import tempfile
import os
import json
from typing import Dict, List, Optional
from unittest.mock import Mock, patch, AsyncMock

# Import the functions to test
from app.services.pdf_processor import generate_explanations, _generate_explanations_async, retry_failed_pages
from app.cache_processor import (
    get_file_hash, save_result_to_file, load_result_from_file,
    validate_cache_data, cached_process_pdf
)


class TestPageLevelCacheRecall:
    """Test suite for page-level cache recall."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for cache files
        self.temp_dir = tempfile.mkdtemp()
        self.original_temp_dir = None
        
        # Mock PDF bytes (minimal valid PDF)
        self.sample_pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n179\n%%EOF"
        
        # Sample parameters
        self.params = {
            "api_key": "test_key",
            "model_name": "test_model",
            "user_prompt": "Test prompt",
            "temperature": 0.7,
            "max_tokens": 1000,
            "dpi": 150,
            "concurrency": 1,
            "rpm_limit": 60,
            "tpm_budget": 1000000,
            "rpd_limit": 10000,
        }
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_skip_cached_pages_in_async_function(self):
        """Test that cached pages are skipped in _generate_explanations_async."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="New explanation")
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # Existing explanations (page 0 and 2 are cached)
        existing_explanations = {
            0: "Cached explanation for page 1",
            2: "Cached explanation for page 3"
        }
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
        import asyncio
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=1,
                on_progress=on_progress,
                on_log=on_log,
                global_concurrency_controller=None,
                on_page_status=on_page_status,
                target_pages=None,
                on_partial_save=None,
                existing_explanations=existing_explanations,
            )
        )
        
        # Verify that only page 1 (index 1) was processed
        assert mock_llm_client.explain_pages_with_context.call_count == 1
        
        # Verify that cached pages are in the result
        assert 0 in explanations
        assert explanations[0] == "Cached explanation for page 1"
        assert 2 in explanations
        assert explanations[2] == "Cached explanation for page 3"
        
        # Verify that page 1 was processed
        assert 1 in explanations
        assert explanations[1] == "New explanation"
        
        # Verify no failed pages
        assert failed_pages == []
        
        # Verify that on_page_status was called for cached pages
        cached_status_calls = [call for call in on_page_status.call_args_list 
                              if call[0][1] == "completed" and call[0][0] in [0, 2]]
        assert len(cached_status_calls) >= 2  # At least 2 calls for cached pages
    
    def test_load_cache_from_file_hash(self):
        """Test that generate_explanations loads cache from file_hash."""
        # Create a cache file
        file_hash = "test_hash_123"
        cache_data = {
            "status": "partial",
            "explanations": {
                "0": "Cached explanation for page 1",
                "2": "Cached explanation for page 3"
            },
            "failed_pages": [2]
        }
        
        # Save cache file
        with patch('app.cache_processor.TEMP_DIR', self.temp_dir):
            save_result_to_file(file_hash, cache_data)
            
            # Verify cache file exists
            cache_file = os.path.join(self.temp_dir, f"{file_hash}.json")
            assert os.path.exists(cache_file)
            
            # Load cache file
            loaded_cache = load_result_from_file(file_hash)
            assert loaded_cache is not None
            assert "explanations" in loaded_cache
            assert 0 in loaded_cache["explanations"]  # Keys should be converted to int
            assert 2 in loaded_cache["explanations"]
    
    def test_retry_failed_pages_with_cache(self):
        """Test that retry_failed_pages correctly uses existing explanations."""
        # Existing explanations (some pages already cached)
        existing_explanations = {
            0: "Cached explanation for page 1",
            1: "Cached explanation for page 2",
        }
        
        # Failed pages (1-based): page 3 failed
        failed_page_numbers = [3]
        
        # Mock generate_explanations to return new explanation for page 3
        with patch('app.services.pdf_processor.generate_explanations') as mock_gen:
            mock_gen.return_value = (
                {2: "New explanation for page 3"},  # 0-based index
                {1: "preview1", 2: "preview2", 3: "preview3"},
                []  # No failed pages
            )
            
            # Mock PDF document
            with patch('app.services.pdf_processor.fitz') as mock_fitz:
                mock_doc = Mock()
                mock_doc.page_count = 3
                mock_doc.__enter__ = Mock(return_value=mock_doc)
                mock_doc.__exit__ = Mock(return_value=None)
                mock_fitz.open.return_value = mock_doc
                
                # Call retry_failed_pages
                merged_explanations, preview_images, remaining_failed = retry_failed_pages(
                    src_bytes=self.sample_pdf_bytes,
                    existing_explanations=existing_explanations,
                    failed_page_numbers=failed_page_numbers,
                    api_key="test_key",
                    model_name="test_model",
                    user_prompt="Test prompt",
                    temperature=0.7,
                    max_tokens=1000,
                    dpi=150,
                    concurrency=1,
                    rpm_limit=60,
                    tpm_budget=1000000,
                    rpd_limit=10000,
                    file_hash=None,
                )
                
                # Verify that existing_explanations was passed to generate_explanations
                call_args = mock_gen.call_args
                assert call_args is not None
                assert "existing_explanations" in call_args.kwargs
                assert call_args.kwargs["existing_explanations"] == existing_explanations
                
                # Verify merged explanations
                assert 0 in merged_explanations
                assert 1 in merged_explanations
                assert 2 in merged_explanations
                assert merged_explanations[2] == "New explanation for page 3"
    
    def test_all_pages_cached_early_return(self):
        """Test that if all pages are cached, function returns early."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock()
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # All pages are cached
        existing_explanations = {
            0: "Cached explanation for page 1",
            1: "Cached explanation for page 2",
            2: "Cached explanation for page 3"
        }
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
        import asyncio
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=1,
                on_progress=on_progress,
                on_log=on_log,
                global_concurrency_controller=None,
                on_page_status=on_page_status,
                target_pages=None,
                on_partial_save=None,
                existing_explanations=existing_explanations,
            )
        )
        
        # Verify that LLM was never called (all pages cached)
        assert mock_llm_client.explain_pages_with_context.call_count == 0
        
        # Verify that all cached pages are in the result
        assert len(explanations) == 3
        assert explanations == existing_explanations
        
        # Verify that progress was updated to show all pages completed
        on_progress.assert_called_with(3, 3)
        
        # Verify that page status was updated for all cached pages
        assert on_page_status.call_count >= 3
    
    def test_partial_cache_with_target_pages(self):
        """Test cache recall with target_pages specified."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="New explanation")
        
        # Create page images (5 pages)
        page_images = [b"image1", b"image2", b"image3", b"image4", b"image5"]
        
        # Some pages are cached
        existing_explanations = {
            0: "Cached explanation for page 1",
            2: "Cached explanation for page 3",
            4: "Cached explanation for page 5"
        }
        
        # Target pages: 2, 3, 4 (1-based) -> indices 1, 2, 3 (0-based)
        target_pages = [1, 2, 3]  # 0-based
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
        import asyncio
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=1,
                on_progress=on_progress,
                on_log=on_log,
                global_concurrency_controller=None,
                on_page_status=on_page_status,
                target_pages=target_pages,
                on_partial_save=None,
                existing_explanations=existing_explanations,
            )
        )
        
        # Verify that only page 1 and 3 (indices 1, 3) were processed
        # Page 2 (index 2) is cached, so it should be skipped
        assert mock_llm_client.explain_pages_with_context.call_count == 2
        
        # Verify that cached page 2 is in the result
        assert 2 in explanations
        assert explanations[2] == "Cached explanation for page 3"
        
        # Verify that pages 1 and 3 were processed
        assert 1 in explanations
        assert 3 in explanations
    
    def test_empty_cache_works_normally(self):
        """Test that function works normally when no cache exists."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="New explanation")
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # No existing explanations
        existing_explanations = {}
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
        import asyncio
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=1,
                on_progress=on_progress,
                on_log=on_log,
                global_concurrency_controller=None,
                on_page_status=on_page_status,
                target_pages=None,
                on_partial_save=None,
                existing_explanations=existing_explanations,
            )
        )
        
        # Verify that all pages were processed
        assert mock_llm_client.explain_pages_with_context.call_count == 3
        
        # Verify that all pages are in the result
        assert len(explanations) == 3
        assert 0 in explanations
        assert 1 in explanations
        assert 2 in explanations
    
    def test_blank_explanations_not_skipped(self):
        """Test that blank/empty explanations are not skipped."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="New explanation")
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # Page 0 has blank explanation (should be reprocessed)
        existing_explanations = {
            0: "",  # Blank - should be reprocessed
            1: "   ",  # Whitespace only - should be reprocessed
            2: "Valid explanation"  # Valid - should be skipped
        }
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
        import asyncio
        explanations, preview_images, failed_pages = asyncio.run(
            _generate_explanations_async(
                llm_client=mock_llm_client,
                page_images=page_images,
                user_prompt="Test prompt",
                context_prompt=None,
                use_context=False,
                concurrency=1,
                on_progress=on_progress,
                on_log=on_log,
                global_concurrency_controller=None,
                on_page_status=on_page_status,
                target_pages=None,
                on_partial_save=None,
                existing_explanations=existing_explanations,
            )
        )
        
        # Verify that pages 0 and 1 were processed (blank explanations)
        # Page 2 should be skipped (valid explanation)
        assert mock_llm_client.explain_pages_with_context.call_count == 2
        
        # Verify that page 2 is still in the result with its cached value
        assert 2 in explanations
        assert explanations[2] == "Valid explanation"
        
        # Verify that pages 0 and 1 were processed
        assert 0 in explanations
        assert 1 in explanations
        assert explanations[0] == "New explanation"
        assert explanations[1] == "New explanation"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

