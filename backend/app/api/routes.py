from fastapi import APIRouter, UploadFile, File, HTTPException, Body
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
import json
import re
from app.models.schema_models import GenerateRequest, NormalizedSchema, QueryRequest, QueryResponse, SchemaUpdate, PopulateRequest, ExecuteQueryRequest, ExecuteQueryResponse
from app.models.database import get_session, Project
from app.services.schema_service import SchemaService
from app.services.document_service import DocumentService
from app.services.population_service import PopulationService
from app.services.query_service import QueryService
from app.services.chat_service import chat, get_history, clear_history, extract_schema_with_fallback
from app.tasks import generate_schema_task, populate_data_task, export_schema_task
from app.core.llm import get_llm_info, get_llm_run_metadata
from app.utils.research import atomic_write_json, new_run_id, record_run, run_manifest, sha256_file, sha256_text, stable_hash, utc_now
from app.services.metrics_service import MetricsService
from app.services.interaction_logger import interaction_logger
from app.services.backup_service import BackupService
from app.utils.logger import log
from app.utils.exceptions import AppException
from pathlib import Path
import tempfile
import os
import shutil
from typing import Literal

router = APIRouter(prefix="/api")
schema_svc = SchemaService()
doc_svc = DocumentService()
pop_svc = PopulationService()
query_svc = QueryService()
metrics_svc = MetricsService()
backup_svc = BackupService()


def _log_research_run(event_type: str, project_id: str, data: dict, run_id: str | None = None):
    run_id = run_id or new_run_id()
    manifest = data.get("run_manifest")
    if isinstance(manifest, dict):
        manifest["output_schema_hash"] = data.get("schema_final_hash")
        result = data.get("result")
        if isinstance(result, dict):
            manifest["extraction_paths"] = sorted({
                info.get("provenance", {}).get("method")
                for info in result.values() if isinstance(info, dict) and isinstance(info.get("provenance"), dict)
                and info["provenance"].get("method")
            })
            manifest["skipped_count"] = sum(info.get("skipped", 0) for info in result.values() if isinstance(info, dict))
        manifest.setdefault("warnings", [])
    return record_run(interaction_logger, project_id, event_type, run_id, data)

@router.post("/projects")
def create_project(name: str = Body(...), prompt: str = Body("")):
    return schema_svc.create_project(name, prompt)

@router.get("/projects")
def list_projects():
    return schema_svc.list_projects()

@router.get("/projects/{project_id}")
def get_project(project_id: str):
    return schema_svc.get_project(project_id)

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    result = schema_svc.delete_project(project_id)
    result["interaction_events_deleted"] = interaction_logger.erase_project(project_id)
    surveys_deleted = 0
    survey_root = Path("projects") / "surveys"
    if survey_root.exists():
        for survey_path in survey_root.glob("*.json"):
            try:
                with open(survey_path, encoding="utf-8") as source:
                    if json.load(source).get("project_id") == project_id:
                        survey_path.unlink()
                        surveys_deleted += 1
            except (OSError, json.JSONDecodeError):
                continue
    result["surveys_deleted"] = surveys_deleted
    return result

@router.post("/projects/{project_id}/generate")
async def generate_schema(project_id: str, req: GenerateRequest):
    started_at = utc_now()
    run_id = new_run_id()
    document_hashes = []
    for doc_id in req.document_ids:
        try:
            document_hash = sha256_file(doc_svc.get_document(doc_id, project_id).file_path)
            if document_hash:
                document_hashes.append(document_hash)
        except AppException:
            continue
    try:
        result = await schema_svc.generate_from_prompt(project_id, req)
    except Exception as exc:
        _log_research_run("schema_generation_failed", project_id, {
            "status": "failed", "schema_initial_hash": None, "schema_final_hash": None,
            "warnings": [{"category": "generation_error", "error_type": type(exc).__name__}],
            "run_manifest": run_manifest(started_at, "schema_prompt_v1", req, {
                "prompt_sha256": sha256_text(req.prompt), "document_sha256": document_hashes,
            }),
        }, run_id=run_id)
        raise
    _log_research_run("schema_generated", project_id, {
        **get_llm_run_metadata(0.1, req.prompt, document_hashes),
        "schema_initial": result.model_dump(),
        "schema_final": result.model_dump(),
        "schema_initial_hash": stable_hash(result.model_dump()),
        "schema_final_hash": stable_hash(result.model_dump()),
        "document_ids": req.document_ids,
        "run_manifest": run_manifest(started_at, "schema_prompt_v1", req, {
            "prompt_sha256": sha256_text(req.prompt), "document_sha256": document_hashes,
        }),
    }, run_id=run_id)
    return result

@router.get("/projects/{project_id}/schema")
def get_schema(project_id: str):
    return schema_svc.get_schema(project_id)

@router.put("/projects/{project_id}/schema")
def update_schema(project_id: str, schema: NormalizedSchema):
    previous = schema_svc.get_schema(project_id)
    result = schema_svc.update_schema(project_id, schema)
    _log_research_run("schema_updated", project_id, {
        "schema_initial": previous.model_dump() if previous else None,
        "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(previous.model_dump()) if previous else None,
        "schema_final_hash": stable_hash(schema.model_dump()),
        "method": "human_in_the_loop",
    })
    return result

class ChatRequest(BaseModel):
    message: str
    document_ids: list[str] = []
    condition: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    participant_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")

@router.post("/projects/{project_id}/chat")
async def chat_schema(project_id: str, req: ChatRequest):
    started_at = utc_now()
    run_id = new_run_id()
    project = schema_svc.get_project(project_id)
    existing = schema_svc.get_schema(project_id)
    document_hashes = []
    try:
        for doc_id in req.document_ids:
            digest = sha256_file(doc_svc.get_document(doc_id, project_id).file_path)
            if digest:
                document_hashes.append(digest)
        response = await chat(project_id, req.message, req.document_ids, existing_schema=existing)
        schema = await extract_schema_with_fallback(project_id, response, existing_schema=existing)
    except Exception as exc:
        _log_research_run("schema_chat_failed", project_id, {
            "status": "failed", "schema_initial_hash": stable_hash(existing.model_dump()) if existing else None,
            "schema_final_hash": None,
            "warnings": [{"category": "chat_generation_error", "error_type": type(exc).__name__}],
            "run_manifest": run_manifest(started_at, "schema_chat_prompt_v1", req, {
                "prompt_sha256": sha256_text(req.message), "document_sha256": document_hashes,
            }),
        }, run_id=run_id)
        raise
    _log_research_run("schema_chat", project_id, {
        **get_llm_run_metadata(0.1, req.message, document_hashes),
        "schema_initial": existing.model_dump() if existing else None,
        "schema_final": schema.model_dump() if schema else None,
        "schema_initial_hash": stable_hash(existing.model_dump()) if existing else None,
        "schema_final_hash": stable_hash(schema.model_dump()) if schema else None,
        "document_ids": req.document_ids,
        "run_manifest": run_manifest(started_at, "schema_chat_prompt_v1", req, {
            "prompt_sha256": sha256_text(req.message), "document_sha256": document_hashes,
        }),
    }, run_id=run_id)
    return {"response": response, "schema": schema.model_dump() if schema else None}

@router.post("/projects/{project_id}/chat-accept")
def accept_chat_schema(project_id: str, schema: NormalizedSchema):
    previous = schema_svc.get_schema(project_id)
    result = schema_svc.update_schema(project_id, schema)
    clear_history(project_id)
    _log_research_run("schema_updated", project_id, {
        "schema_initial": previous.model_dump() if previous else None,
        "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(previous.model_dump()) if previous else None,
        "schema_final_hash": stable_hash(schema.model_dump()),
        "method": "human_in_the_loop_chat_accept",
    })
    return result

def _remove_temp_file(path: str, attempts: int = 5, retry_delay_seconds: float = 0.1):
    import time
    for attempt in range(attempts):
        try:
            if os.path.exists(path):
                os.unlink(path)
            return
        except PermissionError:
            if attempt == attempts - 1:
                log.warning(f"Could not delete temporary upload file {path}: file handle still held")
                break
            time.sleep(retry_delay_seconds)
        except OSError:
            break


@router.post("/projects/{project_id}/documents")
async def upload_document(project_id: str, file: UploadFile = File(...)):
    schema_svc.get_project(project_id)
    max_upload_size = 25 * 1024 * 1024
    allowed_extensions = {".pdf", ".xls", ".xlsx", ".txt", ".csv", ".sql"}
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()
    if not original_filename or extension not in allowed_extensions:
        raise HTTPException(status_code=422, detail="Formato non supportato. Usa PDF, Excel, CSV, TXT o SQL.")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=extension)
    try:
        total_size = 0
        while chunk := await file.read(min(1024 * 1024, max_upload_size - total_size + 1)):
            total_size += len(chunk)
            if total_size > max_upload_size:
                raise HTTPException(status_code=413, detail="Il file supera il limite di 25 MB.")
            tmp.write(chunk)
        tmp.close()
        doc = doc_svc.upload_document(project_id, tmp.name, original_filename=original_filename)
        digest = sha256_file(doc.file_path)
        interaction_logger.log_event("document_uploaded", project_id, {
            "document_id": doc.id, "file_type": doc.file_type, "sha256": digest,
            "size_bytes": total_size, "extraction_method": "deterministic",
})
        return {"id": doc.id, "filename": doc.filename, "file_type": doc.file_type,
                "provenance": {"sha256": digest, "method": "deterministic"}}
    finally:
        tmp.close()
        _remove_temp_file(tmp.name)

@router.post("/projects/{project_id}/import-sql")
async def import_sql(project_id: str, file: UploadFile = File(...), dialect: str = "sqlite"):
    started_at = utc_now()
    from app.core.sql_importer import extract_schema, clean_inserts, split_sql_statements
    if dialect not in {"sqlite", "postgresql", "mysql", "mssql"}:
        raise HTTPException(status_code=422, detail="Dialetto SQL non supportato.")
    if Path(file.filename or "").suffix.lower() != ".sql":
        raise HTTPException(status_code=422, detail="È richiesto un file .sql.")
    initial_schema = schema_svc.get_schema(project_id)
    max_upload_size = 25 * 1024 * 1024
    chunks = []
    total_size = 0
    while chunk := await file.read(min(1024 * 1024, max_upload_size - total_size + 1)):
        total_size += len(chunk)
        if total_size > max_upload_size:
            raise HTTPException(status_code=413, detail="Il file supera il limite di 25 MB.")
        chunks.append(chunk)
    content = b"".join(chunks)
    sql_text = content.decode("utf-8", errors="replace")

    project = schema_svc.get_project(project_id)

    schema = extract_schema(sql_text, dialect)
    if not schema.tables:
        raise HTTPException(status_code=400, detail="Nessuna tabella trovata nel file SQL")

    db_path = project.db_path
    if not db_path:
        project_dir = Path("projects") / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        db_path = str(project_dir / "database.sqlite")
    target_path = Path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    staging_fd, staging_name = tempfile.mkstemp(prefix=".sql-import-", suffix=".sqlite", dir=target_path.parent)
    os.close(staging_fd)
    os.unlink(staging_name)
    staging_path = Path(staging_name)

    from app.core.db_generator import create_database_from_schema
    try:
        create_database_from_schema(schema, str(staging_path))
        inserts = clean_inserts(sql_text, dialect)
        if inserts.strip():
            from sqlalchemy import create_engine, text
            db_engine = create_engine(f"sqlite:///{staging_path}")
            try:
                with db_engine.begin() as conn:
                    conn.execute(text("PRAGMA foreign_keys = OFF;"))
                    for stmt in split_sql_statements(inserts):
                        stmt = stmt.strip()
                        if not stmt:
                            continue
                        conn.execute(text(stmt))
                    conn.execute(text("PRAGMA foreign_keys = ON;"))
            finally:
                db_engine.dispose()
    except Exception as exc:
        if staging_path.exists():
            staging_path.unlink()
        log.warning(f"SQL import staging failed ({type(exc).__name__})")
        raise HTTPException(status_code=422, detail="DDL o INSERT non validi: importazione annullata.") from exc

    rollback_path = target_path.with_name(f".{target_path.name}.pre-import-{new_run_id()}")
    had_target = target_path.exists()
    if had_target:
        shutil.copy2(target_path, rollback_path)
        backup_svc.auto_backup(str(target_path), project_id, "import_sql")
    try:
        os.replace(staging_path, target_path)
        session = get_session(schema_svc.engine)
        try:
            proj = session.query(Project).filter(Project.id == project_id).first()
            if not proj:
                raise AppException(detail="Project not found", status_code=404)
            proj.db_path = str(target_path)
            proj.schema_json = schema.model_dump(mode="json")
            session.commit()
        finally:
            session.close()
    except Exception:
        if had_target and rollback_path.exists():
            os.replace(rollback_path, target_path)
        elif target_path.exists():
            target_path.unlink()
        raise
    finally:
        if staging_path.exists():
            staging_path.unlink()
        if rollback_path.exists():
            rollback_path.unlink()

    _log_research_run("import_sql", project_id, {
        "dialect": dialect, "tables": len(schema.tables),
        "sql_input_hash": sha256_text(sql_text),
        "schema_initial": initial_schema.model_dump() if initial_schema else None,
        "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(initial_schema.model_dump()) if initial_schema else None,
        "schema_final_hash": stable_hash(schema.model_dump()),
        "method": "deterministic_sql_parser",
        "run_manifest": run_manifest(started_at, "sql_import_v1", input_hashes={"sql_sha256": sha256_text(sql_text)}),
    })
    return {"tables": len(schema.tables), "schema": schema.model_dump()}

@router.get("/projects/{project_id}/documents")
def list_documents(project_id: str):
    schema_svc.get_project(project_id)
    return [{
        "id": doc.id, "project_id": doc.project_id, "filename": doc.filename,
        "file_type": doc.file_type,
        "created_at": doc.created_at, "provenance": {
            "sha256": sha256_file(doc.file_path), "method": "deterministic"
        }
    } for doc in doc_svc.list_documents(project_id)]

@router.delete("/projects/{project_id}/documents/{doc_id}")
def delete_document(project_id: str, doc_id: str):
    return doc_svc.delete_document(project_id, doc_id)

@router.post("/projects/{project_id}/populate")
async def populate(project_id: str, req: PopulateRequest):
    started_at = utc_now()
    run_id = new_run_id()
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        _log_research_run("population_failed", project_id, {
            "status": "failed", "warnings": [{"category": "schema_missing"}],
            "run_manifest": run_manifest(started_at, "population_prompt_v1", req),
        }, run_id=run_id)
        raise HTTPException(status_code=400, detail="Generate schema first")
    # Resolve ownership before the automatic backup so cross-project IDs have
    # no filesystem or database side effects.
    try:
        for document_id in set(req.document_ids):
            doc_svc.get_document(document_id, project_id)
    except Exception as exc:
        _log_research_run("population_failed", project_id, {
            "status": "failed", "schema_initial_hash": stable_hash(schema.model_dump()),
            "schema_final_hash": stable_hash(schema.model_dump()),
            "warnings": [{"category": "ownership_error", "error_type": type(exc).__name__}],
            "run_manifest": run_manifest(started_at, "population_prompt_v1", req),
        }, run_id=run_id)
        raise
    if project.db_path:
        backup_svc.auto_backup(project.db_path, project_id, "populate")
    try:
        result = await pop_svc.populate(project_id, project.db_path, schema, req.document_ids)
    except Exception as exc:
        _log_research_run("population_failed", project_id, {
            "status": "failed", "schema_initial_hash": stable_hash(schema.model_dump()),
            "schema_final_hash": stable_hash(schema.model_dump()),
            "warnings": [{"category": "population_error", "error_type": type(exc).__name__}],
            "run_manifest": run_manifest(started_at, "population_prompt_v1", req, {
                "schema_sha256": stable_hash(schema.model_dump()), "document_sha256": [],
            }),
        }, run_id=run_id)
        raise
    document_hashes = [sha256_file(doc_svc.get_document(doc_id, project_id).file_path) for doc_id in req.document_ids]
    _log_research_run("populate", project_id, {
        "result": result, "schema_initial": schema.model_dump(), "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(schema.model_dump()),
        "schema_final_hash": stable_hash(schema.model_dump()),
        "document_hashes": [item for item in document_hashes if item],
        **get_llm_run_metadata(0.0, json.dumps(schema.model_dump(), sort_keys=True), [item for item in document_hashes if item], input_label="population_input"),
        "parameters": {"deterministic_first": True, "semantic_mapping_temperature": 0.0, "fallback_temperature": 0.1},
        "run_manifest": run_manifest(started_at, "population_prompt_v1", req, {
            "schema_sha256": stable_hash(schema.model_dump()),
            "document_sha256": [item for item in document_hashes if item],
        }),
    }, run_id=run_id)
    return result

@router.post("/projects/{project_id}/query")
async def generate_query(project_id: str, req: QueryRequest):
    return await query_svc.generate(project_id, req.prompt, req.dialect)

@router.post("/projects/{project_id}/execute-query")
def execute_query(project_id: str, req: ExecuteQueryRequest):
    project = schema_svc.get_project(project_id)
    if not project or not project.db_path:
        raise HTTPException(status_code=400, detail="Nessun database trovato per questo progetto")

    sql = req.sql
    sql = re.sub(r'```\w*', '', sql)
    sql = sql.replace('```', '')
    sql = sql.strip()
    if not sql:
        raise HTTPException(status_code=400, detail="SQL vuoto")

    stmt_upper = sql.upper().strip()
    if any(kw in stmt_upper for kw in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "CREATE ", "ALTER ")):
        backup_svc.auto_backup(project.db_path, project_id, "execute_query")
        log.info("Auto-backup created before write query")

    db_engine = create_engine(f"sqlite:///{project.db_path}")
    try:
        with db_engine.connect() as conn:
            statements = [s.strip() for s in sql.split(';') if s.strip()]
            last_result = None
            total_affected = 0
            for stmt in statements:
                result = conn.execute(text(stmt))
                if result.returns_rows:
                    last_result = result
                else:
                    total_affected += result.rowcount if result.rowcount is not None else 0
            conn.commit()
            if last_result is not None:
                columns = list(last_result.keys())
                rows = [dict(zip(columns, row)) for row in last_result.fetchall()]
                interaction_logger.log_event("execute_query", project_id, {"type": "select", "columns": len(columns), "rows": len(rows)})
                return ExecuteQueryResponse(columns=columns, rows=rows, affected=len(rows))
            interaction_logger.log_event("execute_query", project_id, {"type": "write", "affected": total_affected})
            return ExecuteQueryResponse(columns=[], rows=[], affected=total_affected)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Esecuzione query fallita: {str(e)}")

@router.get("/projects/{project_id}/data/stats")
def get_table_stats(project_id: str):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema or not project.db_path:
        return {}
    from sqlalchemy import create_engine, text, inspect
    db_engine = create_engine(f"sqlite:///{project.db_path}")
    inspector = inspect(db_engine)
    stats = {}
    with db_engine.connect() as conn:
        for t in inspector.get_table_names():
            try:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM [{t}]")).scalar()
                stats[t] = cnt
            except:
                stats[t] = 0
    return stats

@router.get("/projects/{project_id}/data/{table_name}")
def get_table_data(project_id: str, table_name: str):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    valid_tables = {t.name for t in schema.tables}
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{project.db_path}")
    with engine.connect() as conn:
        result = conn.execute(text(f"SELECT * FROM [{table_name}] LIMIT 100"))
        rows = [dict(r._mapping) for r in result]
    return rows

@router.put("/projects/{project_id}/data/{table_name}")
def update_table_row(project_id: str, table_name: str, row: dict = Body(...)):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    valid_tables = {t.name for t in schema.tables}
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    tdef = next(t for t in schema.tables if t.name == table_name)
    pk_cols = [c.name for c in tdef.columns if c.is_primary_key]
    if not pk_cols:
        raise HTTPException(status_code=400, detail="Table has no primary key")
    set_parts = [f"[{c}] = :{c}" for c in row if c not in pk_cols and c in [x.name for x in tdef.columns]]
    if not set_parts:
        raise HTTPException(status_code=400, detail="No columns to update")
    where_parts = [f"[{pk}] = :{pk}" for pk in pk_cols]
    sql = f"UPDATE [{table_name}] SET {', '.join(set_parts)} WHERE {' AND '.join(where_parts)}"
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{project.db_path}")
    with engine.connect() as conn:
        conn.execute(text(sql), row)
        conn.commit()
    interaction_logger.log_event("data_row_update", project_id, {"table": table_name, "columns": sorted(c for c in row if c not in pk_cols), "pk_columns": pk_cols})
    return {"updated": True}

@router.delete("/projects/{project_id}/data/{table_name}")
def delete_table_row(project_id: str, table_name: str, pks: dict = Body(..., embed=True)):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    valid_tables = {t.name for t in schema.tables}
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    tdef = next(t for t in schema.tables if t.name == table_name)
    pk_cols = [c.name for c in tdef.columns if c.is_primary_key]
    for pk in pk_cols:
        if pk not in pks:
            raise HTTPException(status_code=400, detail=f"Missing PK column: {pk}")
    where_parts = [f"[{pk}] = :{pk}" for pk in pk_cols]
    sql = f"DELETE FROM [{table_name}] WHERE {' AND '.join(where_parts)}"
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{project.db_path}")
    with engine.connect() as conn:
        conn.execute(text(sql), pks)
        conn.commit()
    interaction_logger.log_event("data_row_delete", project_id, {"table": table_name, "pk_columns": pk_cols})
    return {"deleted": True}

@router.post("/projects/{project_id}/data/{table_name}")
def insert_table_row(project_id: str, table_name: str, row: dict = Body(...)):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    valid_tables = {t.name for t in schema.tables}
    if table_name not in valid_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name: {table_name}")
    tdef = next(t for t in schema.tables if t.name == table_name)
    valid_cols = [c.name for c in tdef.columns]
    cols = [c for c in valid_cols if c in row]
    if not cols:
        raise HTTPException(status_code=400, detail="No valid columns provided")
    col_list = ", ".join(f"[{c}]" for c in cols)
    param_list = ", ".join(f":{c}" for c in cols)
    sql = f"INSERT INTO [{table_name}] ({col_list}) VALUES ({param_list})"
    from sqlalchemy import create_engine, text
    engine = create_engine(f"sqlite:///{project.db_path}")
    with engine.connect() as conn:
        conn.execute(text(sql), {c: row[c] for c in cols})
        conn.commit()
    interaction_logger.log_event("data_row_insert", project_id, {"table": table_name, "columns": sorted(cols)})
    return {"inserted": True}

@router.get("/projects/{project_id}/metrics")
def get_metrics(project_id: str):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    metrics = {
        "norm3": metrics_svc.check_3nf(schema),
        "relationships": metrics_svc.relationship_f1(schema),
    }
    if project.db_path:
        metrics["data_quality"] = metrics_svc.data_quality(project_id, project.db_path, schema)
    metrics_svc.save_metrics(project_id, metrics)
    return metrics

class ClientInteraction(BaseModel):
    type: Literal["rename_column", "add_constraint", "remove_constraint", "ignore_suggestion", "accept_suggestion", "navigation"]
    target_type: Literal["project", "table", "column", "relationship", "suggestion"]
    target_name: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    action: str | None = Field(default=None, max_length=64, pattern=r"^[A-Za-z0-9_.-]+$")

    model_config = {"extra": "forbid"}


@router.post("/projects/{project_id}/interactions")
def log_interaction(project_id: str, event: ClientInteraction):
    schema_svc.get_project(project_id)
    interaction_logger.log_event(event.type, project_id, event.model_dump(exclude_none=True))
    return {"status": "logged"}

@router.get("/projects/{project_id}/interactions")
def get_interactions(project_id: str):
    schema_svc.get_project(project_id)
    return interaction_logger.get_events(project_id)

@router.post("/projects/{project_id}/export-interactions")
def export_interactions(project_id: str):
    schema_svc.get_project(project_id)
    from pathlib import Path
    export_path = Path("projects") / project_id / "interactions.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    count = interaction_logger.save_events(str(export_path), project_id=project_id)
    return {"path": str(export_path), "count": count}

@router.post("/experiments/compare")
def compare_approaches(payload: dict):
    from app.core.llm import generate_schema
    from app.models.database import get_session, Document
    import asyncio
    prompt = payload.get("prompt", "")
    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(status_code=422, detail="project_id obbligatorio.")
    schema_svc.get_project(project_id)
    doc_ids = payload.get("document_ids", [])
    session = get_session(schema_svc.engine)
    doc_context = ""
    if doc_ids:
        parts = []
        for doc_id in doc_ids:
            doc = session.query(Document).filter(Document.id == doc_id, Document.project_id == project_id).first()
            if not doc:
                session.close()
                raise HTTPException(status_code=404, detail="Document not found")
            if doc and doc.content_summary:
                parts.append(f"--- {doc.filename} ---\n{doc.content_summary}")
        doc_context = "\n\n".join(parts)
    session.close()
    auto_schema = asyncio.run(generate_schema(prompt, doc_context))
    auto_metrics = {"norm3": metrics_svc.check_3nf(auto_schema), "relationships": metrics_svc.relationship_f1(auto_schema)}
    return {"automatic": {"schema": auto_schema.model_dump(), "metrics": auto_metrics}}

@router.post("/surveys/nasa-tlx")
def submit_nasa_tlx(payload: dict):
    """Submit NASA-TLX survey for cognitive load measurement."""
    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(status_code=422, detail="project_id obbligatorio.")
    schema_svc.get_project(project_id)
    keys = ("mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration")
    if any(key not in payload for key in keys):
        raise HTTPException(status_code=422, detail="Completa tutte le sei dimensioni NASA Raw-TLX.")
    scores = {key: payload[key] for key in keys}
    if any(not isinstance(score, (int, float)) or isinstance(score, bool) or score < 0 or score > 100 or score % 5 != 0 for score in scores.values()):
        raise HTTPException(status_code=422, detail="I punteggi NASA Raw-TLX devono essere tra 0 e 100, con incrementi di 5.")
    aggregate_score = sum(scores.values()) / len(scores)
    survey = {
        "timestamp": utc_now().isoformat(),
        "type": "nasa_tlx",
        "project_id": payload.get("project_id", ""),
        "scores": scores,
        "aggregate_score": aggregate_score,
    }
    survey_path = Path("projects") / "surveys" / f"nasa_tlx_{survey['timestamp'].replace(':', '-')}_{new_run_id()}.json"
    survey_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(survey_path, survey)
    interaction_logger.log_event("survey_nasa_tlx", survey["project_id"], {"aggregate_score": aggregate_score})
    return {"status": "saved", "aggregate_score": aggregate_score}

@router.post("/surveys/sus")
def submit_sus(payload: dict):
    """Submit SUS (System Usability Scale) survey."""
    project_id = payload.get("project_id")
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(status_code=422, detail="project_id obbligatorio.")
    schema_svc.get_project(project_id)
    scores = payload.get("scores")
    if not isinstance(scores, list) or len(scores) != 10:
        raise HTTPException(status_code=422, detail="Completa tutte le 10 domande SUS.")
    if any(not isinstance(score, int) or isinstance(score, bool) or score < 1 or score > 5 for score in scores):
        raise HTTPException(status_code=422, detail="Ogni risposta SUS deve essere un intero tra 1 e 5.")
    survey = {
        "timestamp": utc_now().isoformat(),
        "type": "sus",
        "project_id": payload.get("project_id", ""),
        "scores": scores,
    }
    survey["total_score"] = sum((score - 1) if i % 2 == 0 else (5 - score) for i, score in enumerate(scores)) * 2.5
    survey_path = Path("projects") / "surveys" / f"sus_{survey['timestamp'].replace(':', '-')}_{new_run_id()}.json"
    survey_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_json(survey_path, survey)
    interaction_logger.log_event("survey_sus", survey["project_id"], {"aggregate_score": survey["total_score"]})
    return {"status": "saved", "total_score": survey["total_score"]}


@router.get("/llm/info")
def llm_info():
    return get_llm_info()

@router.get("/projects/{project_id}/export-full")
def export_full(project_id: str, dialect: str = "sqlite"):
    from app.core.db_export import export_full as do_export
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    content = do_export(dialect, project.db_path, schema)
    ext_map = {"sqlite": "sql", "postgresql": "sql", "mysql": "sql", "mssql": "sql"}
    return {"format": dialect, "content": content, "extension": ext_map.get(dialect, "sql")}

@router.post("/projects/{project_id}/backup")
def create_backup(project_id: str, label: str = ""):
    project = schema_svc.get_project(project_id)
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    result = backup_svc.create_backup(project.db_path, project_id, label)
    interaction_logger.log_event("backup", project_id, {"label": label, "file": result.get("file")})
    return result

@router.get("/projects/{project_id}/backups")
def list_backups(project_id: str):
    project = schema_svc.get_project(project_id)
    return backup_svc.list_backups(project_id, project.db_path)

@router.post("/projects/{project_id}/restore")
def restore_backup(project_id: str, backup_name: str = Body(..., embed=True)):
    project = schema_svc.get_project(project_id)
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    result = backup_svc.restore_backup(project.db_path, backup_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    interaction_logger.log_event("restore", project_id, {"backup": backup_name})
    return result

@router.get("/projects/{project_id}/export")
def export_schema(project_id: str, format: str = "sql"):
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")

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
                if col.is_unique:
                    col_def += " UNIQUE"
                cols.append(col_def)
            lines.append(f"CREATE TABLE {table.name} (\n" + ",\n".join(cols) + "\n);")
        return {"format": "sql", "content": "\n\n".join(lines)}

    elif format == "json":
        return {"format": "json", "content": schema.model_dump_json(indent=2)}

    elif format == "csv":
        import csv
        import io
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["table", "column", "type", "primary_key", "foreign_key", "not_null", "unique"])
        for table in schema.tables:
            for col in table.columns:
                writer.writerow([
                    table.name,
                    col.name,
                    col.data_type,
                    col.is_primary_key,
                    f"{col.foreign_key_table}.{col.foreign_key_column}" if col.is_foreign_key else "",
                    col.is_not_null,
                    col.is_unique,
                ])
        return {"format": "csv", "content": output.getvalue()}

    raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")

@router.post("/projects/{project_id}/generate-async")
def generate_schema_async(project_id: str, req: GenerateRequest):
    """Start async schema generation."""
    schema_svc.get_project(project_id)
    for document_id in set(req.document_ids):
        doc_svc.get_document(document_id, project_id)
    document_hashes = [sha256_file(doc_svc.get_document(doc_id, project_id).file_path) for doc_id in req.document_ids]
    context = {"condition": req.condition, "session_id": req.session_id, "participant_id": req.participant_id,
               **get_llm_run_metadata(0.1, req.prompt, [item for item in document_hashes if item]),
               "parameters": {"temperature": 0.1}, "document_hashes": [item for item in document_hashes if item]}
    task = generate_schema_task.delay(project_id, req.prompt, req.document_ids, context)
    return {"task_id": task.id, "status": "started"}

@router.post("/projects/{project_id}/populate-async")
def populate_async(project_id: str, req: PopulateRequest):
    """Start async data population."""
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    for document_id in set(req.document_ids):
        doc_svc.get_document(document_id, project_id)
    document_hashes = [sha256_file(doc_svc.get_document(doc_id, project_id).file_path) for doc_id in req.document_ids]
    context = {"condition": req.condition, "session_id": req.session_id, "participant_id": req.participant_id,
               **get_llm_run_metadata(0.0, json.dumps(schema.model_dump(), sort_keys=True),
                                      [item for item in document_hashes if item], input_label="population_input"),
               "schema_input_hash": stable_hash(schema.model_dump()),
               "parameters": {"deterministic_first": True, "semantic_mapping_temperature": 0.0,
                              "fallback_temperature": 0.1},
               "document_hashes": [item for item in document_hashes if item]}
    task = populate_data_task.delay(project_id, project.db_path, json.loads(schema.model_dump_json()), req.document_ids, context)
    return {"task_id": task.id, "status": "started"}

@router.post("/projects/{project_id}/export-async")
def export_async(project_id: str, format: str = "sql"):
    """Start async schema export."""
    schema_svc.get_project(project_id)
    task = export_schema_task.delay(project_id, format)
    return {"task_id": task.id, "status": "started"}

@router.get("/tasks/{task_id}")
def get_task_status(task_id: str):
    """Get async task status."""
    from app.tasks import celery
    task = celery.AsyncResult(task_id)
    return {"task_id": task_id, "status": task.status, "result": task.result if task.ready() else None}

