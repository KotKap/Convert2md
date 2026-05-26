# Vector Graphics Safety & Reliability

## Problem Statement

When converting DOCX files with embedded EMF/WMF vector graphics to PNG, third-party tools like Inkscape can crash on malformed files. This document explains the safety mechanisms implemented in Convert2MD.

## Crash Root Cause

**Inkscape 1.4.4 Segmentation Fault (macOS):**
- Crash in `Emf::myEnhMetaFileProc()` when processing certain EMF files
- Null pointer dereference in platform string handling
- No error message or recovery - process terminates immediately
- Can occur even with "valid-looking" EMF files with corrupted internal structures

**Error Example:**
```
Exception Type:    EXC_BAD_ACCESS (SIGSEGV)
Exception Subtype: KERN_INVALID_ADDRESS at 0x0000000000000000
```

## Safety Strategy: Multi-Layer Defense

### Layer 1: EMF File Validation
**Method**: `_validate_emf_file(path: Path) -> bool`

Before attempting Inkscape processing, the EMF file structure is validated by checking magic numbers:

```python
# Valid EMF signatures:
0x01000900  # Old EMF format
0x464D4520  # Modern EMF format (` FME` in ASCII)
```

**Benefits:**
- ✅ Detects obviously corrupted files immediately
- ✅ Zero overhead (4 bytes read)
- ✅ Prevents Inkscape even starting on known-bad files
- ⚠️ Limitation: Valid signature doesn't guarantee valid internal structure

### Layer 2: Process Timeout
**Method**: `subprocess.run(..., timeout=30)`

All external tool invocations have a 30-second timeout:

```python
subprocess.run(
    ['inkscape', ...],
    timeout=30  # Kill process if not done in 30 seconds
)
```

**Benefits:**
- ✅ Prevents indefinite hangs on problematic files
- ✅ Protects batch operations from stalling
- ✅ Applies to both Inkscape and ImageMagick
- ⚠️ Risk: Legitimate large images might exceed timeout

### Layer 3: Automatic Fallback
**Method**: Catch `TimeoutExpired` and retry with ImageMagick

```
Try Inkscape (30s timeout)
    ├─ Success? → Use PNG output
    ├─ Timeout? → Kill process, try ImageMagick
    └─ Error? → Try ImageMagick
    
Try ImageMagick (30s timeout)
    ├─ Success? → Use PNG output
    └─ Fail? → Keep original EMF/WMF
```

**Benefits:**
- ✅ Single file failure doesn't block batch operation
- ✅ ImageMagick is more tolerant of malformed files
- ✅ Original files preserved if all tools fail
- ⚠️ ImageMagick output may be lower quality for complex EMF

### Layer 4: Graceful Degradation
**Method**: Log warnings and continue with original files

If both Inkscape and ImageMagick fail, the original EMF/WMF files are preserved in the output directory:

```markdown
![Vector Image](picture_document/image4.emf)  <!-- May not render in all viewers -->
```

**Benefits:**
- ✅ Conversion completes rather than crashing
- ✅ User can manually convert problematic files later
- ✅ Full document still produced

## Conversion Flow

```
DOCX File
    ↓
Pandoc extraction (creates picture_*/media/)
    ↓
For each EMF/WMF file:
    ├─ Validate magic number
    │   ├─ Invalid? → Try ImageMagick only
    │   └─ Valid? → Try Inkscape first
    │
    ├─ Try Inkscape (with 30s timeout)
    │   ├─ Success? → PNG ready
    │   ├─ Timeout? → (kill process) → Try ImageMagick
    │   └─ Error? → Try ImageMagick
    │
    ├─ Try ImageMagick (with 30s timeout)
    │   ├─ Success? → PNG ready
    │   └─ Fail? → Keep original EMF/WMF
    │
    └─ Log result and continue
    ↓
Flatten media/ directory
    ↓
Generate Markdown with image links
    ↓
Output complete document
```

## Logging

Enable verbose logging to see conversion details:

```bash
# Python logging (if configured)
python convert2md.py convert document.docx --verbose
```

Log output includes:
- File validation results
- Tool selection (Inkscape vs ImageMagick)
- Timeout warnings
- Conversion success/failure

## Performance Impact

### Validation Overhead
- Reading first 4 bytes: **< 1ms**
- Applied only to EMF/WMF files, not images

### Timeout Overhead
- Normal case: **No overhead** (tools finish naturally)
- Timeout case: **30s added** (acceptable for batch operations)

## Known Issues & Trade-offs

### Timeout May Be Too Short
- Large, complex EMF files might legitimately need > 30s
- Solution: Could make timeout configurable

### Signature Validation Is Incomplete
- Magic number check catches corrupted headers
- Cannot detect structural issues deep in file
- Solution: Would require full EMF parser (too complex)

### ImageMagick Quality
- May produce lower-quality PNGs for complex EMF
- Uses fallback rendering, not true EMF interpretation
- Solution: Accept trade-off between safety and quality

## Future Improvements

1. **Configurable Timeout**
   ```python
   --emf-timeout 60  # seconds
   ```

2. **Tool Preference**
   ```python
   --image-tool imagemagick  # Skip Inkscape
   --image-tool inkscape     # Require Inkscape
   ```

3. **Detailed Error Reports**
   ```
   Failed conversions: image4.emf (timeout), image7.wmf (invalid)
   ```

4. **EMF File Sanitization**
   - Use dedicated EMF parser to rebuild clean file
   - Requires new dependency

## Summary

Convert2MD handles problematic EMF/WMF files through:
1. **Early detection** (file validation)
2. **Process isolation** (timeouts)
3. **Intelligent fallback** (multiple tools)
4. **Graceful failure** (preserve originals)

This ensures batch conversions complete reliably even with malformed or pathological input files.
