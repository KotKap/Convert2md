"""
Configuration and constants for Convert2MD.
"""

from pathlib import Path

# Project metadata
PROJECT_NAME = "Convert2MD"
VERSION = "1.0.0"
AUTHOR = "Development Team"
DESCRIPTION = "Convert PDF and DOCX documents to Markdown format"

# Supported file formats
SUPPORTED_FORMATS = {
    '.pdf': 'PDF Document',
    '.docx': 'Microsoft Word Document',
    '.doc': 'Microsoft Word 97-2003 Document',
}

# Image directory naming
IMAGE_DIR_PREFIX = "picture_"

# Conversion settings
class ConversionSettings:
    """Default conversion settings."""
    
    # Image extraction
    EXTRACT_IMAGES = True
    IMAGE_FORMATS = ['.png', '.jpg', '.jpeg', '.gif', '.webp']
    
    # Formula handling
    PRESERVE_FORMULAS = True
    FORMULA_FORMAT = 'latex'  # 'latex' or 'mathml'
    
    # Noise filtering
    FILTER_PAGE_NUMBERS = True
    FILTER_HEADERS_FOOTERS = True
    REMOVE_EXCESS_WHITESPACE = True
    
    # Output
    MARKDOWN_FLAVOR = 'gfm'  # GitHub Flavored Markdown
    RELATIVE_PATHS = True
    ENCODING = 'utf-8'
    
    # PDF-specific
    PDF_MAX_PAGES = None  # None for unlimited
    PDF_SEMANTIC_FILTERING = True
    
    # DOCX-specific
    DOCX_PRESERVE_TABLES = True
    DOCX_PRESERVE_FORMATTING = True
    
    # Batch processing
    BATCH_PARALLEL_WORKERS = 1  # Single-threaded for now
    BATCH_CONTINUE_ON_ERROR = True

# Logging configuration
class LoggingConfig:
    """Logging settings."""
    
    LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

# Default directories (relative to project root)
DEFAULTS = {
    'output_dir': '.',
    'temp_dir': './.convert2md_temp/',
    'log_dir': './logs/',
}

# Limitations and constraints
LIMITS = {
    'max_pdf_size_mb': 500,
    'max_docx_size_mb': 100,
    'max_images_per_document': 1000,
    'max_batch_files': 10000,
}

# Exit codes
EXIT_CODES = {
    'SUCCESS': 0,
    'GENERAL_ERROR': 1,
    'COMMAND_LINE_ERROR': 2,
    'FILE_NOT_FOUND': 3,
    'UNSUPPORTED_FORMAT': 4,
    'CONVERSION_ERROR': 5,
}
