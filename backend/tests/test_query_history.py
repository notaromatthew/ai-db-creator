from app.models.schema_models import QueryResponse
from app.services import query_service

from test_schema_versions import as_user


def make_database(c, pid):
    sql = (b"CREATE TABLE persone (id INTEGER PRIMARY KEY, nome TEXT);"
           b"INSERT INTO persone (id, nome) VALUES (1, 'Ada');INSERT INTO persone (id, nome) VALUES (2, 'Linus');")
    assert c.post(f"/api/projects/{pid}/import-sql?dialect=sqlite", files={"file": ("s.sql", sql, "text/sql")}).status_code == 200


def fake_query(monkeypatch, sql="SELECT * FROM persone", fail=False):
    async def fake(prompt, schema, dialect="sqlite"):
        if fail:
            raise RuntimeError("modello non raggiungibile")
        return QueryResponse(sql=sql)
    monkeypatch.setattr(query_service, "generate_query", fake)


def test_generated_query_is_recorded_with_question(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    make_database(c, pid)
    fake_query(monkeypatch)
    assert c.post(f"/api/projects/{pid}/query", json={"prompt": "tutte le persone"}).status_code == 200
    history = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert len(history) == 1
    assert history[0]["question"] == "tutte le persone"
    assert history[0]["sql"] == "SELECT * FROM persone"
    assert history[0]["outcome"] == "ok" and history[0]["source"] == "query"
    assert history[0]["user_id"] == "test-user"


def test_failed_generation_is_recorded_as_error(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    make_database(c, pid)
    fake_query(monkeypatch, fail=True)
    c2 = c
    try:
        response = c2.post(f"/api/projects/{pid}/query", json={"prompt": "domanda"})
        assert response.status_code >= 500
    except RuntimeError:
        pass
    history = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert history[0]["question"] == "domanda" and history[0]["outcome"] == "errore"
    assert history[0]["sql"] is None


def test_executed_queries_are_recorded_with_rows_and_errors(client, project):
    c, _ = client
    pid = project["id"]
    make_database(c, pid)
    assert c.post(f"/api/projects/{pid}/execute-query", json={"sql": "SELECT * FROM persone"}).status_code == 200
    assert c.post(f"/api/projects/{pid}/execute-query", json={"sql": "SELECT * FROM inesistente"}).status_code == 400
    history = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert [(h["outcome"], h["rows"], h["source"]) for h in history] == [("errore", None, "execute"), ("ok", 2, "execute")]
    assert history[1]["sql"] == "SELECT * FROM persone"


def test_history_is_limited_to_fifty_and_newest_first(client, project):
    c, _ = client
    pid = project["id"]
    for index in range(55):
        query_service.record_query(pid, "test-user", f"domanda {index}", "SELECT 1", "ok", rows=1)
    history = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert len(history) == 50
    assert history[0]["question"] == "domanda 54"


def test_history_follows_the_acl(client, project):
    c, _ = client
    pid = project["id"]
    query_service.record_query(pid, "test-user", "d", "SELECT 1", "ok")
    as_user("viewer", "v@example.com")
    c.get("/api/me")
    as_user("test-user", "owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": "v@example.com", "role": "viewer"})
    as_user("viewer", "v@example.com")
    assert len(c.get(f"/api/projects/{pid}/queries").json()["queries"]) == 1
    as_user("stranger", "s@example.com")
    assert c.get(f"/api/projects/{pid}/queries").status_code == 404
