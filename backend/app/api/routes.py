from fastapi import APIRouter, UploadFile, File, HTTPException, Body, Depends
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text
import json
import re
import httpx

from app.core.auth import get_current_user
from app.core.quota import consume_ai
from app.core.research import require_research
from app.core.acl import is_admin, require_admin, ProjectAccess, ensure_user, project_editor, project_owner, project_viewer, resolve_role
from app.config import settings
from app.services.benchmark_service import run_model_benchmark, save_user_vote, BENCHMARK_SCENARIOS
from app.models.database import get_session, init_db, BenchmarkResult, UserVote
from app.models.schema_models import GenerateRequest, NormalizedSchema, QueryRequest, QueryResponse, SchemaUpdate, PopulateRequest, ExecuteQueryRequest, ExecuteQueryResponse
from app.models.database import get_session, Project
from app.services.schema_service import SchemaService, get_last_repair
from app.services.document_service import DocumentService
from app.services.population_service import PopulationService
from app.services.query_service import QueryService, record_query, list_queries
from app.services.chat_service import chat, get_history, clear_history, extract_schema_with_fallback
from app.tasks import generate_schema_task, populate_data_task, export_schema_task
from app import tasks as job_tasks
from app.core.llm import get_llm_info, get_llm_run_metadata
from app.utils.research import atomic_write_json, new_run_id, record_run, run_manifest, sha256_file, sha256_text, stable_hash, utc_now
from app.services.metrics_service import MetricsService
from app.services.interaction_logger import interaction_logger
from app.services.backup_service import BackupService
from app.utils.logger import log
from app.utils.exceptions import AppException
from pathlib import Path
import tempfile
from starlette.concurrency import run_in_threadpool
import os
import shutil
from typing import Literal


def _outbound_tls_verify() -> bool:
    """Verifica del certificato attiva di default; si spegne solo con OUTBOUND_TLS_VERIFY=0 (sviluppo, Ollama con certificato autofirmato)."""
    return os.getenv("OUTBOUND_TLS_VERIFY", "1") != "0"


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
def create_project(name: str = Body(...), prompt: str = Body(""), user: dict = Depends(get_current_user)):
    row = ensure_user(user)
    from app.core.runtime import get_setting
    if len(schema_svc.list_projects(user_id=row.id)) >= get_setting("max_projects_per_user"):
        raise AppException(detail="Hai raggiunto il numero massimo di progetti. Eliminane uno per crearne un altro.", status_code=409)
    return schema_svc.create_project(name, prompt, owner_id=row.id)

@router.get("/projects")
def list_projects(user: dict = Depends(get_current_user)):
    row = ensure_user(user)
    return schema_svc.list_project_summaries(user_id=row.id)


@router.get("/projects/{project_id}")
def get_project(project_id: str, access: ProjectAccess = Depends(project_viewer)):
    project = schema_svc.get_project(project_id)
    return {**{c.name: getattr(project, c.name) for c in project.__table__.columns}, "my_role": access.role}

@router.delete("/projects/{project_id}")
def delete_project(project_id: str, access: ProjectAccess = Depends(project_owner)):
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

def _with_repair(manifest: dict) -> dict:
    """Aggiunge al manifesto di run i tentativi di riparazione dello schema generato."""
    repair = get_last_repair()
    manifest["repair_attempts"] = repair["attempts"]
    manifest["repair_log"] = repair["log"]
    return manifest


@router.post("/projects/{project_id}/generate", dependencies=[Depends(project_editor), Depends(consume_ai("generate"))])
async def generate_schema(project_id: str, req: GenerateRequest, access: ProjectAccess = Depends(project_editor)):
    _set_finalized(project_id, None)
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
        result = await schema_svc.generate_from_prompt(project_id, req, author=access.user_id)
    except Exception as exc:
        _log_research_run("schema_generation_failed", project_id, {
            "status": "failed", "schema_initial_hash": None, "schema_final_hash": None,
            "warnings": [{"category": "generation_error", "error_type": type(exc).__name__}],
            "run_manifest": _with_repair(run_manifest(started_at, "schema_prompt_v1", req, {
                "prompt_sha256": sha256_text(req.prompt), "document_sha256": document_hashes,
            })),
        }, run_id=run_id)
        raise
    _log_research_run("schema_generated", project_id, {
        **get_llm_run_metadata(0.1, req.prompt, document_hashes),
        "schema_initial": result.model_dump(),
        "schema_final": result.model_dump(),
        "schema_initial_hash": stable_hash(result.model_dump()),
        "schema_final_hash": stable_hash(result.model_dump()),
        "document_ids": req.document_ids,
        "run_manifest": _with_repair(run_manifest(started_at, "schema_prompt_v1", req, {
            "prompt_sha256": sha256_text(req.prompt), "document_sha256": document_hashes,
        })),
    }, run_id=run_id)
    return result

@router.get("/projects/{project_id}/schema", dependencies=[Depends(project_viewer)])
def get_schema(project_id: str):
    return schema_svc.get_schema(project_id)

@router.put("/projects/{project_id}/schema", dependencies=[Depends(project_editor)])
def update_schema(project_id: str, schema: NormalizedSchema, access: ProjectAccess = Depends(project_editor)):
    _ensure_not_finalized(project_id)
    previous = schema_svc.get_schema(project_id)
    result = schema_svc.update_schema(project_id, schema, author=access.user_id, origin="manuale")
    _log_research_run("schema_updated", project_id, {
        "schema_initial": previous.model_dump() if previous else None,
        "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(previous.model_dump()) if previous else None,
        "schema_final_hash": stable_hash(schema.model_dump()),
        "method": "human_in_the_loop",
    })
    return result

def _ensure_not_finalized(project_id: str):
    if schema_svc.get_project(project_id).schema_finalized_at is not None:
        raise AppException(detail="Lo schema è definitivo: non si può più modificare.", status_code=409)


def _set_finalized(project_id: str, value):
    session = get_session(schema_svc.engine)
    try:
        session.query(Project).filter(Project.id == project_id).update({"schema_finalized_at": value})
        session.commit()
    finally:
        session.close()


@router.post("/projects/{project_id}/finalize", dependencies=[Depends(project_editor)])
def finalize_schema(project_id: str):
    from datetime import datetime, timezone
    if not schema_svc.get_schema(project_id):
        raise AppException(detail="Genera prima lo schema.", status_code=400)
    _set_finalized(project_id, datetime.now(timezone.utc).replace(tzinfo=None))
    return {"finalized": True}


@router.post("/projects/{project_id}/reset-data", dependencies=[Depends(project_editor)])
def reset_data(project_id: str):
    """Svuota le tabelle del progetto (dopo un backup) senza toccare lo schema."""
    project = schema_svc.get_project(project_id)
    schema = schema_svc.get_schema(project_id)
    if not project.db_path or not schema:
        raise AppException(detail="Nessun database da svuotare.", status_code=400)
    backup_svc.auto_backup(project.db_path, project_id, "reset_data")
    import sqlite3
    con = sqlite3.connect(project.db_path)
    try:
        con.execute("PRAGMA foreign_keys=OFF")
        for table in schema.tables:
            con.execute(f'DELETE FROM "{table.name.replace(chr(34), "")}"')
        con.commit()
    finally:
        con.close()
    return {"reset": True}


class ChatRequest(BaseModel):
    message: str
    document_ids: list[str] = []
    condition: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,64}$")
    session_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")
    participant_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9_.-]{1,128}$")

@router.post("/projects/{project_id}/chat", dependencies=[Depends(project_editor), Depends(consume_ai("chat"))])
async def chat_schema(project_id: str, req: ChatRequest):
    _ensure_not_finalized(project_id)
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

@router.get("/projects/{project_id}/chat/history", dependencies=[Depends(project_viewer)])
def chat_history(project_id: str):
    return {"messages": get_history(project_id)}

@router.post("/projects/{project_id}/chat-accept", dependencies=[Depends(project_editor)])
def accept_chat_schema(project_id: str, schema: NormalizedSchema, access: ProjectAccess = Depends(project_editor)):
    previous = schema_svc.get_schema(project_id)
    result = schema_svc.update_schema(project_id, schema, author=access.user_id, origin="chat")
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


@router.post("/projects/{project_id}/documents", dependencies=[Depends(project_editor)])
async def upload_document(project_id: str, file: UploadFile = File(...), user: dict = Depends(get_current_user)):
    schema_svc.get_project(project_id)
    from app.core.runtime import get_setting
    upload_mb = int(get_setting("max_upload_mb"))
    max_upload_size = upload_mb * 1024 * 1024
    allowed_extensions = {".pdf", ".xls", ".xlsx", ".txt", ".csv", ".sql"}
    original_filename = Path(file.filename or "").name
    extension = Path(original_filename).suffix.lower()
    if not original_filename or extension not in allowed_extensions:
        raise HTTPException(status_code=422, detail="Formato non supportato. Usa PDF, Excel, CSV, TXT o SQL.")

    tmp = await run_in_threadpool(tempfile.NamedTemporaryFile, delete=False, suffix=extension)
    try:
        total_size = 0
        while chunk := await file.read(min(1024 * 1024, max_upload_size - total_size + 1)):
            total_size += len(chunk)
            if total_size > max_upload_size:
                raise HTTPException(status_code=413, detail=f"Il file supera il limite di {upload_mb} MB.")
            tmp.write(chunk)
        tmp.close()

        def ocr_gate():
            # l'OCR e' una chiamata al modello: consuma la quota come le altre
            try:
                _consume_ai_now(user, "ocr", project_id)
                return True
            except AppException:
                return False

        doc = await run_in_threadpool(doc_svc.upload_document, project_id, tmp.name,
                                      original_filename=original_filename, ocr_gate=ocr_gate)
        digest = sha256_file(doc.file_path)
        interaction_logger.log_event("document_uploaded", project_id, {
            "document_id": doc.id, "file_type": doc.file_type, "sha256": digest,
            "size_bytes": total_size, "extraction_method": "deterministic",
})
        return {"id": doc.id, "filename": doc.filename, "file_type": doc.file_type,
                "needs_ocr": bool(doc.needs_ocr),
                "provenance": {"sha256": digest, "method": "deterministic"}}
    finally:
        tmp.close()
        _remove_temp_file(tmp.name)

@router.post("/projects/{project_id}/import-sql", dependencies=[Depends(project_editor)])
async def import_sql(project_id: str, file: UploadFile = File(...), dialect: str = "sqlite",
                     access: ProjectAccess = Depends(project_editor)):
    _set_finalized(project_id, None)
    started_at = utc_now()
    from app.core.sql_importer import extract_schema, clean_inserts, split_sql_statements
    if dialect not in {"sqlite", "postgresql", "mysql", "mssql"}:
        raise HTTPException(status_code=422, detail="Dialetto SQL non supportato.")
    if Path(file.filename or "").suffix.lower() != ".sql":
        raise HTTPException(status_code=422, detail="È richiesto un file .sql.")
    initial_schema = schema_svc.get_schema(project_id)
    from app.core.runtime import get_setting
    upload_mb = int(get_setting("max_upload_mb"))
    max_upload_size = upload_mb * 1024 * 1024
    chunks = []
    total_size = 0
    while chunk := await file.read(min(1024 * 1024, max_upload_size - total_size + 1)):
        total_size += len(chunk)
        if total_size > max_upload_size:
            raise HTTPException(status_code=413, detail=f"Il file supera il limite di {upload_mb} MB.")
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

    schema_svc.record_version(project_id, schema, access.user_id, "manuale")
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

@router.get("/projects/{project_id}/documents", dependencies=[Depends(project_viewer)])
def list_documents(project_id: str):
    schema_svc.get_project(project_id)
    return [{
        "id": doc.id, "project_id": doc.project_id, "filename": doc.filename,
        "file_type": doc.file_type, "needs_ocr": bool(doc.needs_ocr),
        "created_at": doc.created_at, "provenance": {
            "sha256": sha256_file(doc.file_path), "method": "deterministic"
        }
    } for doc in doc_svc.list_documents(project_id)]

@router.delete("/projects/{project_id}/documents/{doc_id}", dependencies=[Depends(project_editor)])
def delete_document(project_id: str, doc_id: str):
    return doc_svc.delete_document(project_id, doc_id)

@router.post("/projects/{project_id}/populate", dependencies=[Depends(project_editor), Depends(consume_ai("populate"))])
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

@router.post("/projects/{project_id}/query", dependencies=[Depends(project_viewer), Depends(consume_ai("query"))])
async def generate_query(project_id: str, req: QueryRequest, access: ProjectAccess = Depends(project_viewer)):
    try:
        response = await query_svc.generate(project_id, req.prompt, req.dialect)
    except Exception:
        record_query(project_id, access.user_id, req.prompt, None, "errore", source="query")
        raise
    record_query(project_id, access.user_id, req.prompt, response.sql, "ok", source="query")
    return response



def _author_labels(user_ids, access: "ProjectAccess") -> dict:
    """Etichette per gli autori: mai l'id interno. Il proprietario vede il nome visualizzato, gli altri
    solo "Tu" per le proprie voci e "Altro membro" per il resto."""
    from app.models.database import User
    labels: dict = {}
    names: dict = {}
    wanted = {u for u in user_ids if u}
    if wanted and access.role == "owner":
        session = get_session(schema_svc.engine)
        try:
            names = {u.id: (u.display_name or "").strip() for u in session.query(User).filter(User.id.in_(wanted)).all()}
        finally:
            session.close()
    for uid in wanted:
        if uid == access.user_id:
            labels[uid] = "Tu"
        elif access.role == "owner":
            name = names.get(uid)
            labels[uid] = name if name and name != uid else "Membro"
        else:
            labels[uid] = "Altro membro"
    return labels


def _visible_to(access: "ProjectAccess", owner_of_entry: str | None) -> bool:
    """Il proprietario del progetto vede tutto, gli altri solo le proprie voci."""
    return access.role == "owner" or owner_of_entry == access.user_id


@router.get("/projects/{project_id}/queries")
def query_history(project_id: str, access: ProjectAccess = Depends(project_viewer)):
    """Ultime 50 domande: il proprietario vede quelle di tutti, gli altri membri solo le proprie."""
    schema_svc.get_project(project_id)
    items = list_queries(project_id, user_id=None if access.role == "owner" else access.user_id)
    labels = _author_labels([i["user_id"] for i in items], access)
    for item in items:
        uid = item.pop("user_id", None)
        item["mine"] = uid == access.user_id
        item["author_label"] = labels.get(uid, "Sconosciuto")
    return {"queries": items}

_WRITE_WORDS = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|REPLACE|VACUUM|ATTACH|DETACH|PRAGMA|REINDEX)\b")


def _install_sqlite_guard(engine, read_only: bool):
    """Autorizzatore SQLite: niente ATTACH/PRAGMA/estensioni per nessuno; i lettori non scrivono."""
    import sqlite3
    from sqlalchemy import event

    deny = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}
    read_ok = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, sqlite3.SQLITE_RECURSIVE}

    def authorizer(action, arg1, arg2, db_name, source):
        if action in deny:
            return sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() in {"load_extension", "readfile", "writefile"}:
            return sqlite3.SQLITE_DENY
        if read_only and action not in read_ok:
            return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK

    @event.listens_for(engine, "connect")
    def _on_connect(dbapi_conn, _record):
        dbapi_conn.set_authorizer(authorizer)


@router.post("/projects/{project_id}/execute-query", dependencies=[Depends(project_viewer)])
def execute_query(project_id: str, req: ExecuteQueryRequest, access: ProjectAccess = Depends(project_viewer)):
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
    is_write = bool(_WRITE_WORDS.search(stmt_upper)) or not stmt_upper.startswith(("SELECT", "WITH", "EXPLAIN"))
    if is_write and not access.allows("editor"):
        raise HTTPException(status_code=403, detail="Con il ruolo di lettore puoi eseguire solo query di lettura")
    if is_write:
        backup_svc.auto_backup(project.db_path, project_id, "execute_query")
        log.info("Auto-backup created before write query")

    db_engine = create_engine(f"sqlite:///{project.db_path}")
    _install_sqlite_guard(db_engine, read_only=not access.allows("editor"))
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
                record_query(project_id, access.user_id, None, sql, "ok", rows=len(rows), source="execute")
                return ExecuteQueryResponse(columns=columns, rows=rows, affected=len(rows))
            interaction_logger.log_event("execute_query", project_id, {"type": "write", "affected": total_affected})
            record_query(project_id, access.user_id, None, sql, "ok", rows=total_affected, source="execute")
            return ExecuteQueryResponse(columns=[], rows=[], affected=total_affected)
    except Exception as e:
        record_query(project_id, access.user_id, None, sql, "errore", source="execute")
        raise HTTPException(status_code=400, detail=f"Esecuzione query fallita: {str(e)}")

@router.get("/projects/{project_id}/data/stats", dependencies=[Depends(project_viewer)])
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

@router.get("/projects/{project_id}/data/{table_name}", dependencies=[Depends(project_viewer)])
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

@router.put("/projects/{project_id}/data/{table_name}", dependencies=[Depends(project_editor)])
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

@router.delete("/projects/{project_id}/data/{table_name}", dependencies=[Depends(project_editor)])
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

@router.post("/projects/{project_id}/data/{table_name}", dependencies=[Depends(project_editor)])
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

@router.get("/projects/{project_id}/metrics", dependencies=[Depends(project_viewer)])
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


@router.post("/projects/{project_id}/interactions", dependencies=[Depends(project_viewer)])
def log_interaction(project_id: str, event: ClientInteraction):
    if not settings.research_mode:
        return {"status": "disabled"}
    schema_svc.get_project(project_id)
    interaction_logger.log_event(event.type, project_id, event.model_dump(exclude_none=True))
    return {"status": "logged"}

@router.get("/projects/{project_id}/interactions", dependencies=[Depends(project_viewer), Depends(require_research)])
def get_interactions(project_id: str):
    schema_svc.get_project(project_id)
    return interaction_logger.get_events(project_id)

@router.post("/projects/{project_id}/export-interactions", dependencies=[Depends(project_viewer), Depends(require_research)])
def export_interactions(project_id: str):
    schema_svc.get_project(project_id)
    from pathlib import Path
    export_path = Path("projects") / project_id / "interactions.json"
    export_path.parent.mkdir(parents=True, exist_ok=True)
    count = interaction_logger.save_events(str(export_path), project_id=project_id)
    return {"path": str(export_path), "count": count}

def _assert_project_role(project_id, user: dict, minimum: str):
    from app.core.acl import ROLE_RANK, resolve_role
    if not isinstance(project_id, str) or not project_id:
        raise HTTPException(status_code=422, detail="project_id obbligatorio.")
    row = ensure_user(user)
    role = resolve_role(project_id, row.id)
    if role is None:
        raise AppException(detail="Project not found", status_code=404)
    if ROLE_RANK[role] < ROLE_RANK[minimum]:
        raise AppException(detail="Permesso insufficiente per questa azione", status_code=403)


def _consume_ai_now(user: dict, kind: str, project_id=None):
    row = ensure_user(user)
    return consume_ai(kind)(project_id, row)


@router.post("/experiments/compare", dependencies=[Depends(require_research)])
def compare_approaches(payload: dict, user: dict = Depends(get_current_user)):
    _assert_project_role(payload.get("project_id"), user, "viewer")
    _consume_ai_now(user, "experiment", payload.get("project_id"))
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

@router.post("/surveys/nasa-tlx", dependencies=[Depends(require_research)])
def submit_nasa_tlx(payload: dict, user: dict = Depends(get_current_user)):
    _assert_project_role(payload.get("project_id"), user, "viewer")
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

@router.post("/surveys/sus", dependencies=[Depends(require_research)])
def submit_sus(payload: dict, user: dict = Depends(get_current_user)):
    _assert_project_role(payload.get("project_id"), user, "viewer")
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
def llm_info(user: dict = Depends(get_current_user)):
    return get_llm_info()

@router.get("/projects/{project_id}/export-full", dependencies=[Depends(project_viewer)])
def export_full(project_id: str, dialect: str | None = None):
    from app.core.db_export import export_full as do_export, SUPPORTED_DIALECTS
    project = schema_svc.get_project(project_id)
    dialect = dialect or project.target_dialect or "sqlite"
    if dialect not in SUPPORTED_DIALECTS:
        raise HTTPException(status_code=422, detail="Dialetto non supportato. Usa: " + ", ".join(SUPPORTED_DIALECTS) + ".")
    schema = schema_svc.get_schema(project_id)
    if not schema:
        raise HTTPException(status_code=400, detail="Generate schema first")
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    content = do_export(dialect, project.db_path, schema)
    ext_map = {name: "sql" for name in SUPPORTED_DIALECTS}
    return {"format": dialect, "content": content, "extension": ext_map.get(dialect, "sql")}

@router.post("/projects/{project_id}/backup", dependencies=[Depends(project_editor)])
def create_backup(project_id: str, label: str = ""):
    project = schema_svc.get_project(project_id)
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    result = backup_svc.create_backup(project.db_path, project_id, label)
    interaction_logger.log_event("backup", project_id, {"label": label, "file": result.get("file")})
    return result

@router.get("/projects/{project_id}/backups", dependencies=[Depends(project_viewer)])
def list_backups(project_id: str):
    project = schema_svc.get_project(project_id)
    return backup_svc.list_backups(project_id, project.db_path)

@router.post("/projects/{project_id}/restore", dependencies=[Depends(project_editor)])
def restore_backup(project_id: str, backup_name: str = Body(..., embed=True)):
    project = schema_svc.get_project(project_id)
    if not project.db_path:
        raise HTTPException(status_code=400, detail="No database found")
    result = backup_svc.restore_backup(project.db_path, backup_name)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    interaction_logger.log_event("restore", project_id, {"backup": backup_name})
    return result

@router.get("/projects/{project_id}/export", dependencies=[Depends(project_viewer)])
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

@router.post("/projects/{project_id}/generate-async", dependencies=[Depends(project_editor), Depends(consume_ai("generate"))])
def generate_schema_async(project_id: str, req: GenerateRequest, access: ProjectAccess = Depends(project_editor)):
    """Start async schema generation."""
    schema_svc.get_project(project_id)
    for document_id in set(req.document_ids):
        doc_svc.get_document(document_id, project_id)
    document_hashes = [sha256_file(doc_svc.get_document(doc_id, project_id).file_path) for doc_id in req.document_ids]
    context = {"condition": req.condition, "session_id": req.session_id, "participant_id": req.participant_id,
               **get_llm_run_metadata(0.1, req.prompt, [item for item in document_hashes if item]),
               "parameters": {"temperature": 0.1}, "document_hashes": [item for item in document_hashes if item]}
    task = generate_schema_task.apply_async(args=(project_id, req.prompt, req.document_ids, context),
                                            task_id=_new_task_id(project_id, access.user_id))
    return {"task_id": task.id, "status": "started"}

@router.post("/projects/{project_id}/populate-async", dependencies=[Depends(project_editor), Depends(consume_ai("populate"))])
def populate_async(project_id: str, req: PopulateRequest, access: ProjectAccess = Depends(project_editor)):
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
    task = populate_data_task.apply_async(
        args=(project_id, project.db_path, json.loads(schema.model_dump_json()), req.document_ids, context),
        task_id=_new_task_id(project_id, access.user_id))
    return {"task_id": task.id, "status": "started"}

@router.post("/projects/{project_id}/export-async", dependencies=[Depends(project_viewer)])
def export_async(project_id: str, format: str = "sql", access: ProjectAccess = Depends(project_viewer)):
    """Start async schema export."""
    schema_svc.get_project(project_id)
    task = export_schema_task.apply_async(args=(project_id, format), task_id=_new_task_id(project_id, access.user_id))
    return {"task_id": task.id, "status": "started"}

def hmac_equal(a: str, b: str) -> bool:
    import hmac
    return hmac.compare_digest(a, b)


def _task_tag(user_id: str) -> str:
    import hashlib, hmac
    key = (os.getenv("TASK_BINDING_SECRET") or "aidb-task-binding").encode("utf-8")
    return hmac.new(key, str(user_id).encode("utf-8"), hashlib.sha256).hexdigest()[:16]


def _new_task_id(project_id: str, user_id: str) -> str:
    """L'id del task contiene progetto e un'etichetta del creatore: lo stato si legge solo con l'ACL del progetto."""
    import uuid
    return f"{project_id}.{_task_tag(user_id)}.{uuid.uuid4().hex}"


@router.get("/tasks/{task_id}")
def get_task_status(task_id: str, user: dict = Depends(get_current_user)):
    """Stato di un task asincrono: serve un ruolo sul progetto del task; il risultato lo vede solo chi l'ha avviato.
    L'admin senza ruolo sul progetto riceve 404 e non vede mai il risultato."""
    parts = task_id.split(".")
    if len(parts) != 3:
        raise AppException(detail="Task non trovato", status_code=404)
    project_id, tag, _ = parts
    row = ensure_user(user)
    if resolve_role(project_id, row.id) is None:
        raise AppException(detail="Task non trovato", status_code=404)
    from app.tasks import celery
    task = celery.AsyncResult(task_id)
    own = hmac_equal(tag, _task_tag(row.id))
    return {"task_id": task_id, "status": task.status, "project_id": project_id,
            "result": task.result if (own and task.ready()) else None}


# ==========================================
# Dialetto di destinazione, versioni dello schema, lavori in coda
# ==========================================

class DialectRequest(BaseModel):
    dialect: str


@router.put("/projects/{project_id}/dialect", dependencies=[Depends(project_editor)])
def set_target_dialect(project_id: str, body: DialectRequest):
    """Ricorda il dialetto di destinazione scelto per il progetto."""
    from app.core.db_export import SUPPORTED_DIALECTS
    if body.dialect not in SUPPORTED_DIALECTS:
        raise HTTPException(status_code=422, detail="Dialetto non supportato. Usa: " + ", ".join(SUPPORTED_DIALECTS) + ".")
    schema_svc.get_project(project_id)
    session = get_session(schema_svc.engine)
    try:
        session.query(Project).filter(Project.id == project_id).update({"target_dialect": body.dialect})
        session.commit()
    finally:
        session.close()
    return {"target_dialect": body.dialect}


def _mask_author(entry: dict, labels: dict, access: "ProjectAccess") -> dict:
    uid = entry.pop("author", None)
    entry["mine"] = uid == access.user_id
    entry["author_label"] = labels.get(uid, "Sistema")
    return entry


@router.get("/projects/{project_id}/schema/versions")
def list_schema_versions(project_id: str, access: ProjectAccess = Depends(project_viewer)):
    """Lo schema e' condiviso, quindi tutti i membri vedono l'elenco delle versioni; l'autore e' solo un'etichetta."""
    project = schema_svc.get_project(project_id)
    versions = schema_svc.list_versions(project_id)
    labels = _author_labels([v.get("author") for v in versions], access)
    return {"current": project.schema_version or 0, "finalized": project.schema_finalized_at is not None,
            "versions": [_mask_author(v, labels, access) for v in versions]}


@router.get("/projects/{project_id}/schema/versions/{version}")
def get_schema_version(project_id: str, version: int, access: ProjectAccess = Depends(project_viewer)):
    schema_svc.get_project(project_id)
    entry = schema_svc.get_version(project_id, version)
    return _mask_author(entry, _author_labels([entry.get("author")], access), access)


@router.post("/projects/{project_id}/schema/versions/{version}/restore")
def restore_schema_version(project_id: str, version: int, access: ProjectAccess = Depends(project_editor)):
    """Riporta lo schema a una versione precedente; il ripristino crea a sua volta una nuova versione."""
    _ensure_not_finalized(project_id)
    stored = schema_svc.get_version(project_id, version)
    schema = NormalizedSchema(**stored["schema"])
    previous = schema_svc.get_schema(project_id)
    schema_svc.update_schema(project_id, schema, author=access.user_id, origin="ripristino")
    _log_research_run("schema_updated", project_id, {
        "schema_initial": previous.model_dump() if previous else None,
        "schema_final": schema.model_dump(),
        "schema_initial_hash": stable_hash(previous.model_dump()) if previous else None,
        "schema_final_hash": stable_hash(schema.model_dump()),
        "method": "schema_version_restore",
    })
    return {"schema": schema.model_dump(), "schema_version": schema_svc.get_project(project_id).schema_version,
            "restored_from": version}


class JobRequest(BaseModel):
    kind: Literal["schema", "dati", "esportazione"]
    prompt: str | None = None
    document_ids: list[str] = []
    format: Literal["sql", "json"] = "sql"
    dialect: str | None = None


def _job_to_dict(job, access: "ProjectAccess | None" = None, labels: dict | None = None) -> dict:
    mine = access is not None and job.user_id == access.user_id
    label = (labels or {}).get(job.user_id) or ("Tu" if mine else "Altro membro")
    return {"id": job.id, "project_id": job.project_id, "mine": mine, "author_label": label, "kind": job.kind,
            "status": job.status, "progress": job.progress, "error": job.error, "result": job.result,
            "created_at": job.created_at, "updated_at": job.updated_at}


def _load_job(project_id: str, job_id: str, access: "ProjectAccess"):
    from app.models.database import Job
    session = get_session(schema_svc.engine)
    try:
        job = session.query(Job).filter(Job.id == job_id, Job.project_id == project_id).first()
        if job is None or not _visible_to(access, job.user_id):
            raise AppException(detail="Lavoro non trovato", status_code=404)
        return _job_to_dict(job, access, _author_labels([job.user_id], access))
    finally:
        session.close()


@router.post("/projects/{project_id}/jobs", status_code=202)
def create_job(project_id: str, req: JobRequest, user: dict = Depends(get_current_user),
               access: ProjectAccess = Depends(project_editor)):
    """Accoda un lavoro lungo: la risposta e' immediata, lo stato si legge con GET .../jobs/{id}."""
    from app.models.database import Job
    from app.core.db_export import SUPPORTED_DIALECTS
    row = ensure_user(user)
    schema_svc.get_project(project_id)
    params: dict = {}
    if req.kind == "schema":
        if not (req.prompt or "").strip():
            raise HTTPException(status_code=422, detail="Descrivi il database da generare.")
        params = {"prompt": req.prompt}
    if req.kind in ("schema", "dati"):
        for document_id in set(req.document_ids):
            doc_svc.get_document(document_id, project_id)
        params["document_ids"] = list(req.document_ids)
    if req.kind in ("dati", "esportazione") and not schema_svc.get_schema(project_id):
        raise HTTPException(status_code=400, detail="Genera prima lo schema.")
    if req.kind == "esportazione":
        if req.dialect is not None and req.dialect not in SUPPORTED_DIALECTS:
            raise HTTPException(status_code=422, detail="Dialetto non supportato.")
        params.update({"format": req.format, "dialect": req.dialect})
    job_tasks.expire_stale_jobs()
    from sqlalchemy.exc import IntegrityError
    busy_message = "C'è già un lavoro in corso su questo progetto. Attendi che finisca."
    session = get_session(schema_svc.engine)
    try:
        # un'unica transazione: il controllo e l'inserimento sono garantiti dall'indice unico parziale
        # (progetto, schema/dati, queued/running), quindi due richieste concorrenti non passano entrambe
        job = Job(project_id=project_id, user_id=row.id, kind=req.kind, status="queued", progress=0, params=params)
        session.add(job)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise AppException(detail=busy_message, status_code=409)
        job_id = job.id
    finally:
        session.close()
    if req.kind in ("schema", "dati"):
        try:
            _consume_ai_now(user, "generate" if req.kind == "schema" else "populate", project_id)
        except BaseException:
            # quota negata (o errore): il lavoro non parte e non occupa piu' il posto del progetto
            session = get_session(schema_svc.engine)
            try:
                session.query(Job).filter(Job.id == job_id).delete()
                session.commit()
            finally:
                session.close()
            raise
    executor = job_tasks.dispatch_job(job_id)
    job_tasks.update_job(job_id, executor=executor)
    return _load_job(project_id, job_id, access)


@router.get("/projects/{project_id}/jobs")
def list_jobs(project_id: str, status: str | None = None, access: ProjectAccess = Depends(project_viewer)):
    from app.models.database import Job
    schema_svc.get_project(project_id)
    job_tasks.expire_stale_jobs()
    session = get_session(schema_svc.engine)
    try:
        query = session.query(Job).filter(Job.project_id == project_id)
        if access.role != "owner":
            query = query.filter(Job.user_id == access.user_id)
        if status:
            query = query.filter(Job.status == status)
        jobs = query.order_by(Job.created_at.desc(), Job.id.desc()).limit(50).all()
        labels = _author_labels([j.user_id for j in jobs], access)
        return {"jobs": [_job_to_dict(j, access, labels) for j in jobs]}
    finally:
        session.close()


@router.get("/projects/{project_id}/jobs/{job_id}")
def get_job(project_id: str, job_id: str, access: ProjectAccess = Depends(project_viewer)):
    job_tasks.expire_stale_jobs()
    return _load_job(project_id, job_id, access)


@router.post("/projects/{project_id}/jobs/{job_id}/cancel")
def cancel_job(project_id: str, job_id: str, access: ProjectAccess = Depends(project_editor)):
    """Annulla un lavoro in coda o in corso: il risultato non viene salvato."""
    from app.models.database import Job
    session = get_session(schema_svc.engine)
    try:
        job = session.query(Job).filter(Job.id == job_id, Job.project_id == project_id).first()
        if job is None or not _visible_to(access, job.user_id):
            raise AppException(detail="Lavoro non trovato", status_code=404)
        if job.status not in ("queued", "running"):
            raise AppException(detail="Il lavoro è già terminato.", status_code=409)
        changed = session.query(Job).filter(
            Job.id == job_id, Job.status.in_(("queued", "running"))
        ).update({"status": "cancelled", "updated_at": job_tasks._now_naive()}, synchronize_session=False)
        session.commit()
        if not changed:
            raise AppException(detail="Il lavoro è già terminato.", status_code=409)
    finally:
        session.close()
    job_tasks.revoke_job(job_id)
    return _load_job(project_id, job_id, access)


# ==========================================
# Settings & Configuration Endpoints
# ==========================================

class SettingsUpdateSchema(BaseModel):
    llm_provider: str | None = None
    openai_model: str | None = None
    openai_api_key: str | None = None
    google_model: str | None = None
    google_api_key: str | None = None
    groq_model: str | None = None
    groq_api_key: str | None = None
    openrouter_model: str | None = None
    openrouter_api_key: str | None = None
    ollama_mode: str | None = None
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    ollama_api_key: str | None = None
    use_ollama: bool | None = None
    llm_temperature: float | None = None
    llm_top_p: float | None = None
    llm_max_tokens: int | None = None
    llm_max_requests_per_minute: int | None = None

@router.get("/settings/ollama-models")

async def list_ollama_models(
    base_url: str | None = None,
    api_key: str | None = None,
    user: dict = Depends(require_admin)
):
    target_url = base_url if base_url else settings.ollama_base_url
    target_key = api_key if api_key is not None else settings.ollama_api_key
    try:
        headers = {}
        if target_key and target_key.strip():
            headers["Authorization"] = f"Bearer {target_key.strip()}"
        url = f"{target_url.rstrip('/')}/api/tags"
        async with httpx.AsyncClient(verify=_outbound_tls_verify(), timeout=5.0) as client:
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                models = res.json().get("models", [])
                model_names = [m["name"] for m in models if "name" in m]
                if model_names:
                    return {"models": model_names}
            else:
                log.warning(f"Ollama tags endpoint returned status {res.status_code}: {res.text[:200]}")
    except Exception as e:
        log.warning(f"Failed to fetch Ollama models from {target_url}: {e}")
    return {"models": [settings.ollama_model]}


class OllamaTestRequest(BaseModel):
    prompt: str = "Rispondi in italiano: Che giorno è oggi?"
    model: str | None = None

@router.post("/settings/ollama-test")
async def test_ollama_prompt(body: OllamaTestRequest, user: dict = Depends(require_admin)):
    target_url = settings.ollama_base_url
    target_key = settings.ollama_api_key
    model = body.model or settings.ollama_model or "gemma2:9b"

    headers = {"Content-Type": "application/json"}
    if target_key and target_key.strip():
        headers["Authorization"] = f"Bearer {target_key.strip()}"

    api_url = f"{target_url.rstrip('/')}/api/generate"
    payload = {
        "model": model,
        "prompt": body.prompt,
        "stream": False,
    }

    log.info(f"🧪 Ollama test: POST {api_url} model={model} prompt={body.prompt[:60]}...")
    try:
        async with httpx.AsyncClient(verify=_outbound_tls_verify(), timeout=60.0) as client:
            res = await client.post(api_url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                return {
                    "success": True,
                    "model": model,
                    "response": data.get("response", ""),
                    "total_duration_ms": round(data.get("total_duration", 0) / 1_000_000, 1),
                    "eval_count": data.get("eval_count", 0),
                }
            else:
                log.error(f"Ollama test failed: {res.status_code} - {res.text[:300]}")
                return {
                    "success": False,
                    "model": model,
                    "error": f"HTTP {res.status_code}: {res.text[:300]}",
                }
    except Exception as e:
        log.error(f"Ollama test connection error: {e}")
        return {
            "success": False,
            "model": model,
            "error": f"Connessione fallita: {str(e)}",
        }


def _mask(value: str) -> str:
    return "••••" + value[-4:] if value and len(value) > 8 else ("••••" if value else "")


@router.get("/settings")
def get_app_settings(user: dict = Depends(require_admin)):
    info = get_llm_info()
    return {
        "provider": info["provider"],
        "model": info["model"],
        "llm_provider": settings.llm_provider,
        "openai_model": settings.openai_model,
        "openai_api_key": _mask(settings.openai_api_key),
        "google_model": settings.google_model,
        "google_api_key": _mask(settings.google_api_key),
        "groq_model": settings.groq_model,
        "groq_api_key": _mask(settings.groq_api_key),
        "openrouter_model": settings.openrouter_model,
        "openrouter_api_key": _mask(settings.openrouter_api_key),
        "ollama_mode": settings.ollama_mode,
        "ollama_model": settings.ollama_model,
        "ollama_base_url": settings.ollama_base_url,
        "ollama_api_key": _mask(settings.ollama_api_key),
        "use_ollama": settings.use_ollama,
        "llm_temperature": settings.llm_temperature,
        "llm_top_p": settings.llm_top_p,
        "llm_max_tokens": settings.llm_max_tokens,
        "llm_max_requests_per_minute": settings.llm_max_requests_per_minute,
        "user": user,
    }

@router.put("/settings")
def update_app_settings(body: SettingsUpdateSchema, user: dict = Depends(require_admin)):
    if body.llm_provider is not None:
        settings.llm_provider = body.llm_provider
        settings.use_ollama = (body.llm_provider == "ollama")

    if body.openai_model is not None:
        settings.openai_model = body.openai_model
    if body.openai_api_key is not None and not body.openai_api_key.startswith("••••"):
        settings.openai_api_key = body.openai_api_key
    if body.google_model is not None:
        settings.google_model = body.google_model
    if body.google_api_key is not None and not body.google_api_key.startswith("••••"):
        settings.google_api_key = body.google_api_key
    if body.groq_model is not None:
        settings.groq_model = body.groq_model
    if body.groq_api_key is not None and not body.groq_api_key.startswith("••••"):
        settings.groq_api_key = body.groq_api_key
    if body.openrouter_model is not None:
        settings.openrouter_model = body.openrouter_model
    if body.openrouter_api_key is not None and not body.openrouter_api_key.startswith("••••"):
        settings.openrouter_api_key = body.openrouter_api_key
    if body.ollama_mode is not None:
        settings.ollama_mode = body.ollama_mode
        if body.ollama_mode == "local" and not body.ollama_base_url:
            settings.ollama_base_url = "http://localhost:11434"
        elif body.ollama_mode == "remote" and not body.ollama_base_url:
            settings.ollama_base_url = "https://ollamaapi-u11fj34m2h9druz26hamz3xb.89.168.29.98.sslip.io"

    if body.ollama_model is not None:
        settings.ollama_model = body.ollama_model
    if body.ollama_base_url is not None:
        settings.ollama_base_url = body.ollama_base_url
    if body.ollama_api_key is not None and not body.ollama_api_key.startswith("••••"):
        settings.ollama_api_key = body.ollama_api_key
    if body.use_ollama is not None:
        settings.use_ollama = body.use_ollama
    if body.llm_temperature is not None:
        settings.llm_temperature = body.llm_temperature

    if body.llm_top_p is not None:
        settings.llm_top_p = body.llm_top_p
    if body.llm_max_tokens is not None:
        settings.llm_max_tokens = body.llm_max_tokens
    if body.llm_max_requests_per_minute is not None:
        settings.llm_max_requests_per_minute = body.llm_max_requests_per_minute

    # Persist updated settings directly to backend/.env
    try:
        env_path = Path(".env")
        env_content = f"""LLM_PROVIDER={settings.llm_provider}
USE_OLLAMA={'true' if settings.use_ollama else 'false'}
OLLAMA_MODE={settings.ollama_mode}
OLLAMA_BASE_URL={settings.ollama_base_url}
OLLAMA_API_KEY={settings.ollama_api_key}
OLLAMA_MODEL={settings.ollama_model}

OPENAI_API_KEY={settings.openai_api_key}
OPENAI_MODEL={settings.openai_model}

GROQ_API_KEY={settings.groq_api_key}
GROQ_MODEL={settings.groq_model}

OPENROUTER_API_KEY={settings.openrouter_api_key}
OPENROUTER_MODEL={settings.openrouter_model}

GOOGLE_API_KEY={settings.google_api_key}
GOOGLE_MODEL={settings.google_model}
"""
        env_path.write_text(env_content, encoding="utf-8")
    except Exception as err:
        log.warning(f"Could not persist settings to .env file: {err}")

    return get_app_settings(user)




# ==========================================
# Benchmark & Expert Evaluation Endpoints
# ==========================================

class BenchmarkRunRequest(BaseModel):
    scenario: str = "ecommerce"
    temperature: float = 0.1
    provider: str | None = None
    model: str | None = None

class UserVoteRequest(BaseModel):
    project_id: str | None = None
    benchmark_id: str | None = None
    schema_rating: int = Field(..., ge=1, le=5)
    data_rating: int = Field(..., ge=1, le=5)
    comment: str = ""

@router.get("/benchmark/scenarios", dependencies=[Depends(require_research)])
def list_benchmark_scenarios(user: dict = Depends(get_current_user)):
    return [
        {"key": k, "title": v["title"], "prompt": v["prompt"], "gold_tables": v["gold_tables"]}
        for k, v in BENCHMARK_SCENARIOS.items()
    ]

@router.post("/benchmark/run", dependencies=[Depends(require_research)])
async def run_benchmark(req: BenchmarkRunRequest, user: dict = Depends(get_current_user)):
    _consume_ai_now(user, "benchmark")
    res = await run_model_benchmark(
        scenario_key=req.scenario,
        temperature=req.temperature,
        model_name=req.model,
        provider=req.provider
    )
    if isinstance(res, dict) and "error" in res:
        raise HTTPException(status_code=500, detail=res["error"])
    return res


@router.get("/benchmark/results", dependencies=[Depends(require_research)])
def get_benchmark_results(user: dict = Depends(get_current_user)):
    engine = init_db()
    session = get_session(engine)
    results = session.query(BenchmarkResult).order_by(BenchmarkResult.created_at.desc()).limit(50).all()
    votes = session.query(UserVote).order_by(UserVote.created_at.desc()).limit(50).all()
    return {
        "results": [
            {
                "id": r.id,
                "scenario": r.scenario_name,
                "provider": r.provider,
                "model": r.model_name,
                "norm3_score": r.norm3_score,
                "relationship_f1": r.relationship_f1,
                "cell_precision": r.cell_precision,
                "latency_seconds": r.latency_seconds,
                "token_cost_estimate": r.token_cost_estimate,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results
        ],
        "votes": [
            {
                "id": v.id,
                "user_id": v.user_id if is_admin(user) else None,
                "schema_rating": v.schema_rating,
                "data_rating": v.data_rating,
                "comment": v.comment if is_admin(user) else None,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in votes
        ]
    }

@router.post("/surveys/vote", dependencies=[Depends(require_research)])
def submit_user_vote(req: UserVoteRequest, user: dict = Depends(get_current_user)):
    user_id = user.get("sub", "anonymous")
    vote = save_user_vote(
        user_id=user_id,
        schema_rating=req.schema_rating,
        data_rating=req.data_rating,
        comment=req.comment,
        project_id=req.project_id,
        benchmark_id=req.benchmark_id
    )
    return {"status": "saved", "vote_id": vote.id}


