"""Local REST API used by the graphical Convert2MD web interface."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import base64
import json
import os
from pathlib import Path
import tempfile
import zipfile
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from .converter import DocumentConverter
from .diagram_converter import DiagramConversionError, GeminiDiagramProvider, ImageMermaidConverter
from .diagram_models import DEFAULT_MODELS, ModelLimits, estimate_image_tokens
from .model_management import (
    Budget, BudgetPeriod, Model, ModelStatus, Price, Provider, RegisterUsageCommand,
    UsageQuery, create_model_management_api, import_configuration, import_usage,
)
from .model_management.domain import json_ready
from .quota import QuotaLedger, RateLimiter


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def state_dir() -> Path:
    return Path(os.getenv("CONVERT2MD_STATE_DIR", Path.home() / ".convert2md"))


def create_web_app(data_dir: Path | None = None) -> FastAPI:
    root = data_dir or state_dir()
    management = create_model_management_api(root)
    ledger = QuotaLedger(root / "quota.sqlite3")
    app = FastAPI(title="Convert2MD API", version="1.0")
    app.state.management = management
    app.state.ledger = ledger
    app.add_middleware(
        CORSMiddleware,
        # The CLI permits a custom UI port. Restrict CORS to loopback hosts,
        # while accepting any port used by the local frontend.
        allow_origin_regex=r"^https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$",
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "repository": str(root / "model_management.sqlite3")}

    @app.get("/api/v1/dashboard")
    def dashboard():
        summary = management.get_usage_summary(UsageQuery())
        return {
            "models": len(management.list_models(include_disabled=True)),
            "providers": len(management.list_providers()),
            "requests": summary.request_count,
            "input_tokens": summary.input_tokens,
            "output_tokens": summary.output_tokens,
            "total_cost": str(summary.total_cost),
            "currency": summary.currency,
            "successful": summary.successful_requests,
            "failed": summary.failed_requests,
            "by_model": summary.by_model,
            "repository": str(root / "model_management.sqlite3"),
        }

    @app.get("/api/v1/providers")
    def providers():
        return [json_ready(item) for item in management.list_providers()]

    @app.post("/api/v1/providers")
    def save_provider(payload: ProviderPayload):
        try:
            return json_ready(management.save_provider(Provider(
                payload.code, payload.display_name, payload.adapter,
                payload.secret_ref or None, payload.enabled,
            )))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/v1/models")
    def models():
        return [json_ready(item) for item in management.list_models(include_disabled=True)]

    @app.post("/api/v1/models")
    def save_model(payload: ModelPayload):
        try:
            return json_ready(management.save_model(Model(
                payload.provider_code, payload.code, payload.display_name,
                payload.context_window, payload.max_output_tokens,
                ModelStatus(payload.status), tuple(payload.capabilities),
                payload.rpm, payload.tpm, payload.rpd, payload.concurrent_requests,
            )))
        except (ValueError, LookupError) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/v1/prices")
    def prices():
        return [json_ready(item) for item in management.list_prices()]

    @app.post("/api/v1/prices")
    def save_price(payload: PricePayload):
        try:
            price = Price(
                payload.model_id, payload.currency, _decimal(payload.input_per_million),
                _decimal(payload.cached_input_per_million),
                _decimal(payload.output_per_million), _decimal(payload.image_each),
                _timestamp(payload.effective_from), payload.source,
            )
            return json_ready(management.save_price(price))
        except (ValueError, LookupError) as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/v1/budgets")
    def budgets():
        return [json_ready(item) for item in management.list_budgets()]

    @app.post("/api/v1/budgets")
    def save_budget(payload: BudgetPayload):
        try:
            return json_ready(management.save_budget(Budget(
                payload.scope, Decimal(payload.amount), payload.currency,
                BudgetPeriod(payload.period), Decimal(payload.warning_ratio), payload.enabled,
            )))
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

    @app.get("/api/v1/usage")
    def usage(model_id: str | None = None, scope: str | None = None):
        return management.get_usage_summary(UsageQuery(model_id=model_id, scope=scope)).to_dict()

    @app.post("/api/v1/usage")
    def record_usage(payload: UsagePayload):
        try:
            record = management.register_usage(RegisterUsageCommand(
                model_id=payload.model_id, operation=payload.operation,
                input_tokens=payload.input_tokens, output_tokens=payload.output_tokens,
                cached_input_tokens=payload.cached_input_tokens,
                reasoning_tokens=payload.reasoning_tokens, image_count=payload.image_count,
                duration_ms=payload.duration_ms, status=payload.status,
                occurred_at=_timestamp(payload.occurred_at), scope=payload.scope,
                document_id=payload.document_id or None,
            ))
            return record.to_dict()
        except (ValueError, LookupError) as error:
            raise HTTPException(400, str(error)) from error

    @app.post("/api/v1/config/import")
    async def config_import(file: UploadFile = File(...)):
        suffix = Path(file.filename or "config.json").suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(await file.read())
            path = Path(temporary.name)
        try:
            return import_configuration(management, path).to_dict()
        except (ValueError, RuntimeError, KeyError) as error:
            raise HTTPException(400, str(error)) from error
        finally:
            path.unlink(missing_ok=True)

    @app.post("/api/v1/usage/import")
    async def usage_history_import(file: UploadFile = File(...)):
        suffix = Path(file.filename or "usage.json").suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
            temporary.write(await file.read())
            path = Path(temporary.name)
        try:
            return {"imported": import_usage(management, path)}
        except (ValueError, LookupError, json.JSONDecodeError) as error:
            raise HTTPException(400, str(error)) from error
        finally:
            path.unlink(missing_ok=True)

    @app.get("/api/v1/ui-schemas/{entity}")
    def form_schema(entity: str):
        try:
            return management.get_form_schema(entity)
        except LookupError as error:
            raise HTTPException(404, str(error)) from error

    @app.post("/api/v1/convert/document")
    async def convert_document(file: UploadFile = File(...), no_filter: bool = False):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".pdf", ".docx", ".doc"}:
            raise HTTPException(400, "Supported document formats: PDF, DOCX and DOC")
        with tempfile.TemporaryDirectory(prefix="convert2md-web-") as temporary:
            path = Path(temporary) / (file.filename or f"document{suffix}")
            path.write_bytes(await file.read())
            try:
                markdown, metadata = DocumentConverter().convert(path, no_filter=no_filter)
                markdown_path = path.with_suffix(".md")
                markdown_path.write_text(markdown, encoding="utf-8")
                assets = [
                    item for item in Path(temporary).rglob("*")
                    if item.is_file() and item != path and item != markdown_path
                ]
                archive = None
                if assets:
                    archive_path = Path(temporary) / f"{path.stem}.zip"
                    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as bundle:
                        bundle.write(markdown_path, markdown_path.name)
                        for asset in assets:
                            bundle.write(asset, asset.relative_to(temporary))
                    archive = base64.b64encode(archive_path.read_bytes()).decode("ascii")
                return {
                    "filename": f"{path.stem}.md", "markdown": markdown, "metadata": metadata,
                    "archive_filename": f"{path.stem}.zip" if archive else None,
                    "archive_base64": archive,
                }
            except Exception as error:
                raise HTTPException(500, str(error)) from error

    @app.post("/api/v1/convert/diagram")
    async def convert_diagram(file: UploadFile = File(...), model_id: str | None = None):
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg"}:
            raise HTTPException(400, "Supported diagram formats: PNG and JPG")
        selected_id = model_id or "google:gemini-3.1-flash-lite"
        if ":" not in selected_id or selected_id.split(":", 1)[0] != "google":
            raise HTTPException(400, "Diagram conversion currently requires a Google model")
        code = selected_id.split(":", 1)[1]
        try:
            managed_model = management.get_model(selected_id)
        except LookupError as error:
            raise HTTPException(400, str(error)) from error
        if managed_model.status.value not in {"active", "experimental"}:
            raise HTTPException(400, f"Model is not available for requests: {selected_id}")
        if "vision" not in managed_model.capabilities:
            raise HTTPException(400, f"Model does not support vision: {selected_id}")
        limits = ModelLimits(code, managed_model.rpm or 1, managed_model.tpm or 250_000,
                             managed_model.rpd or 1)
        with tempfile.TemporaryDirectory(prefix="convert2md-diagram-") as temporary:
            path = Path(temporary) / (file.filename or f"diagram{suffix}")
            path.write_bytes(await file.read())
            try:
                converter = ImageMermaidConverter(
                    GeminiDiagramProvider(), ledger, RateLimiter(ledger),
                    model_management=management,
                )
                output = converter.convert(path, limits)
                return {"filename": f"{path.stem}.md", "markdown": output.read_text(encoding="utf-8"),
                        "estimated_tokens": estimate_image_tokens(path)}
            except DiagramConversionError as error:
                raise HTTPException(400, f"{error.code}: {error}") from error

    return app


class ProviderPayload(BaseModel):
    code: str
    display_name: str
    adapter: str
    secret_ref: str = ""
    enabled: bool = True


class ModelPayload(BaseModel):
    provider_code: str
    code: str
    display_name: str
    context_window: int = Field(gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    status: str = "active"
    capabilities: list[str] = ["text"]
    rpm: int | None = Field(default=None, gt=0)
    tpm: int | None = Field(default=None, gt=0)
    rpd: int | None = Field(default=None, gt=0)
    concurrent_requests: int | None = Field(default=None, gt=0)


class PricePayload(BaseModel):
    model_id: str
    currency: str = "USD"
    input_per_million: str | None = None
    cached_input_per_million: str | None = None
    output_per_million: str | None = None
    image_each: str | None = None
    effective_from: str | None = None
    source: str = "manual"


class BudgetPayload(BaseModel):
    scope: str
    amount: str
    currency: str = "USD"
    period: str = "monthly"
    warning_ratio: str = "0.8"
    enabled: bool = True


class UsagePayload(BaseModel):
    model_id: str
    operation: str = "historical"
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(default=0, ge=0)
    cached_input_tokens: int = Field(default=0, ge=0)
    reasoning_tokens: int = Field(default=0, ge=0)
    image_count: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    status: str = "success"
    occurred_at: str | None = None
    scope: str = "application"
    document_id: str = ""


def _decimal(value: str | None) -> Decimal | None:
    return Decimal(value) if value not in (None, "") else None


def _timestamp(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
