# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-05-13

### Added
- Initial release of Convert2MD CLI application
- PDF to Markdown conversion using Docling with:
  - Advanced PDF parsing
  - Image extraction to `picture_*` directories
  - Formula preservation in LaTeX format
  - Header/footer/page number filtering
- DOCX/DOC to Markdown conversion using Pandoc with:
  - Table preservation
  - Image extraction
  - Formatting conversion to Markdown
- CLI interface with Typer featuring:
  - Single document conversion: `convert` command
  - Batch conversion: `batch` command
  - Pattern matching for file selection
  - Recursive directory processing
  - Verbose output and progress tracking
- Converter Strategy pattern for extensible architecture
- Comprehensive test suite with 15+ test cases covering:
  - Structural requirements (paths, relative links)
  - Content handling (tables, formulas, noise filtering)
  - Resource handling (large files, vector graphics)
  - Format-specific functionality
- Complete documentation:
  - README.md with usage examples and roadmap
  - TEST_CHECKLIST.md with manual and automated tests
  - CONTRIBUTING.md with development guidelines
  - Docstrings for all public APIs
- Project configuration:
  - setup.py for package distribution
  - requirements.txt with pinned dependencies
  - pytest.ini for test discovery
  - .gitignore for version control
  - .mypy.ini for type checking

### Features

#### PDF Conversion
- Parse PDFs using IBM's Docling engine
- Extract text with semantic understanding
- Preserve document structure
- Extract and organize images
- Convert formulas to LaTeX ($...$)
- Filter noise and artifacts

#### DOCX Conversion
- Convert using Pandoc (requires external installation)
- Extract embedded images
- Preserve table structures
- Convert formatting to Markdown
- Flatten Pandoc `media/` output into `picture_*` directories for consistent DOCX/PDF image layout
- Convert embedded EMF/WMF graphics to PNG using Inkscape first, then ImageMagick

#### CLI Commands
- **convert**: Convert a single document
  - Options: `-o/--output`, `-v/--verbose`
- **batch**: Convert multiple documents
  - Options: `-o/--output`, `-p/--pattern`, `-r/--recursive`, `-v/--verbose`

#### Output Structure
- Markdown file with same name as input (`.md` extension)
- `picture_{filename}/` directory with extracted images
- Relative image paths for portability

### Documentation
- 200+ line README with features, installation, usage, architecture
- Comprehensive test checklist with manual and automated tests
- Contributing guide for developers
- Setup.py for pip installation
- Type hints for IDE support

### Testing
- 15+ automated tests using pytest
- Test categories:
  - Structural (4 tests)
  - Content (5 tests)
  - Resources (3 tests)
  - Format-specific (5 tests)
- Coverage reporting with pytest-cov
- Manual test checklist with verification steps

### Future Roadmap (Stage 2)
- PySide6-based GUI application
- macOS app bundle support
- Dark mode integration
- Drag-and-drop interface
- Real-time preview panel
- Metal acceleration for M1/M2/M3 chips
- Settings/preferences dialog
- System integration (notifications, etc.)

---

## [Unreleased]

### Planned Features
- GUI application with PySide6 (Stage 2)
- Plugin system for additional formats
- OCR support for scanned PDFs
- Cloud storage integration
- Conversion profiles/presets
- More granular conversion options

---

## Version History

### Pre-release
- Initial concept and prompt development
- Architecture planning
- Core module implementation
- Test suite creation
- Documentation writing

---

## Notes

### Compatibility
- **Python**: 3.10+
- **Platforms**: macOS, Linux, Windows
- **Pandoc**: Required for DOCX support

### Known Limitations
1. Very complex tables may convert to text format
2. Embedded fonts not preserved
3. Some hyperlinks may be lost
4. Document comments not included

### Breaking Changes
None in v1.0.0 (initial release)

---

## Contributors
- Initial development team

---

## How to Report Issues

Please use the GitHub Issues page with the following template:

```markdown
**Description**
Brief description of the issue

**Environment**
- Python version: 3.10.x
- OS: macOS/Linux/Windows
- Convert2MD version: 1.0.0

**Steps to Reproduce**
1. ...
2. ...

**Expected Behavior**
...

**Actual Behavior**
...

**Additional Context**
Any relevant screenshots, logs, or file samples
```

---

For more information, see [README.md](README.md)
