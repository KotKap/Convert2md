# Test Scenarios and Verification Checklist

This document provides a comprehensive checklist for manual and automated testing of the Convert2MD application.

## Structural Tests

### ✓ Test_Paths
- **Description**: Verify that image directories are created with the correct naming convention
- **Test Case**: Convert a PDF/DOCX with embedded images
- **Expected Result**: 
  - Directory created as `picture_<filename>` in the same location as the input file
  - Example: Converting `/path/to/report.pdf` creates `/path/to/picture_report/`
- **Automated Test**: ✓ `test_picture_directory_naming()`

### ✓ Test_Relative_Links
- **Description**: Ensure image paths in Markdown are relative, not absolute
- **Test Cases**:
  1. Single document conversion
  2. Batch conversion with subdirectories
  3. Documents with many images
- **Expected Result**: 
  - ✗ No absolute paths (e.g., `/Users/name/...`, `C:\Users\...`)
  - ✓ Relative paths only (e.g., `picture_report/image1.png`)
- **Verification Command**:
  ```bash
  grep -E '!\[.*\]\((/|[A-Z]:)' output.md  # Should return nothing
  ```
- **Automated Test**: ✓ `test_relative_image_links()`

---

## Content Tests (Document Nuances)

### ✓ Test_Complex_Tables
- **Description**: Handle PDFs with complex table structures
- **Sample Document**: Should contain:
  - Merged cells
  - Multi-row headers
  - Diagonal text
  - Nested tables
- **Expected Result**:
  - Option A: Valid Markdown table grid
  - Option B: Readable text representation with clear structure
  - No loss of data
- **Verification**: Manually review table structure in output
- **Automated Test**: ✓ `test_complex_tables_structure()`

### ✓ Test_Math_LaTeX
- **Description**: Verify formulas are properly converted to LaTeX
- **Sample Document**: Should contain:
  - Inline equations (fractions, Greek letters)
  - Display equations (integrals, matrices)
  - Complex mathematical expressions
- **Expected Result**:
  - Inline math: `$E=mc^2$`
  - Display math: `$$\int_0^\infty e^{-x} dx = 1$$`
  - Valid LaTeX syntax
- **Verification**:
  ```bash
  grep -E '\$\$?[^$]+\$\$?' output.md | head -5
  ```
- **Automated Test**: ✓ `test_latex_formula_format()`

### ✓ Test_Noise_Reduction
- **Description**: Remove headers, footers, and page numbers
- **Sample Document**: Should contain:
  - Header with document title on every page
  - Footer with page numbers
  - Repeated content
- **Expected Result**:
  - Header/footer content removed
  - No standalone page numbers (e.g., "1", "2", etc.)
  - No repetitive content
- **Verification**:
  ```bash
  grep -E '^\s*\d+\s*$' output.md  # Should return nothing
  ```
- **Automated Test**: ✓ `test_noise_filtering()`

### ✓ Test_Multi_Column
- **Description**: Handle multi-column layouts correctly
- **Sample Document**: 2-column or 3-column PDF report
- **Expected Result**:
  - Text flows logically from column 1 → column 2 → next page column 1
  - No interleaving or scrambled content
  - Reading order preserved
- **Verification**: Manual review of logical flow
- **Automated Test**: ✓ `test_multicolumn_text_order()`

---

## Resource Tests

### ✓ Test_Large_PDF
- **Description**: Process large PDF files without memory issues
- **Sample Document**: 50+ pages with multiple images and tables
- **Expected Result**:
  - Conversion completes successfully
  - Memory usage remains stable
  - No crashes or timeouts
- **Performance Metrics**:
  - Target: < 5 GB memory for 100-page PDF
  - Speed: ~5-10 seconds per page
- **Automated Test**: ✓ `test_large_pdf_processing()`

### ✓ Test_Vector_Graphics
- **Description**: Convert vector graphics to raster format
- **Sample Document**: PDF with:
  - Diagrams (flowcharts, org charts)
  - Charts and graphs
  - Shapes and annotations
- **Expected Result**:
  - Vector graphics converted to PNG/JPG
  - Saved in picture directory
  - Proper linking in Markdown
- **Automated Test**: ✓ `test_vector_graphics_handling()`

---

## CLI Tests

### ✓ Test_Single_File_Conversion
```bash
python convert2md.py convert sample.pdf
```
**Expected Output**:
- ✓ Confirmation message: "Conversion successful!"
- ✓ Output file created: `sample.md`
- ✓ Image directory created: `picture_sample/`

### ✓ Test_Custom_Output_Path
```bash
python convert2md.py convert document.docx -o custom_output.md
```
**Expected Output**:
- ✓ File created at specified path: `custom_output.md`

### ✓ Test_Batch_Conversion
```bash
python convert2md.py batch ./documents/
```
**Expected Output**:
- ✓ All supported files converted
- ✓ Status summary: "Successful: X, Failed: Y"

### ✓ Test_Recursive_Batch
```bash
python convert2md.py batch ./documents/ --recursive
```
**Expected Output**:
- ✓ Files in subdirectories converted
- ✓ Directory structure preserved

### ✓ Test_Pattern_Matching
```bash
python convert2md.py batch ./documents/ --pattern "*.pdf"
```
**Expected Output**:
- ✓ Only PDF files processed
- ✓ DOCX files ignored

### ✓ Test_Verbose_Output
```bash
python convert2md.py convert report.pdf --verbose
```
**Expected Output**:
- ✓ Detailed metadata displayed
- ✓ Image list shown
- ✓ Processing steps logged

### ✓ Test_Error_Handling

**Unsupported Format**:
```bash
python convert2md.py convert document.txt
```
**Expected**: Error message about unsupported format

**Missing File**:
```bash
python convert2md.py convert nonexistent.pdf
```
**Expected**: FileNotFoundError message

**Missing Pandoc** (for DOCX):
```bash
# On system without pandoc installed
python convert2md.py convert document.docx
```
**Expected**: Clear error message about Pandoc requirement

---

## Format-Specific Tests

### PDF Tests

- ✓ `test_pdf_format_support()`: Verify .pdf files are recognized
- ✓ `test_pdf_file_not_found()`: Error handling for missing files
- **Manual Tests**:
  - Scanned PDF (image-based) → Text extraction quality?
  - Native PDF (text-based) → Perfect conversion?
  - PDF with forms → Field values preserved?

### DOCX Tests

- ✓ `test_docx_format_support()`: Verify .docx/.doc files are recognized
- ✓ `test_docx_file_not_found()`: Error handling for missing files
- **Manual Tests**:
  - DOCX with tables → Conversion quality?
  - DOCX with images → All images extracted?
  - DOCX with embedded vector graphics (EMF/WMF) → Converted to PNG and referenced in `picture_*`?
  - DOCX with complex formatting → Markdown equivalent readable?

---

## Performance Tests

### Memory Usage
```bash
/usr/bin/time -v python convert2md.py batch ./large_documents/ --recursive 2>&1 | grep "Maximum resident"
```
**Target**: < 2 GB for typical usage

### Conversion Speed
```bash
time python convert2md.py convert large_file.pdf
```
**Target**: 
- PDF: ~2-5 seconds per page
- DOCX: ~1-2 seconds per page

---

## Automated Testing Commands

### Run All Tests
```bash
pytest
```

### Run with Coverage Report
```bash
pytest --cov=src --cov-report=html
```

### Run Specific Test Category
```bash
pytest tests/test_convert2md.py::TestStructuralRequirements
pytest tests/test_convert2md.py::TestContentRequirements
pytest tests/test_convert2md.py::TestResourceHandling
```

### Run Tests Matching Pattern
```bash
pytest -k "noise" -v
pytest -k "relative" -v
```

---

## Manual Testing Workflow

### Setup Test Environment
```bash
1. cd /Volumes/Work/MyProject/Convert2MD
2. python3 -m venv venv
3. source venv/bin/activate
4. pip install -r requirements.txt
5. brew install pandoc  # macOS
```

### Prepare Test Samples
- [ ] Create `test_samples/simple.pdf` (1-page, no images)
- [ ] Create `test_samples/complex.pdf` (10+ pages, tables, images)
- [ ] Create `test_samples/document.docx` (tables, images, formatting)

### Execute Test Cases
1. [ ] Run all automated tests: `pytest`
2. [ ] Perform structural tests manually
3. [ ] Verify content handling with sample files
4. [ ] Test CLI commands with various options
5. [ ] Check error handling with invalid inputs

### Verification Checklist
- [ ] All tests pass
- [ ] No memory leaks detected
- [ ] Output files are valid Markdown
- [ ] Image links are relative
- [ ] No absolute paths in output
- [ ] Formulas are in LaTeX format
- [ ] Noise is properly filtered

---

## Known Issues & Workarounds

### Issue: Pandoc Not Found
**Solution**: Install Pandoc from https://pandoc.org/installing.html

### Issue: PDF with Scanned Images
**Workaround**: Use OCR preprocessing tool before conversion

### Issue: Very Large Tables in Markdown
**Workaround**: Markdown doesn't support complex tables; use HTML tables in output

---

## Sign-Off

- [ ] All structural tests pass
- [ ] All content tests pass
- [ ] All resource tests pass
- [ ] CLI functionality verified
- [ ] Error handling verified
- [ ] Performance targets met
- [ ] Documentation complete

**Date Completed**: _______________
**Tested By**: _______________
**Status**: ☐ Ready for Release / ☐ Needs Fixes
