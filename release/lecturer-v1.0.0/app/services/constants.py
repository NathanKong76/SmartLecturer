"""
Constants used across the application.

This module centralizes all magic numbers and configuration values
to improve maintainability and consistency.
"""

# PDF Composition Constants
PDF_WIDTH_MULTIPLIER = 3  # New PDF width = original width * this value
COLUMN_SPACING_PT = 12  # Space between columns in points
DEFAULT_MARGIN_X_PT = 25  # Horizontal margin in points
DEFAULT_MARGIN_Y_PT = 40  # Vertical margin in points
MAX_COLUMNS = 3  # Maximum number of columns for explanations

# Text Layout Constants
CHAR_WIDTH_FACTOR_CJK = 0.55  # Character width factor for CJK fonts
CHAR_WIDTH_FACTOR_LATIN = 0.45  # Character width factor for Latin fonts
MARKDOWN_LINE_HEIGHT_MULTIPLIER = 1.15  # Extra spacing for markdown elements
CAPACITY_FACTOR = 0.5  # Conservative capacity estimation factor
SMALL_CAPACITY_FACTOR = 0.7  # More generous factor for small capacities (< 50 chars)

# Font Constants
DEFAULT_FONT_SIZE = 12  # Default font size in points
MIN_FONT_SIZE = 8  # Minimum font size
MAX_FONT_SIZE = 20  # Maximum font size
DEFAULT_LINE_SPACING = 1.2  # Default line spacing multiplier

# Rendering Constants
DEFAULT_DPI = 180  # Default DPI for page rendering (for LLM)
DEFAULT_SCREENSHOT_DPI = 150  # Default DPI for screenshots
MIN_DPI = 96  # Minimum DPI
MAX_DPI = 300  # Maximum DPI

# Continuation Pages Constants
MAX_CONTINUATION_DEPTH = 5  # Maximum depth for continuation pages
CONTINUATION_PAGE_SUFFIX = "续"  # Suffix for continuation pages

# File Upload Constants
MAX_FILES_PER_BATCH = 20  # Maximum number of files in a batch
MAX_FILE_SIZE_MB = 50  # Maximum file size in MB
MAX_TOTAL_SIZE_MB = 200  # Maximum total size in MB

# API Rate Limiting Constants (defaults)
DEFAULT_RPM_LIMIT = 150  # Default requests per minute
DEFAULT_TPM_BUDGET = 2000000  # Default tokens per minute
DEFAULT_RPD_LIMIT = 10000  # Default requests per day

# Cache Constants
CACHE_DIR_NAME = "pdf_processor_cache"  # Cache directory name
CACHE_EXPIRY_DAYS = 7  # Cache expiry time in days

