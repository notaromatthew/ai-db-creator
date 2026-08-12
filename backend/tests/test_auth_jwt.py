import base64
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.core import auth


def _b64_int(value: int) -> str:
    raw = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def test_real_rs256_jwks_validation_and_roles(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private_key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": "test-key", "use": "sig", "alg": "RS256", "n": _b64_int(public.n), "e": _b64_int(public.e)}

    async def fake_jwks():
        return {"keys": [jwk]}

    monkeypatch.setattr(settings, "enable_auth", True)
    monkeypatch.setattr(auth, "_get_jwks", fake_jwks)
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "participant-1", "preferred_username": "participant",
            "iat": now, "exp": now + timedelta(minutes=5), "aud": "account",
            "iss": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}",
            "azp": settings.keycloak_client_id,
            "realm_access": {"roles": ["researcher"]},
            "resource_access": {settings.keycloak_client_id: {"roles": ["admin"]}},
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )
    app = FastAPI()

    @app.get("/protected")
    async def protected(user=Depends(auth.get_current_user)):
        return user

    response = TestClient(app).get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["sub"] == "participant-1"
    assert response.json()["roles"] == ["admin", "researcher"]
    assert TestClient(app).get("/protected").status_code == 401


def test_rs256_rejects_wrong_client_and_missing_expiry(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = private_key.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": "k", "use": "sig", "alg": "RS256", "n": _b64_int(public.n), "e": _b64_int(public.e)}
    async def fake_jwks(): return {"keys": [jwk]}
    monkeypatch.setattr(settings, "enable_auth", True)
    monkeypatch.setattr(auth, "_get_jwks", fake_jwks)
    app = FastAPI()
    @app.get("/protected")
    async def protected(user=Depends(auth.get_current_user)): return user
    now = datetime.now(timezone.utc)
    base = {"sub": "u", "iat": now, "aud": "account", "iss": f"{settings.keycloak_url}/realms/{settings.keycloak_realm}"}
    wrong_client = jwt.encode({**base, "exp": now + timedelta(minutes=5), "azp": "other"}, private_key, algorithm="RS256", headers={"kid": "k"})
    no_expiry = jwt.encode({**base, "azp": settings.keycloak_client_id}, private_key, algorithm="RS256", headers={"kid": "k"})
    client = TestClient(app)
    assert client.get("/protected", headers={"Authorization": f"Bearer {wrong_client}"}).status_code == 401
    assert client.get("/protected", headers={"Authorization": f"Bearer {no_expiry}"}).status_code == 401
