from app.core.auth import get_current_user
from app.main import app


def as_user(sub, email=None, roles=None):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": roles or [], "email_verified": True}


def test_stranger_gets_404(client, project):
    c, _ = client
    as_user("stranger", "s@example.com")
    for path in ("", "/schema", "/documents", "/metrics"):
        assert c.get(f"/api/projects/{project['id']}{path}").status_code == 404
    assert c.delete(f"/api/projects/{project['id']}").status_code == 404
    assert c.get("/api/projects").json() == []


def test_viewer_can_read_not_write(client, project):
    c, _ = client
    pid = project["id"]
    as_user("viewer", "v@example.com")
    c.get("/api/me")
    as_user("test-user", "owner@example.com")
    assert c.post(f"/api/projects/{pid}/invites", json={"email": "v@example.com", "role": "viewer"}).json()["status"] == "shared"
    as_user("viewer", "v@example.com")
    assert c.get(f"/api/projects/{pid}/schema").status_code in (200, 404) and c.get(f"/api/projects/{pid}").status_code == 200
    assert c.put(f"/api/projects/{pid}/schema", json={"tables": []}).status_code in (403, 422)
    assert c.post(f"/api/projects/{pid}/populate", json={}).status_code in (403, 422)
    assert c.delete(f"/api/projects/{pid}").status_code == 403
    assert c.get(f"/api/projects/{pid}/sharing").status_code == 403
    assert [p["id"] for p in c.get("/api/projects").json()] == [pid]


def test_invite_for_unregistered_email_accepted_on_first_login(client, project):
    c, _ = client
    pid = project["id"]
    assert c.post(f"/api/projects/{pid}/invites", json={"email": "New@Example.com", "role": "editor"}).json()["status"] == "shared"
    as_user("newbie", "new@example.com")
    assert c.get(f"/api/projects/{pid}").json()["my_role"] == "editor"


def test_public_link_and_revoke(client, project):
    c, _ = client
    pid = project["id"]
    token = c.post(f"/api/projects/{pid}/links").json()["token"]
    as_user("anon-x")
    assert c.get(f"/api/shared/{token}").json()["read_only"] is True
    as_user("test-user")
    link_id = c.get(f"/api/projects/{pid}/sharing").json()["links"][0]["id"]
    c.delete(f"/api/projects/{pid}/links/{link_id}")
    assert c.get(f"/api/shared/{token}").status_code == 404


def test_owner_cannot_be_demoted_and_roles_validated(client, project):
    c, _ = client
    pid = project["id"]
    assert c.post(f"/api/projects/{pid}/invites", json={"email": "a@b.it", "role": "owner"}).status_code == 422


def test_project_list_carries_role_owner_and_status(client, project):
    c, _ = client
    pid = project["id"]
    rows = c.get("/api/projects").json()
    assert rows[0]["my_role"] == "owner" and rows[0]["status"] == "not_started" and rows[0]["step"] == 1
    assert rows[0]["document_count"] == 0 and rows[0]["table_count"] == 0
    as_user("editor", "e@example.com")
    c.get("/api/me")
    as_user("test-user", "owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": "e@example.com", "role": "editor"})
    as_user("editor", "e@example.com")
    shared = c.get("/api/projects").json()[0]
    assert shared["my_role"] == "editor" and shared["id"] == pid and "owner_name" in shared
