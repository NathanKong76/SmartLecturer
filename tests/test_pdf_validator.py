"""
Comprehensive tests for PDF Validator.

This test suite verifies:
1. PDF file validation
2. Blank explanation detection
3. JSON loading with various encodings
4. Edge cases and error handling
"""

import pytest
import json
import fitz
from unittest.mock import Mock, patch

from app.services.pdf_validator import (
    validate_pdf_file,
    is_blank_explanation,
    safe_utf8_loads,
    pages_with_blank_explanations
)


class TestValidatePdfFile:
    """Test suite for validate_pdf_file function."""
    
    def test_valid_pdf(self):
        """Test validation of valid PDF."""
        # Create a minimal valid PDF
        pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n179\n%%EOF"
        
        is_valid, error_msg = validate_pdf_file(pdf_bytes)
        
        assert is_valid is True
        assert error_msg == ""
    
    def test_invalid_pdf(self):
        """Test validation of invalid PDF."""
        invalid_pdf = b"This is not a PDF file"
        
        is_valid, error_msg = validate_pdf_file(invalid_pdf)
        
        assert is_valid is False
        assert len(error_msg) > 0
    
    def test_empty_pdf(self):
        """Test validation of empty PDF."""
        empty_pdf = b""
        
        is_valid, error_msg = validate_pdf_file(empty_pdf)
        
        assert is_valid is False
        assert len(error_msg) > 0
    
    def test_pdf_with_zero_pages(self):
        """Test validation of PDF with zero pages."""
        # Create a PDF structure but with 0 pages
        # This is harder to create, so we'll mock it
        with patch('app.services.pdf_validator.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 0
            mock_fitz.open.return_value = mock_doc
            
            is_valid, error_msg = validate_pdf_file(b"fake_pdf")
            
            assert is_valid is False
            assert "没有页面" in error_msg or len(error_msg) > 0
    
    def test_pdf_with_invalid_page(self):
        """Test validation of PDF with invalid page."""
        with patch('app.services.pdf_validator.fitz') as mock_fitz:
            mock_doc = Mock()
            mock_doc.page_count = 1
            mock_page = Mock()
            mock_page.rect.width = 0
            mock_page.rect.height = 0
            mock_doc.load_page.return_value = mock_page
            mock_fitz.open.return_value = mock_doc
            
            is_valid, error_msg = validate_pdf_file(b"fake_pdf")
            
            assert is_valid is False
            assert len(error_msg) > 0


class TestIsBlankExplanation:
    """Test suite for is_blank_explanation function."""
    
    def test_valid_explanation(self):
        """Test that valid explanation is not blank."""
        explanation = "This is a valid explanation with enough content"
        
        assert is_blank_explanation(explanation) is False
    
    def test_short_explanation(self):
        """Test that short explanation is blank."""
        explanation = "Short"
        
        assert is_blank_explanation(explanation, min_chars=10) is True
    
    def test_none_explanation(self):
        """Test that None explanation is blank."""
        assert is_blank_explanation(None) is True
    
    def test_empty_string(self):
        """Test that empty string is blank."""
        assert is_blank_explanation("") is True
    
    def test_whitespace_only(self):
        """Test that whitespace-only string is blank."""
        assert is_blank_explanation("   \n\t  ") is True
    
    def test_punctuation_only(self):
        """Test that punctuation-only string is blank."""
        assert is_blank_explanation("!@#$%^&*()") is True
    
    def test_mixed_content(self):
        """Test explanation with mixed content."""
        explanation = "Valid explanation! @#$%"
        
        assert is_blank_explanation(explanation) is False
    
    def test_custom_min_chars(self):
        """Test with custom minimum characters."""
        explanation = "Short"
        
        assert is_blank_explanation(explanation, min_chars=3) is False
        assert is_blank_explanation(explanation, min_chars=10) is True


class TestSafeUtf8Loads:
    """Test suite for safe_utf8_loads function."""
    
    def test_valid_utf8_json(self):
        """Test loading valid UTF-8 JSON."""
        json_data = {"key": "value", "中文": "测试"}
        json_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        
        result = safe_utf8_loads(json_bytes)
        
        assert result == json_data
    
    def test_valid_ascii_json(self):
        """Test loading valid ASCII JSON."""
        json_data = {"key": "value"}
        json_bytes = json.dumps(json_data).encode('ascii')
        
        result = safe_utf8_loads(json_bytes)
        
        assert result == json_data
    
    def test_utf8_sig_encoding(self):
        """Test loading JSON with UTF-8 BOM."""
        json_data = {"key": "value"}
        json_bytes = json.dumps(json_data).encode('utf-8-sig')
        
        result = safe_utf8_loads(json_bytes)
        
        assert result == json_data
    
    def test_invalid_json(self):
        """Test loading invalid JSON."""
        invalid_json = b"{invalid json}"
        
        with pytest.raises(json.JSONDecodeError):
            safe_utf8_loads(invalid_json)
    
    def test_empty_json(self):
        """Test loading empty JSON."""
        empty_json = b"{}"
        
        result = safe_utf8_loads(empty_json)
        
        assert result == {}
    
    def test_unicode_content(self):
        """Test loading JSON with unicode content."""
        json_data = {
            "chinese": "中文",
            "japanese": "日本語",
            "korean": "한국어",
            "emoji": "😀🎉"
        }
        json_bytes = json.dumps(json_data, ensure_ascii=False).encode('utf-8')
        
        result = safe_utf8_loads(json_bytes)
        
        assert result == json_data


class TestPagesWithBlankExplanations:
    """Test suite for pages_with_blank_explanations function."""
    
    def test_all_valid(self):
        """Test when all explanations are valid."""
        explanations = {
            0: "Valid explanation 1",
            1: "Valid explanation 2",
            2: "Valid explanation 3"
        }
        
        blank_pages = pages_with_blank_explanations(explanations)
        
        assert blank_pages == []
    
    def test_some_blank(self):
        """Test when some explanations are blank."""
        explanations = {
            0: "Valid explanation",
            1: "",  # Blank
            2: "   ",  # Whitespace only
            3: "Valid explanation 2"
        }
        
        blank_pages = pages_with_blank_explanations(explanations)
        
        assert 1 in blank_pages
        assert 2 in blank_pages
        assert 0 not in blank_pages
        assert 3 not in blank_pages
    
    def test_all_blank(self):
        """Test when all explanations are blank."""
        explanations = {
            0: "",
            1: "   ",
            2: "!@#$"
        }
        
        blank_pages = pages_with_blank_explanations(explanations)
        
        assert len(blank_pages) == 3
        assert 0 in blank_pages
        assert 1 in blank_pages
        assert 2 in blank_pages
    
    def test_empty_dict(self):
        """Test with empty dictionary."""
        explanations = {}
        
        blank_pages = pages_with_blank_explanations(explanations)
        
        assert blank_pages == []
    
    def test_custom_min_chars(self):
        """Test with custom minimum characters."""
        explanations = {
            0: "Short",  # 5 chars
            1: "Long enough explanation"  # > 10 chars
        }
        
        blank_pages = pages_with_blank_explanations(explanations, min_chars=10)
        
        assert 0 in blank_pages
        assert 1 not in blank_pages


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

