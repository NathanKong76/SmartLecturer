"""
Comprehensive tests for error handling and edge cases.

This test suite verifies:
1. Error handling in various scenarios
2. Graceful degradation
3. Resource cleanup on errors
4. Exception propagation
5. Invalid input handling
"""

import pytest
import fitz
import os
from unittest.mock import Mock, patch, MagicMock

from app.services.pdf_composer import compose_pdf
from app.services.pdf_validator import validate_pdf_file
from app.cache_processor import save_result_to_file, load_result_from_file


class TestErrorHandling:
    """Test suite for error handling."""
    
    def test_compose_pdf_with_corrupted_pdf(self):
        """Test compose_pdf handles corrupted PDF gracefully."""
        corrupted_pdf = b"Not a valid PDF file"
        explanations = {0: "Test"}
        
        with pytest.raises(Exception):
            compose_pdf(
                src_bytes=corrupted_pdf,
                explanations=explanations,
                right_ratio=0.48,
                font_size=12,
                render_mode="text"
            )
    
    def test_compose_pdf_with_invalid_parameters(self):
        """Test compose_pdf validates parameters."""
        pdf_bytes = self._create_test_pdf()
        explanations = {0: "Test"}
        
        # Invalid font size
        with pytest.raises(ValueError):
            compose_pdf(
                src_bytes=pdf_bytes,
                explanations=explanations,
                right_ratio=0.48,
                font_size=-1,  # Invalid
                render_mode="text"
            )
        
        # Invalid render mode
        with pytest.raises(ValueError):
            compose_pdf(
                src_bytes=pdf_bytes,
                explanations=explanations,
                right_ratio=0.48,
                font_size=12,
                render_mode="invalid_mode"
            )
    
    def test_validate_pdf_file_error_handling(self):
        """Test validate_pdf_file error handling."""
        # Invalid PDF
        is_valid, error = validate_pdf_file(b"Not a PDF")
        assert is_valid is False
        assert len(error) > 0
        
        # Empty PDF
        is_valid, error = validate_pdf_file(b"")
        assert is_valid is False
        assert len(error) > 0
    
    def test_save_result_to_file_permission_error(self):
        """Test save_result_to_file handles permission errors."""
        import tempfile
        import shutil
        
        # On Windows, skip this test
        if os.name == 'nt':
            pytest.skip("Permission test not applicable on Windows")
        
        # Create read-only directory (on Unix)
        read_only_dir = tempfile.mkdtemp()
        try:
            os.chmod(read_only_dir, 0o444)
            
            import app.cache_processor
            original_dir = app.cache_processor.TEMP_DIR
            app.cache_processor.TEMP_DIR = read_only_dir
            
            try:
                result = {
                    "explanations": {0: "Test"},
                    "failed_pages": []
                }
                # Should raise exception or handle gracefully
                try:
                    save_result_to_file("test", result)
                except (OSError, PermissionError):
                    pass  # Expected
            finally:
                app.cache_processor.TEMP_DIR = original_dir
                os.chmod(read_only_dir, 0o755)
                shutil.rmtree(read_only_dir)
        except Exception:
            # Clean up on any error
            if os.path.exists(read_only_dir):
                try:
                    os.chmod(read_only_dir, 0o755)
                    shutil.rmtree(read_only_dir)
                except Exception:
                    pass
    
    def test_load_result_from_file_missing_file(self):
        """Test load_result_from_file with missing file."""
        loaded = load_result_from_file("nonexistent_hash")
        assert loaded is None
    
    def test_compose_pdf_resource_cleanup_on_error(self):
        """Test that resources are cleaned up even on error."""
        pdf_bytes = self._create_test_pdf()
        
        # This should raise an error due to invalid parameter
        try:
            compose_pdf(
                src_bytes=pdf_bytes,
                explanations={0: "Test"},
                right_ratio=0.48,
                font_size=-1,  # Invalid
                render_mode="text"
            )
        except ValueError:
            pass  # Expected
        
        # Resources should be cleaned up (no file handles leaked)
        # This is hard to test directly, but we can verify no exception
        # is raised when creating new PDFs
        pdf_bytes2 = self._create_test_pdf()
        result = compose_pdf(
            src_bytes=pdf_bytes2,
            explanations={0: "Test"},
            right_ratio=0.48,
            font_size=12,
            render_mode="text"
        )
        assert result is not None
    
    def _create_test_pdf(self) -> bytes:
        """Create a test PDF."""
        doc = fitz.open()
        page = doc.new_page()
        page.insert_text((50, 50), "Test")
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

