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
            "iat": now, "exp": now + timedelta(minutes=5),
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
