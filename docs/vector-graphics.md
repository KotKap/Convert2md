# Vector graphics and EMF/WMF safety

DOCX files can contain Windows Enhanced Metafile (`.emf`) and Windows Metafile
(`.wmf`) graphics. Most Markdown renderers cannot display these formats, so
Convert2MD converts them to PNG.

## Conversion order

The current order is:

1. LibreOffice Draw in headless mode;
2. Inkscape;
3. ImageMagick (`magick` or `convert`);
4. preserve the original EMF/WMF when every converter fails.

LibreOffice is preferred because valid Office-generated EMFs can crash the
native EMF importer in Inkscape 1.4.x.

## Safety measures

- EMF header and declared-size validation.
- Separate headless LibreOffice profile for each conversion.
- 30-second timeout for every external converter.
- PNG readability and dimension validation.
- Removal of partial or invalid raster output.
- Automatic fallback to the next converter.
- Preservation of the original vector resource on total failure.

## Inkscape 1.4.4 incident

The issue was reproduced with:

```text
GB922_Sales_v26.0.docx
```

Several structurally valid embedded EMFs terminated Inkscape 1.4.4 with
`EXC_BAD_ACCESS (SIGSEGV)` inside:

```text
Inkscape::Extension::Internal::Emf::myEnhMetaFileProc
```

This was an Inkscape importer crash rather than a corrupt DOCX or a Python
exception. ImageMagick also failed because its EMF delegate expected an
unavailable `libreoffice` executable.

Headless `soffice` successfully converted all 19 embedded EMFs. Convert2MD was
therefore changed to use LibreOffice Draw before Inkscape. A complete conversion
of the document produced 19 PNG images without invoking the crashing path.

The original crash report is retained at
[diagnostics/inkscape-1.4.4-crash.txt](diagnostics/inkscape-1.4.4-crash.txt).

## Recommended installation

macOS:

```bash
brew install --cask libreoffice
brew install --cask inkscape
brew install imagemagick
```

Ubuntu/Debian:

```bash
sudo apt-get install libreoffice inkscape imagemagick
```

Only one converter is required, but LibreOffice is recommended for DOCX files
containing Office-generated EMF graphics.
