"""Exercise a real Keycloak token against the protected backend API.

Creates and always removes one ephemeral Keycloak user. Tokens, passwords and
response bodies are never printed.
"""

import argparse
import secrets
import time

import httpx


def run(keycloak_url: str, backend_url: str, admin_user: str, admin_password: str,
        realm: str = "aidbcreator", client_id: str = "aidbcreator-app") -> dict:
    username = f"ci-smoke-{secrets.token_hex(6)}"
    password = secrets.token_urlsafe(24)
    user_id = None
    started = time.monotonic()
    with httpx.Client(timeout=15.0, verify=True) as client:
        token_response = client.post(
            f"{keycloak_url}/realms/master/protocol/openid-connect/token",
            data={"client_id": "admin-cli", "username": admin_user, "password": admin_password, "grant_type": "password"},
        )
        token_response.raise_for_status()
        admin_headers = {"Authorization": f"Bearer {token_response.json()['access_token']}"}
        try:
            create = client.post(
                f"{keycloak_url}/admin/realms/{realm}/users",
                headers=admin_headers,
                json={
                    "username": username,
                    "email": f"{username}@example.invalid",
                    "emailVerified": True,
                    "firstName": "CI",
                    "lastName": "Smoke",
                    "enabled": True,
                    "requiredActions": [],
                    "credentials": [{"type": "password", "value": password, "temporary": False}],
                },
            )
            create.raise_for_status()
            user_id = create.headers["Location"].rstrip("/").rsplit("/", 1)[-1]
            login = client.post(
                f"{keycloak_url}/realms/{realm}/protocol/openid-connect/token",
                data={"client_id": client_id, "username": username, "password": password, "grant_type": "password"},
            )
            login.raise_for_status()
            bearer = {"Authorization": f"Bearer {login.json()['access_token']}"}
            missing = client.get(f"{backend_url}/api/projects")
            protected = client.get(f"{backend_url}/api/projects", headers=bearer)
            if missing.status_code != 401 or protected.status_code != 200:
                raise RuntimeError(f"authentication smoke failed: anonymous={missing.status_code}, bearer={protected.status_code}")
            return {"status": "pass", "anonymous": 401, "authenticated": 200, "latency_ms": round((time.monotonic() - started) * 1000)}
        finally:
            if user_id:
                client.delete(f"{keycloak_url}/admin/realms/{realm}/users/{user_id}", headers=admin_headers).raise_for_status()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--keycloak-url", default="http://127.0.0.1:8080")
    parser.add_argument("--backend-url", default="http://127.0.0.1:8000")
    parser.add_argument("--admin-user", required=True)
    parser.add_argument("--admin-password", required=True)
    args = parser.parse_args()
    result = run(args.keycloak_url, args.backend_url, args.admin_user, args.admin_password)
    print(f"authenticated_smoke={result['status']} latency_ms={result['latency_ms']}")
