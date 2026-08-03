from app.models.schema_models import QueryResponse
from app.utils.exceptions import AppException
from app.core.llm import generate_query
from app.utils.logger import log
from app.models.database import Project, get_session, init_db

class QueryService:
    def __init__(self):
        self.engine = init_db()

    async def generate(self, project_id: str, prompt: str, dialect: str = "sqlite") -> QueryResponse:
        session = get_session(self.engine)
        project = session.query(Project).filter(Project.id == project_id).first()
        session.close()
        if not project:
            raise AppException(detail="Project not found", status_code=404)
        schema_str = ""
        if project.schema_json:
            import json
            schema_str = json.dumps(project.schema_json, indent=2)
        return await generate_query(prompt, schema_str, dialect)

