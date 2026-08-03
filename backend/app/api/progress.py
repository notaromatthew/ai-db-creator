from fastapi import APIRouter
from app.utils.logger import log
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

def set_progress(project_id: str, status: str, progress: int, message: str = ""):
    data = {
        "status": status,
        "progress": progress,
        "message": message,
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
    return _in_memory_store.get(project_id, {"status": "idle", "progress": 0, "message": ""})

@router.get("/progress/{project_id}")
def get_progress(project_id: str):
    return get_progress_state(project_id)

@router.post("/progress/{project_id}")
def update_progress(project_id: str, status: str, progress: int, message: str = ""):
    set_progress(project_id, status, progress, message)
    log.info(f"Progress {project_id}: {status} ({progress}%) - {message}")
    return {"status": "updated"}
