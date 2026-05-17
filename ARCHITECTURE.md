# Project Architecture

## Overview

Convert2MD is a modular CLI application for converting documents to Markdown. The architecture emphasizes separation of concerns, extensibility, and testability using the Strategy and Factory design patterns.

## Directory Structure

```
Convert2MD/
├── src/                           # Source code
│   ├── __init__.py               # Package initialization
│   ├── converter_strategy.py      # Abstract strategy interface
│   ├── pdf_converter.py           # PDF conversion implementation
│   ├── docx_converter.py          # DOCX conversion implementation
│   ├── converter.py               # Factory & orchestration
│   ├── cli.py                     # CLI interface (Typer)
│   └── utils.py                   # Utility functions
├── tests/                         # Test suite
│   ├── __init__.py               # Test package
│   └── test_convert2md.py        # All tests
├── test_samples/                 # Sample documents (user-added)
├── convert2md.py                 # Entry point
├── setup.py                      # Package configuration
├── requirements.txt              # Production dependencies
├── requirements-dev.txt          # Development dependencies
├── pytest.ini                    # Pytest configuration
├── Makefile                      # Development tasks
├── .gitignore                    # Git ignore rules
├── .mypy.ini                     # Type checking config
├── README.md                     # Project overview
├── QUICKSTART.md                 # Getting started
├── CONTRIBUTING.md               # Developer guide
├── TEST_CHECKLIST.md             # Test scenarios
├── CHANGELOG.md                  # Version history
└── ARCHITECTURE.md              # This file
```

## Core Modules

### 1. converter_strategy.py
**Purpose**: Define the converter interface

```python
class ConverterStrategy(ABC):
    """Abstract base class for converters."""
    
    @abstractmethod
    def convert(self, input_path: Path) -> Tuple[str, dict]:
        """Convert document to Markdown."""
    
    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """Check if this converter supports the file type."""
```

**Key Classes**:
- `ConverterStrategy`: Abstract base class
- `ConversionMetadata`: Metadata holder for conversion results

### 2. pdf_converter.py
**Purpose**: Convert PDF documents to Markdown

**Implementation**:
- Uses Docling (IBM) for advanced PDF parsing
- Extracts images to `picture_<filename>/` directory
- Filters noise (headers, footers, page numbers)
- Converts formulas to LaTeX format

**Key Methods**:
- `convert()`: Main conversion method
- `_process_images()`: Handle image extraction
- `_filter_noise()`: Remove artifacts
- `_ensure_latex_format()`: Format mathematical expressions

### 3. docx_converter.py
**Purpose**: Convert DOCX/DOC documents to Markdown

**Implementation**:
- Uses Pandoc via pypandoc for conversion
- Extracts images to `picture_<filename>/` directory
- Flattens nested Pandoc `media/` output into `picture_<filename>/`
- Converts embedded vector graphics (EMF/WMF) to PNG using Inkscape first, then ImageMagick
- Updates image paths to be relative
- Handles complex formatting

**Key Methods**:
- `convert()`: Main conversion method
- `_convert_with_pandoc()`: Pandoc integration
- `_update_image_paths()`: Ensure relative paths
- `_filter_noise()`: Remove artifacts

### 4. converter.py
**Purpose**: Factory pattern and orchestration

```python
class ConverterFactory:
    """Selects appropriate converter based on file type."""
    
    def get_converter(self, file_path: Path) -> ConverterStrategy:
        """Get converter for file type."""

class DocumentConverter:
    """Main converter orchestrator."""
    
    def convert(self, input_path: str) -> Tuple[str, dict]:
        """Convert a document."""
    
    def save_markdown(self, content: str, path: str) -> Path:
        """Save markdown to file."""
```

### 5. cli.py
**Purpose**: Command-line interface using Typer

**Commands**:
- `convert`: Single file conversion
- `batch`: Batch conversion with filtering and recursion

**Features**:
- Rich terminal output (colors, progress bars)
- Error handling with user-friendly messages
- Verbose mode for debugging
- Progress tracking

### 6. utils.py
**Purpose**: Utility functions

**Functions**:
- `get_supported_formats()`: List of supported file types
- `is_supported_file()`: Check if file is supported
- `get_output_md_path()`: Calculate output path
- `get_picture_dir_path()`: Calculate picture directory path
- `cleanup_conversion_artifacts()`: Remove generated files

## Data Flow

### Single File Conversion
```
Input File (PDF/DOCX)
        ↓
[CLI.convert command]
        ↓
[DocumentConverter.convert()]
        ↓
[ConverterFactory.get_converter()]
        ↓
[PDFConverter / DOCXConverter]
        ↓
[Extract text, images, metadata]
        ↓
[Filter noise, format formulas]
        ↓
[DocumentConverter.save_markdown()]
        ↓
Output Files:
  - document.md
  - picture_document/
```

### Batch Conversion
```
Input Directory
        ↓
[CLI.batch command]
        ↓
[Find matching files with pattern]
        ↓
[For each file:]
  ├── [Convert using DocumentConverter]
  ├── [Create output directory structure]
  └── [Save to output location]
        ↓
[Progress tracking & error handling]
        ↓
Summary Report
```

## Design Patterns

### Strategy Pattern
Defines a family of conversion algorithms:

```python
# Client code (CLI) is independent of converter implementation
converter = factory.get_converter(file_path)
markdown, metadata = converter.convert(file_path)
```

**Benefits**:
- Easy to add new formats (RTF, HTML, etc.)
- Converters can be tested independently
- Encapsulation of format-specific logic

### Factory Pattern
Creates appropriate converter instances:

```python
class ConverterFactory:
    def get_converter(self, file_path):
        for converter in self.converters:
            if converter.supports(file_path):
                return converter
```

**Benefits**:
- Decouples file type detection from conversion
- Centralized converter registration
- Easy to extend with new formats

### Separation of Concerns

```
┌─────────────────────────────────────┐
│ CLI Interface (cli.py)              │  User Input/Output
├─────────────────────────────────────┤
│ Converter Orchestration (converter)  │  High-level workflow
├─────────────────────────────────────┤
│ Strategy Implementations            │  Format-specific logic
│ ├─ PDFConverter                     │
│ ├─ DOCXConverter                    │
│ └─ [Future converters]              │
├─────────────────────────────────────┤
│ Utilities (utils.py)                │  Helper functions
└─────────────────────────────────────┘
```

## Extension Points

### Adding a New Format (e.g., RTF)

1. **Create Converter Class**:
```python
# src/rtf_converter.py
class RTFConverter(ConverterStrategy):
    def supports(self, file_path: Path) -> bool:
        return file_path.suffix.lower() == '.rtf'
    
    def convert(self, input_path: Path) -> Tuple[str, dict]:
        # RTF-specific logic
        pass
```

2. **Register in Factory**:
```python
# src/converter.py
class ConverterFactory:
    def __init__(self):
        self.converters = [
            PDFConverter(),
            DOCXConverter(),
            RTFConverter(),  # Add here
        ]
```

3. **Add Tests**:
```python
# tests/test_convert2md.py
class TestRTFConverter:
    def test_rtf_support(self):
        converter = RTFConverter()
        assert converter.supports(Path("test.rtf"))
```

### Adding a GUI (Stage 2)

The architecture supports GUI integration without modifying core converters:

```python
# stage2/gui.py
from src.converter import DocumentConverter

class MainWindow:
    def __init__(self):
        self.converter = DocumentConverter()  # Reuse core logic
    
    def convert_file(self, path):
        markdown, metadata = self.converter.convert(path)
        self.show_preview(markdown)
```

## Testing Architecture

### Test Organization

```
tests/
└── test_convert2md.py
    ├── TestStructuralRequirements    (4 tests)
    ├── TestContentRequirements       (5 tests)
    ├── TestResourceHandling          (3 tests)
    ├── TestPDFConverter             (2 tests)
    ├── TestDOCXConverter            (2 tests)
    └── TestConverterFactory         (2 tests)
```

### Test Strategy

- **Unit Tests**: Individual components (converters, factory)
- **Integration Tests**: Full conversion pipeline
- **Behavior Tests**: Verify output format and content

### Example Test Structure

```python
@pytest.fixture
def converter():
    return DocumentConverter()

class TestPDFConverter:
    def test_pdf_conversion(self, converter):
        # Arrange
        input_file = Path("test.pdf")
        
        # Act
        markdown, metadata = converter.convert(input_file)
        
        # Assert
        assert markdown is not None
        assert isinstance(metadata, dict)
```

## Dependencies

### Core Dependencies
- **docling**: Advanced PDF parsing with formula support
- **pypandoc**: DOCX conversion via Pandoc
- **typer**: Type-safe CLI framework
- **rich**: Rich terminal output with colors and progress

### Development Dependencies
- **pytest**: Testing framework
- **pytest-cov**: Coverage reporting
- **mypy**: Static type checking
- **black**: Code formatting
- **flake8**: Linting

### Why These Choices?

| Package | Reason |
|---------|--------|
| Docling | Industry-leading PDF parser with ML capabilities |
| pypandoc | Most robust DOCX converter (uses Pandoc) |
| Typer | Modern, type-safe CLI with auto-docs |
| Rich | Beautiful terminal UI with minimal code |
| pytest | Most popular Python testing framework |

## Performance Considerations

### Memory Management
- Stream-based processing for large files
- Image processing in chunks
- Cleanup of temporary files

### Optimization Points
1. Caching converter instances
2. Lazy loading of document engines
3. Parallel batch processing (future)

### Profiling

To profile conversion:
```bash
python -m cProfile -s cumtime convert2md.py convert large.pdf
```

## Error Handling

### Graceful Degradation
```python
try:
    markdown_content = converter.convert(input_path)
except FileNotFoundError:
    console.print("File not found")
except ValueError as e:
    console.print(f"Unsupported format: {e}")
except Exception as e:
    console.print(f"Conversion failed: {e}")
```

### Error Recovery
- Clean up partial outputs on failure
- Provide actionable error messages
- Log detailed error information in verbose mode

## Future Architectural Improvements

1. **Plugin System**: Allow third-party converters
2. **Async Processing**: Use asyncio for batch conversion
3. **Caching**: Cache conversion results
4. **Configuration**: Support config files
5. **Event System**: Emit events during conversion
6. **Database**: Track conversion history

## Deployment

### Package Distribution
```bash
# Build distribution
python setup.py sdist bdist_wheel

# Upload to PyPI
twine upload dist/*

# Install from PyPI
pip install convert2md
```

### macOS App (Stage 2)
```bash
# Create app bundle
pyinstaller --onedir convert2md.spec

# Create DMG installer
create-dmg Convert2MD.app Convert2MD.dmg
```

## Maintenance

### Code Quality
- Type hints on all public APIs
- Comprehensive docstrings
- Test coverage > 80%
- Linting with flake8

### Documentation
- README for overview
- Docstrings for code
- Test checklist for verification
- Contributing guide for developers

### Version Control
- Semantic versioning (MAJOR.MINOR.PATCH)
- Detailed changelog
- Release notes for each version

---

**See also**:
- [README.md](README.md) - Project overview
- [CONTRIBUTING.md](CONTRIBUTING.md) - Development guide
- [TEST_CHECKLIST.md](TEST_CHECKLIST.md) - Test scenarios
