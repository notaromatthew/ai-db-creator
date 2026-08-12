from app.core.auth import get_current_user
from app.main import app
from app.services import task_registry


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


class QueuedTask:
    def __init__(self, task_id: str):
        self.id = task_id


class CompletedTask:
    status = "SUCCESS"
    result = {
        "project_id": "private-project",
        "db_path": "private/database.sqlite",
        "tables": 2,
        "_schema_snapshot": {"private": True},
    }

    @staticmethod
    def ready():
        return True


def test_async_enqueue_routes_register_owner_and_task_status_is_private(
    client, monkeypatch
):
    test_client, routes = client
    monkeypatch.setattr(task_registry, "_get_redis_client", lambda: None)
    task_registry._in_memory_registry.clear()
    _as_user("owner-user")
    project = test_client.post("/api/projects", json={"name": "Owner", "prompt": ""}).json()
    project_id = project["id"]
    assert test_client.post(f"/api/projects/{project_id}/chat-accept", json=SCHEMA).status_code == 200

    monkeypatch.setattr(routes.generate_schema_task, "delay", lambda *_args: QueuedTask("task-generate"))
    monkeypatch.setattr(routes.populate_data_task, "delay", lambda *_args: QueuedTask("task-populate"))
    monkeypatch.setattr(routes.export_schema_task, "delay", lambda *_args: QueuedTask("task-export"))

    assert test_client.post(
        f"/api/projects/{project_id}/generate-async",
        json={"prompt": "catalogo", "document_ids": []},
    ).json()["task_id"] == "task-generate"
    assert test_client.post(
        f"/api/projects/{project_id}/populate-async", json={"document_ids": []}
    ).json()["task_id"] == "task-populate"
    assert test_client.post(
        f"/api/projects/{project_id}/export-async?format=json"
    ).json()["task_id"] == "task-export"

    for task_id in ("task-generate", "task-populate", "task-export"):
        assert task_registry.get_task_registration(task_id) == {
            "user_id": "owner-user",
            "project_id": project_id,
        }

    async_result_calls = []
    from app.tasks import celery
    monkeypatch.setattr(
        celery,
        "AsyncResult",
        lambda task_id: async_result_calls.append(task_id) or CompletedTask(),
    )
    owner_response = test_client.get("/api/tasks/task-generate")
    assert owner_response.status_code == 200
    assert owner_response.json()["result"] == {"tables": 2}

    _as_user("intruder-user")
    for task_id in ("task-generate", "task-populate", "task-export", "unknown-task"):
        assert test_client.get(f"/api/tasks/{task_id}").status_code == 404
    assert async_result_calls == ["task-generate"]


def test_in_memory_task_registry_honours_ttl(monkeypatch):
    monkeypatch.setattr(task_registry, "_get_redis_client", lambda: None)
    task_registry._in_memory_registry.clear()
    task_registry.register_task("expired", "user", "project", ttl_seconds=-1)
    assert task_registry.get_task_registration("expired") is None
