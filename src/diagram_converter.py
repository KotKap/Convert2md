"""Image-to-Mermaid conversion service and Gemini provider."""

from __future__ import annotations

from dataclasses import dataclass
import json
import mimetypes
import os
from pathlib import Path
import random
import tempfile
import time

from .diagram_models import ModelLimits, estimate_image_tokens


class DiagramConversionError(RuntimeError):
    def __init__(self, message: str, code: str = "conversion_error", retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


@dataclass(frozen=True)
class DiagramResult:
    diagram_type: str
    mermaid_code: str
    actual_tokens: int | None = None


class GeminiDiagramProvider:
    PROMPT = (
        "Analyze the diagram. Reproduce its text, nodes and connections as valid Mermaid. "
        "Return JSON only with diagram_type and mermaid_code. Do not include Markdown fences."
    )

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise DiagramConversionError("GEMINI_API_KEY is not configured", "authentication")

    def convert(self, image_path: Path, model: ModelLimits) -> DiagramResult:
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise DiagramConversionError(
                "Install optional Gemini dependencies to convert diagrams", "dependency"
            ) from error

        mime_type, _ = mimetypes.guess_type(image_path.name)
        if mime_type not in {"image/png", "image/jpeg"}:
            raise DiagramConversionError(f"Unsupported image type: {image_path.suffix}", "input")

        schema = {
            "type": "object",
            "properties": {
                "diagram_type": {"type": "string"},
                "mermaid_code": {"type": "string"},
            },
            "required": ["diagram_type", "mermaid_code"],
        }
        try:
            client = genai.Client(api_key=self.api_key)
            response = client.models.generate_content(
                model=model.name,
                contents=[
                    types.Part.from_bytes(data=image_path.read_bytes(), mime_type=mime_type),
                    self.PROMPT,
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1,
                ),
            )
            payload = json.loads(response.text)
            code = validate_mermaid(payload["mermaid_code"])
            usage = getattr(response, "usage_metadata", None)
            actual_tokens = getattr(usage, "total_token_count", None) if usage else None
            return DiagramResult(payload["diagram_type"], code, actual_tokens)
        except DiagramConversionError:
            raise
        except Exception as error:
            message = str(error)
            lowered = message.lower()
            if "429" in lowered or "resource_exhausted" in lowered or "quota" in lowered:
                raise DiagramConversionError(message, "quota", retryable=False) from error
            if "401" in lowered or "403" in lowered or "api key" in lowered:
                raise DiagramConversionError(message, "authentication", retryable=False) from error
            if "not found" in lowered or "unsupported" in lowered:
                raise DiagramConversionError(message, "model_unavailable", retryable=False) from error
            raise DiagramConversionError(message, "provider_error", retryable=True) from error


class ImageMermaidConverter:
    def __init__(self, provider, ledger, rate_limiter, sleep=time.sleep, max_retries: int = 2):
        self.provider = provider
        self.ledger = ledger
        self.rate_limiter = rate_limiter
        self.sleep = sleep
        self.max_retries = max_retries

    def convert(self, image_path: Path, model: ModelLimits) -> Path:
        estimated_tokens = estimate_image_tokens(image_path)
        for attempt in range(self.max_retries + 1):
            self.rate_limiter.wait(model, estimated_tokens)
            try:
                result = self.provider.convert(image_path, model)
                output_path = image_path.with_suffix('.md')
                content = f"```mermaid\n{result.mermaid_code}\n```\n"
                self._atomic_write(output_path, content)
                self.ledger.record(
                    model.name, estimated_tokens, "success", actual_tokens=result.actual_tokens
                )
                return output_path
            except DiagramConversionError as error:
                self.ledger.record(model.name, estimated_tokens, "failed", error_code=error.code)
                if not error.retryable or attempt >= self.max_retries:
                    raise
                self.sleep((2 ** attempt) + random.uniform(0, 0.5))
        raise AssertionError("unreachable")

    @staticmethod
    def _atomic_write(output_path: Path, content: str) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=output_path.parent, delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(output_path)


def validate_mermaid(code: str) -> str:
    code = code.strip()
    if code.startswith("```"):
        code = code.removeprefix("```mermaid").removeprefix("```")
        code = code.removesuffix("```").strip()
    first_line = code.splitlines()[0].strip().lower() if code else ""
    valid_starts = (
        "flowchart", "graph", "sequencediagram", "classdiagram", "statediagram",
        "erdiagram", "journey", "gantt", "mindmap", "timeline", "architecture",
    )
    if not code or not first_line.startswith(valid_starts):
        raise DiagramConversionError("The model returned invalid Mermaid code", "invalid_mermaid")
    return code
