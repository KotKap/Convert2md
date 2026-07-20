"""Safe, format-independent cleanup of generated Markdown."""

from __future__ import annotations

import re


class MarkdownPostProcessor:
    """Normalize converter output without damaging structural Markdown blocks."""

    _IMAGE_ATTRIBUTES = re.compile(
        r'(?P<image>!\[[^\]]*\]\([^\n)]*\))'
        r'[ \t]*\{(?=[^{}]*(?:width|height)\s*=)[^{}]*\}',
        flags=re.IGNORECASE | re.DOTALL,
    )
    _UNDERLINE = re.compile(r'\[([^\]\n]+)\]\{\.underline\}')
    _EMPTY_COMMENT = re.compile(r'^[ \t]*<!--\s*-->[ \t]*$', re.MULTILINE)
    _BOLD_BACKSLASH = re.compile(r'^[ \t]*\*\*\\\*\*[ \t]*$', re.MULTILINE)

    def process(self, markdown: str) -> str:
        """Apply all output-format requirements in a deterministic order."""
        markdown = self._IMAGE_ATTRIBUTES.sub(r'\g<image>', markdown)
        markdown = self._UNDERLINE.sub(r'<u>\1</u>', markdown)
        markdown = self._EMPTY_COMMENT.sub('', markdown)
        markdown = self._BOLD_BACKSLASH.sub('', markdown)
        markdown = self._collapse_text_paragraphs(markdown)
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        return markdown.strip()

    def _collapse_text_paragraphs(self, markdown: str) -> str:
        """Join wrapped prose while preserving Markdown block structure."""
        lines = markdown.splitlines()
        output: list[str] = []
        paragraph: list[str] = []
        in_fence = False
        in_html_table = False
        in_grid_table = False

        def flush_paragraph() -> None:
            if paragraph:
                output.append(' '.join(part.strip() for part in paragraph))
                paragraph.clear()

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('```', '~~~')):
                flush_paragraph()
                output.append(line)
                in_fence = not in_fence
                continue
            if in_fence:
                output.append(line)
                continue
            if re.match(r'^<table(?:\s|>)', stripped, re.IGNORECASE):
                flush_paragraph()
                in_html_table = True
            if in_html_table:
                output.append(line)
                if re.search(r'</table>', stripped, re.IGNORECASE):
                    in_html_table = False
                continue
            if re.match(r'^\+(?:[-=:]+\+)+$', stripped):
                flush_paragraph()
                in_grid_table = True
                output.append(line)
                continue
            if in_grid_table:
                output.append(line)
                if not stripped or not (stripped.startswith(('+', '|'))):
                    in_grid_table = False
                continue
            if not stripped:
                flush_paragraph()
                output.append('')
                continue
            if self._is_structural_line(stripped):
                flush_paragraph()
                output.append(line)
                continue
            paragraph.append(line)
        flush_paragraph()
        return '\n'.join(output)

    @staticmethod
    def _is_structural_line(line: str) -> bool:
        return bool(
            line.startswith(('#', '>', '|', '<', '![', '$$'))
            or re.match(r'^(?:[-+*]|\d+[.)])\s+', line)
            or re.match(r'^ {0,3}(?:---+|___+|\*\*\*+)\s*$', line)
            or re.match(r'^\[[^\]]+\]:\s+', line)
        )
