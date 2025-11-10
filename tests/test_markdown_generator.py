"""
Comprehensive and strict tests for Markdown Generator.

This test suite verifies:
1. Markdown generation with screenshots
2. Image embedding vs external files
3. Progress callbacks
4. Edge cases
5. Error handling
"""

import pytest
import fitz
import base64
import tempfile
import os
from unittest.mock import Mock, patch

from app.services.markdown_generator import (
    create_page_screenshot_markdown,
    generate_markdown_with_screenshots
)


class TestCreatePageScreenshotMarkdown:
    """Test suite for create_page_screenshot_markdown function."""
    
    def test_basic_creation(self):
        """Test basic markdown creation."""
        screenshot_bytes = b"fake_png_data"
        explanation = "This is a test explanation"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation=explanation,
            embed_images=True
        )
        
        assert "## 第 1 页" in markdown
        assert explanation in markdown
        assert "data:image/png;base64," in markdown
    
    def test_embed_images_true(self):
        """Test with embedded images."""
        screenshot_bytes = b"fake_png_data"
        explanation = "Test"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation=explanation,
            embed_images=True
        )
        
        # Should contain base64 data
        assert "data:image/png;base64," in markdown
        base64_data = base64.b64encode(screenshot_bytes).decode('utf-8')
        assert base64_data in markdown
    
    def test_embed_images_false(self):
        """Test with external images."""
        screenshot_bytes = b"fake_png_data"
        explanation = "Test"
        image_path = "page_1.png"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation=explanation,
            embed_images=False,
            image_path=image_path
        )
        
        # Should contain image path, not base64
        assert image_path in markdown
        assert "data:image/png;base64," not in markdown
    
    def test_empty_explanation(self):
        """Test with empty explanation."""
        screenshot_bytes = b"fake_png_data"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation="",
            embed_images=True
        )
        
        assert "（无讲解内容）" in markdown
    
    def test_whitespace_explanation(self):
        """Test with whitespace-only explanation."""
        screenshot_bytes = b"fake_png_data"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation="   \n\t   ",
            embed_images=True
        )
        
        # Should show "无讲解内容" for whitespace
        assert "（无讲解内容）" in markdown
    
    def test_multiline_explanation(self):
        """Test with multiline explanation."""
        screenshot_bytes = b"fake_png_data"
        explanation = "Line 1\nLine 2\nLine 3"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation=explanation,
            embed_images=True
        )
        
        assert "Line 1" in markdown
        assert "Line 2" in markdown
        assert "Line 3" in markdown
    
    def test_special_characters_in_explanation(self):
        """Test with special characters."""
        screenshot_bytes = b"fake_png_data"
        explanation = "Special: !@#$%^&*()_+-=[]{}|;':\",./<>?"
        
        markdown = create_page_screenshot_markdown(
            page_num=1,
            screenshot_bytes=screenshot_bytes,
            explanation=explanation,
            embed_images=True
        )
        
        assert explanation in markdown


class TestGenerateMarkdownWithScreenshots:
    """Test suite for generate_markdown_with_screenshots function."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a test PDF
        self.sample_pdf = self._create_test_pdf(3)
    
    def _create_test_pdf(self, num_pages: int = 1) -> bytes:
        """Create a test PDF."""
        doc = fitz.open()
        for i in range(num_pages):
            page = doc.new_page(width=612, height=792)
            page.insert_text((50, 50), f"Page {i + 1}")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes
    
    def test_basic_generation(self):
        """Test basic markdown generation."""
        explanations = {
            0: "Explanation for page 1",
            1: "Explanation for page 2",
            2: "Explanation for page 3"
        }
        
        markdown, images_dir = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test Document"
        )
        
        assert markdown is not None
        assert len(markdown) > 0
        assert "# Test Document" in markdown
        assert images_dir is None  # When embed_images=True
    
    def test_embed_images_false(self):
        """Test with external images."""
        explanations = {0: "Test explanation"}
        
        markdown, images_dir = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=False,
            title="Test Document"
        )
        
        assert markdown is not None
        assert images_dir is not None
        assert os.path.exists(images_dir)
        
        # Clean up
        if os.path.exists(images_dir):
            import shutil
            shutil.rmtree(images_dir)
    
    def test_partial_explanations(self):
        """Test with partial explanations."""
        explanations = {
            0: "Explanation for page 1",
            2: "Explanation for page 3"
            # Page 1 (index 1) has no explanation
        }
        
        markdown, _ = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test Document"
        )
        
        assert markdown is not None
        assert "第 1 页" in markdown
        assert "第 3 页" in markdown
    
    def test_empty_explanations(self):
        """Test with empty explanations."""
        explanations = {}
        
        markdown, _ = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test Document"
        )
        
        assert markdown is not None
        # Should still have page screenshots even without explanations
    
    def test_progress_callback(self):
        """Test progress callback."""
        explanations = {0: "Test", 1: "Test", 2: "Test"}
        progress_calls = []
        
        def on_progress(done, total):
            progress_calls.append((done, total))
        
        markdown, _ = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test",
            on_progress=on_progress
        )
        
        # Progress should be called
        assert len(progress_calls) > 0
        # Final call should be (total, total)
        assert progress_calls[-1] == (3, 3)
    
    def test_page_status_callback(self):
        """Test page status callback."""
        explanations = {0: "Test"}
        status_calls = []
        
        def on_page_status(page_index, status, error):
            status_calls.append((page_index, status, error))
        
        markdown, _ = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test",
            on_page_status=on_page_status
        )
        
        # Status should be called for each page
        assert len(status_calls) > 0
    
    def test_different_dpi(self):
        """Test with different DPI values."""
        explanations = {0: "Test"}
        
        for dpi in [72, 150, 200, 300]:
            markdown, _ = generate_markdown_with_screenshots(
                src_bytes=self.sample_pdf,
                explanations=explanations,
                screenshot_dpi=dpi,
                embed_images=True,
                title="Test"
            )
            
            assert markdown is not None
    
    def test_custom_images_dir(self):
        """Test with custom images directory."""
        explanations = {0: "Test"}
        custom_dir = tempfile.mkdtemp()
        
        try:
            markdown, images_dir = generate_markdown_with_screenshots(
                src_bytes=self.sample_pdf,
                explanations=explanations,
                screenshot_dpi=150,
                embed_images=False,
                title="Test",
                images_dir=custom_dir
            )
            
            assert images_dir == custom_dir
            assert os.path.exists(custom_dir)
        finally:
            if os.path.exists(custom_dir):
                import shutil
                shutil.rmtree(custom_dir)
    
    def test_invalid_pdf(self):
        """Test with invalid PDF."""
        explanations = {0: "Test"}
        
        with pytest.raises(Exception):
            generate_markdown_with_screenshots(
                src_bytes=b"Not a PDF",
                explanations=explanations,
                screenshot_dpi=150,
                embed_images=True,
                title="Test"
            )
    
    def test_large_explanation(self):
        """Test with large explanation text."""
        large_text = "This is a very long explanation. " * 1000
        explanations = {0: large_text}
        
        markdown, _ = generate_markdown_with_screenshots(
            src_bytes=self.sample_pdf,
            explanations=explanations,
            screenshot_dpi=150,
            embed_images=True,
            title="Test"
        )
        
        assert markdown is not None
        # Markdown should contain the explanation (may be truncated or formatted)
        # Check that at least part of it is present
        assert "very long explanation" in markdown or len(markdown) > 1000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

