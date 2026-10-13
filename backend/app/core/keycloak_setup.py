import os

import httpx
from app.config import settings
from app.utils.logger import log


class KeycloakConfigError(RuntimeError):
    """Configurazione Keycloak non sicura o incompleta: il setup si ferma."""


def _is_dev_environment() -> bool:
    env = (os.getenv("APP_ENV") or os.getenv("ENVIRONMENT") or settings.environment or "").strip().lower()
    return env in {"development", "dev", "test", "testing", "local"}


def build_realm_config() -> dict:
    """Realm settings: login con registrazione self-service davanti all'app."""
    realm = {
        "realm": settings.keycloak_realm,
        "enabled": True,
        "displayName": "TecnIA · AI DB Creator",
        "sslRequired": "external",
        "registrationAllowed": settings.keycloak_allow_registration,
        "registrationEmailAsUsername": False,
        "verifyEmail": settings.keycloak_verify_email,
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
    if not origin and not _is_dev_environment():
        raise KeycloakConfigError(
            "APP_PUBLIC_URL non impostato: rifiuto di creare o sincronizzare il client Keycloak con "
            "redirectUris=['*']. Imposta APP_PUBLIC_URL (es. https://aidbcreator.tecniaweb.it) "
            "oppure ENVIRONMENT=development in locale.")
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


async def ensure_admin_role(client, realm_url: str, headers: dict) -> bool:
    """Crea il ruolo realm admin (idempotente) e, alla prima configurazione, lo assegna.

    Il primo admin e' l'utente con email FIRST_ADMIN_EMAIL. L'assegnazione avviene solo se il
    ruolo e' appena stato creato o non ha ancora nessun titolare, mai su un ruolo gia' in uso.
    """
    role_name = settings.admin_role
    role_url = f"{realm_url}/roles/{role_name}"
    res = await client.get(role_url, headers=headers)
    created = False
    if res.status_code == 404:
        post = await client.post(f"{realm_url}/roles", headers=headers,
                                 json={"name": role_name, "description": "Amministratori di AI DB Creator"})
        if post.status_code not in (201, 204, 409):
            log.warning(f"Keycloak role '{role_name}' creation failed ({post.status_code})")
            return False
        created = post.status_code != 409
        res = await client.get(role_url, headers=headers)
    if res.status_code != 200:
        return False
    role = res.json()

    email = (os.getenv("FIRST_ADMIN_EMAIL") or "").strip().lower()
    if not email:
        return True
    if not created:
        holders = await client.get(f"{role_url}/users", headers=headers, params={"max": 1})
        if holders.status_code != 200 or holders.json():
            return True
    found = await client.get(f"{realm_url}/users", headers=headers, params={"email": email, "exact": "true"})
    users = [u for u in (found.json() if found.status_code == 200 else [])
             if (u.get("email") or "").lower() == email and u.get("emailVerified") is True]
    if not users:
        log.info("Keycloak: primo admin non ancora registrato o con email non verificata, "
                 "il ruolo sara' assegnato alla prossima configurazione")
        return True
    mapped = await client.post(f"{realm_url}/users/{users[0]['id']}/role-mappings/realm", headers=headers,
                               json=[{"id": role["id"], "name": role["name"]}])
    log.info(f"Keycloak: ruolo '{role_name}' assegnato al primo admin: {mapped.status_code}")
    return True


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
        client_config = build_client_config()  # fallisce subito se manca APP_PUBLIC_URL in produzione
    except KeycloakConfigError as e:
        log.error(str(e))
        return False

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
                c_res = await client.post(f"{realm_url}/clients", headers=headers, json=client_config)
                log.info(f"Keycloak Client '{settings.keycloak_client_id}' created: {c_res.status_code}")
            else:
                cfg = client_config
                u_res = await client.put(f"{realm_url}/clients/{existing[0]['id']}", headers=headers,
                                         json={**existing[0], **cfg})
                log.info(f"Keycloak Client '{settings.keycloak_client_id}' synced: {u_res.status_code}")

            await ensure_admin_role(client, realm_url, headers)
            return True
    except Exception as e:
        log.warning(f"Keycloak Realm setup skipped or unreachable: {e}")
        return False
