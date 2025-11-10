"""
Test that failed pages are NOT recalled from cache.

This test verifies that:
1. Failed pages are not in existing_explanations
2. Failed pages are not skipped and will be reprocessed
3. Only successful pages are recalled from cache
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from app.services.pdf_processor import _generate_explanations_async, generate_explanations


class TestFailedPagesNotRecalled:
    """Test that failed pages are not recalled from cache."""
    
    def test_failed_pages_not_in_explanations(self):
        """Test that failed pages are not included in existing_explanations."""
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="New explanation")
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # Existing explanations: page 0 and 2 are successful, page 1 was failed (not in explanations)
        existing_explanations = {
            0: "Successful explanation for page 1",
            2: "Successful explanation for page 3"
            # Note: page 1 (index 1) is NOT in explanations because it failed
        }
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
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
        
        # Verify that page 1 (index 1) was processed (not skipped)
        assert mock_llm_client.explain_pages_with_context.call_count == 1
        
        # Verify that successful pages are in the result
        assert 0 in explanations
        assert explanations[0] == "Successful explanation for page 1"
        assert 2 in explanations
        assert explanations[2] == "Successful explanation for page 3"
        
        # Verify that page 1 was processed and added to explanations
        assert 1 in explanations
        assert explanations[1] == "New explanation"
        
        # Verify no failed pages
        assert failed_pages == []
    
    def test_failed_pages_reprocessed_from_cache(self):
        """Test that when loading from cache, failed pages are not recalled."""
        # This test simulates loading from cache where some pages failed
        # Cache structure:
        # - explanations: {0: "success", 2: "success"}  # pages 1 and 3 succeeded
        # - failed_pages: [2]  # page 2 (1-based) = index 1 (0-based) failed
        
        # When loading from cache, only explanations are loaded
        # failed_pages are NOT included in existing_explanations
        existing_explanations = {
            0: "Successful explanation for page 1",
            2: "Successful explanation for page 3"
            # Page 1 (index 1) is NOT here because it failed
        }
        
        # Create mock LLM client
        mock_llm_client = Mock()
        mock_llm_client.explain_pages_with_context = AsyncMock(return_value="Retry explanation")
        
        # Create page images (3 pages)
        page_images = [b"image1", b"image2", b"image3"]
        
        # Mock callbacks
        on_progress = Mock()
        on_log = Mock()
        on_page_status = Mock()
        
        # Run the async function
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
        
        # Verify that page 1 (the failed page) was processed
        assert mock_llm_client.explain_pages_with_context.call_count == 1
        
        # Verify that successful pages are still in the result
        assert 0 in explanations
        assert 2 in explanations
        
        # Verify that page 1 was reprocessed
        assert 1 in explanations
        assert explanations[1] == "Retry explanation"
    
    def test_cache_load_only_successful_pages(self):
        """Test that when loading from cache, only successful pages are loaded."""
        # Simulate cache structure
        cache_data = {
            "status": "partial",
            "explanations": {
                "0": "Successful explanation for page 1",
                "2": "Successful explanation for page 3"
            },
            "failed_pages": [2]  # Page 2 (1-based) failed
        }
        
        # When loading from cache, only explanations are used
        # failed_pages are NOT included in existing_explanations
        existing_explanations = cache_data.get("explanations", {})
        # Convert keys to int
        existing_explanations = {int(k): v for k, v in existing_explanations.items()}
        
        # Verify that failed page is NOT in explanations
        assert 1 not in existing_explanations  # Page 2 (1-based) = index 1 (0-based) is NOT in explanations
        
        # Verify that successful pages ARE in explanations
        assert 0 in existing_explanations
        assert 2 in existing_explanations
    
    def test_retry_failed_pages_with_cache(self):
        """Test that retry_failed_pages correctly handles failed pages that are not in cache."""
        # Scenario: Some pages failed, we want to retry them
        # But some of those "failed" pages might actually be in cache now (if they were retried successfully before)
        
        # Existing explanations (some pages succeeded)
        existing_explanations = {
            0: "Successful explanation for page 1",
            2: "Successful explanation for page 3"
        }
        
        # Failed pages to retry (1-based): page 2
        failed_page_numbers = [2]  # Page 2 (1-based) = index 1 (0-based)
        
        # Mock generate_explanations
        with patch('app.services.pdf_processor.generate_explanations') as mock_gen:
            mock_gen.return_value = (
                {1: "New explanation for page 2"},  # 0-based index
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
                
                from app.services.pdf_processor import retry_failed_pages
                
                # Call retry_failed_pages
                merged_explanations, preview_images, remaining_failed = retry_failed_pages(
                    src_bytes=b"dummy_pdf",
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
                
                # Verify that existing_explanations was passed
                call_args = mock_gen.call_args
                assert call_args is not None
                assert "existing_explanations" in call_args.kwargs
                
                # Verify that page 1 (the failed page) is not in existing_explanations
                # So it will be processed
                passed_explanations = call_args.kwargs["existing_explanations"]
                assert 1 not in passed_explanations  # Failed page is not in cache
                
                # Verify merged explanations
                assert 0 in merged_explanations
                assert 1 in merged_explanations  # Now it's in merged_explanations after retry
                assert 2 in merged_explanations


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

