"""Composition root and built-in catalog."""

from __future__ import annotations

from pathlib import Path

from .domain import Model, ModelStatus, Provider
from .facade import ModelManagementAPI
from .repository import SQLiteRepository


BUILTIN_MODELS = (
    Model("google", "gemini-3.1-flash-lite", "Gemini 3.1 Flash Lite", 1_000_000, 65_536,
          capabilities=("text", "vision", "structured_output"), rpm=15, tpm=250_000, rpd=500),
    Model("google", "gemini-3.5-flash-lite", "Gemini 3.5 Flash Lite", 1_000_000, 65_536,
          capabilities=("text", "vision", "structured_output"), rpm=10, tpm=250_000, rpd=100),
    Model("google", "gemini-3.5-flash", "Gemini 3.5 Flash", 1_000_000, 65_536,
          capabilities=("text", "vision", "structured_output"), rpm=5, tpm=250_000, rpd=20),
    Model("google", "gemini-3.6-flash", "Gemini 3.6 Flash", 1_000_000, 65_536,
          capabilities=("text", "vision", "structured_output"), rpm=5, tpm=250_000, rpd=20),
    Model("google", "gemini-3-flash-preview", "Gemini 3 Flash Preview", 1_000_000, 65_536,
          ModelStatus.EXPERIMENTAL, ("text", "vision", "structured_output"),
          rpm=5, tpm=250_000, rpd=20),
)

LEGACY_MODEL_STATUS = {
    "google:gemini-2.5-flash": ModelStatus.DEPRECATED,
    "google:gemini-2.5-flash-lite": ModelStatus.DEPRECATED,
    "google:gemini-3-flash": ModelStatus.DISABLED,
    "google:gemini-3-1-flash-lite": ModelStatus.DISABLED,
    "google:gemini-3-5-flash": ModelStatus.DISABLED,
    "google:gemini-3-5-flash-lite": ModelStatus.DISABLED,
    "google:gemini-3-6-flash": ModelStatus.DISABLED,
    "google:gemini-2-5-flash-tts": ModelStatus.DISABLED,
    "google:gemini-3-1-flash-tts": ModelStatus.DISABLED,
    "google:antigravity": ModelStatus.DISABLED,
    "google:gemma-4-26b": ModelStatus.DISABLED,
    "google:gemma-4-31b": ModelStatus.DISABLED,
}


def create_model_management_api(state_dir: Path, seed: bool = True) -> ModelManagementAPI:
    api = ModelManagementAPI(SQLiteRepository(state_dir / "model_management.sqlite3"))
    if seed:
        api.save_provider(Provider("google", "Google AI", "google-genai",
                                   "env://GEMINI_API_KEY"))
        existing_models = {
            model.id: model for model in api.list_models(include_disabled=True)
        }
        for model in BUILTIN_MODELS:
            if model.id not in existing_models:
                api.save_model(model)
        for model_id, status in LEGACY_MODEL_STATUS.items():
            legacy = existing_models.get(model_id)
            if legacy and legacy.status != status:
                # Existing bad identifiers must be quarantined even though the
                # public facade now rejects creating them.
                api.repository.upsert_model(Model(
                    legacy.provider_code, legacy.code, legacy.display_name,
                    legacy.context_window, legacy.max_output_tokens, status,
                    legacy.capabilities, legacy.rpm, legacy.tpm, legacy.rpd,
                    legacy.concurrent_requests,
                    {**legacy.metadata, "disabled_reason": "obsolete_or_invalid_google_model_id"},
                ))
    return api
