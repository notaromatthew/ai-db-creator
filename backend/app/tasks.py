from celery import Celery
from app.core.llm import generate_schema
from app.core.db_generator import create_database_from_schema
from app.models.database import get_session, init_db, Project, Document
from app.utils.logger import log
from app.api.progress import set_progress
import asyncio
import json
import os
import threading
from app.utils.research import tracked_worker_run
from app.utils.research import sha256_file, sha256_text, stable_hash
from app.core.llm import get_llm_run_metadata

celery = Celery(
    "ai_db_creator",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)


@celery.task(bind=True)
@tracked_worker_run("schema_generated_async", "schema_prompt_v1")
def generate_schema_task(self, project_id: str, prompt: str, document_ids: list[str], run_context: dict | None = None):
    """Async task to generate schema from prompt and documents."""
    log.info(f"Starting schema generation for project {project_id}")

    engine = init_db()
    session = get_session(engine)
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        session.close()
        raise ValueError("Project not found")

    doc_context = ""
    document_hashes = []
    if document_ids:
        parts = []
        for doc_id in document_ids:
            doc = session.query(Document).filter(Document.id == doc_id, Document.project_id == project_id).first()
            if not doc:
                session.close()
                raise ValueError("Document not found")
            if doc and doc.content_summary:
                parts.append(f"--- {doc.filename} ---\n{doc.content_summary}")
            digest = sha256_file(doc.file_path)
            if digest:
                document_hashes.append(digest)
        doc_context = "\n\n".join(parts)
    session.close()

    set_progress(project_id, "generating_schema", 10, "Loading documents...")
    set_progress(project_id, "generating_schema", 30, "Calling LLM to generate schema...")
    schema = asyncio.run(generate_schema(prompt, doc_context))

    set_progress(project_id, "generating_schema", 60, "Creating database...")
    from pathlib import Path
    project_dir = Path("projects") / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    db_path = str(project_dir / "database.sqlite")
    create_database_from_schema(schema, db_path)

    set_progress(project_id, "generating_schema", 85, "Saving to project...")
    session = get_session(engine)
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        session.close()
        raise ValueError("Project not found")
    project.schema_json = json.loads(schema.model_dump_json())
    project.db_path = db_path
    project.prompt = prompt
    session.commit()
    session.close()
    from app.services.schema_service import SchemaService
    SchemaService().record_version(project_id, schema, None, "generazione")

    set_progress(project_id, "complete", 100, "Schema generation complete")
    log.info(f"Schema generation complete for project {project_id}")
    return {"project_id": project_id, "tables": len(schema.tables), "db_path": db_path,
            "_schema_snapshot": schema.model_dump(), "_run_metadata": {
                **get_llm_run_metadata(0.1, prompt, document_hashes),
                "parameters": {"temperature": 0.1}, "document_hashes": document_hashes,
            }}


@celery.task(bind=True)
@tracked_worker_run("population_async", "population_prompt_v1")
def populate_data_task(self, project_id: str, db_path: str, schema_json: dict, document_ids: list[str], run_context: dict | None = None):
    """Async task to populate database with extracted data."""
    from app.services.population_service import PopulationService
    from app.models.schema_models import NormalizedSchema

    engine = init_db()
    session = get_session(engine)
    try:
        project = session.query(Project).filter(Project.id == project_id).first()
        owned_count = session.query(Document).filter(
            Document.project_id == project_id, Document.id.in_(document_ids)
        ).count() if document_ids else 0
        if not project or owned_count != len(set(document_ids)):
            raise ValueError("Project or document not found")
    finally:
        session.close()
    log.info(f"Starting data population for project {project_id}")
    set_progress(project_id, "populating", 10, "Parsing documents...")
    schema = NormalizedSchema(**schema_json)
    pop_svc = PopulationService()
    set_progress(project_id, "populating", 40, "Inserting data...")
    results = asyncio.run(pop_svc.populate(project_id, db_path, schema, document_ids))
    set_progress(project_id, "complete", 100, "Population complete")
    log.info(f"Data population complete for project {project_id}: {results}")
    document_hashes = []
    session = get_session(engine)
    try:
        for document in session.query(Document).filter(Document.project_id == project_id, Document.id.in_(document_ids)).all():
            digest = sha256_file(document.file_path)
            if digest:
                document_hashes.append(digest)
    finally:
        session.close()
    return {"project_id": project_id, "results": results, "_schema_snapshot": schema_json,
            "_run_metadata": {**get_llm_run_metadata(
                0.0, json.dumps(schema_json, sort_keys=True), document_hashes, input_label="population_input"
            ), "schema_input_hash": stable_hash(schema_json), "document_hashes": document_hashes,
                "parameters": {"deterministic_first": True, "semantic_mapping_temperature": 0.0,
                               "fallback_temperature": 0.1}}}


@celery.task(bind=True)
def export_schema_task(self, project_id: str, format: str):
    """Async task to export schema."""
    log.info(f"Exporting schema for project {project_id} as {format}")

    engine = init_db()
    session = get_session(engine)
    project = session.query(Project).filter(Project.id == project_id).first()
    session.close()

    if not project:
        raise ValueError("Project not found")
    if not project.schema_json:
        return {"error": "Schema not found"}

    set_progress(project_id, "exporting", 50, f"Exporting as {format}...")

    from app.models.schema_models import NormalizedSchema
    schema = NormalizedSchema(**project.schema_json)

    if format == "sql":
        from app.core.db_generator import _map_type
        lines = []
        for table in schema.tables:
            cols = []
            for col in table.columns:
                col_type = _map_type(col.data_type)
                col_def = f"  {col.name} {col_type}"
                if col.is_primary_key:
                    col_def += " PRIMARY KEY"
                if col.is_not_null:
                    col_def += " NOT NULL"
                cols.append(col_def)
            lines.append(f"CREATE TABLE {table.name} (\n" + ",\n".join(cols) + "\n);")
        set_progress(project_id, "complete", 100, "Export complete")
        return {"format": "sql", "content": "\n\n".join(lines)}

    elif format == "json":
        set_progress(project_id, "complete", 100, "Export complete")
        return {"format": "json", "content": schema.model_dump_json(indent=2)}

    set_progress(project_id, "error", 100, "Unsupported format")
    return {"error": f"Unsupported format: {format}"}


# ---------------------------------------------------------------------------
# Lavori in coda (tabella jobs): schema, dati, esportazione
# ---------------------------------------------------------------------------

JOB_STALE_SECONDS = 30 * 60
_job_threads: dict[str, "threading.Thread"] = {}
_active_job_ids: set[str] = set()


class JobCancelled(Exception):
    pass


def _now_naive():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


def update_job(job_id: str, **fields) -> None:
    """Aggiorna un lavoro; non sovrascrive mai uno stato terminale con "running"."""
    from app.models.database import Job
    session = get_session(init_db())
    try:
        job = session.get(Job, job_id)
        if job is None:
            return
        if job.status in ("cancelled", "done", "failed") and fields.get("status") in (None, "running"):
            return
        for key, value in fields.items():
            setattr(job, key, value)
        job.updated_at = _now_naive()
        session.commit()
    finally:
        session.close()


def _check_cancelled(job_id: str) -> None:
    from app.models.database import Job
    session = get_session(init_db())
    try:
        job = session.get(Job, job_id)
        if job is None or job.status == "cancelled":
            raise JobCancelled()
    finally:
        session.close()


def _public_error(exc: Exception) -> str:
    """Messaggio per l'utente: mai testo grezzo di eccezioni (potrebbe contenere dati o segreti)."""
    detail = getattr(exc, "detail", None)
    if isinstance(detail, str) and detail:
        return detail[:300]
    return f"Operazione non riuscita ({type(exc).__name__}). Riprova."


def _run_schema_job(job, params: dict) -> dict:
    from datetime import datetime
    from app.models.schema_models import GenerateRequest
    from app.services.schema_service import SchemaService, get_last_repair
    from app.models.database import Project
    svc = SchemaService()
    request = GenerateRequest(prompt=params.get("prompt", ""), document_ids=params.get("document_ids", []))
    update_job(job.id, progress=20)

    async def generate():
        schema = await svc.generate_schema_only(job.project_id, request)
        return schema, get_last_repair()

    update_job(job.id, progress=30)
    schema, repair = asyncio.run(generate())
    _check_cancelled(job.id)
    update_job(job.id, progress=80)
    session = get_session(init_db())
    try:
        session.query(Project).filter(Project.id == job.project_id).update({"schema_finalized_at": None})
        session.commit()
    finally:
        session.close()
    svc.apply_generated_schema(job.project_id, schema, prompt=request.prompt, author=job.user_id)
    return {"tables": len(schema.tables), "repair_attempts": repair["attempts"],
            "remaining_errors": repair["remaining_errors"]}


def _run_population_job(job, params: dict) -> dict:
    from app.services.backup_service import BackupService
    from app.services.population_service import PopulationService
    from app.services.schema_service import SchemaService
    from pathlib import Path
    svc = SchemaService()
    project = svc.get_project(job.project_id)
    schema = svc.get_schema(job.project_id)
    if schema is None:
        raise ValueError("Genera prima lo schema.")
    document_ids = params.get("document_ids", [])
    db_path = project.db_path
    if not db_path:
        directory = Path("projects") / job.project_id
        directory.mkdir(parents=True, exist_ok=True)
        db_path = str(directory / "database.sqlite")
    else:
        BackupService().auto_backup(db_path, job.project_id, "populate")
    update_job(job.id, progress=30)
    result = asyncio.run(PopulationService().populate(job.project_id, db_path, schema, document_ids))
    _check_cancelled(job.id)
    return {"tables": {name: {key: info.get(key, 0) for key in ("inserted", "skipped", "failed")}
                       for name, info in result.items() if isinstance(info, dict)}}


def _run_export_job(job, params: dict) -> dict:
    from app.core.db_export import SUPPORTED_DIALECTS, export_full, _generate_create_table
    from app.services.schema_service import SchemaService
    svc = SchemaService()
    project = svc.get_project(job.project_id)
    schema = svc.get_schema(job.project_id)
    if schema is None:
        raise ValueError("Genera prima lo schema.")
    fmt = params.get("format", "sql")
    update_job(job.id, progress=40)
    if fmt == "json":
        return {"format": "json", "content": schema.model_dump_json(indent=2), "extension": "json"}
    if fmt != "sql":
        raise ValueError("Formato di esportazione non supportato.")
    dialect = params.get("dialect") or project.target_dialect or "sqlite"
    if dialect not in SUPPORTED_DIALECTS:
        raise ValueError("Dialetto non supportato.")
    if project.db_path and os.path.exists(project.db_path):
        content = export_full(dialect, project.db_path, schema)
    else:
        content = "\n\n".join(_generate_create_table(t, dialect, schema) for t in schema.tables)
    return {"format": dialect, "content": content, "extension": "sql"}


_JOB_RUNNERS = {"schema": _run_schema_job, "dati": _run_population_job, "esportazione": _run_export_job}


def run_job(job_id: str) -> None:
    """Esegue un lavoro in coda, aggiorna stato e avanzamento e non lascia mai uscire un'eccezione."""
    from app.models.database import Job
    session = get_session(init_db())
    try:
        job = session.get(Job, job_id)
        if job is None or job.status != "queued":
            return
        session.expunge(job)
        params = dict(job.params or {})
    finally:
        session.close()
    _active_job_ids.add(job_id)
    try:
        update_job(job_id, status="running", progress=5)
        result = _JOB_RUNNERS[job.kind](job, params)
        _check_cancelled(job_id)
        update_job(job_id, status="done", progress=100, result=result, error=None)
    except JobCancelled:
        update_job(job_id, status="cancelled")
    except Exception as exc:
        log.warning(f"Lavoro {job_id} non riuscito ({type(exc).__name__})")
        update_job(job_id, status="failed", error=_public_error(exc))
    finally:
        _active_job_ids.discard(job_id)


@celery.task(bind=True)
def run_job_task(self, job_id: str):
    run_job(job_id)
    return {"job_id": job_id}


def _celery_available() -> bool:
    if os.getenv("JOBS_FORCE_THREAD") == "1" or not os.getenv("REDIS_URL"):
        return False
    try:
        with celery.connection_for_write() as connection:
            connection.ensure_connection(max_retries=1, timeout=2)
        return True
    except Exception:
        return False


def dispatch_job(job_id: str) -> str:
    """Accoda il lavoro sul worker Celery; senza Redis lo esegue in un thread. Restituisce "celery" o "thread"."""
    import threading
    if _celery_available():
        try:
            run_job_task.delay(job_id)
            return "celery"
        except Exception as exc:
            log.warning(f"Celery non raggiungibile ({type(exc).__name__}): esecuzione in thread")
    thread = threading.Thread(target=run_job, args=(job_id,), daemon=True, name=f"job-{job_id[:8]}")
    _job_threads[job_id] = thread
    thread.start()
    return "thread"


def revoke_job(job_id: str) -> None:
    """Prova a fermare un lavoro gia' consegnato a Celery (il controllo vero e' lo stato nella tabella)."""
    try:
        celery.control.revoke(job_id)
    except Exception:
        pass


def expire_stale_jobs() -> int:
    """Segna come falliti i lavori rimasti in coda o in corso da troppo tempo (per esempio dopo un riavvio)."""
    from datetime import timedelta
    from app.models.database import Job
    limit = _now_naive() - timedelta(seconds=JOB_STALE_SECONDS)
    session = get_session(init_db())
    try:
        stale = session.query(Job).filter(Job.status.in_(("queued", "running")), Job.updated_at < limit).all()
        for job in stale:
            if job.id in _active_job_ids:
                continue
            job.status = "failed"
            job.error = "Lavoro interrotto: riavvia l'operazione."
            job.updated_at = _now_naive()
        session.commit()
        return len(stale)
    finally:
        session.close()


if __name__ == "__main__":
    celery.start()
