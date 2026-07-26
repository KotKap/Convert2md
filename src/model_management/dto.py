"""Serializable commands and DTOs shared by CLI, desktop and web adapters."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from .domain import PriceSnapshot, json_ready


class Serializable:
    schema_version = "1.0"

    def to_dict(self) -> dict[str, Any]:
        result = json_ready(self)
        result["schema_version"] = self.schema_version
        return result


@dataclass(frozen=True)
class ModelRequest(Serializable):
    model_id: str
    operation: str
    estimated_input_tokens: int
    requested_output_tokens: int = 0
    capabilities: tuple[str, ...] = ()
    image_count: int = 0
    scope: str = "application"
    document_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ValidationIssue(Serializable):
    code: str
    message: str
    field: str | None = None


@dataclass(frozen=True)
class ValidationResult(Serializable):
    allowed: bool
    errors: tuple[ValidationIssue, ...] = ()
    warnings: tuple[ValidationIssue, ...] = ()
    estimated_cost: Decimal | None = None
    selected_model_id: str | None = None


@dataclass(frozen=True)
class RegisterUsageCommand(Serializable):
    model_id: str
    operation: str
    input_tokens: int
    output_tokens: int = 0
    cached_input_tokens: int = 0
    reasoning_tokens: int = 0
    image_count: int = 0
    duration_ms: int = 0
    status: str = "success"
    request_id: str = field(default_factory=lambda: str(uuid4()))
    scope: str = "application"
    document_id: str | None = None
    provider_request_id: str | None = None
    error_code: str | None = None
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class UsageRecord(Serializable):
    request_id: str
    model_id: str
    provider_code: str
    operation: str
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    image_count: int
    duration_ms: int
    status: str
    total_cost: Decimal | None
    currency: str | None
    price_snapshot: PriceSnapshot | None
    occurred_at: datetime
    scope: str
    document_id: str | None
    provider_request_id: str | None
    error_code: str | None
    metadata: dict[str, Any]


@dataclass(frozen=True)
class UsageQuery(Serializable):
    model_id: str | None = None
    scope: str | None = None
    since: datetime | None = None
    until: datetime | None = None


@dataclass(frozen=True)
class UsageSummary(Serializable):
    request_count: int
    successful_requests: int
    failed_requests: int
    input_tokens: int
    output_tokens: int
    cached_input_tokens: int
    reasoning_tokens: int
    image_count: int
    total_cost: Decimal
    currency: str
    by_model: dict[str, dict[str, Any]]


@dataclass(frozen=True)
class BudgetStatus(Serializable):
    scope: str
    limit: Decimal
    consumed: Decimal
    remaining: Decimal
    currency: str
    exceeded: bool
    warning: bool


@dataclass(frozen=True)
class ImportResult(Serializable):
    providers: int
    models: int
    prices: int
    budgets: int
    warnings: tuple[str, ...] = ()
