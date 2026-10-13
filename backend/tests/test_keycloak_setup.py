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


# --- ruolo admin e primo admin (task 1.7) ---
import asyncio

import httpx

from app.core.keycloak_setup import ensure_admin_role


class FakeKeycloak:
    """Keycloak minimo in memoria: ruoli realm, utenti e mappature."""

    def __init__(self, users=None, role_exists=False, holders=None):
        self.users = users if users is not None else []
        self.role = {"id": "r1", "name": "aidb-admin"} if role_exists else None
        self.holders = list(holders or [])
        self.calls = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        self.calls.append((method, path))
        if path.endswith("/roles/aidb-admin") and method == "GET":
            return httpx.Response(200, json=self.role) if self.role else httpx.Response(404)
        if path.endswith("/roles") and method == "POST":
            if self.role:
                return httpx.Response(409)
            self.role = {"id": "r1", "name": "aidb-admin"}
            return httpx.Response(201)
        if path.endswith("/roles/aidb-admin/users"):
            return httpx.Response(200, json=[{"id": h} for h in self.holders])
        if path.endswith("/users") and method == "GET":
            email = request.url.params.get("email")
            return httpx.Response(200, json=[u for u in self.users if u["email"] == email])
        if "/role-mappings/realm" in path and method == "POST":
            self.holders.append(path.split("/")[-3])
            return httpx.Response(204)
        return httpx.Response(500)


def run_ensure(fake):
    async def go():
        async with httpx.AsyncClient(transport=httpx.MockTransport(fake.handler)) as client:
            return await ensure_admin_role(client, "http://kc/admin/realms/r", {})
    return asyncio.run(go())


def mapped(fake):
    return [c for c in fake.calls if "role-mappings" in c[1]]


def test_role_created_and_first_admin_assigned(monkeypatch):
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", "Boss@Example.com")
    fake = FakeKeycloak(users=[{"id": "u1", "email": "boss@example.com"}])
    assert run_ensure(fake) is True
    assert fake.role is not None and fake.holders == ["u1"]


def test_role_creation_is_idempotent_and_no_reassignment(monkeypatch):
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", "boss@example.com")
    fake = FakeKeycloak(users=[{"id": "u1", "email": "boss@example.com"}], role_exists=True, holders=["other"])
    assert run_ensure(fake) is True
    assert mapped(fake) == []
    assert not any(c == ("POST", "/admin/realms/r/roles") for c in fake.calls)


def test_no_assignment_without_variable(monkeypatch):
    monkeypatch.delenv("FIRST_ADMIN_EMAIL", raising=False)
    fake = FakeKeycloak(users=[{"id": "u1", "email": "boss@example.com"}])
    assert run_ensure(fake) is True
    assert fake.role is not None and mapped(fake) == []


def test_first_admin_not_registered_yet_is_assigned_later(monkeypatch):
    monkeypatch.setenv("FIRST_ADMIN_EMAIL", "boss@example.com")
    fake = FakeKeycloak(users=[])
    assert run_ensure(fake) is True and fake.holders == []
    fake.users.append({"id": "u9", "email": "boss@example.com"})
    assert run_ensure(fake) is True and fake.holders == ["u9"]
