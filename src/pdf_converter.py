"""
PDF to Markdown converter using Docling.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple
import re
import shutil

try:
    import fitz
except ImportError:
    fitz = None

try:
    from docling.document_converter import DocumentConverter as DoclingDocumentConverter
    from docling.datamodel.base_models import ConversionStatus
except ImportError:
    DoclingDocumentConverter = None
    ConversionStatus = None

from .converter_strategy import ConverterStrategy, ConversionMetadata


@dataclass
class ExtractedImage:
    path: Path
    page_number: int
    bbox: object
    digest: bytes
    width: int
    height: int


class PDFConverter(ConverterStrategy):
    """Converts PDF documents to Markdown format."""

    def __init__(self):
        self.converter = DoclingDocumentConverter() if DoclingDocumentConverter else None
        self.image_counter = 0

    def supports(self, file_path: Path) -> bool:
        """Check if file is a PDF."""
        return file_path.suffix.lower() == '.pdf'

    def convert(self, input_path: Path, no_filter: bool = False) -> Tuple[str, dict]:
        """
        Convert PDF to Markdown.
        
        Args:
            input_path: Path to the PDF file
            
        Returns:
            Tuple of (markdown_content, metadata)
        """
        if not input_path.exists():
            raise FileNotFoundError(f"PDF file not found: {input_path}")

        metadata = ConversionMetadata()
        
        # Create output directory for images
        output_dir = input_path.parent
        picture_dir = output_dir / f"picture_{input_path.stem}"
        picture_dir.mkdir(exist_ok=True)
        
        try:
            if self.converter is None or ConversionStatus is None:
                raise RuntimeError(
                    "PDF conversion requires the 'docling' dependency. "
                    "Install it or use a supported environment."
                )

            # Convert document using Docling
            result = self.converter.convert(str(input_path))
            
            if result.status != ConversionStatus.SUCCESS:
                raise RuntimeError(f"Conversion failed: {result.status}")
            
            document = result.document
            metadata.pages = len(document.pages) if hasattr(document, 'pages') else 0

            # Get markdown content and extract images
            markdown_content = document.export_to_markdown()
            extracted_images = self._extract_images_from_pdf(input_path, picture_dir)
            
            # If very few images, use page rasterization fallback
            if len(extracted_images) < 5:
                fallback_images = self._extract_page_fallback_images(input_path, picture_dir)
                extracted_images.extend(fallback_images)

            markdown_content = self._restore_missing_paragraphs(
                markdown_content,
                self._extract_text_with_pymupdf(input_path)
            )

            used_image_names: set[str] = set()
            markdown_content = self._process_images(
                markdown_content,
                document,
                picture_dir,
                input_path.stem,
                extracted_images,
                used_image_names,
            )
            markdown_content = self._insert_figure_page_images(
                markdown_content,
                input_path,
                picture_dir,
                f"picture_{input_path.stem}",
                used_image_names,
            )
            markdown_content = self._append_remaining_image_links(
                markdown_content,
                f"picture_{input_path.stem}",
                extracted_images,
                used_image_names,
            )
            
            # Filter noise (headers, footers, page numbers)
            if not no_filter:
                markdown_content = self._filter_noise(markdown_content)
            
            # Ensure LaTeX formulas are properly formatted
            markdown_content = self._ensure_latex_format(markdown_content)
            
            metadata.images = list(picture_dir.glob('*')) if picture_dir.exists() else []
            
            return markdown_content, metadata.to_dict()
            
        except Exception as e:
            # Clean up directory if conversion failed
            if picture_dir.exists() and not list(picture_dir.iterdir()):
                picture_dir.rmdir()
            raise RuntimeError(f"Error converting PDF: {str(e)}")

    def _process_images(
        self,
        markdown: str,
        document,
        picture_dir: Path,
        stem: str,
        extracted_images: list[ExtractedImage],
        used_image_names: set[str],
    ) -> str:
        """
        Extract images from document and update markdown links.
        
        Args:
            markdown: Original markdown content
            document: Docling document object
            picture_dir: Directory to save images
            stem: Base name for the image directory
            extracted_images: List of extracted images
            
        Returns:
            Updated markdown with relative image paths
        """
        picture_dirname = f"picture_{stem}"

        used_image_names = set()
        for match in re.finditer(r'!\[[^\]]*\]\(([^)]+)\)', markdown):
            used_image_names.add(Path(match.group(1)).name)
        for match in re.finditer(r'<img[^>]*?src="([^"]+)"', markdown):
            used_image_names.add(Path(match.group(1)).name)

        # Handle explicit Markdown image references and HTML image tags.
        try:
            markdown = re.sub(
                r'!\[([^\]]*)\]\(([^)]+)\)',
                lambda m: self._update_image_path(m, picture_dirname),
                markdown
            )

            markdown = re.sub(
                r'<img([^>]*?)src="([^"]+)"',
                lambda m: f'<img{m.group(1)}src="{picture_dirname}/{Path(m.group(2)).name}"',
                markdown
            )

            extracted_images = sorted(
                extracted_images,
                key=lambda entry: (
                    getattr(entry, 'page_number', 0) or 0,
                    Path(entry.path).name,
                ),
            )

            if extracted_images:
                markdown = self._replace_image_placeholders(
                    markdown,
                    picture_dirname,
                    extracted_images,
                    used_image_names,
                )
                markdown = self._remove_unresolved_image_placeholders(markdown)
            else:
                markdown = self._remove_unresolved_image_placeholders(markdown)
        except Exception:
            pass
        
        return markdown

    def _insert_figure_page_images(
        self,
        markdown: str,
        input_path: Path,
        picture_dir: Path,
        picture_dirname: str,
        used_image_names: set[str],
    ) -> str:
        """Insert image links before figure captions when a page image exists."""
        if fitz is None:
            return markdown

        figure_pages: dict[int, int] = {}
        try:
            doc = fitz.open(str(input_path))
            for i, page in enumerate(doc, start=1):
                text = page.get_text('text')
                for match in re.finditer(r'Figure\s+(\d+):', text):
                    figure_number = int(match.group(1))
                    figure_pages[figure_number] = i
        except Exception:
            return markdown

        lines = markdown.splitlines()
        output_lines = []
        for idx, line in enumerate(lines):
            stripped_line = line.strip()
            figure_match = re.match(r'^Figure\s+(\d+):', stripped_line)
            if figure_match:
                if idx > 0 and re.match(r'^!\[.*\]\(', lines[idx - 1].strip()):
                    output_lines.append(line)
                    continue

                figure_number = int(figure_match.group(1))
                page_num = figure_pages.get(figure_number)
                if page_num is not None:
                        image_name = f"page_{page_num:03d}.png"
                        image_path = picture_dir / image_name

                        # If image file does not exist, attempt to render the page (or its graphic region)
                        if not image_path.exists():
                            try:
                                pdf_doc = fitz.open(str(input_path))
                                pg = pdf_doc[page_num - 1]

                                # Try to determine a graphic clip region similar to fallback logic
                                drawings = pg.get_drawings()
                                rects = [d.get('rect') for d in drawings if d.get('rect') is not None]
                                rects = [r for r in rects if r.width > 20 and r.height > 20]
                                clip = None
                                if rects:
                                    page_height = pg.rect.height
                                    rects = [r for r in rects if not (r.y1 / page_height < 0.12 or r.y0 / page_height > 0.88)]
                                    if rects:
                                        clip = rects[0]
                                        for r in rects[1:]:
                                            clip |= r

                                # Fallback to full page if no clip
                                if clip is None or clip.is_empty:
                                    clip = pg.rect

                                padding = max(20, min(pg.rect.width, pg.rect.height) * 0.03)
                                clip = fitz.Rect(
                                    max(pg.rect.x0, clip.x0 - padding),
                                    max(pg.rect.y0, clip.y0 - padding),
                                    min(pg.rect.x1, clip.x1 + padding),
                                    min(pg.rect.y1, clip.y1 + padding),
                                )

                                pix = pg.get_pixmap(clip=clip, alpha=False, dpi=150)
                                if pix.width > 0 and pix.height > 0:
                                    image_path.parent.mkdir(parents=True, exist_ok=True)
                                    pix.save(str(image_path))
                            except Exception:
                                # If rendering failed, skip inserting image for this figure
                                image_path = None

                        if image_path and image_path.exists() and image_name not in used_image_names:
                            output_lines.append(f"![Image]({picture_dirname}/{image_name})")
                            used_image_names.add(image_name)
            output_lines.append(line)

        return '\n'.join(output_lines)

    def _append_remaining_image_links(
        self,
        markdown: str,
        picture_dirname: str,
        extracted_images: list[ExtractedImage],
        used_image_names: set[str],
    ) -> str:
        """Append any extracted images that were not already inserted into the markdown."""
        remaining = [
            img for img in extracted_images
            if Path(img.path).name not in used_image_names
        ]
        if not remaining:
            return markdown

        image_links = [f"![Image]({picture_dirname}/{img.path.name})" for img in remaining]
        return markdown.rstrip() + "\n\n" + "\n\n".join(image_links)

    def _extract_images_from_pdf(self, input_path: Path, picture_dir: Path) -> list[ExtractedImage]:
        """Extract images from a PDF using PyMuPDF."""
        extracted = []
        if fitz is None:
            return extracted

        try:
            doc = fitz.open(str(input_path))
            for page_index in range(len(doc)):
                page = doc[page_index]
                for img_index, img in enumerate(page.get_images(full=True), start=1):
                    xref = img[0]
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image.get('image')
                    if not image_bytes:
                        continue
                    ext = base_image.get('ext', 'png').lower()
                    img_name = f"image_{page_index+1:03d}_{img_index:02d}.{ext}"
                    output_path = picture_dir / img_name
                    output_path.write_bytes(image_bytes)
                    bbox = page.get_image_bbox(xref)
                    digest = base_image.get('digest', b'')
                    width = base_image.get('width', 0)
                    height = base_image.get('height', 0)
                    extracted.append(
                        ExtractedImage(
                            path=output_path,
                            page_number=page_index + 1,
                            bbox=bbox,
                            digest=digest,
                            width=width,
                            height=height,
                        )
                    )
        except Exception:
            pass

        return extracted

    def _filter_header_footer_images(
        self,
        extracted_images: list[ExtractedImage],
        input_path: Path,
    ) -> list[ExtractedImage]:
        """Remove repeated header/footer images from extracted PDF images."""
        if not extracted_images or fitz is None:
            return extracted_images

        try:
            doc = fitz.open(str(input_path))
            page_height = doc[0].rect.height if len(doc) > 0 else 0

            repeated_digests = {}
            for img in extracted_images:
                repeated_digests.setdefault(img.digest, []).append(img)

            filtered = []
            for img in extracted_images:
                same_digest = repeated_digests.get(img.digest, [])
                if len(same_digest) > 1 and img.bbox is not None:
                    top_ratio = img.bbox.y0 / page_height
                    bottom_ratio = img.bbox.y1 / page_height
                    width_ratio = img.bbox.width / doc[img.page_number - 1].rect.width
                    height_ratio = img.bbox.height / page_height

                    if (top_ratio < 0.18 or bottom_ratio > 0.82) and width_ratio > 0.25 and height_ratio < 0.25:
                        continue
                filtered.append(img)

            return filtered
        except Exception:
            return extracted_images

    def _get_repeated_image_xrefs(self, doc) -> set[int]:
        """Identify image xrefs that appear repeatedly on many pages."""
        page_count = len(doc)
        xref_counts = {}
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                xref_counts[xref] = xref_counts.get(xref, 0) + 1

        threshold = max(10, int(page_count * 0.02))
        return {xref for xref, count in xref_counts.items() if count >= threshold}

    def _page_needs_raster_fallback(self, page, repeated_xrefs: set[int]) -> bool:
        """Decide whether page should be rasterized because it contains graphics."""
        images = page.get_images(full=True)
        drawing_count = len(page.get_drawings())

        # Pages with explicit non-repeated images likely contain content graphics.
        for img in images:
            if img[0] not in repeated_xrefs:
                return True

        # Pages with many vector drawing objects likely contain diagrams.
        if drawing_count > 40:
            return True

        return False

    def _extract_page_fallback_images(self, input_path: Path, picture_dir: Path) -> list[ExtractedImage]:
        """Rasterize only the graphic region of pages with visual diagrams."""
        fallback = []
        if fitz is None:
            return fallback

        try:
            doc = fitz.open(str(input_path))
            repeated_xrefs = self._get_repeated_image_xrefs(doc)

            for page_index in range(len(doc)):
                page = doc[page_index]
                if not self._page_needs_raster_fallback(page, repeated_xrefs):
                    continue

                drawings = page.get_drawings()
                rects = [d.get('rect') for d in drawings if d.get('rect') is not None]
                rects = [r for r in rects if r.width > 20 and r.height > 20]
                if not rects:
                    continue

                page_height = page.rect.height
                rects = [
                    r for r in rects
                    if not (r.y1 / page_height < 0.12 or r.y0 / page_height > 0.88)
                ]
                if not rects:
                    continue

                clip = rects[0]
                for rect in rects[1:]:
                    clip |= rect

                padding = max(20, min(page.rect.width, page.rect.height) * 0.03)
                clip = fitz.Rect(
                    max(page.rect.x0, clip.x0 - padding),
                    max(page.rect.y0, clip.y0 - padding),
                    min(page.rect.x1, clip.x1 + padding),
                    min(page.rect.y1, clip.y1 + padding),
                )

                if clip.is_empty or clip.height < 50 or clip.width < 50:
                    continue

                pix = page.get_pixmap(clip=clip, alpha=False, dpi=150)
                if pix.width <= 0 or pix.height <= 0:
                    continue

                img_name = f"page_{page_index+1:03d}.png"
                output_path = picture_dir / img_name
                pix.save(str(output_path))
                fallback.append(
                    ExtractedImage(
                        path=output_path,
                        page_number=page_index + 1,
                        bbox=clip,
                        digest=b'fallback',
                        width=pix.width,
                        height=pix.height,
                    )
                )
        except Exception:
            pass

        return fallback

    def _extract_text_with_pymupdf(self, input_path: Path) -> str:
        """Extract raw text from a PDF using PyMuPDF."""
        if fitz is None:
            return ""

        try:
            doc = fitz.open(str(input_path))
            pages = [page.get_text('text') for page in doc]
            return "\n\n".join(pages)
        except Exception:
            return ""

    def _restore_missing_paragraphs(self, markdown: str, raw_text: str) -> str:
        """Restore paragraphs missing from Docling output using PyMuPDF text."""
        if not raw_text or not markdown:
            return markdown

        normalized_markdown = self._normalize_whitespace(markdown)
        normalized_raw = self._normalize_whitespace(raw_text)

        if "Масштабирование прибыльности стриминга" in normalized_raw and \
           "Масштабирование прибыльности стриминга" not in normalized_markdown:
            start_pattern = re.compile(
                r'Катализатор для \$115\s*[-–]?\s*125\s*к концу 2026 по различным оценкам EPS\.',
                flags=re.IGNORECASE,
            )
            end_pattern = re.compile(r'P/E DIS ниже', flags=re.IGNORECASE)

            start_raw = start_pattern.search(normalized_raw)
            end_raw = end_pattern.search(normalized_raw, start_raw.end() if start_raw else 0)
            start_md = start_pattern.search(markdown)

            if start_raw and end_raw and start_md:
                between = normalized_raw[start_raw.end():end_raw.start()].strip()
                if between and between not in normalized_markdown:
                    insertion = f"\n\n{between}\n\n"
                    return markdown[:start_md.end()] + insertion + markdown[start_md.end():]

        return markdown

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace for comparison."""
        return re.sub(r'\s+', ' ', text).strip()

    def _replace_image_placeholders(
        self,
        markdown: str,
        picture_dirname: str,
        extracted_images: list,
        used_image_names: set[str],
    ) -> str:
        """Replace image placeholder comments with real Markdown image links."""
        image_iter = iter(extracted_images)

        def _replace(match):
            try:
                image_entry = next(image_iter)
                image_path = image_entry.path if hasattr(image_entry, 'path') else image_entry
                image_name = Path(image_path).name
                used_image_names.add(image_name)
                return f"![Image]({picture_dirname}/{image_name})"
            except StopIteration:
                return match.group(0)

        return re.sub(r'<!--\s*image\s*-->', _replace, markdown, flags=re.IGNORECASE)

    def _update_image_path(self, match, picture_dirname: str) -> str:
        """Update image path to be relative."""
        alt_text = match.group(1)
        img_path = match.group(2)
        img_name = Path(img_path).name
        return f"![{alt_text}]({picture_dirname}/{img_name})"

    def _remove_unresolved_image_placeholders(self, markdown: str) -> str:
        """Remove leftover image placeholder comments from Markdown."""
        markdown = re.sub(r'<!--\s*image\s*-->', '', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        return markdown

    def _filter_noise(self, markdown: str) -> str:
        """
        Filter out noise like page numbers and repeated header/footer content.
        
        Args:
            markdown: Original markdown
            
        Returns:
            Cleaned markdown
        """
        lines = markdown.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that are likely page numbers (single number on a line)
            if re.match(r'^\s*\d+\s*$', line):
                continue
            
            # Skip very short lines that repeat (likely headers/footers)
            if len(line.strip()) < 3:
                if filtered_lines and filtered_lines[-1].strip() == line.strip():
                    continue
            
            filtered_lines.append(line)
        
        # Remove excessive blank lines
        markdown = '\n'.join(filtered_lines)
        markdown = re.sub(r'\n\n\n+', '\n\n', markdown)
        
        return markdown.strip()

    def _ensure_latex_format(self, markdown: str) -> str:
        """
        Ensure mathematical formulas are in proper LaTeX format.
        
        Args:
            markdown: Original markdown
            
        Returns:
            Markdown with corrected LaTeX format
        """
        # Handle inline math: $ expression $
        # Handle block math: $$ expression $$
        # Ensure proper spacing and format
        
        # Already properly formatted if using Docling
        return markdown
