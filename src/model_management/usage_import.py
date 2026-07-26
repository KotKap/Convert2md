"""Import historical usage exported by providers or assembled by users."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from .dto import RegisterUsageCommand
from .facade import ModelManagementAPI


def import_usage(api: ModelManagementAPI, source: Path) -> int:
    """Import CSV, JSON or JSONL records and return the number inserted."""
    records = _read_records(source)
    for row in records:
        api.register_usage(_command(row))
    return len(records)


def _read_records(source: Path) -> list[dict[str, Any]]:
    text = source.read_text(encoding="utf-8")
    if source.suffix.lower() == ".csv":
        return list(csv.DictReader(text.splitlines()))
    if source.suffix.lower() in {".jsonl", ".ndjson"}:
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    payload = json.loads(text)
    if isinstance(payload, dict):
        payload = payload.get("usage", [payload])
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError("Usage import must contain an object or a list of objects")
    return payload


def _command(row: dict[str, Any]) -> RegisterUsageCommand:
    occurred_at = row.get("occurred_at")
    if occurred_at:
        occurred_at = datetime.fromisoformat(str(occurred_at).replace("Z", "+00:00"))
        if occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
    else:
        occurred_at = datetime.now(timezone.utc)
    return RegisterUsageCommand(
        model_id=_required(row, "model_id"),
        operation=str(row.get("operation", "historical")),
        input_tokens=_integer(row, "input_tokens"),
        output_tokens=_integer(row, "output_tokens"),
        cached_input_tokens=_integer(row, "cached_input_tokens"),
        reasoning_tokens=_integer(row, "reasoning_tokens"),
        image_count=_integer(row, "image_count"),
        duration_ms=_integer(row, "duration_ms"),
        status=str(row.get("status", "success")),
        request_id=str(row["request_id"]) if row.get("request_id") else str(uuid4()),
        scope=str(row.get("scope", "application")),
        document_id=_optional(row, "document_id"),
        provider_request_id=_optional(row, "provider_request_id"),
        error_code=_optional(row, "error_code"),
        occurred_at=occurred_at,
        metadata=row.get("metadata", {}) if isinstance(row.get("metadata", {}), dict) else {},
    )


def _required(row: dict[str, Any], name: str) -> str:
    value = row.get(name)
    if value in (None, ""):
        raise ValueError(f"Missing required usage field: {name}")
    return str(value)


def _integer(row: dict[str, Any], name: str) -> int:
    value = int(row.get(name) or 0)
    if value < 0:
        raise ValueError(f"Usage field cannot be negative: {name}")
    return value


def _optional(row: dict[str, Any], name: str) -> str | None:
    return str(row[name]) if row.get(name) not in (None, "") else None
