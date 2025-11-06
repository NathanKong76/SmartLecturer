from __future__ import annotations

from typing import List, Optional

import fitz  # PyMuPDF

from . import constants


def _smart_text_layout(text: str, column_rects: List[fitz.Rect], font_size: int, fontfile: Optional[str],
                      fontname: str, render_mode: str, line_spacing: float) -> List[str]:
    """
    Distribute text among columns with improved overflow handling.
    
    Args:
        text: Input text to distribute
        column_rects: List of column rectangles
        font_size: Font size in points
        fontfile: Path to font file
        fontname: Font name
        render_mode: Rendering mode ("text", "markdown", etc.)
        line_spacing: Line spacing multiplier
        
    Returns:
        List of text parts for each column
    """
    def estimate_text_capacity(rect: fitz.Rect) -> int:
        """Estimate text capacity for a given rectangle with conservative calculation."""
        if not rect or rect.width <= 0 or rect.height <= 0:
            return 0
            
        rect_width, rect_height = rect.width, rect.height
        
        # Conservative character width estimation
        char_width_factor = constants.CHAR_WIDTH_FACTOR_CJK if fontname != "helv" else constants.CHAR_WIDTH_FACTOR_LATIN
        char_width_divisor = font_size * char_width_factor
        if char_width_divisor > 0:
            chars_per_line = max(int(rect_width / char_width_divisor), 1)
        else:
            chars_per_line = 1

        # Line height calculation with safety margin
        actual_line_height = font_size * max(1.0, line_spacing)
        if render_mode == "markdown":
            actual_line_height *= constants.MARKDOWN_LINE_HEIGHT_MULTIPLIER  # Extra spacing for markdown elements

        actual_line_height = max(actual_line_height, font_size * 0.6) if font_size > 0 else 1.0

        if actual_line_height > 0:
            lines_per_rect = max(int(rect_height / actual_line_height), 1)
        else:
            lines_per_rect = 1

        # Conservative capacity factor for significant safety margin
        base_capacity = chars_per_line * lines_per_rect * constants.CAPACITY_FACTOR

        # For small capacities, use more generous factor to avoid edge cases
        SMALL_CAPACITY_THRESHOLD = 50  # Threshold for small capacity detection
        if base_capacity < SMALL_CAPACITY_THRESHOLD:
            return max(int(chars_per_line * lines_per_rect * constants.SMALL_CAPACITY_FACTOR), 1)
        else:
            return int(base_capacity)

    column_capacities = [estimate_text_capacity(rect) for rect in column_rects]
    text_parts = ["" for _ in column_rects]
    remaining_text = text
    total_capacity = max(sum(column_capacities), 1)

    # Improved text distribution algorithm with better balance and safety
    for idx, capacity in enumerate(column_capacities):
        if not remaining_text:
            break

        # For the last column, use extremely conservative allocation
        if idx == len(column_capacities) - 1:
            # Extremely conservative: only allow up to 85% of capacity to prevent overflow
            if len(remaining_text) > capacity * 0.85:
                # Try to find a good split point
                alloc_limit = int(capacity * 0.80)  # Use 80% of capacity for safety
                alloc_text = remaining_text[:alloc_limit]
                split_pos = len(alloc_text)
                # Find nearest sentence boundary with better threshold
                boundary_threshold = int(capacity * 0.70)
                for sep in ['。', '！', '？', '.', '!', '?', '\n\n', '\n']:
                    pos = alloc_text.rfind(sep)
                    if pos > boundary_threshold:
                        split_pos = pos + 1
                        break
                text_parts[idx] = remaining_text[:split_pos]
                remaining_text = remaining_text[split_pos:]
            else:
                # Only allocate if well within capacity
                text_parts[idx] = remaining_text
                remaining_text = ""
            break

        # Calculate proportional allocation with adaptive approach
        remaining_capacity = sum(column_capacities[idx:])
        if remaining_capacity <= 0:
            break
            
        proportional = max(int(len(remaining_text) * (capacity / remaining_capacity)), 1)

        # Adaptive allocation factor based on remaining capacity
        capacity_utilization = capacity / max(sum(column_capacities), 1)
        if capacity_utilization > 0.4:
            # Large capacity allocation: use 0.70 (conservative)
            alloc_factor = 0.70
        elif capacity_utilization > 0.2:
            # Medium capacity allocation: use 0.75
            alloc_factor = 0.75
        else:
            # Small capacity allocation: use 0.80 (more generous)
            alloc_factor = 0.80

        alloc_chars = int(min(max(int(capacity * alloc_factor), proportional), len(remaining_text)))

        alloc_text = remaining_text[:alloc_chars]
        split_pos = alloc_chars
        # Find best split point near the allocation point with better boundary detection
        threshold = int(alloc_chars * 0.70)
        # Enhanced boundary characters with better punctuation
        for sep in ['。', '！', '？', '；', '：', '，', '.', '!', '?', ';', ':', ',', '\n\n', '\n', ' ']:
            pos = alloc_text.rfind(sep)
            if pos > threshold:
                split_pos = pos + 1
                break

        text_parts[idx] = remaining_text[:split_pos]
        remaining_text = remaining_text[split_pos:]

    # If there's still remaining text after distribution, add it to the last column
    # but mark it as overflow for continuation page processing
    if remaining_text and text_parts:
        # Add remaining text to the last column for overflow handling
        text_parts[-1] += "\n\n" + remaining_text

    return text_parts