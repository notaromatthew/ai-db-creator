"""Interruttore AI, impostazioni a caldo, link e consumi admin, audit della condivisione,
revisione del software, manifesto, fallback SPA e prontezza."""
import importlib.util
import json
from pathlib import Path

import pytest

from app.config import settings
from app.core.auth import get_current_user
from app.core.revision import compute_revision, software_revision, tracked_files
from app.main import app


@pytest.fixture(autouse=True)
def no_keycloak_at_startup(monkeypatch):
    async def noop():
        return False
    monkeypatch.setattr("app.main.setup_keycloak_realm", noop)


def as_user(sub, roles=None, email=None):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email or f"{sub}@example.com", "roles": roles or [],
        "email_verified": True}


ADMIN = ["aidb-admin"]


# --- interruttore AI e impostazioni a caldo ---

def test_ai_switch_off_returns_503_with_clear_message(client, project):
    c, _ = client
    pid = project["id"]
    as_user("boss", ADMIN)
    assert c.get("/api/admin/settings").json()["ai_enabled"] is True
    assert c.put("/api/admin/settings", json={"ai_enabled": False}).json() == {"ai_enabled": False}
    assert c.get("/api/config").json()["ai_enabled"] is False
    as_user("test-user")
    res = c.post(f"/api/projects/{pid}/chat", json={"message": "ciao"})
    assert res.status_code == 503 and "sospese" in res.json()["detail"]
    for kind in ("generate", "populate", "query"):
        assert c.post(f"/api/projects/{pid}/{kind}", json=[]).status_code == 503
    # il prodotto senza AI continua a funzionare
    assert c.get(f"/api/projects/{pid}").status_code == 200
    as_user("boss", ADMIN)
    c.put("/api/admin/settings", json={"ai_enabled": True})
    assert c.get("/api/config").json()["ai_enabled"] is True
    as_user("test-user")
    assert c.post(f"/api/projects/{pid}/chat", json=[]).status_code == 422


def test_hot_settings_cover_required_keys_and_validate(client):
    c, _ = client
    as_user("boss", ADMIN)
    current = c.get("/api/admin/settings").json()
    for key in ("ai_enabled", "default_daily_ai_quota", "daily_ai_budget_total",
                "registration_open", "maintenance_message"):
        assert key in current
    ok = c.put("/api/admin/settings", json={
        "ai_enabled": "false", "default_daily_ai_quota": 7, "daily_ai_budget_total": 99,
        "registration_open": False, "maintenance_message": "Manutenzione alle 22"})
    assert ok.status_code == 200
    assert ok.json() == {"ai_enabled": False, "default_daily_ai_quota": 7, "daily_ai_budget_total": 99,
                         "registration_open": False, "maintenance_message": "Manutenzione alle 22"}
    cfg = c.get("/api/config").json()
    assert cfg["maintenance_message"] == "Manutenzione alle 22" and cfg["registration_open"] is False
    for bad in ({"ai_enabled": "forse"}, {"ai_enabled": 5}, {"default_daily_ai_quota": -1},
                {"daily_ai_budget_total": "abc"}, {"max_upload_mb": True}, {"sconosciuta": 1}):
        assert c.put("/api/admin/settings", json=bad).status_code == 422, bad
    as_user("plain")
    assert c.put("/api/admin/settings", json={"ai_enabled": False}).status_code == 403


# --- link pubblici e consumi ---

def test_admin_links_list_and_revoke_with_audit(client, project):
    c, _ = client
    pid = project["id"]
    as_user("test-user", email="owner@example.com")
    token = c.post(f"/api/projects/{pid}/links").json()["token"]
    as_user("plain")
    assert c.get("/api/admin/links").status_code == 403
    as_user("boss", ADMIN)
    rows = c.get("/api/admin/links").json()
    assert len(rows) == 1
    row = rows[0]
    assert {"id", "project_id", "project_name", "created_by", "expires_at"} <= set(row)
    assert row["project_id"] == pid and row["project_name"] == "Ricerca" and row["created_by"] == "test-user"
    assert token not in json.dumps(rows) and "token" not in row
    assert c.delete(f"/api/admin/links/{row['id']}").status_code == 200
    assert c.get("/api/admin/links").json() == []
    assert c.get(f"/api/shared/{token}").status_code == 404
    assert c.delete(f"/api/admin/links/{row['id']}").status_code == 404
    audit = c.get("/api/admin/audit").json()
    assert any(a["action"] == "link.revoke" and a["target"] == pid and a["actor"] == "boss" for a in audit)


def test_admin_usage_grouping(client, project):
    c, _ = client
    pid = project["id"]
    as_user("test-user")
    for _ in range(2):
        c.post(f"/api/projects/{pid}/chat", json=[])
    c.post(f"/api/projects/{pid}/populate", json=[])
    as_user("boss", ADMIN)
    by_user = c.get("/api/admin/usage?group=user&days=7").json()
    assert by_user == [{"key": "test-user", "count": 3}]
    by_kind = {r["key"]: r["count"] for r in c.get("/api/admin/usage?group=kind").json()}
    assert by_kind == {"chat": 2, "populate": 1}
    by_day = c.get("/api/admin/usage?group=day").json()
    assert len(by_day) == 1 and by_day[0]["count"] == 3
    assert c.get("/api/admin/usage?group=boh").status_code == 422
    legacy = c.get("/api/admin/usage").json()
    assert {"day", "kind", "count"} <= set(legacy[0])
    as_user("plain")
    assert c.get("/api/admin/usage?group=user").status_code == 403


# --- registro di audit della condivisione ---

def test_sharing_changes_are_audited(client, project):
    c, _ = client
    pid = project["id"]
    as_user("member", email="member@example.com")
    c.get("/api/me")
    as_user("test-user", email="owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": "member@example.com", "role": "viewer"})
    c.post(f"/api/projects/{pid}/invites", json={"email": "later@example.com", "role": "editor"})
    c.put(f"/api/projects/{pid}/members/member", json={"role": "editor"})
    link_id = None
    c.post(f"/api/projects/{pid}/links")
    link_id = c.get(f"/api/projects/{pid}/sharing").json()["links"][0]["id"]
    invite_id = c.get(f"/api/projects/{pid}/sharing").json()["invites"][0]["id"]
    c.delete(f"/api/projects/{pid}/invites/{invite_id}")
    c.delete(f"/api/projects/{pid}/links/{link_id}")
    c.delete(f"/api/projects/{pid}/members/member")
    as_user("boss", ADMIN)
    audit = [a for a in c.get("/api/admin/audit").json() if a["target"] == pid]
    actions = [a["action"] for a in audit]
    for expected in ("share.invite", "share.role_change", "share.invite_revoke", "link.create",
                     "link.revoke", "share.member_remove"):
        assert expected in actions, expected
    assert actions.count("share.invite") == 2
    assert all(a["actor"] == "test-user" for a in audit)
    text = json.dumps(audit)
    assert "later@example.com" in text and "member@example.com" in text  # solo l'email invitata
    assert "owner@example.com" not in text


def test_member_leaving_is_audited(client, project):
    c, _ = client
    pid = project["id"]
    as_user("member", email="m@example.com")
    c.get("/api/me")
    as_user("test-user")
    c.post(f"/api/projects/{pid}/invites", json={"email": "m@example.com", "role": "viewer"})
    as_user("member", email="m@example.com")
    assert c.delete(f"/api/projects/{pid}/membership").status_code == 200
    as_user("boss", ADMIN)
    assert any(a["action"] == "share.leave" for a in c.get("/api/admin/audit").json())


# --- revisione del software e manifesto ---

def make_tree(tmp_path):
    app_dir = tmp_path / "backend" / "app"
    (app_dir / "tests").mkdir(parents=True)
    (app_dir / "main.py").write_text("print(1)\n")
    (app_dir / "tests" / "test_x.py").write_text("x\n")
    src = tmp_path / "frontend" / "src"
    (src / "site").mkdir(parents=True)
    (src / "pages").mkdir()
    (src / "App.tsx").write_text("app\n")
    (src / "App.test.tsx").write_text("t\n")
    (src / "pages" / "P.tsx").write_text("p\n")
    (src / "site" / "Landing.tsx").write_text("landing\n")
    return app_dir, src


def test_revision_ignores_landing_tests_and_docs(tmp_path):
    app_dir, src = make_tree(tmp_path)
    base = compute_revision(app_dir, src)
    (src / "site" / "Landing.tsx").write_text("cambiata\n")
    (src / "App.test.tsx").write_text("cambiato\n")
    (app_dir / "tests" / "test_x.py").write_text("cambiato\n")
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("doc\n")
    assert compute_revision(app_dir, src) == base
    (src / "pages" / "P.tsx").write_text("modificato\n")
    changed_fe = compute_revision(app_dir, src)
    assert changed_fe != base
    (app_dir / "main.py").write_text("print(2)\n")
    assert compute_revision(app_dir, src) != changed_fe
    labels = [label for label, _ in tracked_files(app_dir, src)]
    assert not any("site/" in label or "test" in label for label in labels)


def test_software_revision_env_override_and_default(monkeypatch):
    monkeypatch.setenv("SOFTWARE_REVISION", "abc123")
    assert software_revision() == "abc123"
    monkeypatch.delenv("SOFTWARE_REVISION")
    assert len(software_revision()) == 16


@pytest.mark.parametrize("mode", [True, False])
def test_manifest_and_config_record_research_mode_and_revision(client, monkeypatch, mode):
    from datetime import datetime, timezone
    from app.utils.research import run_manifest
    c, _ = client
    monkeypatch.setattr(settings, "research_mode", mode)
    monkeypatch.setenv("SOFTWARE_REVISION", "rev-test")
    manifest = run_manifest(datetime.now(timezone.utc), "v1")
    assert manifest["research_mode"] is mode and manifest["software_revision"] == "rev-test"
    cfg = c.get("/api/config").json()
    assert cfg["research_mode"] is mode and cfg["software_revision"] == "rev-test"


def load_check_script():
    path = Path(__file__).resolve().parents[2] / "scripts" / "check_landing_changes.py"
    spec = importlib.util.spec_from_file_location("check_landing_changes", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_check_landing_script(tmp_path, capsys):
    script = load_check_script()
    missing = tmp_path / "research-freeze.json"
    assert script.main(["x", str(missing)]) == 0
    assert "non trovato" in capsys.readouterr().out
    landing = tmp_path / "site"
    landing.mkdir()
    (landing / "Landing.tsx").write_text("uno\n")
    freeze = tmp_path / "freeze.json"
    freeze.write_text(json.dumps({"software_revision": "r1", "landing_hash": script.landing_hash(landing)}))
    assert script.check(freeze, landing, revision="r1") == []
    (landing / "Landing.tsx").write_text("due\n")
    warnings = script.check(freeze, landing, revision="r1")
    assert len(warnings) == 1 and "landing" in warnings[0]
    both = script.check(freeze, landing, revision="r2")
    assert len(both) == 2
    assert script.main(["x", str(freeze)]) == 0  # non blocca mai


# --- fallback SPA e prontezza ---

def test_spa_fallback_serves_index_and_api_404_stays_json(client):
    c, _ = client  # il fixture ha gia' spostato la cwd in una cartella temporanea
    static = Path("static")
    static.mkdir()
    (static / "index.html").write_text("<html>SPA</html>")
    for path in ("/", "/en/", "/app", "/app/projects/x", "/app/shared/t"):
        res = c.get(path)
        assert res.status_code == 200 and "SPA" in res.text, path
    res = c.get("/api/inesistente")
    assert res.status_code == 404 and res.headers["content-type"].startswith("application/json")
    assert res.json() == {"detail": "Not Found"}
    assert c.get("/apix").status_code == 200  # non e' un percorso API


def test_ready_checks_redis_only_when_configured(client, monkeypatch):
    c, _ = client
    monkeypatch.delenv("REDIS_URL", raising=False)
    assert c.get("/ready").json() == {"status": "ready", "database": "ok"}

    class Up:
        def ping(self): return True
        def close(self): pass

    class Down(Up):
        def ping(self): raise ConnectionError("redis://:segreto@host giu'")

    import redis
    monkeypatch.setenv("REDIS_URL", "redis://:segreto@host:6379/0")
    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, *a, **k: Up()))
    assert c.get("/ready").json()["redis"] == "ok"
    monkeypatch.setattr(redis.Redis, "from_url", classmethod(lambda cls, *a, **k: Down()))
    res = c.get("/ready")
    assert res.status_code == 503 and res.json()["redis"] == "down" and "segreto" not in res.text
