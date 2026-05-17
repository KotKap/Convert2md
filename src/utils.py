"""
Utility functions for document conversion.
"""

from pathlib import Path
import logging
from typing import List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def get_supported_formats() -> List[str]:
    """Get list of supported file formats."""
    return ['.pdf', '.docx', '.doc']


def is_supported_file(file_path: Path) -> bool:
    """Check if a file format is supported."""
    return file_path.suffix.lower() in get_supported_formats()


def get_output_md_path(input_path: Path) -> Path:
    """Get the output markdown path for an input document."""
    return input_path.parent / f"{input_path.stem}.md"


def get_picture_dir_path(input_path: Path) -> Path:
    """Get the picture directory path for an input document."""
    return input_path.parent / f"picture_{input_path.stem}"


def cleanup_conversion_artifacts(input_path: Path) -> None:
    """
    Clean up generated files for a document.
    
    Args:
        input_path: Path to the original document
    """
    md_path = get_output_md_path(input_path)
    picture_dir = get_picture_dir_path(input_path)
    
    # Remove markdown file
    if md_path.exists():
        md_path.unlink()
        logger.info(f"Removed: {md_path}")
    
    # Remove picture directory
    if picture_dir.exists():
        import shutil
        shutil.rmtree(picture_dir)
        logger.info(f"Removed: {picture_dir}")
