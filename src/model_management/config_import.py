"""YAML/JSON configuration importer with secret-value rejection."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
from pathlib import Path
from typing import Any

from .domain import Budget, BudgetPeriod, Model, ModelStatus, Price, Provider
from .dto import ImportResult
from .facade import ModelManagementAPI


def import_configuration(api: ModelManagementAPI, source: Path | str | bytes) -> ImportResult:
    data = _load(source)
    _reject_embedded_secrets(data)
    provider_count = model_count = price_count = budget_count = 0
    for raw in data.get("providers", []):
        api.save_provider(Provider(
            raw["code"], raw.get("display_name", raw["code"]), raw.get("adapter", raw["code"]),
            raw.get("secret_ref"), raw.get("enabled", True), raw.get("metadata", {}),
        ))
        provider_count += 1
    for raw in data.get("models", []):
        model = Model(
            raw["provider_code"], raw["code"], raw.get("display_name", raw["code"]),
            int(raw["context_window"]), raw.get("max_output_tokens"),
            ModelStatus(raw.get("status", "active")), tuple(raw.get("capabilities", ["text"])),
            raw.get("rpm"), raw.get("tpm"), raw.get("rpd"), raw.get("concurrent_requests"),
            raw.get("metadata", {}),
        )
        api.save_model(model)
        model_count += 1
        if raw.get("price"):
            _save_price(api, model.id, raw["price"])
            price_count += 1
    for raw in data.get("prices", []):
        _save_price(api, raw["model_id"], raw)
        price_count += 1
    for raw in data.get("budgets", []):
        api.save_budget(Budget(raw["scope"], Decimal(str(raw["amount"])),
                               raw.get("currency", "USD"),
                               BudgetPeriod(raw.get("period", "monthly")),
                               Decimal(str(raw.get("warning_ratio", "0.8"))),
                               raw.get("enabled", True)))
        budget_count += 1
    return ImportResult(provider_count, model_count, price_count, budget_count)


def _save_price(api: ModelManagementAPI, model_id: str, raw: dict[str, Any]) -> None:
    api.save_price(Price(
        model_id, raw.get("currency", "USD"), _dec(raw.get("input_per_million")),
        _dec(raw.get("cached_input_per_million")), _dec(raw.get("output_per_million")),
        _dec(raw.get("image_each")),
        datetime.fromisoformat(raw["effective_from"]) if raw.get("effective_from")
        else datetime.now(timezone.utc), raw.get("source", "configuration"),
    ))


def _load(source: Path | str | bytes) -> dict[str, Any]:
    if isinstance(source, Path):
        text = source.read_text(encoding="utf-8")
        suffix = source.suffix.lower()
    else:
        text = source.decode() if isinstance(source, bytes) else source
        suffix = ""
    if suffix == ".json" or text.lstrip().startswith(("{", "[")):
        result = json.loads(text)
    else:
        try:
            import yaml
        except ImportError as error:
            raise RuntimeError("PyYAML is required to import YAML configuration") from error
        result = yaml.safe_load(text)
    if not isinstance(result, dict):
        raise ValueError("Configuration root must be an object")
    if str(result.get("schema_version", "1.0")) != "1.0":
        raise ValueError("Unsupported configuration schema_version")
    return result


def _reject_embedded_secrets(value: Any, path: str = "") -> None:
    forbidden = {"api_key", "apikey", "token", "secret", "password"}
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key.lower() in forbidden:
                raise ValueError(f"Embedded secret field is forbidden: {child_path}; use secret_ref")
            _reject_embedded_secrets(child, child_path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_embedded_secrets(child, f"{path}[{index}]")


def _dec(value: Any) -> Decimal | None:
    return Decimal(str(value)) if value is not None else None
