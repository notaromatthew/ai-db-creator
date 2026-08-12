from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from app.utils.logger import log
from app.utils.research import new_run_id, sanitize_metadata
import json
import os
import threading
import hashlib


class InteractionLogger:
    """Atomic, project-isolated persistence for research events."""

    def __init__(self, persist_path: str = "projects/interactions_store.json"):
        self.persist_path = Path(persist_path)
        self._thread_lock = threading.RLock()
        self.events = self._load_events()

    def _load_events(self) -> list:
        if self.persist_path.exists():
            try:
                with open(self.persist_path, encoding="utf-8") as source:
                    value = json.load(source)
                    if not isinstance(value, list):
                        return []
                    for index, event in enumerate(value):
                        if isinstance(event, dict) and not event.get("run_id"):
                            canonical = json.dumps(event, sort_keys=True, ensure_ascii=False, default=str)
                            event["run_id"] = "legacy-" + hashlib.sha256(f"{index}:{canonical}".encode("utf-8")).hexdigest()[:24]
                    return value
            except (json.JSONDecodeError, OSError):
                return []
        return []

    @contextmanager
    def _locked(self):
        with self._thread_lock:
            lock_path = self.persist_path.with_suffix(self.persist_path.suffix + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(lock_path, "a+b")
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    if handle.tell() == 0:
                        handle.write(b"0")
                        handle.flush()
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
                yield
            finally:
                if os.name == "nt":
                    handle.seek(0)
                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                handle.close()

    @staticmethod
    def _atomic_write(path: Path, events: list):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
        with open(temp_path, "w", encoding="utf-8") as target:
            json.dump(events, target, indent=2, ensure_ascii=False)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temp_path, path)

    def log_event(self, event_type: str, project_id: str, data: dict, run_id: str | None = None):
        event = {
            "run_id": run_id or new_run_id(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event_type": event_type,
            "project_id": project_id,
            "data": sanitize_metadata(data),
        }
        with self._locked():
            persisted = self._load_events()
            merged = {item.get("run_id"): item for item in persisted if item.get("run_id")}
            merged[event["run_id"]] = event
            self.events = list(merged.values())
            self._atomic_write(self.persist_path, self.events)
        log.info(f"Interaction: {event_type} on project {project_id}")
        return event

    def get_events(self, project_id: str | None = None):
        with self._locked():
            self.events = self._load_events()
            events = list(self.events)
        return [event for event in events if event.get("project_id") == project_id] if project_id else events

    def save_events(self, filepath: str, project_id: str | None = None):
        events = self.get_events(project_id)
        self._atomic_write(Path(filepath), events)
        log.info(f"Saved {len(events)} interaction events to {filepath}")
        return len(events)

    def erase_project(self, project_id: str) -> int:
        with self._locked():
            persisted = self._load_events()
            retained = [event for event in persisted if event.get("project_id") != project_id]
            removed = len(persisted) - len(retained)
            self.events = retained
            self._atomic_write(self.persist_path, retained)
        return removed

    def log_rq4_event(self, project_id: str, data: dict):
        with self._locked():
            persisted = self._load_events()
            rq4 = [event for event in persisted if event.get("project_id") == project_id and event.get("event_type") == "rq4_event"]
            duplicate = next((event for event in rq4 if event.get("data", {}).get("event_id") == data["event_id"]), None)
            if duplicate:
                return duplicate, True
            session_id = data.get("session_id")
            sequences = [event.get("data", {}).get("sequence_no", 0) for event in rq4 if event.get("data", {}).get("session_id") == session_id]
            if data["sequence_no"] != (max(sequences, default=0) + 1):
                raise ValueError("RQ4 sequence out of order")
            event = {"run_id": new_run_id(), "timestamp": datetime.now(timezone.utc).isoformat(),
                     "event_type": "rq4_event", "project_id": project_id, "data": sanitize_metadata(data)}
            persisted.append(event); self.events = persisted; self._atomic_write(self.persist_path, persisted)
            return event, False


interaction_logger = InteractionLogger()
