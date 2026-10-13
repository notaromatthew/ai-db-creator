from app.config import settings
from app.core.auth import get_current_user
from app.main import app


def as_user(sub, roles=None, email=None):
    app.dependency_overrides[get_current_user] = lambda: {"sub": sub, "username": sub, "email": email, "roles": roles or []}


def test_config_is_public_and_has_no_secrets(client):
    c, _ = client
    data = c.get("/api/config").json()
    assert data["research_mode"] is True
    assert "keycloak_admin_password" not in str(data)


def test_research_mode_off_hides_study_tools(client, project):
    c, _ = client
    settings.research_mode = False
    try:
        assert c.get("/api/config").json()["research_mode"] is False
        assert c.post("/api/surveys/sus", json={"project_id": project["id"], "scores": [3] * 10}).status_code == 404
        assert c.get("/api/benchmark/scenarios").status_code == 404
        assert c.get(f"/api/projects/{project['id']}/interactions").status_code == 404
        assert c.post(f"/api/projects/{project['id']}/interactions", json={"type": "navigation", "target_type": "project", "target_name": "x"}).json() == {"status": "disabled"}
        assert c.get("/api/projects").status_code == 200  # il prodotto resta
    finally:
        settings.research_mode = True


def test_admin_endpoints_need_role(client, project):
    c, _ = client
    as_user("plain")
    for path in ("/api/admin/overview", "/api/admin/users", "/api/settings", "/api/admin/audit"):
        assert c.get(path).status_code == 403
    assert c.put("/api/settings", json={"llm_provider": "ollama"}).status_code == 403


def test_admin_sees_metadata_and_audits_changes(client, project):
    c, _ = client
    as_user("boss", ["aidb-admin"])
    assert c.get("/api/admin/overview").json()["projects"] >= 1
    users = c.get("/api/admin/users").json()
    assert any(u["id"] == "test-user" for u in users)
    assert c.put("/api/admin/users/test-user", json={"daily_quota": 1}).status_code == 200
    assert c.put("/api/admin/settings", json={"max_upload_mb": 5}).json() == {"max_upload_mb": 5}
    assert c.put("/api/admin/settings", json={"nope": 1}).status_code == 422
    actions = [a["action"] for a in c.get("/api/admin/audit").json()]
    assert "user.update" in actions and "settings.update" in actions
    # l'admin non legge il contenuto dei progetti altrui
    assert c.get(f"/api/projects/{project['id']}/schema").status_code == 404


def test_quota_blocks_after_limit(client, project, monkeypatch):
    c, routes = client
    as_user("test-user", ["aidb-admin"])
    c.put("/api/admin/users/test-user", json={"daily_quota": 0})
    r = c.post(f"/api/projects/{project['id']}/chat", json={"message": "ciao"})
    assert r.status_code == 429


def test_blocked_user_rejected(client, project):
    c, _ = client
    as_user("boss", ["aidb-admin"])
    c.put("/api/admin/users/test-user", json={"blocked": True})
    as_user("test-user")
    assert c.get("/api/projects").status_code == 403
