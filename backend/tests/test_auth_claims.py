import asyncio
import time

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jose import jwk, jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

from app.config import settings
from app.core import auth

ISS = "https://kc.example/realms/aidb"


@pytest.fixture()
def keys(monkeypatch):
    monkeypatch.setattr(settings, "enable_auth", True)
    monkeypatch.setattr(settings, "keycloak_url", "https://kc.example/")
    monkeypatch.setattr(settings, "keycloak_realm", "aidb")
    monkeypatch.setattr(settings, "keycloak_client_id", "app")
    monkeypatch.setattr(settings, "keycloak_issuer", "")
    monkeypatch.setattr(settings, "keycloak_check_client", True)
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = private.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                serialization.NoEncryption()).decode()
    public = jwk.RSAKey(algorithm="RS256", key=private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()).to_dict()
    public["kid"] = "k1"

    async def fake_jwks(force=False):
        return {"keys": [public]}
    monkeypatch.setattr(auth, "_get_jwks", fake_jwks)
    return pem


def run(pem, **claims):
    base = {"sub": "u1", "iss": ISS, "azp": "app", "aud": "account", "exp": int(time.time()) + 600}
    base.update(claims)
    base = {k: v for k, v in base.items() if v is not None}
    token = jwt.encode(base, pem, algorithm="RS256", headers={"kid": "k1"})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
    return asyncio.run(auth.get_current_user(request=None, credentials=creds))


def test_valid_token_is_accepted(keys):
    assert run(keys)["sub"] == "u1"
    assert run(keys, azp="other", aud=["account", "app"])["sub"] == "u1"  # client tra le audience


def test_issuer_must_be_complete(keys):
    for iss in ("https://evil.example/realms/aidb", "https://kc.example/realms/other", "https://kc.example/x/realms/aidb"):
        with pytest.raises(HTTPException) as exc:
            run(keys, iss=iss)
        assert exc.value.status_code == 401


def test_token_for_another_client_is_rejected(keys):
    with pytest.raises(HTTPException) as exc:
        run(keys, azp="altro-client", aud="account")
    assert exc.value.status_code == 401


def test_client_check_can_be_relaxed(keys, monkeypatch):
    monkeypatch.setattr(settings, "keycloak_check_client", False)
    assert run(keys, azp="altro-client")["sub"] == "u1"
