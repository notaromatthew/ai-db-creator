from app.config import settings
from app.core.keycloak_setup import build_client_config, build_realm_config


def test_realm_enables_self_registration(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_allow_registration", True)
    realm = build_realm_config()
    assert realm["registrationAllowed"] is True
    assert realm["loginWithEmailAllowed"] is True
    assert realm["bruteForceProtected"] is True


def test_realm_registration_can_be_disabled(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_allow_registration", False)
    assert build_realm_config()["registrationAllowed"] is False


def test_login_theme_only_when_configured(monkeypatch):
    monkeypatch.setattr(settings, "keycloak_login_theme", "")
    assert "loginTheme" not in build_realm_config()
    monkeypatch.setattr(settings, "keycloak_login_theme", "tecnia")
    assert build_realm_config()["loginTheme"] == "tecnia"


def test_client_restricted_to_public_url(monkeypatch):
    monkeypatch.setattr(settings, "app_public_url", "https://app.example.org/")
    cfg = build_client_config()
    assert cfg["redirectUris"] == ["https://app.example.org/*"]
    assert cfg["webOrigins"] == ["https://app.example.org"]
    assert cfg["directAccessGrantsEnabled"] is False
    assert cfg["attributes"]["pkce.code.challenge.method"] == "S256"


def test_client_open_when_url_unknown(monkeypatch):
    monkeypatch.setattr(settings, "app_public_url", "")
    assert build_client_config()["redirectUris"] == ["*"]
