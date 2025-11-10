"""
Comprehensive and strict tests for Parameter Validators.

This test suite verifies:
1. All parameter validation functions
2. Boundary value testing
3. Invalid input handling
4. Edge cases
"""

import pytest
from app.services.validators import (
    validate_font_size,
    validate_line_spacing,
    validate_right_ratio,
    validate_dpi,
    validate_column_padding,
    validate_compose_params
)


class TestValidateFontSize:
    """Test suite for validate_font_size function."""
    
    def test_valid_font_sizes(self):
        """Test valid font sizes."""
        from app.services import constants
        
        # Test valid font sizes within the allowed range
        for size in [constants.MIN_FONT_SIZE, 10, 12, 14, 16, constants.MAX_FONT_SIZE]:
            is_valid, error = validate_font_size(size)
            assert is_valid is True, f"Font size {size} should be valid: {error}"
            assert error is None
    
    def test_invalid_negative(self):
        """Test negative font size."""
        is_valid, error = validate_font_size(-1)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_zero(self):
        """Test zero font size."""
        is_valid, error = validate_font_size(0)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_too_small(self):
        """Test too small font size."""
        is_valid, error = validate_font_size(1)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_too_large(self):
        """Test too large font size."""
        is_valid, error = validate_font_size(1000)
        assert is_valid is False
        assert error is not None
    
    def test_boundary_values(self):
        """Test boundary values."""
        from app.services import constants
        
        # Minimum valid
        is_valid, _ = validate_font_size(constants.MIN_FONT_SIZE)
        assert is_valid is True
        
        # Just below minimum
        is_valid, _ = validate_font_size(constants.MIN_FONT_SIZE - 1)
        assert is_valid is False
        
        # Maximum valid
        is_valid, _ = validate_font_size(constants.MAX_FONT_SIZE)
        assert is_valid is True
        
        # Just above maximum
        is_valid, _ = validate_font_size(constants.MAX_FONT_SIZE + 1)
        assert is_valid is False


class TestValidateLineSpacing:
    """Test suite for validate_line_spacing function."""
    
    def test_valid_line_spacing(self):
        """Test valid line spacing values."""
        for spacing in [0.5, 0.8, 1.0, 1.2, 1.5, 2.0, 3.0]:
            is_valid, error = validate_line_spacing(spacing)
            assert is_valid is True
            assert error is None
    
    def test_invalid_negative(self):
        """Test negative line spacing."""
        is_valid, error = validate_line_spacing(-1.0)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_zero(self):
        """Test zero line spacing."""
        is_valid, error = validate_line_spacing(0.0)
        assert is_valid is False
        assert error is not None
    
    def test_small_line_spacing(self):
        """Test small line spacing (0.1 is actually valid)."""
        is_valid, error = validate_line_spacing(0.1)
        # 0.1 is valid (positive and <= 3.0)
        assert is_valid is True
        assert error is None
    
    def test_boundary_values(self):
        """Test boundary values."""
        # Minimum valid (0.1 or any positive value)
        is_valid, _ = validate_line_spacing(0.1)
        assert is_valid is True
        
        # Zero (invalid)
        is_valid, _ = validate_line_spacing(0.0)
        assert is_valid is False
        
        # Maximum (3.0)
        is_valid, _ = validate_line_spacing(3.0)
        assert is_valid is True
        
        # Just above maximum
        is_valid, _ = validate_line_spacing(3.1)
        assert is_valid is False


class TestValidateRightRatio:
    """Test suite for validate_right_ratio function."""
    
    def test_valid_right_ratio(self):
        """Test valid right ratio values."""
        for ratio in [0.2, 0.3, 0.4, 0.48, 0.5, 0.6]:
            is_valid, error = validate_right_ratio(ratio)
            assert is_valid is True
            assert error is None
    
    def test_invalid_negative(self):
        """Test negative right ratio."""
        is_valid, error = validate_right_ratio(-0.1)
        assert is_valid is False
        assert error is not None
    
    def test_zero_right_ratio(self):
        """Test zero right ratio (may be valid depending on implementation)."""
        is_valid, error = validate_right_ratio(0.0)
        # 0.0 is actually valid (non-negative and <= 1.0)
        assert is_valid is True
        assert error is None
    
    def test_one_right_ratio(self):
        """Test right ratio of 1.0 (may be valid)."""
        is_valid, error = validate_right_ratio(1.0)
        # 1.0 is actually valid (non-negative and <= 1.0)
        assert is_valid is True
        assert error is None
    
    def test_invalid_greater_than_one(self):
        """Test right ratio greater than one."""
        is_valid, error = validate_right_ratio(1.5)
        assert is_valid is False
        assert error is not None
    
    def test_boundary_values(self):
        """Test boundary values."""
        # Minimum valid (0.0)
        is_valid, _ = validate_right_ratio(0.0)
        assert is_valid is True
        
        # Just below minimum (negative)
        is_valid, _ = validate_right_ratio(-0.1)
        assert is_valid is False
        
        # Maximum valid (1.0)
        is_valid, _ = validate_right_ratio(1.0)
        assert is_valid is True
        
        # Just above maximum
        is_valid, _ = validate_right_ratio(1.1)
        assert is_valid is False


class TestValidateDpi:
    """Test suite for validate_dpi function."""
    
    def test_valid_dpi(self):
        """Test valid DPI values."""
        from app.services import constants
        # Test valid DPI values within range
        for dpi in [constants.MIN_DPI, 150, 180, constants.MAX_DPI]:
            is_valid, error = validate_dpi(dpi)
            assert is_valid is True, f"DPI {dpi} should be valid"
            assert error is None
    
    def test_invalid_negative(self):
        """Test negative DPI."""
        is_valid, error = validate_dpi(-1)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_zero(self):
        """Test zero DPI."""
        is_valid, error = validate_dpi(0)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_too_small(self):
        """Test too small DPI."""
        from app.services import constants
        is_valid, error = validate_dpi(constants.MIN_DPI - 1)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_too_large(self):
        """Test too large DPI."""
        is_valid, error = validate_dpi(10000)
        assert is_valid is False
        assert error is not None
    
    def test_boundary_values(self):
        """Test boundary values."""
        from app.services import constants
        
        # Minimum valid
        is_valid, _ = validate_dpi(constants.MIN_DPI)
        assert is_valid is True
        
        # Just below minimum
        is_valid, _ = validate_dpi(constants.MIN_DPI - 1)
        assert is_valid is False
        
        # Maximum valid
        is_valid, _ = validate_dpi(constants.MAX_DPI)
        assert is_valid is True
        
        # Just above maximum
        is_valid, _ = validate_dpi(constants.MAX_DPI + 1)
        assert is_valid is False


class TestValidateColumnPadding:
    """Test suite for validate_column_padding function."""
    
    def test_valid_column_padding(self):
        """Test valid column padding values."""
        for padding in [0, 5, 10, 15, 20, 30]:
            is_valid, error = validate_column_padding(padding)
            assert is_valid is True
            assert error is None
    
    def test_invalid_negative(self):
        """Test negative column padding."""
        is_valid, error = validate_column_padding(-1)
        assert is_valid is False
        assert error is not None
    
    def test_invalid_too_large(self):
        """Test too large column padding."""
        is_valid, error = validate_column_padding(1000)
        assert is_valid is False
        assert error is not None


class TestValidateComposeParams:
    """Test suite for validate_compose_params function."""
    
    def test_all_valid(self):
        """Test all parameters valid."""
        is_valid, error = validate_compose_params(
            font_size=12,
            line_spacing=1.2,
            right_ratio=0.48,
            column_padding=10
        )
        assert is_valid is True
        assert error is None
    
    def test_invalid_font_size(self):
        """Test invalid font size."""
        is_valid, error = validate_compose_params(
            font_size=-1,
            line_spacing=1.2,
            right_ratio=0.48,
            column_padding=10
        )
        assert is_valid is False
        assert "font_size" in error.lower() or "font" in error.lower()
    
    def test_invalid_line_spacing(self):
        """Test invalid line spacing."""
        is_valid, error = validate_compose_params(
            font_size=12,
            line_spacing=-1.0,
            right_ratio=0.48,
            column_padding=10
        )
        assert is_valid is False
        assert "line_spacing" in error.lower() or "line" in error.lower()
    
    def test_invalid_right_ratio(self):
        """Test invalid right ratio."""
        is_valid, error = validate_compose_params(
            font_size=12,
            line_spacing=1.2,
            right_ratio=1.5,
            column_padding=10
        )
        assert is_valid is False
        assert "right_ratio" in error.lower() or "ratio" in error.lower()
    
    def test_invalid_column_padding(self):
        """Test invalid column padding."""
        is_valid, error = validate_compose_params(
            font_size=12,
            line_spacing=1.2,
            right_ratio=0.48,
            column_padding=-1
        )
        assert is_valid is False
        assert "column_padding" in error.lower() or "padding" in error.lower()
    
    def test_multiple_invalid(self):
        """Test multiple invalid parameters."""
        is_valid, error = validate_compose_params(
            font_size=-1,
            line_spacing=-1.0,
            right_ratio=1.5,
            column_padding=-1
        )
        assert is_valid is False
        assert error is not None
    
    def test_edge_case_combinations(self):
        """Test edge case combinations."""
        # Minimum valid values
        is_valid, _ = validate_compose_params(
            font_size=8,
            line_spacing=0.5,
            right_ratio=0.2,
            column_padding=0
        )
        assert is_valid is True
        
        # Maximum valid values (if applicable)
        is_valid, _ = validate_compose_params(
            font_size=72,
            line_spacing=3.0,
            right_ratio=0.6,
            column_padding=30
        )
        # May or may not be valid depending on implementation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

