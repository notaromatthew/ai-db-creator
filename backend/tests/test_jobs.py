import asyncio
import threading
from datetime import timedelta

import pytest

from app import tasks
from app.core.acl import utcnow_naive
from app.core.auth import get_current_user
from app.core.quota import count_today
from app.main import app
from app.models.database import Job, get_session
from app.services import population_service, schema_service

from schema_factories import valid_schema


@pytest.fixture(autouse=True)
def thread_executor(monkeypatch):
    """Senza Redis i lavori girano nel thread di ripiego."""
    monkeypatch.delenv("REDIS_URL", raising=False)
    tasks._job_threads.clear()


def as_user(sub, email=None):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": [], "email_verified": True}


def fake_llm(monkeypatch, schema=None):
    async def fake(prompt, document_context="", temperature=None):
        return schema or valid_schema()
    monkeypatch.setattr(schema_service, "generate_schema", fake)


def post_job(c, pid, **body):
    return c.post(f"/api/projects/{pid}/jobs", json=body)


def wait(c, pid, job_id):
    thread = tasks._job_threads.get(job_id)
    if thread:
        thread.join(20)
        assert not thread.is_alive()
    return c.get(f"/api/projects/{pid}/jobs/{job_id}").json()


def test_schema_job_runs_in_fallback_thread_and_result_waits(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    response = post_job(c, pid, kind="schema", prompt="una biblioteca")
    assert response.status_code == 202
    job = response.json()
    assert job["kind"] == "schema" and job["project_id"] == pid and job["mine"] is True and "user_id" not in job
    final = wait(c, pid, job["id"])
    assert final["status"] == "done" and final["progress"] == 100 and final["error"] is None
    assert final["result"]["tables"] == 2 and final["result"]["repair_attempts"] == 0
    # il risultato resta: nuova "apertura della pagina"
    listing = c.get(f"/api/projects/{pid}/jobs").json()["jobs"]
    assert [j["id"] for j in listing] == [job["id"]]
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 1
    assert len(c.get(f"/api/projects/{pid}/schema").json()["tables"]) == 2


def test_schema_job_failure_is_recorded_without_leaking_details(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]

    async def broken(prompt, document_context="", temperature=None):
        raise RuntimeError("chiave-segreta-123")

    monkeypatch.setattr(schema_service, "generate_schema", broken)
    job = post_job(c, pid, kind="schema", prompt="x").json()
    final = wait(c, pid, job["id"])
    assert final["status"] == "failed"
    assert "chiave-segreta-123" not in (final["error"] or "")
    assert final["error"]
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 0


def test_population_job_reports_counts(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    wait(c, pid, post_job(c, pid, kind="schema", prompt="x").json()["id"])
    upload = c.post(f"/api/projects/{pid}/documents", files={"file": ("a.txt", b"Ada Lovelace", "text/plain")})
    doc_id = upload.json()["id"]

    async def sql(_schema, content, temperature=None):
        return "INSERT INTO autori (id, nome) VALUES (1, 'Ada');"

    monkeypatch.setattr(population_service, "generate_sql_for_population", sql)
    job = post_job(c, pid, kind="dati", document_ids=[doc_id]).json()
    final = wait(c, pid, job["id"])
    assert final["status"] == "done", final
    assert final["result"]["tables"]["autori"]["inserted"] == 1
    assert c.get(f"/api/projects/{pid}/data/autori").json()[0]["nome"] == "Ada"


def test_export_job_for_oracle_does_not_consume_quota(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    wait(c, pid, post_job(c, pid, kind="schema", prompt="x").json()["id"])
    used = count_today("test-user")
    job = post_job(c, pid, kind="esportazione", format="sql", dialect="oracle").json()
    final = wait(c, pid, job["id"])
    assert final["status"] == "done"
    assert "NUMBER(10)" in final["result"]["content"] and "CLOB" in final["result"]["content"]
    assert count_today("test-user") == used
    bad = post_job(c, pid, kind="esportazione", dialect="db2")
    assert bad.status_code == 422


def test_ai_jobs_consume_quota_like_the_direct_endpoints(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    before = count_today("test-user")
    wait(c, pid, post_job(c, pid, kind="schema", prompt="x").json()["id"])
    assert count_today("test-user") == before + 1


def test_quota_exhausted_blocks_job_creation(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    from app.core import quota
    monkeypatch.setattr(quota, "get_setting", lambda key: True if key == "ai_enabled" else 0)
    response = post_job(c, pid, kind="schema", prompt="x")
    assert response.status_code == 429
    assert c.get(f"/api/projects/{pid}/jobs").json()["jobs"] == []
    monkeypatch.setattr(quota, "get_setting", lambda key: False if key == "ai_enabled" else 100)
    assert post_job(c, pid, kind="schema", prompt="x").status_code == 503


def test_cancel_stops_a_running_job_and_discards_its_result(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    release = threading.Event()

    async def slow(prompt, document_context="", temperature=None):
        while not release.is_set():
            await asyncio.sleep(0.01)
        return valid_schema()

    monkeypatch.setattr(schema_service, "generate_schema", slow)
    job = post_job(c, pid, kind="schema", prompt="x").json()
    # un secondo lavoro sullo stesso progetto viene rifiutato finche' il primo e' attivo
    assert post_job(c, pid, kind="schema", prompt="y").status_code == 409
    cancelled = c.post(f"/api/projects/{pid}/jobs/{job['id']}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    release.set()
    final = wait(c, pid, job["id"])
    assert final["status"] == "cancelled" and final["result"] is None
    assert c.get(f"/api/projects/{pid}").json()["schema_version"] == 0
    assert c.post(f"/api/projects/{pid}/jobs/{job['id']}/cancel").status_code == 409


def test_job_validation(client, project):
    c, _ = client
    pid = project["id"]
    assert post_job(c, pid, kind="schema").status_code == 422
    assert post_job(c, pid, kind="schema", prompt="  ").status_code == 422
    assert post_job(c, pid, kind="dati").status_code == 400
    assert post_job(c, pid, kind="esportazione").status_code == 400
    assert post_job(c, pid, kind="altro").status_code == 422
    assert post_job(c, pid, kind="schema", prompt="x", document_ids=["inesistente"]).status_code == 404
    assert c.get(f"/api/projects/{pid}/jobs/inesistente").status_code == 404


def test_jobs_follow_the_acl_and_are_scoped_to_the_project(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    fake_llm(monkeypatch)
    job = post_job(c, pid, kind="schema", prompt="x").json()
    wait(c, pid, job["id"])
    other = c.post("/api/projects", json={"name": "Altro"}).json()["id"]
    assert c.get(f"/api/projects/{other}/jobs/{job['id']}").status_code == 404
    as_user("viewer", "v@example.com")
    c.get("/api/me")
    as_user("test-user", "owner@example.com")
    c.post(f"/api/projects/{pid}/invites", json={"email": "v@example.com", "role": "viewer"})
    as_user("viewer", "v@example.com")
    assert c.get(f"/api/projects/{pid}/jobs").json()["jobs"] == []  # i lavori altrui non sono visibili
    assert c.get(f"/api/projects/{pid}/jobs/{job['id']}").status_code == 404
    as_user("test-user", "owner@example.com")
    assert c.get(f"/api/projects/{pid}/jobs/{job['id']}").status_code == 200
    as_user("viewer", "v@example.com")
    assert post_job(c, pid, kind="schema", prompt="x").status_code == 403
    assert c.post(f"/api/projects/{pid}/jobs/{job['id']}/cancel").status_code == 403
    as_user("stranger", "s@example.com")
    assert c.get(f"/api/projects/{pid}/jobs").status_code == 404


def test_stale_jobs_are_marked_failed(client, project):
    c, _ = client
    pid = project["id"]
    session = get_session()
    try:
        job = Job(project_id=pid, user_id="test-user", kind="schema", status="running", progress=40,
                  updated_at=utcnow_naive() - timedelta(hours=2))
        session.add(job)
        session.commit()
        job_id = job.id
    finally:
        session.close()
    final = c.get(f"/api/projects/{pid}/jobs/{job_id}").json()
    assert final["status"] == "failed" and "interrotto" in final["error"].lower()


def test_celery_is_used_when_available(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    sent = []
    monkeypatch.setattr(tasks, "_celery_available", lambda: True)
    monkeypatch.setattr(tasks.run_job_task, "delay", lambda job_id: sent.append(job_id))
    job = post_job(c, pid, kind="schema", prompt="x").json()
    assert sent == [job["id"]]
    assert c.get(f"/api/projects/{pid}/jobs/{job['id']}").json()["status"] == "queued"
