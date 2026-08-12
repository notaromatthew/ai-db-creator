import asyncio
import httpx
from app.config import settings
from app.utils.logger import log

async def setup_keycloak_realm(max_attempts: int = 45, retry_delay: float = 2.0):
    """Ensure Keycloak realm 'aidbcreator' and client 'aidbcreator-app' exist."""
    admin_url = settings.keycloak_url.rstrip('/')
    token_url = f"{admin_url}/realms/master/protocol/openid-connect/token"

    payload = {
        "client_id": "admin-cli",
        "username": settings.keycloak_admin_user,
        "password": settings.keycloak_admin_password,
        "grant_type": "password",
    }

    for attempt in range(1, max_attempts + 1):
        try:
            async with httpx.AsyncClient(verify=True, timeout=10.0) as client:
                res = await client.post(token_url, data=payload)
                if res.status_code != 200:
                    raise httpx.HTTPStatusError("Keycloak admin authentication unavailable", request=res.request, response=res)

                admin_token = res.json().get("access_token")
                headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json",
                }

                realms_res = await client.get(
                    f"{admin_url}/admin/realms/{settings.keycloak_realm}", headers=headers
                )
                if realms_res.status_code == 404:
                    realm_data = {
                        "realm": settings.keycloak_realm,
                        "enabled": True,
                        "displayName": "AI DB Creator Realm",
                        "sslRequired": "external",
                    }
                    create_res = await client.post(
                        f"{admin_url}/admin/realms", headers=headers, json=realm_data
                    )
                    create_res.raise_for_status()
                    log.info("Keycloak realm created: {}", create_res.status_code)

                clients_res = await client.get(
                    f"{admin_url}/admin/realms/{settings.keycloak_realm}/clients", headers=headers
                )
                clients = clients_res.json() if clients_res.status_code == 200 else []
                client_exists = any(c.get("clientId") == settings.keycloak_client_id for c in clients)

                if not client_exists:
                    client_data = {
                        "clientId": settings.keycloak_client_id,
                        "enabled": True,
                        "publicClient": True,
                        "directAccessGrantsEnabled": True,
                        "standardFlowEnabled": True,
                        "webOrigins": ["*"],
                        "redirectUris": ["*"],
                    }
                    c_res = await client.post(
                        f"{admin_url}/admin/realms/{settings.keycloak_realm}/clients",
                        headers=headers,
                        json=client_data,
                    )
                    c_res.raise_for_status()
                    log.info("Keycloak client created: {}", c_res.status_code)

                return True
        except Exception as exc:
            if attempt == max_attempts:
                log.warning("Keycloak realm setup unavailable after {} attempts: {}", max_attempts, exc)
                return False
            log.info("Keycloak not ready (attempt {}/{}); retrying", attempt, max_attempts)
            await asyncio.sleep(retry_delay)
    return False
