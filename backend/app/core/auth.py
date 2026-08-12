from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
import httpx
from app.config import settings
from app.utils.logger import log
from typing import Optional

security = HTTPBearer(auto_error=False)

_jwks_cache = None

async def _get_jwks(force_refresh: bool = False):
    global _jwks_cache
    if _jwks_cache and not force_refresh:
        return _jwks_cache
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
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
            jwks = await _get_jwks(force_refresh=True)
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chiave di firma token Keycloak non trovata")

        signing_key = jwt.PyJWK.from_dict(key).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            audience="account",
            issuer=f"{(settings.keycloak_issuer_url or settings.keycloak_url).rstrip('/')}/realms/{settings.keycloak_realm}",
            options={"require": ["exp", "sub", "iat"]},
        )
        if claims.get("azp") != settings.keycloak_client_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token issued for a different client")

        return {
            "sub": claims.get("sub"),
            "username": claims.get("preferred_username", claims.get("sub")),
            "email": claims.get("email"),
            "roles": sorted(set(claims.get("realm_access", {}).get("roles", [])) |
                            set(claims.get("resource_access", {}).get(settings.keycloak_client_id, {}).get("roles", []))),
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


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if not settings.enable_auth:
        return user
    if "admin" not in set(user.get("roles", [])):
        raise HTTPException(status_code=403, detail="Administrator role required")
    return user

