import json

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, text

from app.config import Settings, settings
from app.core.auth import require_admin
from app.models.database import Base, verify_schema_compatibility
from check_research_gate import check
from validate_governance import validate as validate_governance


def test_settings_never_return_secret_and_do_not_write_env(client, monkeypatch):
    test_client, routes = client
    from app.core.auth import require_admin
    from app.main import app
    app.dependency_overrides[require_admin] = lambda: {"sub": "admin", "roles": ["admin"]}
    secrets = {
        "openai_api_key": "openai-secret", "google_api_key": "google-secret",
        "groq_api_key": "groq-secret", "openrouter_api_key": "router-secret",
        "ollama_api_key": "ollama-secret",
    }
    for key, value in secrets.items(): monkeypatch.setattr(settings, key, value)
    response = test_client.get("/api/settings")
    assert response.status_code == 200
    serialized = response.text
    assert not any(secret in serialized for secret in secrets.values())
    assert all(response.json()[f"{key}_configured"] is True for key in secrets)
    assert test_client.put("/api/settings", json={"openai_api_key": ""}).status_code == 200
    assert settings.openai_api_key == "openai-secret"
    assert not (routes.Path(".env")).exists()


def test_cors_allows_configured_frontend_and_rejects_arbitrary_origins(client):
    test_client, _ = client
    trusted = test_client.options(
        "/api/projects",
        headers={"Origin": "http://localhost:3000", "Access-Control-Request-Method": "GET"},
    )
    assert trusted.headers.get("access-control-allow-origin") == "http://localhost:3000"
    untrusted = test_client.options(
        "/api/projects",
        headers={"Origin": "https://attacker.invalid", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in untrusted.headers


def test_admin_role_enforced(monkeypatch):
    monkeypatch.setattr(settings, "enable_auth", True)
    with pytest.raises(HTTPException) as error:
        require_admin({"sub": "u", "roles": ["user"]})
    assert error.value.status_code == 403
    assert require_admin({"sub": "a", "roles": ["admin"]})["sub"] == "a"


def test_experiment_mode_rejects_placeholder_secrets():
    with pytest.raises(ValueError):
        Settings(experiment_mode=True)


def test_default_settings_never_target_external_infrastructure(monkeypatch):
    for name in (
        "DATABASE_URL", "KEYCLOAK_URL", "OLLAMA_BASE_URL", "SONARQUBE_URL",
        "OLLAMA_MODE", "USE_OLLAMA", "LLM_MAX_REQUESTS_PER_MINUTE",
    ):
        monkeypatch.delenv(name, raising=False)
    defaults = Settings(_env_file=None)
    assert defaults.database_url == "sqlite:///./app.db"
    assert defaults.keycloak_url == "http://localhost:8080"
    assert defaults.ollama_base_url == "http://localhost:11434"
    assert defaults.sonarqube_url == "http://localhost:9000"
    assert defaults.ollama_mode == "local" and defaults.use_ollama is False
    assert defaults.llm_max_requests_per_minute == 8
    assert "localhost:3000" in defaults.cors_allowed_origins


def test_schema_compatibility_empty_current_and_legacy():
    empty = create_engine("sqlite:///:memory:")
    verify_schema_compatibility(empty)
    Base.metadata.create_all(empty)
    verify_schema_compatibility(empty)
    legacy = create_engine("sqlite:///:memory:")
    with legacy.begin() as connection:
        connection.execute(text("CREATE TABLE projects (id VARCHAR PRIMARY KEY, name VARCHAR NOT NULL)"))
    with pytest.raises(RuntimeError, match="migration required"):
        verify_schema_compatibility(legacy)


def test_versioned_research_gate_accepts_only_expected_blockers(tmp_path):
    datasets = tmp_path / "datasets"; datasets.mkdir()
    expectation = datasets / "research-gate-expectations.json"
    expectation.write_text(json.dumps({"version": "v", "datasets": {}}))
    result = check(datasets, expectation)
    assert result["software_gate"] == "pass" and result["research_freeze_gate"] == "blocked"


def test_container_configs_are_nonroot_and_healthchecked():
    root = __import__("pathlib").Path(__file__).resolve().parents[2]
    combined = (root / "Dockerfile").read_text()
    backend = (root / "backend" / "Dockerfile").read_text()
    frontend = (root / "frontend" / "Dockerfile").read_text()
    assert "USER appuser" in combined and "HEALTHCHECK" in combined
    assert "USER appuser" in backend and "HEALTHCHECK" in backend
    assert "migrate_database.py" in combined and "migrate_database.py" in backend
    assert "nginx-unprivileged" in frontend and "EXPOSE 8080" in frontend and "HEALTHCHECK" in frontend
    compose = (root / "docker-compose.yml").read_text()
    backend_service = compose.split("\n  backend:\n", 1)[1].split("\n  worker:\n", 1)[0]
    assert '"6379:6379"' not in compose and '"5432:5432"' not in compose
    assert "/health/ready" in compose and "keycloak: {condition: service_healthy}" in compose
    assert "KEYCLOAK_ADMIN_USER: ${KEYCLOAK_ADMIN_USER:?set KEYCLOAK_ADMIN_USER}" in backend_service
    assert "KEYCLOAK_ADMIN_PASSWORD: ${KEYCLOAK_ADMIN_PASSWORD:?set KEYCLOAK_ADMIN_PASSWORD}" in backend_service
    assert "REDIS_PASSWORD:?set REDIS_PASSWORD" in compose
    assert "--requirepass" in compose and "REDISCLI_AUTH" in compose
    assert "redis://:${REDIS_PASSWORD:?set REDIS_PASSWORD}@redis:6379/0" in compose
    workflow = (root / ".github" / "workflows" / "ci.yml").read_text()
    assert 'healthy_services="$(docker compose ps --format json' in workflow
    assert '[ "$healthy_services" -eq 6 ]' in workflow


def test_governance_without_evidence_is_missing():
    result=validate_governance(None,None)
    assert result["status"]=="missing" and set(result["failures"])=={"public_package_missing","restricted_archive_policy_evidence_missing"}
