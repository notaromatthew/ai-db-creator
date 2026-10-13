from fastapi import APIRouter, Depends
from app.utils.logger import log
from app.config import settings
from app.core.auth import get_current_user
from app.core.acl import ensure_user, resolve_role
from app.utils.exceptions import AppException
from datetime import datetime
import os
import json

router = APIRouter(prefix="/api")

_in_memory_store = {}

def _get_redis_client():
    try:
        import redis as redis_lib
        r = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        r.ping()
        return r
    except Exception:
        return None

def _redis_key(project_id: str) -> str:
    return f"progress:{project_id}"

def set_progress(project_id: str, status: str, progress: int, message: str = "", etc_seconds: float | None = None):
    data = {
        "status": status,
        "progress": progress,
        "message": message,
        "etc_seconds": etc_seconds,
        "updated_at": datetime.now().isoformat(),
    }
    r = _get_redis_client()
    if r:
        try:
            r.set(_redis_key(project_id), json.dumps(data), ex=3600)
            return
        except Exception:
            pass
    _in_memory_store[project_id] = data

def get_progress_state(project_id: str) -> dict:
    r = _get_redis_client()
    if r:
        try:
            data = r.get(_redis_key(project_id))
            if data:
                return json.loads(data)
        except Exception:
            pass
    return _in_memory_store.get(project_id, {"status": "idle", "progress": 0, "message": "", "etc_seconds": None})


def _progress_access(project_id: str, user: dict = Depends(get_current_user)):
    """Il progresso e' leggibile solo da chi ha accesso al progetto; 'benchmark' e' una chiave speciale dello studio."""
    if project_id == "benchmark":
        if not settings.research_mode:
            raise AppException(detail="Not found", status_code=404)
        return
    row = ensure_user(user)
    if resolve_role(project_id, row.id) is None:
        raise AppException(detail="Project not found", status_code=404)


@router.get("/progress/{project_id}", dependencies=[Depends(_progress_access)])
def get_progress(project_id: str):
    return get_progress_state(project_id)
