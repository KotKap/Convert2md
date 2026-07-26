from fastapi.testclient import TestClient

from src.web_api import create_web_app


def test_dashboard_and_catalog_endpoints(tmp_path):
    client = TestClient(create_web_app(tmp_path))
    dashboard = client.get("/api/v1/dashboard")
    assert dashboard.status_code == 200
    assert dashboard.json()["models"] == 5
    assert dashboard.json()["repository"].endswith("model_management.sqlite3")

    models = client.get("/api/v1/models").json()
    assert any(model["code"] == "gemini-3.1-flash-lite" for model in models)


def test_web_api_can_create_provider_model_price_budget_and_usage(tmp_path):
    client = TestClient(create_web_app(tmp_path))
    assert client.post("/api/v1/providers", json={
        "code": "local", "display_name": "Local", "adapter": "generic",
        "secret_ref": "env://LOCAL_KEY",
    }).status_code == 200
    assert client.post("/api/v1/models", json={
        "provider_code": "local", "code": "m1", "display_name": "Model One",
        "context_window": 8192, "capabilities": ["text"],
    }).status_code == 200
    assert client.post("/api/v1/prices", json={
        "model_id": "local:m1", "input_per_million": "2",
        "output_per_million": "8", "effective_from": "2020-01-01T00:00:00Z",
    }).status_code == 200
    assert client.post("/api/v1/budgets", json={
        "scope": "web", "amount": "10", "period": "monthly",
    }).status_code == 200
    usage = client.post("/api/v1/usage", json={
        "model_id": "local:m1", "operation": "manual", "input_tokens": 1000,
        "output_tokens": 500, "scope": "web",
    })
    assert usage.status_code == 200
    assert usage.json()["total_cost"] == "0.006"
    assert client.get("/api/v1/usage?scope=web").json()["request_count"] == 1


def test_web_import_rejects_plaintext_secret(tmp_path):
    client = TestClient(create_web_app(tmp_path))
    response = client.post(
        "/api/v1/config/import",
        files={"file": ("models.json", b'{"providers":[{"code":"x","api_key":"bad"}]}',
                        "application/json")},
    )
    assert response.status_code == 400
    assert "secret_ref" in response.json()["detail"]


def test_local_frontend_custom_port_is_allowed_by_cors(tmp_path):
    client = TestClient(create_web_app(tmp_path))
    response = client.options(
        "/api/v1/convert/diagram",
        headers={
            "Origin": "http://localhost:4173",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:4173"
