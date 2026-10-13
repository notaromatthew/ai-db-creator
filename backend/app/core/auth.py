from fastapi import Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from app.config import settings
from app.utils.logger import log
from typing import Optional

security = HTTPBearer(auto_error=False)

_jwks_cache = None

async def _get_jwks(force: bool = False):
    global _jwks_cache
    if _jwks_cache and not force:
        return _jwks_cache
    jwks_url = f"{settings.keycloak_url}/realms/{settings.keycloak_realm}/protocol/openid-connect/certs"
    async with httpx.AsyncClient(timeout=10.0) as client:
        res = await client.get(jwks_url)
        if res.status_code == 200:
            _jwks_cache = res.json()
            return _jwks_cache
        else:
            raise HTTPException(status_code=503, detail=f"Impossibile recuperare JWKS da Keycloak: {res.status_code}")

def expected_issuer() -> str:
    return (settings.keycloak_issuer or f"{settings.keycloak_url.rstrip('/')}/realms/{settings.keycloak_realm}").rstrip("/")


def validate_claims(claims: dict) -> None:
    """Issuer completo e client del token: un token di un altro realm/client o di un altro Keycloak e' rifiutato."""
    if str(claims.get("iss", "")).rstrip("/") != expected_issuer():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token emesso da un emittente non valido")
    if settings.keycloak_check_client:
        audience = claims.get("aud")
        audiences = [audience] if isinstance(audience, str) else list(audience or [])
        if claims.get("azp") != settings.keycloak_client_id and settings.keycloak_client_id not in audiences:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token non emesso per questa applicazione")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    if not settings.enable_auth:
        return {"sub": "default-user", "username": "davide", "email": "davide@example.com",
                "name": "Davide", "roles": [settings.admin_role]}

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
            jwks = await _get_jwks(force=True)  # chiave ruotata su Keycloak
            key = next((k for k in jwks.get("keys", []) if k.get("kid") == kid), None)
        if not key:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Chiave di firma token Keycloak non trovata")

        claims = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_aud": False, "verify_iss": False}
        )
        validate_claims(claims)

        return {
            "sub": claims.get("sub"),
            "username": claims.get("preferred_username", claims.get("sub")),
            "email": claims.get("email"),
            "email_verified": bool(claims.get("email_verified")),
            "name": claims.get("name"),
            "roles": list((claims.get("realm_access") or {}).get("roles", [])),
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

