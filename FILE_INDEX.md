# Convert2MD - Complete File Index

## Project Root Files

### Documentation
- **README.md** (400+ lines)
  - Project overview, features, installation, usage, architecture, testing, roadmap
  - User-facing comprehensive documentation

- **QUICKSTART.md** (200+ lines)
  - 5-minute getting started guide
  - Basic usage examples and troubleshooting
  - Quick reference for common commands

- **PROJECT_SUMMARY.md** (300+ lines)
  - Complete project summary and status
  - Statistics, features, deliverables checklist
  - Verification status and next steps

- **ARCHITECTURE.md** (400+ lines)
  - System design and architecture overview
  - Module descriptions and data flow
  - Design patterns and extension points
  - Testing architecture and performance considerations

- **VECTOR_SAFETY.md** (NEW, 200+ lines)
  - EMF/WMF file safety mechanisms
  - Process timeout and validation strategies
  - Fallback conversion pipeline details
  - Troubleshooting malformed vector files

- **CONTRIBUTING.md** (300+ lines)
  - Developer setup and workflow
  - Code style guidelines and testing requirements
  - Pull request process and issue reporting

- **TEST_CHECKLIST.md** (500+ lines)
  - Comprehensive test scenarios (30+)
  - Manual and automated testing procedures
  - Verification checklists for each feature category

- **CHANGELOG.md** (150+ lines)
  - Version history and release notes
  - Feature list for v1.0.0
  - Known limitations and compatibility information

### Configuration Files
- **.gitignore**
  - Git ignore patterns for Python, IDE, OS-specific files

- **.mypy.ini**
  - Type checking configuration
  - Ignore rules for external libraries

- **pytest.ini**
  - Test discovery settings
  - Test execution options

### Python Configuration
- **setup.py** (70+ lines)
  - Package metadata and configuration
  - Dependency declarations
  - Entry points for CLI

- **convert2md.py** (10 lines)
  - Main entry point script
  - Launches CLI application

### Dependency Management
- **requirements.txt**
  - Production dependencies (Docling, pypandoc, Typer, Rich)
  - Minimal set for running the application

- **requirements-dev.txt**
  - Development dependencies (pytest, mypy, black, flake8)
  - Testing and code quality tools

### Development Tools
- **Makefile** (80+ lines)
  - Common development tasks
  - Setup, testing, linting, formatting commands

---

## Source Code (`src/` - 775 lines total)

### Core Modules

#### src/__init__.py (6 lines)
- Package initialization
- Public API exports
- Version declaration

#### src/converter_strategy.py (45 lines)
- Abstract base class: `ConverterStrategy`
- Interface definition for document converters
- `ConversionMetadata` class for results
- Purpose: Define converter interface

#### src/pdf_converter.py (180 lines)
- **Class**: `PDFConverter(ConverterStrategy)`
- Methods:
  - `convert()`: Main PDF conversion
  - `_process_images()`: Image extraction
  - `_filter_noise()`: Remove artifacts
  - `_ensure_latex_format()`: Format formulas
- **Engine**: Docling (IBM)
- Purpose: Convert PDFs to Markdown

#### src/docx_converter.py (150 lines)
- **Class**: `DOCXConverter(ConverterStrategy)`
- Methods:
  - `convert()`: Main DOCX conversion
  - `_convert_with_pandoc()`: Pandoc integration
  - `_update_image_paths()`: Path correction
  - `_convert_media_vectors()`: Convert EMF/WMF to PNG
  - `_flatten_media_dir()`: Flatten Pandoc `media/` output
  - `_filter_noise()`: Remove artifacts
- **Engine**: Pandoc (via pypandoc)
- Purpose: Convert DOCX/DOC to Markdown

#### src/converter.py (60 lines)
- **Classes**:
  - `ConverterFactory`: Select converter by file type
  - `DocumentConverter`: Main orchestrator
- Methods:
  - `get_converter()`: Factory method
  - `convert()`: Convert documents
  - `save_markdown()`: Save results
- Purpose: Orchestrate conversion workflow

#### src/cli.py (200 lines)
- **Framework**: Typer
- **Commands**:
  - `convert`: Single file conversion
  - `batch`: Batch conversion
- **Features**:
  - Progress tracking (Rich)
  - Verbose output
  - Error handling with user feedback
- Purpose: CLI interface for end users

#### src/utils.py (60 lines)
- **Functions**:
  - `get_supported_formats()`: List supported types
  - `is_supported_file()`: Format validation
  - `get_output_md_path()`: Calculate output path
  - `get_picture_dir_path()`: Calculate image directory
  - `cleanup_conversion_artifacts()`: Clean up generated files
- Purpose: Utility functions for file operations

#### src/config.py (80 lines)
- **Constants**:
  - Project metadata (name, version, author)
  - Supported formats
  - Image directory naming
- **Classes**:
  - `ConversionSettings`: Default settings
  - `LoggingConfig`: Logging configuration
- Purpose: Centralized configuration management

---

## Tests (`tests/` - 350 lines)

### tests/__init__.py (1 line)
- Test package initialization

### tests/test_convert2md.py (350+ lines)

#### Test Classes and Cases

1. **TestStructuralRequirements** (4 tests)
   - `test_picture_directory_naming`: Directory naming validation
   - `test_relative_image_links`: Path format validation
   - Validates output structure and organization

2. **TestContentRequirements** (5 tests)
   - `test_complex_tables_structure`: Table handling
   - `test_latex_formula_format`: Formula preservation
   - `test_noise_filtering`: Artifact removal
   - `test_multicolumn_text_order`: Layout handling
   - Validates content conversion quality

3. **TestResourceHandling** (3 tests)
   - `test_image_extraction_capability`: Image processing
   - `test_vector_graphics_handling`: Vector-to-raster conversion
   - `test_large_pdf_processing`: Memory efficiency

4. **TestPDFConverter** (2 tests)
   - `test_pdf_format_support`: Format detection
   - `test_pdf_file_not_found`: Error handling

5. **TestDOCXConverter** (2 tests)
   - `test_docx_format_support`: Format detection
   - `test_docx_file_not_found`: Error handling

6. **TestConverterFactory** (2 tests)
   - `test_factory_selects_correct_converter`: Strategy selection
   - `test_unsupported_format_error`: Error handling

#### Total: 18 automated test cases

---

## Project Directories

### `/src` - Source Code
- 8 Python modules
- ~775 lines of code
- Full type hints and documentation

### `/tests` - Test Suite
- Test configuration and discovery
- 18 automated test cases
- ~350 lines of test code

### `/test_samples` - Sample Documents
- Placeholder directory for test documents
- User should add sample PDFs/DOCXs for testing

### `/.vscode` - VS Code Settings
- Editor configuration for development

---

## File Summary Table

| Category | File | Lines | Purpose |
|----------|------|-------|---------|
| **Entry Point** | convert2md.py | 10 | CLI launcher |
| **Package Config** | setup.py | 70 | Distribution setup |
| | pytest.ini | 6 | Test configuration |
| | .mypy.ini | 18 | Type checking config |
| **Dependencies** | requirements.txt | 7 | Production deps |
| | requirements-dev.txt | 6 | Dev deps |
| **Source** | src/__init__.py | 6 | Package init |
| | src/converter_strategy.py | 45 | Abstract interface |
| | src/pdf_converter.py | 180 | PDF converter |
| | src/docx_converter.py | 150 | DOCX converter |
| | src/converter.py | 60 | Factory/orchestrator |
| | src/cli.py | 200 | CLI interface |
| | src/utils.py | 60 | Utilities |
| | src/config.py | 80 | Configuration |
| **Tests** | tests/__init__.py | 1 | Test package |
| | tests/test_convert2md.py | 350 | 18 test cases |
| **Docs** | README.md | 400 | Main guide |
| | QUICKSTART.md | 200 | Quick start |
| | ARCHITECTURE.md | 400 | System design |
| | CONTRIBUTING.md | 300 | Dev guide |
| | TEST_CHECKLIST.md | 500 | Test scenarios |
| | CHANGELOG.md | 150 | Version history |
| | PROJECT_SUMMARY.md | 300 | Project status |
| **Config** | .gitignore | 60 | Git patterns |
| | Makefile | 80 | Dev commands |

---

## Code Organization

### By Layer

```
User Interface (CLI)
  ↓
src/cli.py (200 lines)
  ↓
Orchestration
  ↓
src/converter.py (60 lines)
  ↓
Strategy Selection
  ↓
src/converter_factory (in converter.py)
  ↓
Conversion Strategies
  ├─ src/pdf_converter.py (180 lines)
  └─ src/docx_converter.py (150 lines)
  ↓
Support Layer
  ├─ src/converter_strategy.py (45 lines) [Interface]
  ├─ src/utils.py (60 lines) [Helpers]
  ├─ src/config.py (80 lines) [Settings]
  └─ src/__init__.py (6 lines) [Package]
```

### By Module Count
- **Total Modules**: 8
- **Strategy Implementations**: 2 (PDF, DOCX)
- **Orchestration**: 1
- **Interface Definition**: 1
- **CLI Interface**: 1
- **Utilities**: 1
- **Configuration**: 1
- **Package**: 1

---

## Key Statistics

| Metric | Count |
|--------|-------|
| Total Python Code Lines | 775 |
| Total Test Lines | 350 |
| Total Documentation Lines | 2500+ |
| Python Modules | 8 |
| Converter Strategies | 2 |
| Test Cases (Automated) | 18 |
| Test Cases (Manual) | 30+ |
| Configuration Files | 3 |
| Documentation Files | 7 |
| Total Project Files | 25+ |

---

## Dependencies

### Production (7)
- docling >= 1.0.0
- pypandoc >= 1.11
- typer >= 0.9.0
- rich >= 13.0.0
- Click (via Typer)
- typing-extensions (for Python 3.10)

### Development (6)
- pytest >= 7.4.0
- pytest-cov >= 4.1.0
- pytest-watch >= 4.2.0
- mypy >= 1.5.0
- black >= 23.9.0
- flake8 >= 6.1.0

### External (1)
- Pandoc (system dependency)

---

## Quick Navigation

### For Users
- Start here: **QUICKSTART.md**
- Full guide: **README.md**
- Examples: **TEST_CHECKLIST.md**

### For Developers
- Architecture: **ARCHITECTURE.md**
- Contributing: **CONTRIBUTING.md**
- Code: **src/** modules
- Tests: **tests/test_convert2md.py**

### For Project Management
- Status: **PROJECT_SUMMARY.md**
- History: **CHANGELOG.md**
- All files: This index

---

## File Descriptions Quick Reference

```
.gitignore ..................... Git ignore patterns
.mypy.ini ....................... Type checking config
ARCHITECTURE.md ................ System design (400+ lines)
CHANGELOG.md ................... Version history (150+ lines)
CONTRIBUTING.md ............... Developer guide (300+ lines)
Makefile ....................... Development tasks
PROJECT_SUMMARY.md ............ Project status (300+ lines)
QUICKSTART.md .................. 5-min getting started (200+ lines)
README.md ...................... Main documentation (400+ lines)
TEST_CHECKLIST.md ............. Test scenarios (500+ lines)
convert2md.py .................. Entry point
pytest.ini ..................... Test configuration
requirements.txt .............. Production dependencies
requirements-dev.txt .......... Development dependencies
setup.py ....................... Package configuration
src/
  __init__.py ............... Package initialization
  cli.py .................... CLI interface (200 lines)
  config.py ................. Configuration (80 lines)
  converter.py .............. Orchestration (60 lines)
  converter_strategy.py ..... Abstract interface (45 lines)
  docx_converter.py ......... DOCX converter (150 lines)
  pdf_converter.py .......... PDF converter (180 lines)
  utils.py .................. Utilities (60 lines)
test_samples/ ................ Sample documents (placeholder)
tests/
  __init__.py ............... Package initialization
  test_convert2md.py ....... Test suite (350 lines, 18 tests)
```

---

**For complete project information, see PROJECT_SUMMARY.md**
