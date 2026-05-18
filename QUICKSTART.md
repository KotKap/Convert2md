# Quick Start Guide

Get Convert2MD up and running in 5 minutes!

## 1. Installation (2 minutes)

### Prerequisites
- Python 3.10 or higher
- Pandoc (for DOCX support)
- **Inkscape** or **ImageMagick** (required separately for DOCX vector image conversion, e.g. EMF/WMF to PNG)

### macOS Setup
```bash
# Install Pandoc (if not already installed)
brew install pandoc

# Create project directory and virtual environment
cd /Volumes/Work/MyProject/Convert2MD
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Linux/Windows Setup
```bash
# Install Pandoc
# Ubuntu: sudo apt-get install pandoc
# Windows: choco install pandoc

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## 2. Verify Installation (1 minute)

```bash
# Check CLI is working
python convert2md.py --help

# Expected output shows main commands: convert, batch
```

## 3. Basic Usage (2 minutes)

### Convert a Single PDF
```bash
# Simple conversion
python convert2md.py convert sample.pdf

# Output:
# ✓ Conversion successful!
# Output: sample.md
# picture_sample/  (contains extracted images)
```

### Convert with Verbose Output
```bash
python convert2md.py convert report.pdf --verbose

# Shows:
# - Number of pages
# - Number of extracted images
# - Conversion metadata
```

### Convert DOCX
```bash
python convert2md.py convert document.docx
# Creates: document.md and picture_document/
```

If DOCX contains vector graphics such as EMF/WMF, Convert2MD will try to convert them to PNG using Inkscape first, then ImageMagick. This keeps DOCX image output consistent with PDF output.

### Batch Convert
```bash
# Convert all PDFs in directory
python convert2md.py batch ./documents/

# Convert specific type
python convert2md.py batch ./documents/ --pattern "*.pdf"

# Recursive (include subdirectories)
python convert2md.py batch ./documents/ --recursive
```

## 4. Check Results

```bash
# View markdown output
cat sample.md

# Check extracted images
ls picture_sample/

# Count converted files
find . -name "*.md" -type f | wc -l
```

## Common Commands

### Single File Conversion
```bash
# Default: saves as input_name.md
python convert2md.py convert input.pdf

# Custom output location
python convert2md.py convert input.pdf -o custom_output.md

# Verbose mode
python convert2md.py convert input.pdf -v
```

### Batch Conversion
```bash
# All supported formats in directory
python convert2md.py batch ./my_documents/

# Specific format only
python convert2md.py batch ./my_documents/ --pattern "*.pdf"

# Including subdirectories
python convert2md.py batch ./my_documents/ -r

# Custom output directory
python convert2md.py batch ./input/ --output ./output/
```

## Understanding the Output

### Markdown File (`sample.md`)
```markdown
# Document Title

Some text with **bold** and *italic*.

![Figure 1](picture_sample/image_001.png)

## Section

More content...
```

### Image Directory (`picture_sample/`)
```
picture_sample/
├── image_001.png      # First extracted image
├── image_002.png      # Second extracted image
└── image_003.jpg      # Can be PNG or JPG
```

### Image Links in Markdown
All image links are **relative** paths:
```markdown
✓ Good:   ![alt](picture_sample/image.png)
✗ Bad:    ![alt](/Users/john/project/picture_sample/image.png)
```

## Troubleshooting

### "Pandoc not found" Error
```bash
# Install Pandoc
brew install pandoc  # macOS
sudo apt-get install pandoc  # Linux
choco install pandoc  # Windows
```

### Virtual Environment Not Activated
```bash
# Activate it
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows
```

### "Module not found" Error
```bash
# Ensure dependencies installed
pip install -r requirements.txt
```

### Large File Causing Issues
```bash
# Process individual file with verbose output
python convert2md.py convert large_file.pdf --verbose

# Check available memory
top  # macOS/Linux
```

## Running Tests

```bash
# Run all tests (optional, requires pytest)
pip install pytest
pytest

# Run specific tests
pytest tests/test_convert2md.py::TestStructuralRequirements -v
```

## Next Steps

1. **Read Full Documentation**: See [README.md](README.md)
2. **Check Test Examples**: See [TEST_CHECKLIST.md](TEST_CHECKLIST.md)
3. **Contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)
4. **Report Issues**: Use GitHub Issues

## Example Workflow

```bash
# 1. Navigate to your documents
cd ~/Documents/reports

# 2. Convert all PDFs
python /path/to/convert2md.py batch . --pattern "*.pdf" --recursive

# 3. Review results
find . -name "*.md" | head -5

# 4. View converted document
open report.md

# 5. Check images were extracted
ls picture_report/ | wc -l
```

## Performance Tips

- Process large batches with `--recursive` for directory structures
- Use `--pattern` to filter file types
- Enable `--verbose` only when debugging
- For very large PDFs (100+ pages), convert individually to monitor progress

## Support

- **Stuck?** Read [README.md](README.md) troubleshooting section
- **Want to test?** Check [TEST_CHECKLIST.md](TEST_CHECKLIST.md)
- **Want to contribute?** See [CONTRIBUTING.md](CONTRIBUTING.md)

---

**Ready to convert documents?** 🚀
```bash
python convert2md.py convert myfile.pdf
```
