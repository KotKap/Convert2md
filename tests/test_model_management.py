from datetime import datetime, timezone
from decimal import Decimal
import json

import pytest

from src.model_management import (
    Budget, BudgetPeriod, Model, ModelRequest, ModelStatus, Price, Provider,
    RegisterUsageCommand, UsageQuery, create_model_management_api, import_configuration,
    import_usage,
)


def api(tmp_path):
    return create_model_management_api(tmp_path, seed=False)


def configured_api(tmp_path):
    service = api(tmp_path)
    service.save_provider(Provider("test", "Test", "fake", "env://TEST_API_KEY"))
    service.save_model(Model(
        "test", "vision", "Vision", 10_000, 1_000,
        capabilities=("text", "vision"), rpm=10, tpm=20_000, rpd=100,
    ))
    service.save_price(Price(
        "test:vision", "USD", Decimal("2"), Decimal("1"), Decimal("8"),
        Decimal("0.01"), datetime(2020, 1, 1, tzinfo=timezone.utc), "test",
    ))
    return service


def test_preflight_limits_capabilities_and_estimates_cost(tmp_path):
    service = configured_api(tmp_path)
    result = service.validate_request(ModelRequest(
        "test:vision", "diagram", 1_000, 500, ("vision",), image_count=1,
    ))
    assert result.allowed
    assert result.estimated_cost == Decimal("0.016")

    rejected = service.validate_request(ModelRequest(
        "test:vision", "audio", 1_000, capabilities=("audio",),
    ))
    assert not rejected.allowed
    assert rejected.errors[0].code == "unsupported_capability"


def test_usage_preserves_price_snapshot_when_current_price_changes(tmp_path):
    service = configured_api(tmp_path)
    record = service.register_usage(RegisterUsageCommand(
        "test:vision", "diagram", 1_000, 500, image_count=1,
    ))
    service.save_price(Price(
        "test:vision", "USD", Decimal("200"), output_per_million=Decimal("800"),
        effective_from=datetime.now(timezone.utc), source="new",
    ))
    assert record.total_cost == Decimal("0.016")
    assert record.price_snapshot.input_per_million == "2"
    summary = service.get_usage_summary(UsageQuery(model_id="test:vision"))
    assert summary.request_count == 1
    assert summary.total_cost == Decimal("0.016")


def test_budget_blocks_request_that_would_exceed_remaining_amount(tmp_path):
    service = configured_api(tmp_path)
    service.save_budget(Budget("application", Decimal("0.01"), period=BudgetPeriod.TOTAL))
    result = service.validate_request(ModelRequest(
        "test:vision", "diagram", 1_000, 500, ("vision",), image_count=1,
    ))
    assert not result.allowed
    assert any(issue.code == "budget_exceeded" for issue in result.errors)


def test_json_import_and_form_schema_are_ui_independent(tmp_path):
    service = api(tmp_path)
    result = import_configuration(service, json.dumps({
        "schema_version": "1.0",
        "providers": [{"code": "local", "adapter": "generic",
                       "secret_ref": "env://LOCAL_MODEL_KEY"}],
        "models": [{"provider_code": "local", "code": "m1", "context_window": 4096,
                    "capabilities": ["text"]}],
    }))
    assert result.providers == result.models == 1
    assert service.get_model("local:m1").context_window == 4096
    assert service.get_form_schema("model")["schema_version"] == "1.0"


def test_import_rejects_secret_values(tmp_path):
    with pytest.raises(ValueError, match="use secret_ref"):
        import_configuration(api(tmp_path), json.dumps({
            "providers": [{"code": "bad", "adapter": "fake", "api_key": "plaintext"}],
        }))


def test_import_historical_usage_from_csv(tmp_path):
    service = configured_api(tmp_path)
    source = tmp_path / "usage.csv"
    source.write_text(
        "model_id,operation,input_tokens,output_tokens,occurred_at,scope\n"
        "test:vision,legacy-conversion,1000,500,2024-01-02T03:04:05Z,archive\n",
        encoding="utf-8",
    )
    assert import_usage(service, source) == 1
    summary = service.get_usage_summary(UsageQuery(scope="archive"))
    assert summary.request_count == 1
    assert summary.input_tokens == 1000
    assert summary.total_cost == Decimal("0.006")


def test_models_repository_contains_imported_model(tmp_path):
    service = api(tmp_path)
    import_configuration(service, json.dumps({
        "providers": [{"code": "custom", "adapter": "generic"}],
        "models": [{"provider_code": "custom", "code": "private-model",
                    "context_window": 8192}],
    }))
    assert [model.id for model in service.list_models()] == ["custom:private-model"]


def test_google_model_ids_require_dotted_version_numbers(tmp_path):
    service = api(tmp_path)
    service.save_provider(Provider("google", "Google", "google-genai"))
    with pytest.raises(ValueError, match="use dots"):
        service.save_model(Model("google", "gemini-3-5-flash", "Invalid", 1000))


def test_bootstrap_quarantines_legacy_google_models(tmp_path):
    service = api(tmp_path)
    service.save_provider(Provider("google", "Google", "google-genai"))
    service.repository.upsert_model(
        Model("google", "gemini-3-5-flash", "Legacy", 1000)
    )

    seeded = create_model_management_api(tmp_path)

    assert seeded.get_model("google:gemini-3-5-flash").status == ModelStatus.DISABLED
    assert seeded.get_model("google:gemini-3.1-flash-lite").status == ModelStatus.ACTIVE
