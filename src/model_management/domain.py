"""Domain types for the UI-independent model-management subsystem."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any


class ModelStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"


class BudgetPeriod(str, Enum):
    DAILY = "daily"
    MONTHLY = "monthly"
    TOTAL = "total"


@dataclass(frozen=True)
class Provider:
    code: str
    display_name: str
    adapter: str
    secret_ref: str | None = None
    enabled: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.secret_ref and "://" not in self.secret_ref:
            raise ValueError("Provider credentials must be represented by a secret_ref URI")


@dataclass(frozen=True)
class Model:
    provider_code: str
    code: str
    display_name: str
    context_window: int
    max_output_tokens: int | None = None
    status: ModelStatus = ModelStatus.ACTIVE
    capabilities: tuple[str, ...] = ("text",)
    rpm: int | None = None
    tpm: int | None = None
    rpd: int | None = None
    concurrent_requests: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def id(self) -> str:
        return f"{self.provider_code}:{self.code}"


@dataclass(frozen=True)
class Price:
    model_id: str
    currency: str = "USD"
    input_per_million: Decimal | None = None
    cached_input_per_million: Decimal | None = None
    output_per_million: Decimal | None = None
    image_each: Decimal | None = None
    effective_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    source: str = "manual"


@dataclass(frozen=True)
class Budget:
    scope: str
    amount: Decimal
    currency: str = "USD"
    period: BudgetPeriod = BudgetPeriod.MONTHLY
    warning_ratio: Decimal = Decimal("0.8")
    enabled: bool = True


@dataclass(frozen=True)
class PriceSnapshot:
    currency: str
    input_per_million: str | None
    cached_input_per_million: str | None
    output_per_million: str | None
    image_each: str | None
    effective_from: str
    source: str

    @classmethod
    def from_price(cls, price: Price) -> "PriceSnapshot":
        return cls(
            price.currency,
            _decimal_string(price.input_per_million),
            _decimal_string(price.cached_input_per_million),
            _decimal_string(price.output_per_million),
            _decimal_string(price.image_each),
            price.effective_from.isoformat(),
            price.source,
        )


def _decimal_string(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def json_ready(value: Any) -> Any:
    """Convert domain/DTO values into data accepted by JSON encoders."""
    if hasattr(value, "__dataclass_fields__"):
        return json_ready(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (datetime, Decimal)):
        return str(value)
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [json_ready(item) for item in value]
    return value
