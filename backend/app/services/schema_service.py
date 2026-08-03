from app.models.schema_models import NormalizedSchema, GenerateRequest
from app.core.llm import generate_schema
from app.core.parser import get_parser, ParsedDocument
from app.core.db_generator import create_database_from_schema
from app.utils.exceptions import AppException
from app.utils.logger import log
from app.models.database import Project, Document, get_session, init_db
from pathlib import Path
import json
import os
import shutil

APP_DB_PATH = "app.db"


class SchemaService:
    def __init__(self):
        self.engine = init_db()
    
    def create_project(self, name: str, prompt: str = "") -> Project:
        session = get_session(self.engine)
        project = Project(name=name, prompt=prompt)
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
    
    def list_projects(self) -> list:
        session = get_session(self.engine)
        projects = session.query(Project).all()
        session.close()
        return projects
    
    async def generate_from_prompt(self, project_id: str, request: GenerateRequest) -> NormalizedSchema:
        project = self.get_project(project_id)
        project.prompt = request.prompt
        
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
        
        schema = await generate_schema(request.prompt, doc_context)
        
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
        session.commit()
        session.close()
        
        return schema
    
    def update_schema(self, project_id: str, schema: NormalizedSchema) -> NormalizedSchema:
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
