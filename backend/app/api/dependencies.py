from fastapi import Depends, HTTPException, Request, status

from app.core.auth import get_current_user
from app.models.database import Project, get_session, init_db


def endpoint_capability(path: str, method: str) -> str:
    """Explicit experiment policy; unknown mutations are denied by default."""
    if path.rstrip("/").endswith("/experiments/compare") and method == "POST":
        return "ai_generate"
    suffix = path.split("/projects/", 1)[-1].split("/", 1)[1] if "/projects/" in path and "/" in path.split("/projects/", 1)[-1] else ""
    rules = {
        "chat": "chat", "chat-accept": "chat", "import-sql": "import_sql",
        "generate": "ai_generate", "generate-async": "ai_generate", "populate": "populate",
        "populate-async": "populate", "schema": "edit", "execute-query": "query",
        "query": "query", "documents": "document", "interactions": "rq4_event",
        "export-interactions": "export", "export-full": "export", "export-sql": "export",
        "backup": "export", "restore": "edit",
        "data": "edit", "export-async": "export",
    }
    action = suffix.split("/", 1)[0]
    if not action and method == "DELETE":
        return "project_delete"
    if method == "GET" and action in {"", "schema", "documents", "interactions", "data"}:
        return "project_view"
    if action in rules:
        return rules[action]
    return "deny_mutation" if method in {"POST", "PUT", "PATCH", "DELETE"} else "project_view"


def authenticated_user_id(user: dict) -> str:
    user_id = user.get("sub") if isinstance(user, dict) else None
    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identità utente non valida",
        )
    return user_id


def require_owned_project(project_id: str, user: dict) -> Project:
    user_id = authenticated_user_id(user)
    session = get_session(init_db())
    try:
        project = session.query(Project).filter(
            Project.id == project_id,
            Project.user_id == user_id,
        ).first()
    finally:
        session.close()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def get_owned_project(
    project_id: str,
    request: Request,
    user: dict = Depends(get_current_user),
) -> Project:
    project = require_owned_project(project_id, user)
    from app.config import settings
    if settings.experiment_mode:
        capability = endpoint_capability(request.url.path, request.method)
        from app.services.experiment_service import experiment_service
        try:
            experiment_service.require(authenticated_user_id(user), project_id, capability)
        except TimeoutError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
    return project
