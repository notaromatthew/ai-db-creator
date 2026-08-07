from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.config import settings
from app.utils.logger import log
from typing import Optional

security = HTTPBearer(auto_error=False)

_jwks_cache = None

async def _get_jwks():
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
        res = await client.get(jwks_url)
        if res.status_code == 200:
            _jwks_cache = res.json()
            return _jwks_cache
        else:
            raise HTTPException(status_code=503, detail=f"Impossibile recuperare JWKS da Keycloak: {res.status_code}")

async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    if not settings.enable_auth:
        return {"sub": "default-user", "username": "davide", "email": "davide@example.com"}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticazione richiesta: token Bearer mancante",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    jwks = await _get_jwks()

    try:
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")
        key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chiave di firma token Keycloak non trovata")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_aud": False}
        )

        return {
            "sub": claims.get("sub"),
            "username": claims.get("preferred_username", claims.get("sub")),
            "email": claims.get("email"),
        }
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"JWT Validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token di autenticazione non valido o scaduto",
            headers={"WWW-Authenticate": "Bearer"},
        )

