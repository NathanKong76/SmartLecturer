"""
Input validation utilities for the application.

This module provides validation functions to ensure inputs are within
acceptable ranges and prevent runtime errors.
"""

from typing import Tuple, Optional
from . import constants


def validate_font_size(font_size: int) -> Tuple[bool, Optional[str]]:
    """
    Validate font size parameter.
    
    Args:
        font_size: Font size in points
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(font_size, int):
        return False, f"font_size must be an integer, got {type(font_size).__name__}"
    if font_size < constants.MIN_FONT_SIZE:
        return False, f"font_size must be at least {constants.MIN_FONT_SIZE}, got {font_size}"
    if font_size > constants.MAX_FONT_SIZE:
        return False, f"font_size must be at most {constants.MAX_FONT_SIZE}, got {font_size}"
    return True, None


def validate_line_spacing(line_spacing: float) -> Tuple[bool, Optional[str]]:
    """
    Validate line spacing parameter.
    
    Args:
        line_spacing: Line spacing multiplier
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(line_spacing, (int, float)):
        return False, f"line_spacing must be a number, got {type(line_spacing).__name__}"
    if line_spacing <= 0:
        return False, f"line_spacing must be positive, got {line_spacing}"
    if line_spacing > 3.0:
        return False, f"line_spacing should not exceed 3.0, got {line_spacing}"
    return True, None


def validate_right_ratio(right_ratio: float) -> Tuple[bool, Optional[str]]:
    """
    Validate right side ratio parameter.
    
    Args:
        right_ratio: Right side ratio (0.0 to 1.0)
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(right_ratio, (int, float)):
        return False, f"right_ratio must be a number, got {type(right_ratio).__name__}"
    if right_ratio < 0.0:
        return False, f"right_ratio must be non-negative, got {right_ratio}"
    if right_ratio > 1.0:
        return False, f"right_ratio must not exceed 1.0, got {right_ratio}"
    return True, None


def validate_dpi(dpi: int) -> Tuple[bool, Optional[str]]:
    """
    Validate DPI parameter.
    
    Args:
        dpi: Dots per inch
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(dpi, int):
        return False, f"dpi must be an integer, got {type(dpi).__name__}"
    if dpi < constants.MIN_DPI:
        return False, f"dpi must be at least {constants.MIN_DPI}, got {dpi}"
    if dpi > constants.MAX_DPI:
        return False, f"dpi must be at most {constants.MAX_DPI}, got {dpi}"
    return True, None


def validate_column_padding(column_padding: int) -> Tuple[bool, Optional[str]]:
    """
    Validate column padding parameter.
    
    Args:
        column_padding: Column padding in pixels
        
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(column_padding, int):
        return False, f"column_padding must be an integer, got {type(column_padding).__name__}"
    if column_padding < 0:
        return False, f"column_padding must be non-negative, got {column_padding}"
    if column_padding > 50:
        return False, f"column_padding should not exceed 50, got {column_padding}"
    return True, None


def validate_compose_params(
    font_size: int,
    line_spacing: float,
    right_ratio: float,
    column_padding: int = 10
) -> Tuple[bool, Optional[str]]:
    """
    Validate all parameters for compose_pdf function.
    
    Args:
        font_size: Font size in points
        line_spacing: Line spacing multiplier
        right_ratio: Right side ratio
        column_padding: Column padding in pixels
        
    Returns:
        (is_valid, error_message)
    """
    valid, error = validate_font_size(font_size)
    if not valid:
        return False, error
    
    valid, error = validate_line_spacing(line_spacing)
    if not valid:
        return False, error
    
    valid, error = validate_right_ratio(right_ratio)
    if not valid:
        return False, error
    
    valid, error = validate_column_padding(column_padding)
    if not valid:
        return False, error
    
    return True, None

