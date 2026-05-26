# Convert2MD - Document to Markdown Converter

A powerful CLI application for converting PDF and DOCX/DOC documents to Markdown format with intelligent image extraction, formula preservation, and noise filtering.

## Features

- **PDF Support**: Convert PDF documents using Docling with advanced parsing capabilities
- **DOCX/DOC Support**: Convert Microsoft Word documents via Pandoc
- **DOCX image handling**: Flatten Pandoc `media/` output into `picture_*` directories and convert EMF/WMF vectors to PNG
- **Image Extraction**: Automatically extract and organize images in dedicated `picture_*` directories
- **Relative Links**: Generate Markdown with relative image paths for portability
- **Formula Preservation**: Convert mathematical expressions to LaTeX format ($...$, $$...$$)
- **Noise Filtering**: Automatically remove headers, footers, and page numbers
- **Batch Processing**: Convert multiple documents in a single command
- **Recursive Processing**: Handle directory trees with optional recursion
- **Verbose Output**: Detailed logging and metadata reporting

## Project Structure

```
Convert2MD/
├── src/
│   ├── __init__.py              # Package initialization
│   ├── converter_strategy.py    # Abstract converter interface
│   ├── pdf_converter.py         # PDF-to-Markdown conversion logic
│   ├── docx_converter.py        # DOCX-to-Markdown conversion logic
│   ├── converter.py             # Converter factory and orchestration
│   └── cli.py                   # CLI interface (Typer)
├── tests/
│   └── test_convert2md.py       # Comprehensive test suite
├── test_samples/                # Test documents (to be added)
├── convert2md.py                # Main entry point
├── requirements.txt             # Python dependencies
└── README.md                    # This file
```

## Installation

### Prerequisites

- **Python 3.10+**
- **Pandoc** (required for DOCX conversion): [Install Pandoc](https://pandoc.org/installing.html)
- **Inkscape** or **ImageMagick** (required separately for DOCX vector image conversion, e.g. EMF/WMF to PNG)

### Setup

1. Clone the repository or extract the project
2. Create a virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Verify installation:
   ```bash
   python convert2md.py --help
   ```

## Usage

### Convert Single File

Convert a PDF document to Markdown:
```bash
python convert2md.py convert report.pdf
```

Convert with custom output path:
```bash
python convert2md.py convert document.docx --output myfile.md
```

Enable verbose output:
```bash
python convert2md.py convert report.pdf --verbose
```

### Batch Convert

Convert all PDFs in a directory:
```bash
python convert2md.py batch ./documents/
```

Convert specific file types:
```bash
python convert2md.py batch ./documents/ --pattern "*.pdf"
```

Recursive batch conversion:
```bash
python convert2md.py batch ./documents/ --recursive
```

With custom output directory:
```bash
python convert2md.py batch ./input/ --output ./output/ --recursive
```

## Conversion Output

When converting a document:
- **PDF**: `report.pdf` → `report.md` + `picture_report/` directory
- **DOCX**: `document.docx` → `document.md` + `picture_document/` directory

The image directory is created in the same location as the input file and contains all extracted images with relative links in the Markdown file. If Pandoc extracts Word media into a nested `media/` directory, Convert2MD now flattens those files into `picture_document/` so DOCX output matches PDF output structure.

### Example Output

**Input**: `/documents/report.pdf`

**Creates**:
```
/documents/
├── report.md          # Markdown content
└── picture_report/    # Extracted images
    ├── image_001.png
    ├── image_002.png
    └── image_003.png
```

**Image links in report.md**:
```markdown
![Figure 1](picture_report/image_001.png)
![Figure 2](picture_report/image_002.png)
```

## Architecture

### Design Patterns

**Strategy Pattern**: The converter system uses the Strategy pattern to support multiple document formats:

```python
class ConverterStrategy(ABC):
    @abstractmethod
    def convert(self, input_path: Path) -> Tuple[str, dict]:
        """Convert document to Markdown."""
        pass

class PDFConverter(ConverterStrategy):
    """PDF-specific conversion logic."""
    
class DOCXConverter(ConverterStrategy):
    """DOCX-specific conversion logic."""
```

**Factory Pattern**: The `ConverterFactory` selects the appropriate strategy based on file type, separating the logic of choosing a converter from the conversion itself.

### Separation of Concerns

- **Conversion Logic** (`converter_strategy.py`, `pdf_converter.py`, `docx_converter.py`): Pure document processing
- **Orchestration** (`converter.py`): High-level conversion workflow
- **CLI Interface** (`cli.py`): User interaction and I/O

This separation enables:
1. Easy testing of conversion logic independently
2. Future GUI integration without modifying core converters
3. Extensibility for new file formats

## Test Suite

The project includes comprehensive automated tests:

### Structural Tests
- **test_picture_directory_naming**: Validates correct image directory naming
- **test_relative_image_links**: Ensures image paths are relative, not absolute

### Content Tests
- **test_complex_tables_structure**: Validates table conversion from PDFs
- **test_latex_formula_format**: Ensures formulas use proper LaTeX syntax
- **test_noise_filtering**: Verifies headers/footers/page numbers are removed
- **test_multicolumn_text_order**: Validates multi-column layout handling

### Resource Tests
- **test_image_extraction_capability**: Image extraction verification
- **test_vector_graphics_handling**: Vector-to-raster conversion
- **test_large_pdf_processing**: Large file stability

### Format-Specific Tests
- **test_pdf_format_support**: PDF converter detection
- **test_docx_format_support**: DOCX/DOC converter detection
- **test_factory_selects_correct_converter**: Factory selection logic

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src tests/

# Run specific test class
pytest tests/test_convert2md.py::TestStructuralRequirements

# Run with verbose output
pytest -v
```

## Configuration

### Environment Variables

Future releases may support:
- `CONVERT2MD_OUTPUT_DIR`: Default output directory
- `CONVERT2MD_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING)

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| docling | >=1.0.0 | PDF parsing and extraction |
| pypandoc | >=1.11 | DOCX/DOC conversion via Pandoc |
| PyMuPDF | >=1.24.0 | PDF image extraction fallback |
| typer | >=0.9.0 | CLI framework |
| rich | >=13.0.0 | Rich terminal output |
| pytest | >=7.4.0 | Testing framework |

## Known Limitations

1. **Complex Tables**: Highly complex tables with merged cells may be converted to text format
2. **Embedded Fonts**: Special fonts may not be preserved in conversion
3. **Hyperlinks**: Some hyperlink information may be lost during conversion
4. **Comments**: Document comments and annotations are not preserved
5. **Corrupted EMF/WMF Files**: Malformed vector image files are detected and skipped with fallback to original format

## Troubleshooting

### Pandoc Not Found
If you get "Pandoc not found" error:
```bash
# macOS
brew install pandoc

# Linux (Ubuntu/Debian)
sudo apt-get install pandoc

# Windows (with Chocolatey)
choco install pandoc
```

### Import Errors
Ensure virtual environment is activated and dependencies are installed:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### DOCX EMF/WMF Image Conversion
For DOCX files with embedded vector graphics, Convert2MD now tries to convert `.emf`/`.wmf` images to `.png` using Inkscape first, then ImageMagick (`magick` / `convert`). Install at least one of these tools for the best output.
```bash
# macOS
brew install --cask inkscape
brew install imagemagick

# Ubuntu/Debian
sudo apt-get install inkscape imagemagick
```

**Safety Features:**
- **EMF File Validation**: Checks file structure before processing to prevent crashes
- **30-second Timeout**: Prevents Inkscape from hanging indefinitely
- **Automatic Fallback**: Uses ImageMagick if Inkscape fails or times out
- **Graceful Degradation**: Preserves original EMF/WMF files if conversion fails

If vector images remain as `.emf`/`.wmf`, the converter still preserves them in the `picture_*` directory, but Markdown may not render them in all viewers.

### Memory Issues with Large Files
If processing large PDFs causes memory issues:
- Process files individually rather than in batch
- Monitor system resources with `top` or Task Manager

## Roadmap: Stage 2 — Graphical Interface and macOS App

### Overview
The Stage 2 development will transform the CLI tool into a native macOS application with a graphical interface, making the tool more accessible to non-technical users.

### Technical Requirements

#### 1. GUI Framework
- **Framework**: PySide6 (Qt for Python)
- **Rationale**: Cross-platform, mature, native look-and-feel support
- **Alternative**: PyQt6 (similar architecture, GPL licensing)

#### 2. User Interface Components

**Main Window**
```
┌─────────────────────────────────────────────────────────┐
│ Convert2MD - Document to Markdown                        │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Drag files here or click to select documents   │    │
│  │          [Supported: PDF, DOCX, DOC]            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  📁 Input Directory: [/path/to/documents       ]  [...]  │
│  📁 Output Directory: [/path/to/output        ]  [...]  │
│                                                           │
│  ☑ Recursive (include subdirectories)                    │
│  ☑ Verbose output                                        │
│                                                           │
│  ┌─────────────────────────────────────────────────┐    │
│  │ Conversion Progress:                            │    │
│  │ ████████░░░░░░░░ 40% (2/5 documents)            │    │
│  │ Current: report.pdf                            │    │
│  └─────────────────────────────────────────────────┘    │
│                                                           │
│  [ ◄ Cancel ]              [ Convert ► ]                │
├─────────────────────────────────────────────────────────┤
│ ✓ Conversion complete: 5 successful, 0 failed           │
└─────────────────────────────────────────────────────────┘
```

**Drag-and-Drop Zone**
- Accept file drops from Finder
- Visual feedback during drag (highlight, drop indicator)
- Support multiple file selection
- Display file list with status icons

**Progress Tracking**
- Progress bar for overall batch conversion
- Real-time status for current file
- Estimated time remaining
- Cancel button for ongoing conversion

**Preview Panel** (Optional Enhancement)
- Split view: Markdown editor + preview
- Syntax highlighting for Markdown
- Live preview of rendered content
- Copy to clipboard functionality

#### 3. System Integration

**macOS Features**
- **Dark Mode Support**: Automatic detection and theme switching
- **Native Look**: Integration with macOS design guidelines
- **Accessibility**: Full keyboard navigation, VoiceOver support
- **Notifications**: System notifications for completed conversions

**Application Distribution**
```
convert2md.app/
├── Contents/
│   ├── MacOS/
│   │   └── convert2md          # Executable
│   ├── Resources/
│   │   ├── AppIcon.icns
│   │   └── [other resources]
│   └── Info.plist              # App metadata
```

**Packaging Options**:
1. **PyInstaller**: Direct .app generation
2. **py2app**: macOS-specific packaging
3. **DMG Installer**: Professional distribution

**Running a macOS app bundle from Terminal**

This works for both Intel and Apple Silicon bundles.

If you have a bundled app such as `dist/Convert2MD.app` or `dist/Convert2MDs.app`, run it with:

```bash
open dist/Convert2MDs.app --args convert '/path/to/document.docx'
```

Or launch the internal executable directly:

```bash
./run-macos-app.sh dist/Convert2MDs.app convert '/path/to/document.docx'
```

#### 4. Performance Optimization

**Concurrency Architecture**
```python
class ConversionWorker(QThread):
    """Worker thread for document conversion."""
    progress = Signal(int)
    finished = Signal(list)
    error = Signal(str)
    
    def run(self):
        """Conversion logic runs in separate thread."""
        try:
            results = self.converter.batch_convert(...)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))

class MainWindow(QMainWindow):
    def on_convert_clicked(self):
        """Start conversion in background thread."""
        self.worker = ConversionWorker()
        self.worker.progress.connect(self.update_progress)
        self.worker.finished.connect(self.on_conversion_complete)
        self.worker.start()
```

**Metal Acceleration** (Apple Silicon)
- Use PyTorch with Metal Performance Shaders (MPS)
- Accelerate ML-based document parsing
- Conditional MPS usage for M1/M2/M3 Macs

#### 5. Implementation Timeline

**Phase 1: Core GUI (Weeks 1-2)**
- [ ] Set up PySide6 project structure
- [ ] Implement main window and file selection
- [ ] Create drag-and-drop zone
- [ ] Basic file list display

**Phase 2: Conversion Integration (Weeks 2-3)**
- [ ] Integrate with existing converter module
- [ ] Implement progress tracking
- [ ] Add error handling and user feedback
- [ ] Threading for non-blocking UI

**Phase 3: Polish (Weeks 3-4)**
- [ ] Dark mode support
- [ ] Accessibility features
- [ ] Settings/preferences dialog
- [ ] User documentation

**Phase 4: Distribution (Week 4)**
- [ ] Package as .app bundle
- [ ] Create DMG installer
- [ ] Code signing and notarization
- [ ] Release notes and user guide

#### 6. Configuration & Settings

**Preferences Dialog**
```
┌──────────────────────────────┐
│ Convert2MD Preferences       │
├──────────────────────────────┤
│ General    │ Output │ Advanced│
│                              │
│ ☑ Launch at startup          │
│ ☑ Show notifications         │
│ ☑ Auto-save settings         │
│                              │
│ Default output directory:    │
│ [~/Documents/Converted   ] □ │
│                              │
│ ☑ Remove source files after  │
│    successful conversion     │
│                              │
│ ☑ Verbose logging            │
│                              │
│         [ Cancel ]  [ Save ] │
└──────────────────────────────┘
```

### Dependencies for Stage 2

```txt
# GUI
PySide6>=6.6.0

# Image processing
Pillow>=10.0.0

# System integration
pyobjc-framework-Cocoa>=10.0.0  # macOS-specific

# Performance
torch>=2.1.0  # Optional: for ML acceleration
```

### Testing Strategy for Stage 2

- **Unit Tests**: Test GUI logic separately from conversion
- **Integration Tests**: Test GUI + converter interaction
- **UI Tests**: Automated UI testing with PyAutoGUI or similar
- **macOS-Specific Tests**: Dark mode, drag-and-drop, notifications

### Migration Path

The existing CLI module becomes a library layer:
```python
# Stage 1: CLI directly uses converters
from src.converter import DocumentConverter

# Stage 2: GUI layer uses CLI library
from src.converter import DocumentConverter
from src.gui import MainWindow  # New module
```

### Future Enhancements

1. **Plugin System**: Allow third-party converters for other formats
2. **Conversion Profiles**: Save and load conversion settings
3. **Real-time Preview**: Live Markdown rendering as you select files
4. **Cloud Integration**: Save directly to cloud storage (Dropbox, iCloud)
5. **CLI Tool Integration**: Shell command for quick conversions

## Contributing

Contributions are welcome! Please:
1. Create a feature branch
2. Add tests for new functionality
3. Ensure all tests pass
4. Submit a pull request

## License

This project is provided as-is for educational and commercial use.

## Support

For issues, questions, or suggestions:
- Check existing documentation
- Review test cases for usage examples
- Consult the troubleshooting section

## Changelog

### Version 1.0.0 (Initial Release)
- Core CLI application with Typer
- PDF support via Docling
- DOCX/DOC support via Pandoc
- Image extraction and organization
- Comprehensive test suite
- Full documentation
- Roadmap for Stage 2 GUI development

### Version 1.0.1 (Safety & Stability)
- **EMF/WMF Validation**: Added file structure validation before Inkscape processing
- **Process Timeout**: 30-second timeout on image conversion tools to prevent hangs
- **Smart Fallback**: Automatic fallback from Inkscape to ImageMagick on failure
- **Improved Logging**: Debug logging for conversion pipeline
- **Graceful Degradation**: Preserves original files if conversion fails

---

**Made with ❤️ for document conversion**
