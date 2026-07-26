"""Stable application facade; UI code should depend on this module only."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import re
from typing import Any

from .domain import Budget, BudgetPeriod, Model, ModelStatus, Price, PriceSnapshot, Provider
from .dto import (
    BudgetStatus, ModelRequest, RegisterUsageCommand, UsageQuery, UsageRecord,
    ValidationIssue, ValidationResult,
)
from .repository import SQLiteRepository


class ModelManagementAPI:
    api_version = "v1"

    def __init__(self, repository: SQLiteRepository):
        self.repository = repository

    def list_providers(self) -> list[Provider]:
        return self.repository.list_providers()

    def save_provider(self, provider: Provider) -> Provider:
        self.repository.upsert_provider(provider)
        return provider

    def list_models(self, include_disabled: bool = False) -> list[Model]:
        return self.repository.list_models(include_disabled)

    def get_model(self, model_id: str) -> Model:
        model = self.repository.get_model(model_id)
        if not model:
            raise LookupError(f"Unknown model: {model_id}")
        return model

    def save_model(self, model: Model) -> Model:
        if not any(provider.code == model.provider_code for provider in self.list_providers()):
            raise ValueError(f"Unknown provider: {model.provider_code}")
        if model.provider_code == "google" and re.match(r"^gemini-\d+-\d+-", model.code):
            raise ValueError(
                f"Invalid Google model ID '{model.code}': use dots in version numbers "
                "(for example, gemini-3.5-flash)"
            )
        self.repository.upsert_model(model)
        return model

    def save_price(self, price: Price) -> Price:
        self.get_model(price.model_id)
        self.repository.add_price(price)
        return price

    def list_prices(self) -> list[Price]:
        return self.repository.list_current_prices()

    def save_budget(self, budget: Budget) -> Budget:
        self.repository.upsert_budget(budget)
        return budget

    def list_budgets(self) -> list[Budget]:
        return self.repository.list_budgets()

    def estimate_cost(
        self, model_id: str, input_tokens: int, output_tokens: int = 0,
        cached_input_tokens: int = 0, image_count: int = 0,
        at: datetime | None = None,
    ) -> tuple[Decimal | None, PriceSnapshot | None]:
        price = self.repository.current_price(model_id, at)
        if not price:
            return None, None
        million = Decimal(1_000_000)
        cost = (
            Decimal(input_tokens) * (price.input_per_million or Decimal(0)) / million
            + Decimal(cached_input_tokens) * (price.cached_input_per_million or Decimal(0)) / million
            + Decimal(output_tokens) * (price.output_per_million or Decimal(0)) / million
            + Decimal(image_count) * (price.image_each or Decimal(0))
        )
        return cost, PriceSnapshot.from_price(price)

    def validate_request(self, request: ModelRequest) -> ValidationResult:
        errors, warnings = [], []
        model = self.repository.get_model(request.model_id)
        if not model:
            return ValidationResult(False, (ValidationIssue("unknown_model", "Model is not configured"),))
        if model.status not in {ModelStatus.ACTIVE, ModelStatus.EXPERIMENTAL}:
            errors.append(ValidationIssue("model_inactive", "Model is not active", "model_id"))
        missing = sorted(set(request.capabilities) - set(model.capabilities))
        if missing:
            errors.append(ValidationIssue("unsupported_capability",
                                          f"Model lacks capabilities: {', '.join(missing)}",
                                          "capabilities"))
        total = request.estimated_input_tokens + request.requested_output_tokens
        if total > model.context_window:
            errors.append(ValidationIssue("context_exceeded",
                                          f"Requested {total} tokens exceeds context window "
                                          f"{model.context_window}", "estimated_input_tokens"))
        if model.max_output_tokens is not None and request.requested_output_tokens > model.max_output_tokens:
            errors.append(ValidationIssue("output_exceeded", "Requested output exceeds model limit",
                                          "requested_output_tokens"))
        if model.tpm is not None and request.estimated_input_tokens > model.tpm:
            errors.append(ValidationIssue("tpm_exceeded", "Input exceeds per-minute token limit",
                                          "estimated_input_tokens"))
        cost, _ = self.estimate_cost(model.id, request.estimated_input_tokens,
                                     request.requested_output_tokens, image_count=request.image_count)
        if cost is None:
            warnings.append(ValidationIssue("price_unknown", "No active price; cost is unknown"))
        budget_status = self.get_budget_status(request.scope)
        if budget_status and cost is not None and budget_status.remaining < cost:
            errors.append(ValidationIssue("budget_exceeded", "Request would exceed the budget"))
        return ValidationResult(not errors, tuple(errors), tuple(warnings), cost,
                                model.id if not errors else None)

    def register_usage(self, command: RegisterUsageCommand) -> UsageRecord:
        model = self.get_model(command.model_id)
        cost, snapshot = self.estimate_cost(
            model.id, command.input_tokens, command.output_tokens,
            command.cached_input_tokens, command.image_count, command.occurred_at,
        )
        record = UsageRecord(
            command.request_id, model.id, model.provider_code, command.operation,
            command.input_tokens, command.output_tokens, command.cached_input_tokens,
            command.reasoning_tokens, command.image_count, command.duration_ms, command.status,
            cost, snapshot.currency if snapshot else None, snapshot, command.occurred_at,
            command.scope, command.document_id, command.provider_request_id,
            command.error_code, command.metadata,
        )
        self.repository.insert_usage(record)
        return record

    def get_usage_summary(self, query: UsageQuery | None = None):
        return self.repository.usage_summary(query or UsageQuery())

    def get_budget_status(self, scope: str) -> BudgetStatus | None:
        budget = self.repository.get_budget(scope)
        if not budget or not budget.enabled:
            return None
        now = datetime.now(timezone.utc)
        since = None
        if budget.period == BudgetPeriod.DAILY:
            since = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif budget.period == BudgetPeriod.MONTHLY:
            since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        consumed = self.get_usage_summary(UsageQuery(scope=scope, since=since)).total_cost
        remaining = max(Decimal(0), budget.amount - consumed)
        return BudgetStatus(scope, budget.amount, consumed, remaining, budget.currency,
                            consumed >= budget.amount,
                            consumed >= budget.amount * budget.warning_ratio)

    def get_form_schema(self, entity: str) -> dict[str, Any]:
        schemas = {
            "provider": [
                _field("code", "string", True), _field("display_name", "string", True),
                _field("adapter", "string", True),
                _field("secret_ref", "string", False, "Secret reference URI; never a secret value"),
                _field("enabled", "boolean", True),
            ],
            "model": [
                _field("provider_code", "string", True), _field("code", "string", True),
                _field("display_name", "string", True), _field("context_window", "integer", True, minimum=1),
                _field("max_output_tokens", "integer", False, minimum=1),
                _field("capabilities", "array", True),
            ],
            "budget": [
                _field("scope", "string", True), _field("amount", "decimal", True, minimum=0),
                _field("currency", "string", True), _field("period", "enum", True,
                                                          choices=[p.value for p in BudgetPeriod]),
            ],
        }
        if entity not in schemas:
            raise LookupError(f"Unknown form schema: {entity}")
        return {"schema_version": "1.0", "entity": entity, "fields": schemas[entity]}


def _field(name: str, kind: str, required: bool, help_text: str | None = None, **extra):
    return {"name": name, "type": kind, "required": required, "help": help_text, **extra}
