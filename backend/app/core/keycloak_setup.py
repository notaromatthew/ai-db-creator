import httpx
from app.config import settings
from app.utils.logger import log


def build_realm_config() -> dict:
    """Realm settings: login con registrazione self-service davanti all'app."""
    realm = {
        "realm": settings.keycloak_realm,
        "enabled": True,
        "displayName": "TecnIA · AI DB Creator",
        "sslRequired": "external",
        "registrationAllowed": settings.keycloak_allow_registration,
        "registrationEmailAsUsername": False,
        "loginWithEmailAllowed": True,
        "duplicateEmailsAllowed": False,
        "resetPasswordAllowed": True,
        "rememberMe": True,
        "bruteForceProtected": True,
        "internationalizationEnabled": True,
        "supportedLocales": ["it", "en"],
        "defaultLocale": "it",
    }
    if settings.keycloak_login_theme:
        realm["loginTheme"] = settings.keycloak_login_theme
    return realm


def build_client_config() -> dict:
    """Client pubblico PKCE; redirect e origini limitati all'URL dell'app se noto."""
    origin = settings.app_public_url.rstrip("/")
    redirect_uris = [f"{origin}/*"] if origin else ["*"]
    web_origins = [origin] if origin else ["*"]
    return {
        "clientId": settings.keycloak_client_id,
        "enabled": True,
        "publicClient": True,
        "directAccessGrantsEnabled": False,
        "standardFlowEnabled": True,
        "webOrigins": web_origins,
        "redirectUris": redirect_uris,
        "attributes": {"pkce.code.challenge.method": "S256"},
    }


async def setup_keycloak_realm():
    """Ensure realm and client exist and that self-registration is enabled."""
    admin_url = settings.keycloak_url.rstrip('/')
    token_url = f"{admin_url}/realms/master/protocol/openid-connect/token"

    payload = {
        "client_id": "admin-cli",
        "username": settings.keycloak_admin_user,
        "password": settings.keycloak_admin_password,
        "grant_type": "password",
    }

    try:
        async with httpx.AsyncClient(verify=False, timeout=10.0) as client:
            res = await client.post(token_url, data=payload)
            if res.status_code != 200:
                log.warning(f"Keycloak admin authentication failed ({res.status_code})")
                return False

            admin_token = res.json().get("access_token")
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            }
            realm_url = f"{admin_url}/admin/realms/{settings.keycloak_realm}"

            realms_res = await client.get(realm_url, headers=headers)
            if realms_res.status_code == 404:
                create_res = await client.post(f"{admin_url}/admin/realms", headers=headers, json=build_realm_config())
                log.info(f"Keycloak Realm '{settings.keycloak_realm}' created: {create_res.status_code}")
            else:
                # Realm già presente: riallinea le impostazioni di accesso.
                update_res = await client.put(realm_url, headers=headers, json=build_realm_config())
                log.info(f"Keycloak Realm '{settings.keycloak_realm}' settings synced: {update_res.status_code}")

            clients_res = await client.get(f"{realm_url}/clients", headers=headers,
                                           params={"clientId": settings.keycloak_client_id})
            existing = clients_res.json() if clients_res.status_code == 200 else []
            existing = [c for c in existing if c.get("clientId") == settings.keycloak_client_id]

            if not existing:
                c_res = await client.post(f"{realm_url}/clients", headers=headers, json=build_client_config())
                log.info(f"Keycloak Client '{settings.keycloak_client_id}' created: {c_res.status_code}")
            elif settings.app_public_url:
                # Stringe redirect URI e origini solo quando l'URL pubblico è configurato.
                cfg = build_client_config()
                u_res = await client.put(f"{realm_url}/clients/{existing[0]['id']}", headers=headers,
                                         json={**existing[0], **cfg})
                log.info(f"Keycloak Client '{settings.keycloak_client_id}' synced: {u_res.status_code}")

            return True
    except Exception as e:
        log.warning(f"Keycloak Realm setup skipped or unreachable: {e}")
        return False
