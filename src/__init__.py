"""
Convert2MD - Convert PDF and DOCX documents to Markdown format.
"""

from .converter import DocumentConverter
from .converter_strategy import ConverterStrategy

__version__ = "1.0.0"
__all__ = ["DocumentConverter", "ConverterStrategy"]
