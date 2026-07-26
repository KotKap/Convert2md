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
from .model_management.dto import ModelRequest, RegisterUsageCommand


class DiagramConversionError(RuntimeError):
    def __init__(
        self, message: str, code: str = "conversion_error", retryable: bool = False,
        response_excerpt: str | None = None,
    ):
        super().__init__(message)
        self.code = code
        self.retryable = retryable
        self.response_excerpt = response_excerpt


@dataclass(frozen=True)
class DiagramResult:
    diagram_type: str
    mermaid_code: str
    actual_tokens: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    provider_request_id: str | None = None


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
                ),
            )
            payload = json.loads(response.text)
            code = validate_mermaid(payload["mermaid_code"])
            usage = getattr(response, "usage_metadata", None)
            actual_tokens = getattr(usage, "total_token_count", None) if usage else None
            return DiagramResult(
                payload["diagram_type"], code, actual_tokens,
                getattr(usage, "prompt_token_count", None) if usage else None,
                getattr(usage, "candidates_token_count", None) if usage else None,
                (getattr(usage, "cached_content_token_count", 0) or 0) if usage else 0,
                (getattr(usage, "thoughts_token_count", 0) or 0) if usage else 0,
                getattr(response, "response_id", None),
            )
        except DiagramConversionError:
            raise
        except Exception as error:
            raise classify_provider_error(error) from error


class ImageMermaidConverter:
    def __init__(
        self, provider, ledger, rate_limiter, sleep=time.sleep, max_retries: int = 2,
        model_management=None,
    ):
        self.provider = provider
        self.ledger = ledger
        self.rate_limiter = rate_limiter
        self.sleep = sleep
        self.max_retries = max_retries
        self.model_management = model_management

    def convert(self, image_path: Path, model: ModelLimits) -> Path:
        estimated_tokens = estimate_image_tokens(image_path)
        for attempt in range(self.max_retries + 1):
            started = time.monotonic()
            if self.model_management:
                model_id = f"google:{model.name}"
                validation = self.model_management.validate_request(ModelRequest(
                    model_id=model_id, operation="diagram_to_mermaid",
                    estimated_input_tokens=estimated_tokens, capabilities=("vision",),
                    image_count=1, document_id=str(image_path),
                ))
                if not validation.allowed:
                    message = "; ".join(issue.message for issue in validation.errors)
                    raise DiagramConversionError(message, validation.errors[0].code)
            self.rate_limiter.wait(model, estimated_tokens)
            try:
                result = self.provider.convert(image_path, model)
                output_path = image_path.with_suffix('.md')
                content = f"```mermaid\n{result.mermaid_code}\n```\n"
                self._atomic_write(output_path, content)
                self.ledger.record(
                    model.name, estimated_tokens, "success", actual_tokens=result.actual_tokens
                )
                self._record_usage(
                    model, image_path, result.input_tokens or result.actual_tokens or estimated_tokens,
                    result.output_tokens or 0, result.cached_input_tokens, result.reasoning_tokens,
                    "success", int((time.monotonic() - started) * 1000),
                    provider_request_id=result.provider_request_id,
                )
                return output_path
            except DiagramConversionError as error:
                self.ledger.record(model.name, estimated_tokens, "failed", error_code=error.code)
                self._record_usage(
                    model, image_path, estimated_tokens, 0, 0, 0, "failed",
                    int((time.monotonic() - started) * 1000), error_code=error.code,
                    metadata={
                        "attempt": attempt + 1,
                        "error_message": str(error)[:1000],
                        "response_excerpt": error.response_excerpt,
                    },
                )
                if not error.retryable or attempt >= self.max_retries:
                    raise
                self.sleep((2 ** attempt) + random.uniform(0, 0.5))
        raise AssertionError("unreachable")

    def _record_usage(
        self, model, image_path, input_tokens, output_tokens, cached_input_tokens,
        reasoning_tokens, status, duration_ms, provider_request_id=None, error_code=None,
        metadata=None,
    ) -> None:
        if not self.model_management:
            return
        self.model_management.register_usage(RegisterUsageCommand(
            model_id=f"google:{model.name}", operation="diagram_to_mermaid",
            input_tokens=input_tokens or 0, output_tokens=output_tokens or 0,
            cached_input_tokens=cached_input_tokens or 0,
            reasoning_tokens=reasoning_tokens or 0,
            image_count=1, duration_ms=duration_ms, status=status,
            document_id=str(image_path), provider_request_id=provider_request_id,
            error_code=error_code, metadata=metadata or {},
        ))

    @staticmethod
    def _atomic_write(output_path: Path, content: str) -> None:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=output_path.parent, delete=False
        ) as temp_file:
            temp_file.write(content)
            temp_path = Path(temp_file.name)
        temp_path.replace(output_path)


def validate_mermaid(code: str) -> str:
    code = code.strip().lstrip("\ufeff")
    if code.startswith("```"):
        lines = code.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines.pop()
        code = "\n".join(lines).strip()
    lines = [line.strip() for line in code.splitlines() if line.strip()]
    first_line = next(
        (line.lower() for line in lines if not line.startswith("%%")),
        "",
    )
    # Gemini occasionally returns a complete flowchart body beginning with a
    # top-level subgraph but omits the required root directive.
    if first_line.startswith("subgraph "):
        code = f"flowchart TD\n{code}"
        first_line = "flowchart td"
    valid_starts = (
        "flowchart", "graph", "sequencediagram", "classdiagram", "statediagram",
        "erdiagram", "journey", "gantt", "pie", "quadrantchart",
        "requirementdiagram", "gitgraph", "c4context", "c4container",
        "c4component", "c4dynamic", "c4deployment", "mindmap", "timeline",
        "zenuml", "sankey-beta", "xychart-beta", "block-beta", "packet-beta",
        "kanban", "architecture", "radar-beta", "treemap-beta",
    )
    if not code or not first_line.startswith(valid_starts):
        excerpt = code[:500]
        raise DiagramConversionError(
            f"The model returned unsupported Mermaid syntax beginning with: "
            f"{first_line[:120] or '<empty>'}",
            "invalid_mermaid",
            retryable=True,
            response_excerpt=excerpt,
        )
    return code


def classify_provider_error(error: Exception) -> DiagramConversionError:
    """Map Google SDK/HTTP failures to stable application error codes."""
    message = str(error)
    normalized = message.upper().replace("-", "_")
    if "429" in normalized or "RESOURCE_EXHAUSTED" in normalized or "QUOTA" in normalized:
        return DiagramConversionError(message, "quota", retryable=True)
    if (
        "401" in normalized or "403" in normalized or "UNAUTHENTICATED" in normalized
        or "PERMISSION_DENIED" in normalized or "API KEY" in normalized
    ):
        return DiagramConversionError(message, "authentication")
    if (
        "404" in normalized or "NOT_FOUND" in normalized
        or "NO LONGER AVAILABLE" in normalized or "UNSUPPORTED MODEL" in normalized
    ):
        return DiagramConversionError(message, "model_unavailable")
    if "400" in normalized or "INVALID_ARGUMENT" in normalized or "FAILED_PRECONDITION" in normalized:
        return DiagramConversionError(message, "invalid_request")
    transient_markers = (
        "408", "500", "502", "503", "504", "DEADLINE_EXCEEDED",
        "SERVICE_UNAVAILABLE", "INTERNAL", "TIMEOUT", "TIMED OUT",
        "CONNECTION", "CLIENT HAS BEEN CLOSED",
    )
    retryable = any(marker in normalized for marker in transient_markers)
    return DiagramConversionError(message, "provider_unavailable" if retryable else "provider_error",
                                  retryable=retryable)
