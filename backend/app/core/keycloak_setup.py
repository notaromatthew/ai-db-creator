import httpx
from app.config import settings
from app.utils.logger import log

async def setup_keycloak_realm():
    """Ensure Keycloak realm 'aidbcreator' and client 'aidbcreator-app' exist."""
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
                log.warning(f"Keycloak admin authentication failed ({res.status_code}): {res.text}")
                return False

            admin_token = res.json().get("access_token")
            headers = {
                "Authorization": f"Bearer {admin_token}",
                "Content-Type": "application/json",
            }

            # Check if realm exists
            realms_res = await client.get(f"{admin_url}/admin/realms/{settings.keycloak_realm}", headers=headers)
            if realms_res.status_code == 404:
                # Create realm
                realm_data = {
                    "realm": settings.keycloak_realm,
                    "enabled": True,
                    "displayName": "AI DB Creator Realm",
                    "sslRequired": "external",
                }
                create_res = await client.post(f"{admin_url}/admin/realms", headers=headers, json=realm_data)
                log.info(f"Keycloak Realm '{settings.keycloak_realm}' created: {create_res.status_code}")

            # Check if client exists
            clients_res = await client.get(f"{admin_url}/admin/realms/{settings.keycloak_realm}/clients", headers=headers)
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
                    json=client_data
                )
                log.info(f"Keycloak Client '{settings.keycloak_client_id}' created: {c_res.status_code}")

            return True
    except Exception as e:
        log.warning(f"Keycloak Realm setup skipped or unreachable: {e}")
        return False
