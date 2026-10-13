import asyncio

import pytest

from app.core.auth import get_current_user
from app.main import app
from app.services import schema_service
from app.services.schema_service import generate_schema_with_repair, validate_schema

from schema_factories import invalid_schema, valid_schema


def as_user(sub, email=None):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": [], "email_verified": True}


def fake_generate(monkeypatch, *schemas):
    """Il modello simulato restituisce in ordine gli schemi indicati (l'ultimo si ripete)."""
    calls = []

    async def fake(prompt, document_context="", temperature=None):
        calls.append(prompt)
        return schemas[min(len(calls) - 1, len(schemas) - 1)]

    monkeypatch.setattr(schema_service, "generate_schema", fake)
    return calls


def versions(c, pid):
    return c.get(f"/api/projects/{pid}/schema/versions").json()


def test_validate_schema_reports_every_problem():
    errors = " ".join(validate_schema(invalid_schema()))
    assert "libri non ha una chiave primaria" in errors
    assert "tabella inesistente: editori" in errors
    assert "Tipo non ammesso" in errors
    assert validate_schema(valid_schema()) == []


def test_validate_schema_detects_duplicates_and_bad_fk_column():
    schema = valid_schema()
    schema.tables.append(schema.tables[0].model_copy(deep=True))
    schema.tables[1].columns[2].foreign_key_column = "codice"
    errors = " ".join(validate_schema(schema))
    assert "Nome di tabella duplicato: autori" in errors
    assert "colonna inesistente: autori.codice" in errors


def test_generation_saves_version_one_and_exposes_it_on_the_project(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_generate(monkeypatch, valid_schema())
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 0
    assert c.post(f"/api/projects/{pid}/generate", json={"prompt": "una biblioteca"}).status_code == 200
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 1
    listing = versions(c, pid)
    assert listing["current"] == 1
    assert listing["versions"][0]["origin"] == "generazione"
    assert listing["versions"][0]["mine"] is True and "author" not in listing["versions"][0]
    assert listing["versions"][0]["table_count"] == 2


def test_every_change_saves_a_version_and_unchanged_schema_does_not(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_generate(monkeypatch, valid_schema())
    c.post(f"/api/projects/{pid}/generate", json={"prompt": "x"})
    changed = valid_schema("isbn").model_dump()
    assert c.put(f"/api/projects/{pid}/schema", json=changed).status_code == 200
    assert c.put(f"/api/projects/{pid}/schema", json=changed).status_code == 200  # identico: nessuna nuova versione
    assert c.post(f"/api/projects/{pid}/chat-accept", json=valid_schema("anno").model_dump()).status_code == 200
    listing = versions(c, pid)
    assert [(v["version"], v["origin"]) for v in listing["versions"]] == [(3, "chat"), (2, "manuale"), (1, "generazione")]
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 3
    first = c.get(f"/api/projects/{pid}/schema/versions/1").json()
    assert [col["name"] for col in first["schema"]["tables"][1]["columns"]] == ["id", "titolo", "autore_id"]


def test_import_sql_saves_a_version(client, project):
    c, _ = client
    pid = project["id"]
    response = c.post(f"/api/projects/{pid}/import-sql?dialect=sqlite",
                      files={"file": ("s.sql", b"CREATE TABLE persone (id INTEGER PRIMARY KEY, nome TEXT);", "text/sql")})
    assert response.status_code == 200
    assert versions(c, pid)["current"] == 1


def test_restore_creates_a_new_version_with_old_content(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_generate(monkeypatch, valid_schema())
    c.post(f"/api/projects/{pid}/generate", json={"prompt": "x"})
    c.put(f"/api/projects/{pid}/schema", json=valid_schema("isbn").model_dump())
    response = c.post(f"/api/projects/{pid}/schema/versions/1/restore")
    assert response.status_code == 200
    assert response.json()["schema_version"] == 3
    assert response.json()["restored_from"] == 1
    listing = versions(c, pid)
    assert listing["versions"][0]["origin"] == "ripristino"
    current = c.get(f"/api/projects/{pid}/schema").json()
    assert "isbn" not in [col["name"] for col in current["tables"][1]["columns"]]
    assert c.post(f"/api/projects/{pid}/schema/versions/99/restore").status_code == 404


def test_finalized_schema_blocks_edit_and_restore_until_a_new_generation(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_generate(monkeypatch, valid_schema())
    c.post(f"/api/projects/{pid}/generate", json={"prompt": "x"})
    assert c.post(f"/api/projects/{pid}/finalize").status_code == 200
    assert versions(c, pid)["finalized"] is True
    assert c.put(f"/api/projects/{pid}/schema", json=valid_schema("isbn").model_dump()).status_code == 409
    assert c.post(f"/api/projects/{pid}/schema/versions/1/restore").status_code == 409
    # solo una nuova generazione riapre lo schema, e crea una nuova versione
    fake_generate(monkeypatch, valid_schema("anno"))
    assert c.post(f"/api/projects/{pid}/generate", json={"prompt": "y"}).status_code == 200
    listing = versions(c, pid)
    assert listing["finalized"] is False and listing["current"] == 2


def test_versions_follow_the_acl(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_generate(monkeypatch, valid_schema())
    c.post(f"/api/projects/{pid}/generate", json={"prompt": "x"})
    as_user("viewer", "v@example.com")
    c.get("/api/me")
    as_user("test-user", "owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": "v@example.com", "role": "viewer"})
    as_user("viewer", "v@example.com")
    assert c.get(f"/api/projects/{pid}/schema/versions").status_code == 200
    assert c.post(f"/api/projects/{pid}/schema/versions/1/restore").status_code == 403
    as_user("stranger", "s@example.com")
    assert c.get(f"/api/projects/{pid}/schema/versions").status_code == 404


def test_repair_loop_resends_errors_and_stops_when_valid(monkeypatch):
    calls = fake_generate(monkeypatch, invalid_schema(), valid_schema())
    schema, repair = asyncio.run(generate_schema_with_repair("una biblioteca"))
    assert validate_schema(schema) == []
    assert repair["attempts"] == 1
    assert repair["remaining_errors"] == []
    assert len(calls) == 2
    assert "chiave primaria" in calls[1] and "editori" in calls[1]
    assert repair["log"][0]["outcome"] == "repaired"


def test_repair_loop_is_capped_at_two_attempts_and_never_fails(monkeypatch):
    calls = fake_generate(monkeypatch, invalid_schema())
    schema, repair = asyncio.run(generate_schema_with_repair("x"))
    assert len(calls) == 3  # una generazione e due riparazioni
    assert repair["attempts"] == 2
    assert repair["remaining_errors"]
    assert schema.tables[0].name == "autori"


def test_repair_loop_survives_a_failing_repair_call(monkeypatch):
    state = {"n": 0}

    async def fake(prompt, document_context="", temperature=None):
        state["n"] += 1
        if state["n"] == 1:
            return invalid_schema()
        raise RuntimeError("modello non raggiungibile")

    monkeypatch.setattr(schema_service, "generate_schema", fake)
    schema, repair = asyncio.run(generate_schema_with_repair("x"))
    assert repair["attempts"] == 1 and repair["log"][0]["outcome"] == "failed"
    assert schema.tables[1].name == "libri"


def test_valid_schema_needs_no_repair(monkeypatch):
    calls = fake_generate(monkeypatch, valid_schema())
    _, repair = asyncio.run(generate_schema_with_repair("x"))
    assert repair["attempts"] == 0 and len(calls) == 1


def test_run_manifest_records_repair_attempts(client, project, monkeypatch):
    c, routes = client
    pid = project["id"]
    fake_generate(monkeypatch, invalid_schema(), valid_schema())
    recorded = {}
    original = routes._log_research_run

    def capture(event_type, project_id, data, run_id=None):
        recorded[event_type] = data
        return original(event_type, project_id, data, run_id=run_id)

    monkeypatch.setattr(routes, "_log_research_run", capture)
    assert c.post(f"/api/projects/{pid}/generate", json={"prompt": "x"}).status_code == 200
    manifest = recorded["schema_generated"]["run_manifest"]
    assert manifest["repair_attempts"] == 1
    assert manifest["repair_log"][0]["outcome"] == "repaired"
