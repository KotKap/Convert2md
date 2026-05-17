"""
Base converter strategy interface and utility classes.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple


class ConverterStrategy(ABC):
    """Abstract base class for document conversion strategies."""

    @abstractmethod
    def convert(self, input_path: Path, no_filter: bool = False) -> Tuple[str, dict]:
        """
        Convert a document to Markdown.
        
        Args:
            input_path: Path to the input document
            
        Returns:
            Tuple of (markdown_content, metadata)
            metadata contains 'images' - list of extracted image paths
        """
        pass

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this strategy supports the given file type."""
        pass


class ConversionMetadata:
    """Metadata about conversion process."""

    def __init__(self):
        self.images: list[str] = []
        self.tables: int = 0
        self.formulas: int = 0
        self.pages: int = 0

    def to_dict(self) -> dict:
        """Convert metadata to dictionary."""
        return {
            'images': self.images,
            'tables': self.tables,
            'formulas': self.formulas,
            'pages': self.pages,
        }
