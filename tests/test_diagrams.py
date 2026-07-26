from pathlib import Path

import pytest

from src.diagram_converter import (
    DiagramConversionError,
    DiagramResult,
    ImageMermaidConverter,
    classify_provider_error,
    validate_mermaid,
)
from src.diagram_models import BatchPlanner, ModelLimits
from src.quota import QuotaLedger, RateLimiter


def test_quota_ledger_persists_daily_requests(tmp_path):
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")
    ledger.record("model-a", 100, "success", actual_tokens=80)
    ledger.record("model-a", 100, "failed", error_code="quota")
    assert QuotaLedger(tmp_path / "quota.sqlite3").requests_today("model-a") == 2


def test_batch_planner_uses_another_model_for_remainder(tmp_path):
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")
    models = (
        ModelLimits("first", rpm=5, tpm=100_000, rpd=2),
        ModelLimits("second", rpm=10, tpm=100_000, rpd=3),
    )
    files = [tmp_path / f"image-{number}.png" for number in range(6)]

    plan = BatchPlanner(ledger, models).plan(files, preferred_model="first")

    assert [item.model.name for item in plan.assignments] == [
        "first", "first", "second", "second", "second"
    ]
    assert plan.unassigned == (files[-1],)

    replacement = BatchPlanner(ledger, models).plan(files, excluded_models={"first"})
    assert all(item.model.name == "second" for item in replacement.assignments)
    assert len(replacement.assignments) == 3


def test_rate_limiter_rejects_request_larger_than_tpm(tmp_path):
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")
    limiter = RateLimiter(ledger, sleep=lambda _: None)
    model = ModelLimits("small", rpm=1, tpm=100, rpd=10)
    with pytest.raises(ValueError, match="exceeds TPM"):
        limiter.wait(model, 101)


def test_validate_mermaid_accepts_and_removes_fences():
    assert validate_mermaid("```mermaid\nflowchart TD\nA --> B\n```") == (
        "flowchart TD\nA --> B"
    )


def test_validate_mermaid_repairs_flowchart_body_without_root_directive():
    source = "subgraph sales [Sales]\nA --> B\nend"
    assert validate_mermaid(source) == f"flowchart TD\n{source}"


def test_validate_mermaid_rejects_plain_text():
    with pytest.raises(DiagramConversionError) as error:
        validate_mermaid("This is not Mermaid")
    assert error.value.code == "invalid_mermaid"
    assert error.value.retryable
    assert error.value.response_excerpt == "This is not Mermaid"


@pytest.mark.parametrize("source", [
    "classDiagram\nclass A",
    "requirementDiagram\nrequirement test { id: 1 }",
    "block-beta\ncolumns 1\nA",
    "sankey-beta\nA,B,1",
    "C4Context\nPerson(user, User)",
])
def test_validate_mermaid_accepts_supported_diagram_families(source):
    assert validate_mermaid(source) == source


@pytest.mark.parametrize(("message", "code", "retryable"), [
    ("404 NOT_FOUND: model is no longer available", "model_unavailable", False),
    ("400 INVALID_ARGUMENT: malformed request", "invalid_request", False),
    ("503 UNAVAILABLE: service overloaded", "provider_unavailable", True),
    ("429 RESOURCE_EXHAUSTED: quota", "quota", True),
])
def test_provider_errors_are_classified_for_retry_policy(message, code, retryable):
    error = classify_provider_error(RuntimeError(message))
    assert error.code == code
    assert error.retryable is retryable


def test_image_converter_writes_same_name_atomically(tmp_path):
    image_path = tmp_path / "scheme.png"
    image_path.write_bytes(b"not needed by fake provider")
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")

    class Provider:
        def convert(self, image_path, model):
            return DiagramResult("flowchart", "flowchart TD\nA --> B", 42)

    class Limiter:
        def wait(self, model, estimated_tokens):
            pass

    model = ModelLimits("fake", rpm=1, tpm=10_000, rpd=10)
    output = ImageMermaidConverter(Provider(), ledger, Limiter()).convert(image_path, model)

    assert output == tmp_path / "scheme.md"
    assert output.read_text() == "```mermaid\nflowchart TD\nA --> B\n```\n"
    assert ledger.requests_today("fake") == 1


def test_image_converter_retries_temporary_errors_and_counts_attempts(tmp_path):
    image_path = tmp_path / "scheme.png"
    image_path.write_bytes(b"fake")
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")

    class Provider:
        attempts = 0

        def convert(self, image_path, model):
            self.attempts += 1
            if self.attempts == 1:
                raise DiagramConversionError("temporary", "provider_error", retryable=True)
            return DiagramResult("flowchart", "flowchart TD\nA --> B", 42)

    class Limiter:
        def wait(self, model, estimated_tokens):
            pass

    provider = Provider()
    model = ModelLimits("fake", rpm=5, tpm=10_000, rpd=10)
    converter = ImageMermaidConverter(
        provider, ledger, Limiter(), sleep=lambda _: None, max_retries=2
    )
    converter.convert(image_path, model)

    assert provider.attempts == 2
    assert ledger.requests_today("fake") == 2


def test_image_converter_normalizes_nullable_provider_usage(tmp_path):
    image_path = tmp_path / "scheme.png"
    image_path.write_bytes(b"fake")
    ledger = QuotaLedger(tmp_path / "quota.sqlite3")

    class Provider:
        def convert(self, image_path, model):
            return DiagramResult(
                "flowchart", "flowchart TD\nA --> B", 42, 30, 12,
                cached_input_tokens=None, reasoning_tokens=None,
            )

    class Limiter:
        def wait(self, model, estimated_tokens):
            pass

    class Management:
        command = None

        def validate_request(self, request):
            return type("Result", (), {"allowed": True, "errors": []})()

        def register_usage(self, command):
            self.command = command

    management = Management()
    ImageMermaidConverter(
        Provider(), ledger, Limiter(), model_management=management
    ).convert(image_path, ModelLimits("fake", 1, 10_000, 10))

    assert management.command.cached_input_tokens == 0
    assert management.command.reasoning_tokens == 0
