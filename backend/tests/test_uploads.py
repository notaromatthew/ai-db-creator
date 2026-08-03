def upload(client, project_id, name, content):
    return client.post(
        f"/api/projects/{project_id}/documents",
        files={"file": (name, content, "application/octet-stream")},
    )


def test_valid_xlsx_has_provenance(client, project, xlsx_bytes):
    test_client, _ = client
    response = upload(test_client, project["id"], "dati.xlsx", xlsx_bytes)
    assert response.status_code == 200
    assert response.json()["provenance"]["sha256"]
    documents = test_client.get(f"/api/projects/{project['id']}/documents").json()
    assert documents[0]["filename"] == "dati.xlsx"
    assert documents[0]["provenance"]["method"] == "deterministic"


def test_corrupt_xlsx_is_rejected_without_record(client, project):
    test_client, _ = client
    response = upload(test_client, project["id"], "rotto.xlsx", b"not-an-excel-file")
    assert response.status_code == 422
    assert test_client.get(f"/api/projects/{project['id']}/documents").json() == []


def test_homonymous_uploads_use_distinct_storage(client, project, xlsx_bytes):
    test_client, routes = client
    first = upload(test_client, project["id"], "dati.xlsx", xlsx_bytes)
    second = upload(test_client, project["id"], "dati.xlsx", xlsx_bytes)
    assert first.status_code == second.status_code == 200
    documents = routes.doc_svc.list_documents(project["id"])
    assert len(documents) == 2
    assert documents[0].filename == documents[1].filename == "dati.xlsx"
    assert documents[0].file_path != documents[1].file_path


def test_oversize_upload_is_rejected(client, project):
    test_client, _ = client
    response = upload(test_client, project["id"], "grande.csv", b"x" * (25 * 1024 * 1024 + 1))
    assert response.status_code == 413
    assert test_client.get(f"/api/projects/{project['id']}/documents").json() == []


def test_missing_project_returns_404_without_upload_artifacts(client, xlsx_bytes, tmp_path):
    test_client, _ = client
    response = upload(test_client, "missing", "dati.xlsx", xlsx_bytes)
    assert response.status_code == 404
    assert not (tmp_path / "uploads" / "missing").exists()


def test_import_sql_accepts_multipart_file(client, project):
    test_client, _ = client
    response = test_client.post(
        f"/api/projects/{project['id']}/import-sql?dialect=sqlite",
        files={"file": ("schema.sql", b"CREATE TABLE persone (id INTEGER PRIMARY KEY, nome TEXT);", "text/sql")},
    )
    assert response.status_code == 200
    assert response.json()["tables"] == 1


def test_import_sql_preserves_semicolon_inside_quoted_value(client, project):
    test_client, _ = client
    sql = b"CREATE TABLE luoghi (id INTEGER PRIMARY KEY, nome TEXT);\nINSERT INTO luoghi (id, nome) VALUES (1, 'Roma; Italia');"
    response = test_client.post(
        f"/api/projects/{project['id']}/import-sql?dialect=sqlite",
        files={"file": ("quoted.sql", sql, "text/sql")},
    )
    assert response.status_code == 200
    rows = test_client.get(f"/api/projects/{project['id']}/data/luoghi").json()
    assert rows == [{"id": 1, "nome": "Roma; Italia"}]


def test_document_ownership_blocks_cross_project_access(client, project, xlsx_bytes):
    test_client, _ = client
    other = test_client.post("/api/projects", json={"name": "Altro", "prompt": ""}).json()
    document_id = upload(test_client, project["id"], "dati.xlsx", xlsx_bytes).json()["id"]
    assert test_client.delete(f"/api/projects/{other['id']}/documents/{document_id}").status_code == 404
    assert test_client.post(f"/api/projects/{other['id']}/generate", json={"prompt": "x", "document_ids": [document_id]}).status_code == 404
    assert test_client.post(f"/api/projects/{other['id']}/chat", json={"message": "x", "document_ids": [document_id]}).status_code == 404
    sql = b"CREATE TABLE persone (id INTEGER PRIMARY KEY);"
    assert test_client.post(f"/api/projects/{other['id']}/import-sql", files={"file": ("x.sql", sql, "text/sql")}).status_code == 200
    assert test_client.post(f"/api/projects/{other['id']}/populate", json={"document_ids": [document_id]}).status_code == 404


def test_import_sql_validates_extension_dialect_size_and_rolls_back_bad_insert(client, project):
    test_client, _ = client
    endpoint = f"/api/projects/{project['id']}/import-sql"
    assert test_client.post(endpoint, files={"file": ("x.txt", b"x", "text/plain")}).status_code == 422
    assert test_client.post(endpoint + "?dialect=oracle", files={"file": ("x.sql", b"x", "text/sql")}).status_code == 422
    assert test_client.post(endpoint, files={"file": ("x.sql", b"x" * (25 * 1024 * 1024 + 1), "text/sql")}).status_code == 413
    valid = b"CREATE TABLE persone (id INTEGER PRIMARY KEY, nome TEXT);\nINSERT INTO persone (id, nome) VALUES (1, 'Ada');"
    assert test_client.post(endpoint, files={"file": ("valid.sql", valid, "text/sql")}).status_code == 200
    schema_before = test_client.get(f"/api/projects/{project['id']}/schema").json()
    rows_before = test_client.get(f"/api/projects/{project['id']}/data/persone").json()
    invalid = b"CREATE TABLE sostituzione (id INTEGER PRIMARY KEY);\nINSERT INTO sostituzione (missing) VALUES (1);"
    assert test_client.post(endpoint, files={"file": ("x.sql", invalid, "text/sql")}).status_code == 422
    assert test_client.get(f"/api/projects/{project['id']}/schema").json() == schema_before
    assert test_client.get(f"/api/projects/{project['id']}/data/persone").json() == rows_before


def test_project_erasure_removes_only_owned_artifacts(client, project, xlsx_bytes):
    test_client, routes = client
    other = test_client.post("/api/projects", json={"name": "Conserva", "prompt": ""}).json()
    upload(test_client, project["id"], "delete.xlsx", xlsx_bytes)
    upload(test_client, other["id"], "keep.xlsx", xlsx_bytes)
    routes.interaction_logger.log_event("x", project["id"], {})
    routes.interaction_logger.log_event("x", other["id"], {})
    response = test_client.delete(f"/api/projects/{project['id']}")
    assert response.status_code == 200
    assert test_client.get(f"/api/projects/{project['id']}").status_code == 404
    assert len(test_client.get(f"/api/projects/{other['id']}/documents").json()) == 1
    assert routes.interaction_logger.get_events(project["id"]) == []
    other_events = routes.interaction_logger.get_events(other["id"])
    assert any(event["event_type"] == "x" for event in other_events)
    assert len(other_events) == 2  # document_uploaded (keep.xlsx) + the explicit "x" event


def test_run_artifact_contains_schema_but_global_log_only_references_it(client, project, tmp_path):
    test_client, _ = client
    sql = b"CREATE TABLE persone (id INTEGER PRIMARY KEY);"
    assert test_client.post(f"/api/projects/{project['id']}/import-sql", files={"file": ("x.sql", sql, "text/sql")}).status_code == 200
    event = next(item for item in test_client.get(f"/api/projects/{project['id']}/interactions").json() if item["event_type"] == "import_sql")
    assert "schema_initial" not in event["data"]
    assert "schema_final" not in event["data"]
    artifact = tmp_path / "projects" / project["id"] / event["data"]["run_artifact"]
    payload = __import__("json").loads(artifact.read_text(encoding="utf-8"))
    assert payload["schema_final"]["tables"][0]["name"] == "persone"


def test_compare_and_async_routes_validate_before_llm_or_delay(client, project, xlsx_bytes, monkeypatch):
    test_client, routes = client
    other = test_client.post("/api/projects", json={"name": "Altro", "prompt": ""}).json()
    document_id = upload(test_client, project["id"], "owned.xlsx", xlsx_bytes).json()["id"]
    assert test_client.post("/api/experiments/compare", json={"prompt": "x"}).status_code == 422
    assert test_client.post("/api/experiments/compare", json={"project_id": other["id"], "prompt": "x", "document_ids": [document_id]}).status_code == 404
    delayed = []
    monkeypatch.setattr(routes.generate_schema_task, "delay", lambda *args: delayed.append(args))
    monkeypatch.setattr(routes.export_schema_task, "delay", lambda *args: delayed.append(args))
    assert test_client.post("/api/projects/missing/generate-async", json={"prompt": "x", "document_ids": []}).status_code == 404
    assert test_client.post("/api/projects/missing/export-async").status_code == 404
    assert delayed == []


def test_public_interaction_endpoint_rejects_raw_values_and_missing_project(client, project):
    test_client, routes = client
    malicious = {"type": "navigation", "target_type": "project", "target_name": "safe", "schema_final": {"secret": "value"}}
    assert test_client.post(f"/api/projects/{project['id']}/interactions", json=malicious).status_code == 422
    assert test_client.post("/api/projects/missing/interactions", json={"type": "navigation", "target_type": "project", "target_name": "safe"}).status_code == 404
    assert all("secret" not in str(event) for event in routes.interaction_logger.get_events(project["id"]))


def test_chat_failure_creates_sanitized_failure_artifact(client, project, monkeypatch, tmp_path, xlsx_bytes):
    test_client, routes = client
    document = upload(test_client, project["id"], "chat.xlsx", xlsx_bytes).json()
    async def fail_chat(*args, **kwargs):
        from app.utils.exceptions import AppException
        raise AppException("chat failed", 502)
    monkeypatch.setattr(routes, "chat", fail_chat)
    response = test_client.post(f"/api/projects/{project['id']}/chat", json={"message": "private raw message", "document_ids": [document["id"]]})
    assert response.status_code == 502
    event = next(item for item in routes.interaction_logger.get_events(project["id"]) if item["event_type"] == "schema_chat_failed")
    assert event["data"]["run_manifest"]["status"] == "failed"
    assert len(event["data"]["run_manifest"]["input_hashes"]["document_sha256"]) == 1
    artifact = tmp_path / "projects" / project["id"] / event["data"]["run_artifact"]
    assert artifact.exists()
    assert "private raw message" not in artifact.read_text(encoding="utf-8")
