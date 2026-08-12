from celery import Celery
from app.core.llm import generate_schema
from app.core.db_generator import create_database_from_schema
from app.models.database import get_session, init_db, Project, Document
from app.utils.logger import log
from app.api.progress import set_progress
import asyncio
import json
import os
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
    broker_connection_retry_on_startup=True,
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


if __name__ == "__main__":
    celery.start()
