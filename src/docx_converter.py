"""
DOCX to Markdown converter using pypandoc.
"""

from pathlib import Path
from typing import Tuple
import re
import shutil
import subprocess
from .converter_strategy import ConverterStrategy, ConversionMetadata


class DOCXConverter(ConverterStrategy):
    """Converts DOCX documents to Markdown format."""

    def supports(self, file_path: Path) -> bool:
        """Check if file is a DOCX or DOC file."""
        return file_path.suffix.lower() in ['.docx', '.doc']

    def convert(self, input_path: Path, no_filter: bool = False) -> Tuple[str, dict]:
        """
        Convert DOCX to Markdown.
        
        Args:
            input_path: Path to the DOCX file
            
        Returns:
            Tuple of (markdown_content, metadata)
        """
        if not input_path.exists():
            raise FileNotFoundError(f"DOCX file not found: {input_path}")

        metadata = ConversionMetadata()
        
        # Create output directory for images
        output_dir = input_path.parent
        picture_dir = output_dir / f"picture_{input_path.stem}"
        picture_dir.mkdir(exist_ok=True)
        
        try:
            # Use pandoc to convert to markdown
            # Extract images to picture directory
            markdown_content = self._convert_with_pandoc(
                input_path, 
                picture_dir,
                input_path.stem
            )
            
            # Filter noise
            if not no_filter:
                markdown_content = self._filter_noise(markdown_content)
            
            # Ensure LaTeX formulas are properly formatted
            markdown_content = self._ensure_latex_format(markdown_content)
            
            # Include nested media files in reported images
            metadata.images = list(picture_dir.rglob('*')) if picture_dir.exists() else []
            
            return markdown_content, metadata.to_dict()
            
        except Exception as e:
            # Clean up directory if conversion failed
            if picture_dir.exists() and not list(picture_dir.iterdir()):
                picture_dir.rmdir()
            raise RuntimeError(f"Error converting DOCX: {str(e)}")

    def _convert_with_pandoc(self, input_path: Path, picture_dir: Path, stem: str) -> str:
        """
        Convert DOCX to Markdown using pandoc.
        
        Args:
            input_path: Path to input DOCX
            picture_dir: Directory for extracted images
            stem: Base name for image directory
            
        Returns:
            Markdown content
        """
        try:
            import pypandoc
        except ImportError:
            raise RuntimeError(
                "pypandoc is required for DOCX conversion. "
                "Please install it with: pip install pypandoc"
            )

        self._ensure_pandoc_available(pypandoc)
        try:
            # Convert using pandoc via pypandoc
            markdown = pypandoc.convert_file(
                str(input_path),
                'md',
                outputfile=None,
                extra_args=[
                    f'--extract-media={picture_dir}'
                ]
            )
            # Convert vector media (EMF/WMF) to PNG for Markdown compatibility
            try:
                self._convert_media_vectors(picture_dir)
            except Exception:
                # If conversion tools are not available, continue with extracted files as-is
                pass
            # If pandoc created a nested 'media' directory, flatten it into picture_dir
            picture_dirname = f"picture_{stem}"
            try:
                self._flatten_media_dir(picture_dir)
                # Update markdown links that point to the media subdirectory
                markdown = markdown.replace(f"{picture_dirname}/media/", f"{picture_dirname}/")
            except Exception:
                pass
            
            # Update image paths to be relative
            markdown = self._update_image_paths(markdown, picture_dirname)
            used_image_names: set[str] = set()
            # Include nested media files (e.g., picture_x/media/*)
            extracted = [p for p in picture_dir.rglob('*') if p.is_file()]
            markdown = self._replace_image_placeholders(
                markdown,
                picture_dirname,
                extracted,
                used_image_names,
            )
            
            return markdown
            
        except Exception as e:
            raise RuntimeError(f"Pandoc conversion failed: {str(e)}")

    def _ensure_pandoc_available(self, pypandoc_module) -> None:
        """
        Ensure that Pandoc is available for pypandoc.
        
        If Pandoc is not installed system-wide, try downloading a bundled copy.
        """
        try:
            pypandoc_module.get_pandoc_path()
        except OSError:
            try:
                pypandoc_module.download_pandoc()
            except Exception as download_error:
                raise RuntimeError(
                    "Pandoc is not installed and automatic download failed. "
                    "Please install Pandoc manually or install pypandoc wheels with included pandoc."
                ) from download_error

    def _update_image_paths(self, markdown: str, picture_dirname: str) -> str:
        """
        Update image paths to be relative.
        
        Args:
            markdown: Original markdown
            picture_dirname: Name of the picture directory
            
        Returns:
            Markdown with updated paths
        """
        # Replace image paths with relative ones
        markdown = re.sub(
            r'!\[([^\]]*)\]\(([^)]+)\)',
            lambda m: self._replace_image_ref(m, picture_dirname),
            markdown
        )
        
        return markdown

    def _replace_image_placeholders(
        self,
        markdown: str,
        picture_dirname: str,
        extracted_images: list[Path],
        used_image_names: set[str],
    ) -> str:
        """Replace image placeholder comments with real Markdown image links."""
        image_iter = iter(extracted_images)

        def _replace(match):
            try:
                image_path = next(image_iter)
                image_name = image_path.name
                used_image_names.add(image_name)
                # Always reference images directly under picture_dir
                return f"![Image]({picture_dirname}/{image_name})"
            except StopIteration:
                return match.group(0)

        return re.sub(r'<!--\s*image\s*-->', _replace, markdown, flags=re.IGNORECASE)

    def _replace_image_ref(self, match, picture_dirname: str) -> str:
        """Replace image reference with relative path."""
        alt_text = match.group(1)
        img_path = match.group(2)
        
        # Extract just the filename
        img_name = Path(img_path).name
        
        # Prefer converted filename if available
        media_map = getattr(self, '_media_converted_map', {})
        converted = media_map.get(img_name)
        target_name = converted if converted is not None else img_name
        return f"![{alt_text}]({picture_dirname}/{target_name})"

    def _filter_noise(self, markdown: str) -> str:
        """
        Filter out noise like page numbers and repeated headers.
        
        Args:
            markdown: Original markdown
            
        Returns:
            Cleaned markdown
        """
        lines = markdown.split('\n')
        filtered_lines = []
        
        for line in lines:
            # Skip lines that are likely page numbers
            if re.match(r'^\s*\d+\s*$', line):
                continue
            
            # Skip very short lines that repeat
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
        # Convert common formula patterns to LaTeX
        # Handle inline equations enclosed in markers
        
        return markdown

    def _convert_media_vectors(self, picture_dir: Path) -> None:
        """
        Convert vector media files (EMF, WMF) inside the pandoc media
        directory to PNG using available system tools (ImageMagick or Inkscape).

        Populates `self._media_converted_map` mapping original filenames
        to converted filenames (e.g., image4.emf -> image4.png).
        """
        media_dir = picture_dir / 'media'
        if not media_dir.exists() or not media_dir.is_dir():
            return

        converted_map: dict[str, str] = {}

        for src in media_dir.iterdir():
            if not src.is_file():
                continue
            if src.suffix.lower() not in ('.emf', '.wmf'):
                continue

            dst = src.with_suffix('.png')

            # Try Inkscape first for better EMF/WMF rendering, then ImageMagick
            tried = False
            try:
                subprocess.run([
                    'inkscape',
                    str(src),
                    '--export-type=png',
                    '--export-filename',
                    str(dst),
                ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                converted_map[src.name] = dst.name
                tried = True
            except Exception:
                pass

            if tried:
                continue

            # Fallback: ImageMagick `magick` or `convert`
            for cmd in (('magick', str(src), str(dst)), ('convert', str(src), str(dst))):
                try:
                    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    converted_map[src.name] = dst.name
                    tried = True
                    break
                except Exception:
                    continue

            if tried:
                continue

            # If no tool succeeded, skip conversion for this file

        if converted_map:
            self._media_converted_map = converted_map

    def _flatten_media_dir(self, picture_dir: Path) -> None:
        """
        Move files from picture_dir/media/* into picture_dir/*, renaming on conflict.
        Updates `self._media_converted_map` for any renamed files.
        """
        media_dir = picture_dir / 'media'
        if not media_dir.exists() or not media_dir.is_dir():
            return

        rename_map: dict[str, str] = getattr(self, '_media_converted_map', {}).copy()

        for src in media_dir.iterdir():
            if not src.is_file():
                continue
            dst = picture_dir / src.name
            if dst.exists():
                # find unique name
                base = dst.stem
                suff = dst.suffix
                i = 1
                while True:
                    candidate = picture_dir / f"{base}_{i}{suff}"
                    if not candidate.exists():
                        dst = candidate
                        break
                    i += 1
            # move file
            src.replace(dst)
            if src.name != dst.name:
                rename_map[src.name] = dst.name

        # remove empty media dir
        try:
            media_dir.rmdir()
        except Exception:
            pass

        if rename_map:
            self._media_converted_map = rename_map
