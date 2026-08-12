import json
import os
import time


TASK_REGISTRY_TTL_SECONDS = int(os.getenv("TASK_REGISTRY_TTL_SECONDS", "3600"))
_in_memory_registry: dict[str, tuple[float, dict]] = {}


def _get_redis_client():
    try:
        import redis as redis_lib

        client = redis_lib.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"))
        client.ping()
        return client
    except Exception:
        return None


def _registry_key(task_id: str) -> str:
    return f"task-owner:{task_id}"


def register_task(
    task_id: str,
    user_id: str,
    project_id: str,
    ttl_seconds: int = TASK_REGISTRY_TTL_SECONDS,
) -> None:
    payload = {"user_id": user_id, "project_id": project_id}
    client = _get_redis_client()
    if client:
        try:
            client.set(_registry_key(task_id), json.dumps(payload), ex=ttl_seconds)
            return
        except Exception:
            pass
    _in_memory_registry[task_id] = (time.time() + ttl_seconds, payload)


def get_task_registration(task_id: str) -> dict | None:
    client = _get_redis_client()
    if client:
        try:
            raw = client.get(_registry_key(task_id))
            if raw:
                return json.loads(raw)
        except Exception:
            pass
    entry = _in_memory_registry.get(task_id)
    if not entry:
        return None
    expires_at, payload = entry
    if expires_at <= time.time():
        _in_memory_registry.pop(task_id, None)
        return None
    return payload.copy()
