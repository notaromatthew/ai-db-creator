"""Persistent, concurrency-safe lifecycle for the three-arm experiment."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.utils.research import atomic_write_json, new_run_id, sanitize_metadata, stable_hash

CONDITIONS = ("manual", "ai_only", "ai_interface")
_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[str, threading.RLock] = {}
CAPABILITIES = {
    "manual": {"project_view", "project_delete", "document", "import_sql", "edit", "query", "survey", "rq4_event", "export"},
    "ai_only": {"project_view", "project_delete", "document", "ai_generate", "populate", "survey", "rq4_event", "export"},
    "ai_interface": {"project_view", "project_delete", "document", "import_sql", "ai_generate", "populate", "chat", "edit", "query", "survey", "rq4_event", "export"},
}


class ExperimentService:
    def __init__(self, path: str | Path = "projects/experiment_sessions.json", clock=None, id_factory=None, project_eraser=None):
        self.path = Path(path)
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.id_factory = id_factory or new_run_id
        self.project_eraser = project_eraser
        resolved = str(self.path.resolve())
        with _LOCKS_GUARD:
            self._lock = _PATH_LOCKS.setdefault(resolved, threading.RLock())

    @contextmanager
    def _locked(self):
        """Serialize read-modify-write assignments across threads and worker processes."""
        with self._lock:
            lock_path = self.path.with_suffix(self.path.suffix + ".lock")
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            handle = open(lock_path, "a+b")
            try:
                if os.name == "nt":
                    import msvcrt
                    handle.seek(0)
                    if handle.read(1) == b"":
                        handle.seek(0)
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

    def _load(self) -> dict:
        if not self.path.exists():
            return {"sessions": {}, "subjects": {}}
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {"sessions": {}, "subjects": {}}
        except (OSError, json.JSONDecodeError):
            return {"sessions": {}, "subjects": {}}

    @staticmethod
    def _subject_key(subject: str) -> str:
        secret = os.getenv("EXPERIMENT_PSEUDONYM_SECRET", "development-only-change-me")
        return hmac.new(secret.encode(), subject.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    def _condition(subject_key: str, protocol_version: str) -> str:
        seed = os.getenv("EXPERIMENT_ASSIGNMENT_SEED", "draft-seed")
        digest = hmac.new(seed.encode(), f"{protocol_version}:{subject_key}".encode(), hashlib.sha256).digest()
        return CONDITIONS[int.from_bytes(digest[:8], "big") % len(CONDITIONS)]

    def start(self, subject: str, project_id: str, protocol_version: str,
              duration_minutes: int = 45) -> dict:
        key = self._subject_key(subject)
        with self._locked():
            data = self._load()
            existing_id = data["subjects"].get(key)
            if existing_id:
                return self._public(self._refresh(data, data["sessions"][existing_id]))
            now = self.clock()
            session_id = self.id_factory()
            condition = self._condition(key, protocol_version)
            session = {
                "session_id": session_id, "participant_id": "p-" + key[:16],
                "subject_key": key, "project_id": project_id, "condition": condition,
                "protocol_version": protocol_version, "protocol_hash": stable_hash(protocol_version),
                "status": "active", "started_at": now.isoformat(),
                "deadline_at": (now + timedelta(minutes=duration_minutes)).isoformat(),
                "completed_at": None, "withdrawn_at": None,
                "assignment_method": "deterministic_hmac_allocation",
                "capabilities": sorted(CAPABILITIES[condition]),
            }
            data["sessions"][session_id] = session
            data["subjects"][key] = session_id
            atomic_write_json(self.path, sanitize_metadata(data))
            return self._public(session)

    def _refresh(self, data: dict, session: dict) -> dict:
        if session["status"] == "active" and self.clock() >= datetime.fromisoformat(session["deadline_at"]):
            session["status"] = "timed_out"
            session["completed_at"] = self.clock().isoformat()
            atomic_write_json(self.path, sanitize_metadata(data))
        return session.copy()

    def for_subject(self, subject: str) -> dict | None:
        key = self._subject_key(subject)
        with self._locked():
            data = self._load()
            session_id = data.get("subjects", {}).get(key)
            return self._public(self._refresh(data, data["sessions"][session_id])) if session_id else None

    def transition(self, subject: str, target: str) -> dict:
        if target not in {"completed", "withdrawn"}:
            raise ValueError("invalid transition")
        key = self._subject_key(subject)
        with self._locked():
            data = self._load()
            session_id = data.get("subjects", {}).get(key)
            if not session_id:
                raise KeyError("session not found")
            session = self._refresh(data, data["sessions"][session_id])
            if session["status"] != "active":
                return session
            timestamp = self.clock().isoformat()
            session["status"] = target
            session["completed_at" if target == "completed" else "withdrawn_at"] = timestamp
            data["sessions"][session_id] = session
            atomic_write_json(self.path, sanitize_metadata(data))
            if target == "withdrawn":
                artifact_dir = self.path.parent / "experiment_artifacts" / session_id
                if artifact_dir.exists():
                    for path in sorted(artifact_dir.rglob("*"), reverse=True):
                        if path.is_file():
                            path.unlink()
                        elif path.is_dir():
                            path.rmdir()
                    artifact_dir.rmdir()
                from app.services.interaction_logger import interaction_logger
                from app.services.schema_service import SchemaService
                interaction_logger.erase_project(session["project_id"])
                survey_root = self.path.parent / "surveys"
                if survey_root.exists():
                    for survey_path in survey_root.glob("*.json"):
                        try:
                            if json.loads(survey_path.read_text(encoding="utf-8")).get("project_id") == session["project_id"]:
                                survey_path.unlink()
                        except (OSError, json.JSONDecodeError):
                            continue
                (self.project_eraser or SchemaService().delete_project)(session["project_id"])
                tombstone = {"session_id": session_id, "status": "withdrawn", "withdrawn_at": timestamp,
                             "protocol_hash": session["protocol_hash"]}
                data["sessions"][session_id] = tombstone
                data["subjects"].pop(key, None)
                atomic_write_json(self.path, sanitize_metadata(data))
                return tombstone
            return self._public(session)

    def require(self, subject: str, project_id: str, capability: str) -> dict:
        session = self.for_subject(subject)
        if not session or session["project_id"] != project_id:
            raise PermissionError("active experiment session not found for project")
        if session["status"] != "active":
            raise TimeoutError(f"experiment session is {session['status']}")
        if capability not in session["capabilities"]:
            raise PermissionError(f"capability {capability} disabled for condition")
        return session

    @staticmethod
    def _public(session: dict) -> dict:
        return {key: value for key, value in session.items() if key != "subject_key"}


experiment_service = ExperimentService()
