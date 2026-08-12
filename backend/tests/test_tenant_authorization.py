from app.api.dependencies import get_owned_project
from app.core.auth import get_current_user
from app.main import app
from app.models.database import BenchmarkResult, Project, get_session
from validate_arm_routes import application_routes


SCHEMA = {
    "tables": [
        {
            "name": "prodotti",
            "columns": [
                {"name": "id", "data_type": "INTEGER", "is_primary_key": True}
            ],
        }
    ],
    "relationships": [],
}


def _as_user(user_id: str):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": user_id,
        "username": user_id,
    }


def test_all_project_routes_enforce_owned_project_dependency():
    project_routes = [
        route for route in application_routes()
        if getattr(route, "path", "").startswith("/api/projects/{project_id}")
    ]

    assert project_routes
    for route in project_routes:
        dependency_calls = {dependency.call for dependency in route.dependant.dependencies}
        assert get_owned_project in dependency_calls, f"ownership dependency missing: {route.path}"


def test_project_resources_are_available_to_owner_and_hidden_from_other_user(
    client, monkeypatch
):
    test_client, routes = client
    _as_user("owner-user")
    project = test_client.post("/api/projects", json={"name": "Owner", "prompt": ""}).json()
    project_id = project["id"]

    async def fake_chat(*_args, **_kwargs):
        return "Schema pronto"

    async def fake_extract(*_args, **_kwargs):
        from app.models.schema_models import NormalizedSchema
        return NormalizedSchema(**SCHEMA)

    monkeypatch.setattr(routes, "chat", fake_chat)
    monkeypatch.setattr(routes, "extract_schema_with_fallback", fake_extract)

    assert test_client.get(f"/api/projects/{project_id}").status_code == 200
    assert test_client.post(
        f"/api/projects/{project_id}/chat", json={"message": "catalogo", "document_ids": []}
    ).status_code == 200
    assert test_client.post(f"/api/projects/{project_id}/chat-accept", json=SCHEMA).status_code == 200
    document = test_client.post(
        f"/api/projects/{project_id}/documents",
        files={"file": ("owner.txt", b"owner data", "text/plain")},
    )
    assert document.status_code == 200
    document_id = document.json()["id"]
    assert test_client.get(f"/api/projects/{project_id}/documents").status_code == 200
    assert test_client.get(f"/api/projects/{project_id}/data/stats").status_code == 200
    assert test_client.get(f"/api/projects/{project_id}/data/prodotti").status_code == 200
    assert test_client.get(f"/api/projects/{project_id}/export?format=json").status_code == 200
    assert test_client.post(f"/api/projects/{project_id}/backup?label=owner").status_code == 200

    _as_user("other-user")
    protected_requests = [
        ("get", f"/api/projects/{project_id}", None),
        ("post", f"/api/projects/{project_id}/chat", {"message": "intrusione", "document_ids": []}),
        ("post", f"/api/projects/{project_id}/chat-accept", SCHEMA),
        ("get", f"/api/projects/{project_id}/documents", None),
        ("delete", f"/api/projects/{project_id}/documents/{document_id}", None),
        ("get", f"/api/projects/{project_id}/data/stats", None),
        ("get", f"/api/projects/{project_id}/data/prodotti", None),
        ("get", f"/api/projects/{project_id}/export?format=json", None),
        ("post", f"/api/projects/{project_id}/backup?label=intruder", None),
    ]
    for method, path, payload in protected_requests:
        response = getattr(test_client, method)(path, json=payload) if payload is not None else getattr(test_client, method)(path)
        assert response.status_code == 404, (method, path, response.text)
    upload_response = test_client.post(
        f"/api/projects/{project_id}/documents",
        files={"file": ("intruder.txt", b"intruder data", "text/plain")},
    )
    assert upload_response.status_code == 404


def test_project_listing_never_includes_legacy_or_other_tenant_projects(client):
    test_client, routes = client
    _as_user("owner-user")
    owned = test_client.post("/api/projects", json={"name": "Owned", "prompt": ""}).json()
    _as_user("other-user")
    other = test_client.post("/api/projects", json={"name": "Other", "prompt": ""}).json()
    session = get_session(routes.schema_svc.engine)
    legacy = Project(name="Legacy", prompt="", user_id=None)
    session.add(legacy)
    session.commit()
    legacy_id = legacy.id
    session.close()

    _as_user("owner-user")
    visible_ids = {item["id"] for item in test_client.get("/api/projects").json()}
    assert owned["id"] in visible_ids
    assert other["id"] not in visible_ids
    assert legacy_id not in visible_ids


def test_benchmark_results_share_automatic_metrics_but_only_current_users_votes(client):
    test_client, routes = client
    session = get_session(routes.schema_svc.engine)
    result = BenchmarkResult(
        scenario_name="Shared scenario",
        provider="test",
        model_name="model",
        norm3_score=100,
        relationship_f1=1,
        cell_precision=1,
        latency_seconds=0.1,
        token_cost_estimate=0,
    )
    session.add(result)
    session.commit()
    session.close()

    _as_user("owner-user")
    assert test_client.post(
        "/api/surveys/vote", json={"schema_rating": 5, "data_rating": 4, "comment": "owner note"}
    ).status_code == 200
    _as_user("other-user")
    assert test_client.post(
        "/api/surveys/vote", json={"schema_rating": 1, "data_rating": 1, "comment": "private other note"}
    ).status_code == 200

    _as_user("owner-user")
    payload = test_client.get("/api/benchmark/results").json()
    assert any(item["scenario"] == "Shared scenario" for item in payload["results"])
    assert [vote["comment"] for vote in payload["votes"]] == ["owner note"]
    assert all("user_id" not in vote for vote in payload["votes"])


def test_missing_authenticated_subject_is_rejected(client):
    test_client, _routes = client

    def missing_subject():
        return {"username": "missing-sub"}

    app.dependency_overrides[get_current_user] = missing_subject
    response = test_client.get("/api/projects")
    assert response.status_code == 401


def test_benchmark_progress_is_namespaced_by_authenticated_subject(client, monkeypatch):
    test_client, routes = client
    from app.api import progress as progress_api

    monkeypatch.setattr(progress_api, "_get_redis_client", lambda: None)
    progress_api._in_memory_store.clear()
    progress_api.set_progress("benchmark:owner-user", "running", 35, "owner progress")
    progress_api.set_progress("benchmark:other-user", "saving", 95, "other progress")

    _as_user("owner-user")
    owner_progress = test_client.get("/api/progress/benchmark").json()
    assert owner_progress["message"] == "owner progress"
    assert test_client.post(
        "/api/progress/benchmark?status=completed&progress=100&message=forged"
    ).status_code == 405

    _as_user("other-user")
    other_progress = test_client.get("/api/progress/benchmark").json()
    assert other_progress["message"] == "other progress"

    captured = {}

    async def fake_run_model_benchmark(**kwargs):
        captured.update(kwargs)
        return {"status": "ok"}

    monkeypatch.setattr(routes, "run_model_benchmark", fake_run_model_benchmark)
    assert test_client.post(
        "/api/benchmark/run",
        json={"scenario": "ecommerce", "provider": "ollama", "model": "test"},
    ).status_code == 200
    assert captured["progress_key"] == "benchmark:other-user"
