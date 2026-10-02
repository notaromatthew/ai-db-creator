import asyncio
import httpx
from app.config import settings
from app.utils.logger import log

DEFAULT_ROLES = [
    {"name": "admin", "description": "System administrator with full access"},
    {"name": "researcher", "description": "Researcher for benchmarks and experiments"},
    {"name": "user", "description": "Standard user for database creation and management"},
]

DEFAULT_USERS = [
    {
        "username": "admin",
        "email": "admin@aidbcreator.local",
        "firstName": "Admin",
        "lastName": "User",
        "password": "admin123",
        "roles": ["admin", "researcher", "user"],
    },
    {
        "username": "researcher",
        "email": "researcher@aidbcreator.local",
        "firstName": "Researcher",
        "lastName": "User",
        "password": "researcher123",
        "roles": ["researcher", "user"],
    },
    {
        "username": "davide",
        "email": "davide@example.com",
        "firstName": "Davide",
        "lastName": "User",
        "password": "davide123",
        "roles": ["user"],
    },
    {
        "username": "user",
        "email": "user@aidbcreator.local",
        "firstName": "Standard",
        "lastName": "User",
        "password": "user123",
        "roles": ["user"],
    },
]


async def setup_keycloak_realm(max_attempts: int = 45, retry_delay: float = 2.0) -> bool:
    """Ensure Keycloak realm 'aidbcreator', client 'aidbcreator-app', default roles, and users exist."""
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
            async with httpx.AsyncClient(verify=True, timeout=15.0) as client:
                res = await client.post(token_url, data=payload)
                if res.status_code != 200:
                    raise httpx.HTTPStatusError("Keycloak admin authentication unavailable", request=res.request, response=res)

                admin_token = res.json().get("access_token")
                headers = {
                    "Authorization": f"Bearer {admin_token}",
                    "Content-Type": "application/json",
                }

                # 1. Realm creation / verification
                realms_res = await client.get(
                    f"{admin_url}/admin/realms/{settings.keycloak_realm}", headers=headers
                )
                if realms_res.status_code == 404:
                    realm_data = {
                        "realm": settings.keycloak_realm,
                        "enabled": True,
                        "displayName": "AI DB Creator Realm",
                        "sslRequired": "external",
                        "registrationAllowed": True,
                        "resetPasswordAllowed": True,
                        "rememberMe": True,
                    }
                    create_res = await client.post(
                        f"{admin_url}/admin/realms", headers=headers, json=realm_data
                    )
                    create_res.raise_for_status()
                    log.info("Keycloak realm created: {}", create_res.status_code)

                # 2. Client creation / verification
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

                # 3. Roles creation / verification
                existing_roles_res = await client.get(
                    f"{admin_url}/admin/realms/{settings.keycloak_realm}/roles", headers=headers
                )
                existing_roles = (
                    {r["name"]: r for r in existing_roles_res.json()}
                    if existing_roles_res.status_code == 200
                    else {}
                )

                for role_def in DEFAULT_ROLES:
                    role_name = role_def["name"]
                    if role_name not in existing_roles:
                        r_res = await client.post(
                            f"{admin_url}/admin/realms/{settings.keycloak_realm}/roles",
                            headers=headers,
                            json=role_def,
                        )
                        if r_res.status_code in (201, 204):
                            log.info("Keycloak role '{}' created", role_name)
                        elif r_res.status_code != 409:
                            log.warning("Keycloak role '{}' creation returned {}", role_name, r_res.status_code)

                # Reload roles map with IDs
                roles_res = await client.get(
                    f"{admin_url}/admin/realms/{settings.keycloak_realm}/roles", headers=headers
                )
                roles_map = {r["name"]: r for r in roles_res.json()} if roles_res.status_code == 200 else {}

                # 4. Default users creation and role mapping
                for user_def in DEFAULT_USERS:
                    username = user_def["username"]
                    password = user_def["password"]
                    roles_to_assign = user_def.get("roles", [])

                    u_get = await client.get(
                        f"{admin_url}/admin/realms/{settings.keycloak_realm}/users?username={username}&exact=true",
                        headers=headers,
                    )
                    users_list = u_get.json() if u_get.status_code == 200 else []

                    if not users_list:
                        user_payload = {
                            "username": username,
                            "email": user_def.get("email", f"{username}@aidbcreator.local"),
                            "emailVerified": True,
                            "firstName": user_def.get("firstName", username.capitalize()),
                            "lastName": user_def.get("lastName", "User"),
                            "enabled": True,
                            "credentials": [
                                {
                                    "type": "password",
                                    "value": password,
                                    "temporary": False,
                                }
                            ],
                        }
                        create_u_res = await client.post(
                            f"{admin_url}/admin/realms/{settings.keycloak_realm}/users",
                            headers=headers,
                            json=user_payload,
                        )
                        if create_u_res.status_code in (201, 204):
                            log.info("Keycloak user '{}' created", username)
                        elif create_u_res.status_code != 409:
                            log.warning("Keycloak user '{}' creation returned {}", username, create_u_res.status_code)

                        # Retrieve created user
                        u_get = await client.get(
                            f"{admin_url}/admin/realms/{settings.keycloak_realm}/users?username={username}&exact=true",
                            headers=headers,
                        )
                        users_list = u_get.json() if u_get.status_code == 200 else []

                    if users_list:
                        user_id = users_list[0]["id"]

                        # Ensure credentials are active and non-temporary
                        await client.put(
                            f"{admin_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/reset-password",
                            headers=headers,
                            json={"type": "password", "value": password, "temporary": False},
                        )

                        # Assign roles
                        assigned_res = await client.get(
                            f"{admin_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/role-mappings/realm",
                            headers=headers,
                        )
                        assigned_names = (
                            {r.get("name") for r in assigned_res.json()}
                            if assigned_res.status_code == 200
                            else set()
                        )

                        missing_roles = [
                            roles_map[r_name]
                            for r_name in roles_to_assign
                            if r_name in roles_map and r_name not in assigned_names
                        ]

                        if missing_roles:
                            map_res = await client.post(
                                f"{admin_url}/admin/realms/{settings.keycloak_realm}/users/{user_id}/role-mappings/realm",
                                headers=headers,
                                json=missing_roles,
                            )
                            if map_res.status_code in (200, 204):
                                log.info("Assigned roles {} to user '{}'", [r['name'] for r in missing_roles], username)
                            else:
                                log.warning("Role mapping for '{}' returned {}", username, map_res.status_code)

                log.info("Keycloak realm '{}' bootstrap completed with default roles and users", settings.keycloak_realm)
                return True
        except Exception as exc:
            if attempt == max_attempts:
                log.warning("Keycloak realm setup unavailable after {} attempts: {}", max_attempts, exc)
                return False
            log.info("Keycloak not ready (attempt {}/{}); retrying: {}", attempt, max_attempts, exc)
            await asyncio.sleep(retry_delay)
    return False


if __name__ == "__main__":
    success = asyncio.run(setup_keycloak_realm())
    if not success:
        raise SystemExit(1)

