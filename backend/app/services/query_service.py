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



MAX_HISTORY = 50
_MAX_QUESTION = 2000
_MAX_SQL = 10000


def record_query(project_id: str, user_id: str | None, question: str | None, sql: str | None,
                 outcome: str, rows: int | None = None, source: str = "query") -> None:
    """Salva domanda, query ed esito. Un errore nel salvataggio non deve mai rompere la richiesta."""
    from app.models.database import QueryHistory
    session = get_session(init_db())
    try:
        session.add(QueryHistory(
            project_id=project_id, user_id=user_id,
            question=(question or None) and question[:_MAX_QUESTION],
            generated_sql=(sql or None) and sql[:_MAX_SQL],
            source=source, outcome="ok" if outcome == "ok" else "errore", rows=rows))
        session.commit()
    except Exception as exc:
        session.rollback()
        log.warning(f"Cronologia query non salvata ({type(exc).__name__})")
    finally:
        session.close()


def list_queries(project_id: str, limit: int = MAX_HISTORY) -> list[dict]:
    from app.models.database import QueryHistory
    session = get_session(init_db())
    try:
        rows = (session.query(QueryHistory).filter(QueryHistory.project_id == project_id)
                .order_by(QueryHistory.created_at.desc(), QueryHistory.id.desc())
                .limit(min(max(limit, 1), MAX_HISTORY)).all())
        return [{"id": r.id, "question": r.question, "sql": r.generated_sql, "source": r.source,
                 "outcome": r.outcome, "rows": r.rows, "user_id": r.user_id, "created_at": r.created_at}
                for r in rows]
    finally:
        session.close()
