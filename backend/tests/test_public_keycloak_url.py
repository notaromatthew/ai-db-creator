from app.api import admin
from app.config import settings


def test_public_url_from_issuer(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_url", "http://keycloak:8080")
    monkeypatch.setattr(settings, "keycloak_realm", "aidbcreator")
    monkeypatch.setattr(settings, "keycloak_issuer", "http://localhost:8080/realms/aidbcreator")
    assert admin._public_keycloak_url() == "http://localhost:8080"


def test_public_url_falls_back_to_keycloak_url(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_url", "https://kc.example.org")
    monkeypatch.setattr(settings, "keycloak_issuer", "")
    assert admin._public_keycloak_url() == "https://kc.example.org"
