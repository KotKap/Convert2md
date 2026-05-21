"""
Converter factory and orchestration logic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Tuple
from .converter_strategy import ConverterStrategy
from .pdf_converter import PDFConverter
from .docx_converter import DOCXConverter


class ConverterFactory:
    """Factory for creating appropriate converter strategies."""

    def __init__(self):
        self.converters: list[ConverterStrategy] = [
            PDFConverter(),
            DOCXConverter(),
        ]

    def get_converter(self, file_path: Path) -> ConverterStrategy:
        """
        Get the appropriate converter for the given file.
        
        Args:
            file_path: Path to the file to convert
            
        Returns:
            Appropriate ConverterStrategy instance
            
        Raises:
            ValueError: If no converter supports the file type
        """
        for converter in self.converters:
            if converter.supports(file_path):
                return converter
        
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported formats: PDF, DOCX, DOC"
        )


class DocumentConverter:
    """Main converter orchestrator."""

    def __init__(self):
        self.factory = ConverterFactory()

    def convert(self, input_path: str | Path, no_filter: bool = False) -> Tuple[str, dict]:
        """
        Convert a document to Markdown.
        
        Args:
            input_path: Path to the input document
            
        Returns:
            Tuple of (markdown_content, metadata)
        """
        input_path = Path(input_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        converter = self.factory.get_converter(input_path)
        return converter.convert(input_path, no_filter=no_filter)

    def save_markdown(
        self, 
        markdown_content: str, 
        output_path: str | Path | None = None
    ) -> Path:
        """
        Save markdown content to file.
        
        Args:
            markdown_content: Markdown content to save
            output_path: Output file path (if None, uses input path with .md extension)
            
        Returns:
            Path to the saved file
        """
        output_path = Path(output_path)
        output_path.write_text(markdown_content, encoding='utf-8')
        return output_path
