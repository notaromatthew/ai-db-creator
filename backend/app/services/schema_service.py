from app.models.schema_models import NormalizedSchema, GenerateRequest
from app.core.llm import generate_schema
from app.core.parser import get_parser, ParsedDocument
from app.core.db_generator import create_database_from_schema
from app.utils.exceptions import AppException
from app.utils.logger import log
from app.models.database import Project, ProjectMember, Document, User, SchemaVersion, SCHEMA_ORIGINS, get_session, init_db
from pathlib import Path
from contextvars import ContextVar
import json
import os
import shutil

APP_DB_PATH = "app.db"

# Tipi ammessi nello schema (gli stessi che il generatore del database sa mappare).
ALLOWED_TYPES = frozenset({
    "integer", "int", "text", "varchar", "string", "real", "float", "double",
    "boolean", "bool", "date", "datetime", "timestamp",
})
MAX_REPAIR_ATTEMPTS = 2

# Testo aggiunto alla richiesta quando lo schema generato non supera la validazione.
SCHEMA_REPAIR_PROMPT = (
    "The schema you produced earlier is invalid. Fix every listed error and keep everything else unchanged. "
    "Table names must be unique, every table needs a primary key, foreign keys must point to existing "
    "tables and columns, and data types must be one of: INTEGER, TEXT, REAL, DATE, BOOLEAN, VARCHAR(n), DATETIME."
)

# Esito dell'ultima generazione nel contesto corrente: {"attempts": int, "log": [...], "remaining_errors": [...]}.
_last_repair: ContextVar = ContextVar("schema_last_repair", default=None)


def get_last_repair() -> dict:
    """Tentativi di riparazione dell'ultima generazione fatta nel contesto corrente."""
    return _last_repair.get() or {"attempts": 0, "log": [], "remaining_errors": []}


def validate_schema(schema: NormalizedSchema) -> list[str]:
    """Controlli strutturali sullo schema: nomi unici, chiavi primarie, chiavi esterne coerenti, tipi ammessi."""
    errors: list[str] = []
    if not schema.tables:
        return ["Lo schema non contiene tabelle."]
    seen_tables: dict[str, object] = {}
    for table in schema.tables:
        key = table.name.strip().lower()
        if key in seen_tables:
            errors.append(f"Nome di tabella duplicato: {table.name}.")
        seen_tables[key] = table
    columns_by_table = {}
    for table in schema.tables:
        names = [c.name.strip().lower() for c in table.columns]
        columns_by_table[table.name.strip().lower()] = set(names)
        for name in sorted({n for n in names if names.count(n) > 1}):
            errors.append(f"Colonna duplicata nella tabella {table.name}: {name}.")
        if not table.columns:
            errors.append(f"La tabella {table.name} non ha colonne.")
        elif not any(c.is_primary_key for c in table.columns):
            errors.append(f"La tabella {table.name} non ha una chiave primaria.")
        for col in table.columns:
            base = col.data_type.lower().split("(")[0].strip()
            if base not in ALLOWED_TYPES:
                errors.append(f"Tipo non ammesso in {table.name}.{col.name}: {col.data_type}.")
            if col.is_foreign_key:
                ref_table = (col.foreign_key_table or "").strip().lower()
                ref_col = (col.foreign_key_column or "").strip().lower()
                if not ref_table or not ref_col:
                    errors.append(f"La chiave esterna {table.name}.{col.name} non indica tabella e colonna di destinazione.")
    for table in schema.tables:
        for col in table.columns:
            if not col.is_foreign_key or not col.foreign_key_table or not col.foreign_key_column:
                continue
            ref_table = col.foreign_key_table.strip().lower()
            if ref_table not in columns_by_table:
                errors.append(f"La chiave esterna {table.name}.{col.name} punta a una tabella inesistente: {col.foreign_key_table}.")
            elif col.foreign_key_column.strip().lower() not in columns_by_table[ref_table]:
                errors.append(f"La chiave esterna {table.name}.{col.name} punta a una colonna inesistente: "
                              f"{col.foreign_key_table}.{col.foreign_key_column}.")
    for rel in schema.relationships:
        for t_name, c_name in ((rel.from_table, rel.from_column), (rel.to_table, rel.to_column)):
            cols = columns_by_table.get(t_name.strip().lower())
            if cols is None:
                errors.append(f"La relazione cita una tabella inesistente: {t_name}.")
            elif c_name.strip().lower() not in cols:
                errors.append(f"La relazione cita una colonna inesistente: {t_name}.{c_name}.")
    return errors


def _repair_request(prompt: str, schema: NormalizedSchema, errors: list[str]) -> str:
    listed = "\n".join(f"- {e}" for e in errors[:20])
    return (f"{prompt}\n\n{SCHEMA_REPAIR_PROMPT}\nErrors found:\n{listed}\n"
            f"Previous schema:\n{schema.model_dump_json()}")


async def generate_schema_with_repair(prompt: str, document_context: str = "",
                                      temperature: float | None = None) -> tuple[NormalizedSchema, dict]:
    """Genera lo schema, lo valida e, se serve, lo fa correggere al modello (al massimo 2 tentativi).

    Non fallisce mai per colpa della validazione: se gli errori restano, lo schema migliore viene restituito
    e gli errori rimasti finiscono nel resoconto.
    """
    schema = await generate_schema(prompt, document_context, temperature=temperature)
    errors = validate_schema(schema)
    log_entries: list[dict] = []
    attempts = 0
    while errors and attempts < MAX_REPAIR_ATTEMPTS:
        attempts += 1
        entry = {"attempt": attempts, "errors_before": len(errors), "errors": errors[:10]}
        try:
            candidate = await generate_schema(_repair_request(prompt, schema, errors), document_context,
                                              temperature=temperature)
        except Exception as exc:
            entry.update({"outcome": "failed", "error_type": type(exc).__name__})
            log_entries.append(entry)
            break
        new_errors = validate_schema(candidate)
        entry.update({"outcome": "repaired" if not new_errors else "still_invalid", "errors_after": len(new_errors)})
        log_entries.append(entry)
        if len(new_errors) <= len(errors):
            schema, errors = candidate, new_errors
    return schema, {"attempts": attempts, "log": log_entries, "remaining_errors": errors[:10]}


class SchemaService:
    def __init__(self):
        self.engine = init_db()
    
    def create_project(self, name: str, prompt: str = "", owner_id: str | None = None) -> Project:
        session = get_session(self.engine)
        project = Project(name=name, prompt=prompt, owner_id=owner_id)
        session.add(project)
        session.commit()
        project_id = project.id
        session.close()
        return self.get_project(project_id)
    
    def get_project(self, project_id: str) -> Project:
        session = get_session(self.engine)
        project = session.query(Project).filter(Project.id == project_id).first()
        session.close()
        if not project:
            raise AppException(detail="Project not found", status_code=404)
        return project
    
    def list_projects(self, user_id: str | None = None) -> list:
        session = get_session(self.engine)
        from sqlalchemy import or_
        query = session.query(Project)
        if user_id:
            shared = session.query(ProjectMember.project_id).filter(ProjectMember.user_id == user_id)
            query = query.filter(or_(Project.owner_id == user_id, Project.id.in_(shared)))
        projects = query.all()
        session.close()
        return projects

    def list_project_summaries(self, user_id: str) -> list[dict]:
        """Progetti accessibili con i campi utili alla dashboard: ruolo, proprietario, passo e stato."""
        import sqlite3
        from sqlalchemy import func
        projects = self.list_projects(user_id=user_id)
        session = get_session(self.engine)
        try:
            ids = [p.id for p in projects]
            roles = dict(session.query(ProjectMember.project_id, ProjectMember.role)
                         .filter(ProjectMember.user_id == user_id).all())
            docs = dict(session.query(Document.project_id, func.count(Document.id))
                        .filter(Document.project_id.in_(ids)).group_by(Document.project_id).all()) if ids else {}
            owners = {u.id: (u.display_name or u.email) for u in
                      session.query(User).filter(User.id.in_({p.owner_id for p in projects})).all()} if projects else {}
        finally:
            session.close()
        out = []
        for p in projects:
            tables = [t.get("name") for t in ((p.schema_json or {}).get("tables") or []) if isinstance(t, dict)]
            has_data = False
            if tables and p.db_path and os.path.exists(p.db_path):
                try:
                    con = sqlite3.connect(f"file:{p.db_path}?mode=ro", uri=True)
                    try:
                        for name in tables:
                            safe = str(name).replace('"', '""')
                            if con.execute(f'SELECT 1 FROM "{safe}" LIMIT 1').fetchone():
                                has_data = True
                                break
                    finally:
                        con.close()
                except sqlite3.Error:
                    has_data = False
            step, status = (3, "data_ready") if has_data else (2, "schema_review") if tables else (1, "not_started")
            row = {c.name: getattr(p, c.name) for c in p.__table__.columns}
            row.update({
                "my_role": "owner" if p.owner_id == user_id else roles.get(p.id, "viewer"),
                "owner_name": owners.get(p.owner_id),
                "step": step, "status": status, "table_count": len(tables),
                "document_count": docs.get(p.id, 0),
            })
            out.append(row)
        return out

    async def generate_schema_only(self, project_id: str, request: GenerateRequest,
                                   temperature: float | None = None) -> NormalizedSchema:
        """Chiama il modello (con validazione e riparazione) senza toccare il progetto."""
        _last_repair.set(None)
        self.get_project(project_id)
        doc_context = ""
        if request.document_ids:
            parts = []
            session = get_session(self.engine)
            for doc_id in request.document_ids:
                doc = session.query(Document).filter(Document.id == doc_id, Document.project_id == project_id).first()
                if not doc:
                    session.close()
                    raise AppException(detail="Document not found", status_code=404)
                if doc and doc.content_summary:
                    parts.append(f"--- {doc.filename} ---\n{doc.content_summary}")
            session.close()
            doc_context = "\n\n".join(parts)

        schema, repair = await generate_schema_with_repair(request.prompt, doc_context, temperature=temperature)
        _last_repair.set(repair)
        return schema

    def apply_generated_schema(self, project_id: str, schema: NormalizedSchema, prompt: str | None = None,
                               author: str | None = None) -> NormalizedSchema:
        """Crea il database dallo schema, lo salva nel progetto e ne registra la versione (origine: generazione)."""
        project = self.get_project(project_id)
        project_dir = Path(project.db_path or "").parent if project.db_path else None
        if not project_dir:
            project_dir = Path("projects") / project_id
            project_dir.mkdir(parents=True, exist_ok=True)

        db_path = str(project_dir / "database.sqlite")
        create_database_from_schema(schema, db_path)

        session = get_session(self.engine)
        project = session.query(Project).filter(Project.id == project_id).first()
        project.schema_json = json.loads(schema.model_dump_json())
        project.db_path = db_path
        if prompt is not None:
            project.prompt = prompt
        session.commit()
        session.close()
        self.record_version(project_id, schema, author, "generazione")
        return schema

    async def generate_from_prompt(self, project_id: str, request: GenerateRequest,
                                   temperature: float | None = None, author: str | None = None) -> NormalizedSchema:
        schema = await self.generate_schema_only(project_id, request, temperature=temperature)
        return self.apply_generated_schema(project_id, schema, prompt=request.prompt, author=author)

    # --- versioni dello schema -------------------------------------------------

    def record_version(self, project_id: str, schema: NormalizedSchema, author: str | None, origin: str) -> int:
        """Salva una nuova versione se lo schema e' cambiato; restituisce il numero di versione corrente."""
        from sqlalchemy.exc import IntegrityError
        if origin not in SCHEMA_ORIGINS:
            raise ValueError(f"Origine non valida: {origin}")
        data = json.loads(schema.model_dump_json())
        for _ in range(3):
            session = get_session(self.engine)
            try:
                last = (session.query(SchemaVersion).filter(SchemaVersion.project_id == project_id)
                        .order_by(SchemaVersion.version.desc()).first())
                if last is not None and last.schema_json == data:
                    number = last.version
                else:
                    number = (last.version if last else 0) + 1
                    session.add(SchemaVersion(project_id=project_id, version=number, schema_json=data,
                                              author=author or "sistema", origin=origin))
                session.query(Project).filter(Project.id == project_id).update({"schema_version": number})
                session.commit()
                return number
            except IntegrityError:
                session.rollback()
            finally:
                session.close()
        raise AppException(detail="Impossibile salvare la versione dello schema. Riprova.", status_code=409)

    def list_versions(self, project_id: str) -> list[dict]:
        session = get_session(self.engine)
        try:
            rows = (session.query(SchemaVersion).filter(SchemaVersion.project_id == project_id)
                    .order_by(SchemaVersion.version.desc()).all())
            return [{"version": r.version, "author": r.author, "origin": r.origin, "created_at": r.created_at,
                     "table_count": len((r.schema_json or {}).get("tables") or [])} for r in rows]
        finally:
            session.close()

    def get_version(self, project_id: str, number: int) -> dict:
        session = get_session(self.engine)
        try:
            row = session.query(SchemaVersion).filter(
                SchemaVersion.project_id == project_id, SchemaVersion.version == number).first()
            if row is None:
                raise AppException(detail="Versione non trovata", status_code=404)
            return {"version": row.version, "author": row.author, "origin": row.origin,
                    "created_at": row.created_at, "schema": row.schema_json}
        finally:
            session.close()

    def update_schema(self, project_id: str, schema: NormalizedSchema, author: str | None = None,
                      origin: str = "manuale") -> NormalizedSchema:
        from app.core.db_generator import migrate_database
        project = self.get_project(project_id)
        db_path = project.db_path

        if db_path and os.path.exists(db_path):
            old_schema = self.get_schema(project_id)
            if old_schema:
                migrate_database(old_schema, schema, db_path)
            else:
                from app.core.db_generator import create_database_from_schema
                create_database_from_schema(schema, db_path)
        else:
            if not db_path:
                project_dir = Path("projects") / project_id
                project_dir.mkdir(parents=True, exist_ok=True)
                db_path = str(project_dir / "database.sqlite")
            from app.core.db_generator import create_database_from_schema
            create_database_from_schema(schema, db_path)
        
        session = get_session(self.engine)
        project = session.query(Project).filter(Project.id == project_id).first()
        project.schema_json = json.loads(schema.model_dump_json())
        project.db_path = db_path
        session.commit()
        session.close()
        self.record_version(project_id, schema, author, origin)

        return schema
    
    def delete_project(self, project_id: str):
        project = self.get_project(project_id)
        project_root = (Path("projects") / project_id).resolve()
        upload_root = (Path("uploads") / project_id).resolve()
        allowed_project_parent = Path("projects").resolve()
        allowed_upload_parent = Path("uploads").resolve()
        session = get_session(self.engine)
        session.delete(project)
        session.commit()
        session.close()
        for target, parent in ((project_root, allowed_project_parent), (upload_root, allowed_upload_parent)):
            if target.parent == parent and target.exists():
                shutil.rmtree(target)
        return {"deleted": project_id}

    def get_schema(self, project_id: str) -> NormalizedSchema | None:
        project = self.get_project(project_id)
        if project.schema_json:
            return NormalizedSchema(**project.schema_json)
        return None
