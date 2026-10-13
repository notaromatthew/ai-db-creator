"""Rafforzamenti della revisione: quota atomica, un solo lavoro attivo, annullamento, ACL del lavoro."""
import threading

import pytest

from app import tasks
from app.core import quota
from app.core.acl import ensure_user
from app.core.auth import get_current_user
from app.main import app
from app.models.database import Job, UsageEvent, User, get_session, init_db


@pytest.fixture(autouse=True)
def thread_executor(monkeypatch):
    monkeypatch.delenv("REDIS_URL", raising=False)
    tasks._job_threads.clear()


def set_quota(user_id, value):
    session = get_session(init_db())
    try:
        session.get(User, user_id).daily_ai_quota = value
        session.commit()
    finally:
        session.close()


def test_quota_reservation_is_atomic_under_concurrent_requests(client):
    row = ensure_user({"sub": "u-race", "username": "u-race"})
    set_quota("u-race", 3)
    session = get_session(init_db())
    user = session.get(User, "u-race")
    session.expunge(user)
    session.close()
    barrier = threading.Barrier(12)
    outcomes = []

    def worker():
        barrier.wait()
        try:
            quota.reserve_ai(user, "chat")
            outcomes.append("ok")
        except Exception as exc:
            outcomes.append(getattr(exc, "status_code", type(exc).__name__))

    threads = [threading.Thread(target=worker) for _ in range(12)]
    [t.start() for t in threads]
    [t.join(30) for t in threads]
    assert outcomes.count("ok") == 3
    assert outcomes.count(429) == 9
    assert quota.count_today("u-race") == 3


def test_refund_removes_the_reservation(client):
    ensure_user({"sub": "u-ref", "username": "u-ref"})
    session = get_session(init_db())
    user = session.get(User, "u-ref")
    session.expunge(user)
    session.close()
    event_id = quota.reserve_ai(user, "chat")
    assert quota.count_today("u-ref") == 1
    quota.refund_ai(event_id)
    assert quota.count_today("u-ref") == 0


def test_concurrent_job_creation_allows_only_one_active_job(client, project, monkeypatch):
    c, _ = client
    pid = project["id"]
    started = threading.Event()
    release = threading.Event()

    def slow_dispatch(job_id):
        started.set()
        release.wait(20)
        return "thread"
    monkeypatch.setattr(tasks, "dispatch_job", slow_dispatch)
    monkeypatch.setattr("app.api.routes.job_tasks.dispatch_job", slow_dispatch)
    barrier = threading.Barrier(6)
    codes = []

    def worker():
        barrier.wait()
        codes.append(c.post(f"/api/projects/{pid}/jobs", json={"kind": "schema", "prompt": "biblioteca"}).status_code)

    threads = [threading.Thread(target=worker) for _ in range(6)]
    [t.start() for t in threads]
    started.wait(20)
    release.set()
    [t.join(30) for t in threads]
    assert sorted(codes) == [202, 409, 409, 409, 409, 409]
    session = get_session(init_db())
    try:
        assert session.query(Job).filter(Job.project_id == pid).count() == 1
    finally:
        session.close()


def test_job_is_dropped_and_quota_not_consumed_when_quota_denies(client, project):
    c, _ = client
    pid = project["id"]
    ensure_user({"sub": "test-user", "username": "test-user"})
    set_quota("test-user", 0)
    response = c.post(f"/api/projects/{pid}/jobs", json={"kind": "schema", "prompt": "x"})
    assert response.status_code == 429
    session = get_session(init_db())
    try:
        assert session.query(Job).filter(Job.project_id == pid).count() == 0
        assert session.query(UsageEvent).filter(UsageEvent.user_id == "test-user").count() == 0
    finally:
        session.close()
    # il posto del progetto e' libero: con quota disponibile il lavoro parte
    set_quota("test-user", 5)
    assert c.post(f"/api/projects/{pid}/jobs", json={"kind": "schema", "prompt": "x"}).status_code == 202


def _make_job(project_id, status="running", kind="dati"):
    session = get_session(init_db())
    try:
        job = Job(project_id=project_id, user_id="test-user", kind=kind, status=status, progress=5, params={})
        session.add(job)
        session.commit()
        return job.id
    finally:
        session.close()


def _status(job_id):
    session = get_session(init_db())
    try:
        return session.get(Job, job_id).status
    finally:
        session.close()


def test_cancelled_job_never_becomes_done_or_failed(client, project):
    job_id = _make_job(project["id"])
    c, _ = client
    assert c.post(f"/api/projects/{project['id']}/jobs/{job_id}/cancel").status_code == 200
    assert tasks.update_job(job_id, status="done", progress=100, result={"x": 1}) is False
    assert tasks.update_job(job_id, status="failed", error="e") is False
    assert tasks.update_job(job_id, progress=50) is False
    assert _status(job_id) == "cancelled"
    assert c.post(f"/api/projects/{project['id']}/jobs/{job_id}/cancel").status_code == 409


def test_population_cancel_before_destructive_step_leaves_data_intact(tmp_path, monkeypatch):
    import asyncio
    from sqlalchemy import create_engine, text
    from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef
    from app.services.population_service import PopulationService
    monkeypatch.chdir(tmp_path)
    db = tmp_path / "database.sqlite"
    engine = create_engine(f"sqlite:///{db}")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE persone (id INTEGER PRIMARY KEY, nome TEXT)"))
        conn.execute(text("INSERT INTO persone VALUES (1, 'Ada')"))
    schema = NormalizedSchema(tables=[TableDef(name="persone", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True), ColumnDef(name="nome", data_type="TEXT")])],
        relationships=[])

    def cancelled():
        raise tasks.JobCancelled()
    with pytest.raises(tasks.JobCancelled):
        asyncio.run(PopulationService().populate("p1", str(db), schema, [], cancel_check=cancelled))
    with engine.connect() as conn:
        assert conn.execute(text("SELECT COUNT(*) FROM persone")).scalar() == 1


def _as(sub, email=None, roles=()):
    app.dependency_overrides[get_current_user] = lambda: {
        "sub": sub, "username": sub, "email": email, "roles": list(roles), "email_verified": True}


def test_members_see_only_their_own_history_and_jobs_without_internal_ids(client, project):
    from app.models.database import QueryHistory, SchemaVersion
    c, _ = client
    pid = project["id"]
    for sub, mail in (("u-editor", "editor@example.com"), ("u-viewer", "viewer@example.com")):
        _as(sub, mail)
        c.get("/api/me")
    _as("test-user")
    c.get("/api/me")
    for mail, role in (("editor@example.com", "editor"), ("viewer@example.com", "viewer")):
        assert c.post(f"/api/projects/{pid}/invites", json={"email": mail, "role": role}).status_code == 200
    session = get_session(init_db())
    try:
        for uid in ("test-user", "u-editor", "u-viewer"):
            session.add(QueryHistory(project_id=pid, user_id=uid, question=f"domanda di {uid}", outcome="ok", source="query"))
            session.add(Job(project_id=pid, user_id=uid, kind="esportazione", status="done", progress=100, params={}))
        session.add(SchemaVersion(project_id=pid, version=1, schema_json={"tables": []}, author="u-editor", origin="manuale"))
        session.commit()
    finally:
        session.close()

    _as("u-viewer")
    queries = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert [q["question"] for q in queries] == ["domanda di u-viewer"]
    jobs = c.get(f"/api/projects/{pid}/jobs").json()["jobs"]
    assert len(jobs) == 1 and jobs[0]["mine"] is True
    other_job = Job
    session = get_session(init_db())
    try:
        foreign = session.query(other_job).filter(other_job.user_id == "u-editor").first().id
    finally:
        session.close()
    assert c.get(f"/api/projects/{pid}/jobs/{foreign}").status_code == 404
    versions = c.get(f"/api/projects/{pid}/schema/versions").json()["versions"]
    assert versions[0]["author_label"] == "Altro membro" and "author" not in versions[0]

    _as("test-user")
    queries = c.get(f"/api/projects/{pid}/queries").json()["queries"]
    assert len(queries) == 3 and all("user_id" not in q for q in queries)
    assert len(c.get(f"/api/projects/{pid}/jobs").json()["jobs"]) == 3
    assert c.get(f"/api/projects/{pid}/jobs/{foreign}").status_code == 200
    raw = c.get(f"/api/projects/{pid}/queries").text + c.get(f"/api/projects/{pid}/jobs").text
    assert "u-editor" not in raw.replace("domanda di u-editor", "") and "u-viewer" not in raw.replace("domanda di u-viewer", "")


def test_backup_script_never_puts_the_password_on_the_command_line(tmp_path):
    import os
    import subprocess
    from pathlib import Path
    script = Path(__file__).resolve().parents[2] / "scripts" / "ops_pg_backup.sh"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    pg_dump = fake_bin / "pg_dump"
    pg_dump.write_text('#!/usr/bin/env bash\n'
                       'echo "ARGS:$*" >> "$CAPTURE"\n'
                       'echo "PGPASSWORD=$PGPASSWORD PGHOST=$PGHOST PGUSER=$PGUSER PGDATABASE=$PGDATABASE" >> "$CAPTURE"\n'
                       'head -c 400 /dev/zero | tr "\\0" "x"\n')
    pg_dump.chmod(0o755)
    capture = tmp_path / "capture.txt"
    env = {**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}", "CAPTURE": str(capture),
           "DATABASE_URL": "postgresql://aidb:s3cr%40t@db.internal:5432/aidbprod",
           "BACKUP_DIR": str(tmp_path / "bk")}
    result = subprocess.run(["bash", str(script)], env=env, capture_output=True, text=True, timeout=60)
    text_out = capture.read_text()
    assert "s3cr" not in text_out.split("PGPASSWORD")[0]  # niente nella riga ARGS
    assert "ARGS:--no-owner --no-privileges" in text_out
    assert "PGPASSWORD=s3cr@t PGHOST=db.internal PGUSER=aidb PGDATABASE=aidbprod" in text_out
    assert "s3cr" not in result.stdout + result.stderr


def test_tasks_are_bound_to_project_and_creator(client, project, monkeypatch):
    from app import tasks as app_tasks
    c, _ = client
    pid = project["id"]
    creator = {"sub": "test-user", "username": "test-user", "roles": [], "email_verified": True}

    class FakeResult:
        status = "SUCCESS"
        result = {"schema": "riservato"}

        def ready(self):
            return True
    monkeypatch.setattr(app_tasks.celery, "AsyncResult", lambda task_id: FakeResult())
    from app.api import routes
    own_id = routes._new_task_id(pid, "test-user")
    others_id = routes._new_task_id(pid, "u-editor")

    body = c.get(f"/api/tasks/{own_id}").json()
    assert body["status"] == "SUCCESS" and body["result"] == {"schema": "riservato"}
    # un altro task del progetto: stato visibile ai membri, ma non il risultato
    assert c.get(f"/api/tasks/{others_id}").json()["result"] is None
    # id non legati a un progetto o a un progetto altrui: 404
    assert c.get("/api/tasks/qualunque-id").status_code == 404
    assert c.get(f"/api/tasks/{routes._new_task_id('altro-progetto', 'test-user')}").status_code == 404
    # l'admin senza ruolo sul progetto non vede nulla, nemmeno il risultato
    _as("u-admin", "admin@example.com", ["aidb-admin"])
    assert c.get(f"/api/tasks/{own_id}").status_code == 404
    _as("u-stranger", "s@example.com")
    assert c.get(f"/api/tasks/{own_id}").status_code == 404


def test_security_headers_on_shared_view_and_everywhere(client, project):
    c, _ = client
    pid = project["id"]
    token = c.post(f"/api/projects/{pid}/links").json()["token"]
    shared = c.get(f"/api/shared/{token}")
    assert shared.status_code == 200
    assert shared.headers["Cache-Control"] == "no-store"
    assert shared.headers["Referrer-Policy"] == "no-referrer"
    assert c.get("/health").headers["Referrer-Policy"] == "no-referrer"
    assert "no-store" not in c.get("/health").headers.get("Cache-Control", "")


def test_gateway_terraform_keeps_one_warm_instance_with_cpu_always_on():
    from pathlib import Path
    tf = (Path(__file__).resolve().parents[2] / "infra" / "gcp" / "main.tf").read_text()
    assert "min_instance_count = 1" in tf and "max_instance_count = 1" in tf
    assert "cpu_idle = false" in tf
