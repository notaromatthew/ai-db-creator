import pytest

from app.core.auth import get_current_user
from app.main import app


def as_user(sub, email=None, roles=None, verified=True):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": roles or [], "email_verified": verified}


def make_db(c, routes, pid):
    from app.models.schema_models import NormalizedSchema
    schema = NormalizedSchema(tables=[{"name": "t", "columns": [{"name": "id", "data_type": "INTEGER", "is_primary_key": True}]}], relationships=[])
    routes.schema_svc.save_schema(pid, schema) if hasattr(routes.schema_svc, "save_schema") else None


@pytest.fixture()
def db_project(client, project):
    c, routes = client
    import sqlite3
    from pathlib import Path
    from app.models.database import Project, get_session
    path = Path("projects") / project["id"]
    path.mkdir(parents=True, exist_ok=True)
    db = str(path / "database.sqlite")
    con = sqlite3.connect(db)
    con.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, v TEXT)")
    con.execute("INSERT INTO t VALUES (1, 'a')")
    con.commit(); con.close()
    s = get_session(routes.schema_svc.engine)
    s.query(Project).filter_by(id=project["id"]).update({"db_path": db})
    s.commit(); s.close()
    return project


def share(c, pid, email, role):
    as_user("test-user", "owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": email, "role": role})


def test_viewer_cannot_write_with_whitespace_tricks(client, db_project):
    c, _ = client
    pid = db_project["id"]
    as_user("v", "v@example.com"); c.get("/api/me")
    share(c, pid, "v@example.com", "viewer")
    as_user("v", "v@example.com")
    for sql in ["SELECT 1; DROP\nTABLE t", "SELECT 1;\tDELETE\nFROM t", "WITH x AS (SELECT 1) DELETE\nFROM t", "SELECT 1; VACUUM INTO '/tmp/leak.db'"]:
        r = c.post(f"/api/projects/{pid}/execute-query", json={"sql": sql})
        assert r.status_code in (400, 403), sql
    assert c.post(f"/api/projects/{pid}/execute-query", json={"sql": "SELECT * FROM t"}).status_code == 200
    as_user("test-user")
    assert c.post(f"/api/projects/{pid}/execute-query", json={"sql": "SELECT count(*) AS n FROM t"}).json()["rows"][0]["n"] == 1


def test_attach_and_pragma_denied_even_for_owner(client, db_project):
    c, _ = client
    pid = db_project["id"]
    for sql in ["ATTACH DATABASE 'app.db' AS a; SELECT 1", "PRAGMA table_info(t)"]:
        assert c.post(f"/api/projects/{pid}/execute-query", json={"sql": sql}).status_code == 400


def test_restore_rejects_path_traversal(client, db_project):
    c, _ = client
    pid = db_project["id"]
    for name in ["../../x/database.sqlite", "/etc/passwd", "..\\evil.db", "a/../../b.db"]:
        assert c.post(f"/api/projects/{pid}/restore", json={"backup_name": name}).status_code == 400


def test_progress_requires_access(client, project):
    c, _ = client
    pid = project["id"]
    assert c.get(f"/api/progress/{pid}").status_code == 200
    as_user("stranger", "s@example.com")
    assert c.get(f"/api/progress/{pid}").status_code == 404
    assert c.post(f"/api/progress/{pid}?status=x&progress=1").status_code in (404, 405)


def test_surveys_and_experiments_need_project_access(client, project):
    c, _ = client
    as_user("stranger", "s@example.com")
    body = {"project_id": project["id"], "scores": [3] * 10}
    assert c.post("/api/surveys/sus", json=body).status_code == 404
    assert c.post("/api/experiments/compare", json={"project_id": project["id"], "prompt": "x"}).status_code == 404


def test_invite_not_accepted_without_verified_email(client, project):
    c, _ = client
    pid = project["id"]
    c.post(f"/api/projects/{pid}/invites", json={"email": "victim@example.com", "role": "editor"})
    as_user("attacker", "victim@example.com", verified=False)
    assert c.get(f"/api/projects/{pid}").status_code == 404
    as_user("victim", "victim@example.com", verified=True)
    assert c.get(f"/api/projects/{pid}").json()["my_role"] == "editor"


def test_invite_response_does_not_reveal_registration(client, project):
    c, _ = client
    pid = project["id"]
    as_user("known", "known@example.com"); c.get("/api/me")
    as_user("test-user", "owner@example.com")
    a = c.post(f"/api/projects/{pid}/invites", json={"email": "known@example.com", "role": "viewer"}).json()
    b = c.post(f"/api/projects/{pid}/invites", json={"email": "unknown@example.com", "role": "viewer"}).json()
    assert a["status"] == b["status"]


def test_shared_link_for_deleted_project_is_404(client, project):
    c, _ = client
    pid = project["id"]
    token = c.post(f"/api/projects/{pid}/links").json()["token"]
    c.delete(f"/api/projects/{pid}")
    assert c.get(f"/api/shared/{token}").status_code == 404


def test_legacy_database_is_migrated_with_owners(tmp_path):
    import sqlite3
    from app.models.database import init_db, run_migrations
    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.executescript("""CREATE TABLE projects (id VARCHAR PRIMARY KEY, user_id VARCHAR(255), name VARCHAR(255) NOT NULL, prompt TEXT, schema_json JSON, db_path VARCHAR(512), created_at DATETIME, updated_at DATETIME);
    INSERT INTO projects (id,user_id,name) VALUES ('p1','kc-1','Vecchio'),('p2',NULL,'Orfano');""")
    con.commit()
    engine = init_db(f"sqlite:///{path}")
    run_migrations(engine)
    assert dict(con.execute("select id, owner_id from projects").fetchall()) == {"p1": "kc-1", "p2": "legacy"}
    init_db("sqlite:///./test_app.db")


def test_finalize_blocks_schema_edits_and_reset_data_clears_rows(client, db_project):
    c, routes = client
    pid = db_project["id"]
    from app.models.schema_models import NormalizedSchema
    schema = NormalizedSchema(tables=[{"name": "t", "columns": [
        {"name": "id", "data_type": "INTEGER", "is_primary_key": True}, {"name": "v", "data_type": "TEXT"}]}], relationships=[])
    assert c.put(f"/api/projects/{pid}/schema", json=schema.model_dump()).status_code == 200
    assert c.post(f"/api/projects/{pid}/finalize").json() == {"finalized": True}
    assert c.get(f"/api/projects/{pid}").json()["schema_finalized_at"]
    assert c.put(f"/api/projects/{pid}/schema", json=schema.model_dump()).status_code == 409
    assert c.post(f"/api/projects/{pid}/chat", json={"message": "ciao"}).status_code == 409
    n = lambda: c.post(f"/api/projects/{pid}/execute-query", json={"sql": "SELECT count(*) AS n FROM t"}).json()["rows"][0]["n"]
    assert n() == 1
    assert c.post(f"/api/projects/{pid}/reset-data").json() == {"reset": True}
    assert n() == 0
