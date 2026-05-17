"""
Setup configuration for Convert2MD package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text(encoding="utf-8") if readme_path.exists() else ""

setup(
    name="convert2md",
    version="1.0.0",
    description="Convert PDF and DOCX documents to Markdown format",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/convert2md",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.10",
    install_requires=[
        "docling>=1.0.0",
        "pypandoc>=1.11",
        "PyMuPDF>=1.24.0",
        "typer>=0.9.0",
        "rich>=13.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.4.0",
            "pytest-cov>=4.1.0",
            "mypy>=1.5.0",
        ],
        "gui": [
            "PySide6>=6.6.0",
            "Pillow>=10.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "convert2md=cli:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Office/Business",
        "Topic :: Text Processing :: Markup",
    ],
    keywords="pdf docx markdown conversion document",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/convert2md/issues",
        "Source": "https://github.com/yourusername/convert2md",
    },
)
