"""Small, dependency-free helpers for reproducible research events."""
from __future__ import annotations

import hashlib
import json
import re
import uuid
import os
import functools
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SECRET_KEYS = re.compile(r"(api[_-]?key|authorization|token|password|secret)", re.IGNORECASE)
_SECRET_VALUE = re.compile(
    r"(?i)(bearer\s+)[^\s,;]+|((?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+"
)


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str | None:
    try:
        digest = hashlib.sha256()
        with open(path, "rb") as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def stable_hash(value: Any) -> str:
    return sha256_text(json.dumps(value, sort_keys=True, ensure_ascii=False, default=str))


def sanitize_metadata(value: Any) -> Any:
    """Remove secret-like fields recursively before persisting research metadata."""
    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _SECRET_KEYS.search(str(key)) else sanitize_metadata(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [sanitize_metadata(item) for item in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub(lambda match: f"{match.group(1) or match.group(2)}[REDACTED]", value)
    return value


def new_run_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def run_manifest(started_at: datetime, template_version: str, context: Any = None, input_hashes: dict | None = None) -> dict:
    return {
        "started_at": started_at.astimezone(timezone.utc).isoformat(),
        "ended_at": utc_now().isoformat(),
        "prompt_template_version": template_version,
        "app_version": "1.0.0",
        "software_revision": os.getenv("SOFTWARE_REVISION", "unknown"),
        "condition": getattr(context, "condition", None),
        "session_id": getattr(context, "session_id", None),
        "participant_id": getattr(context, "participant_id", None),
        "input_hashes": input_hashes or {},
    }


def atomic_write_json(path: str | Path, value: Any) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    with open(temporary, "w", encoding="utf-8") as output:
        json.dump(value, output, indent=2, ensure_ascii=False)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, target)


def record_run(logger, project_id: str, event_type: str, run_id: str, data: dict) -> dict:
    """Single persistence path shared by HTTP and worker runs."""
    result = data.get("result") if isinstance(data.get("result"), dict) else {}
    inserted = sum(item.get("inserted", 0) for item in result.values() if isinstance(item, dict))
    skipped = sum(item.get("skipped", 0) for item in result.values() if isinstance(item, dict))
    failed = sum(item.get("failed", 0) for item in result.values() if isinstance(item, dict))
    warnings = sanitize_metadata(data.get("warnings", []))
    for item in result.values():
        if isinstance(item, dict) and isinstance(item.get("warnings"), list):
            warnings = [*warnings, *sanitize_metadata(item["warnings"])]
    if failed:
        warnings = [*warnings, {"category": "row_failures", "count": failed}]
    if skipped:
        warnings = [*warnings, {"category": "rows_skipped", "count": skipped}]
    data["warnings"] = warnings
    manifest = data.setdefault("run_manifest", {})
    manifest.update({"inserted_count": inserted, "skipped_count": skipped, "failed_count": failed,
                     "warnings": warnings, "status": data.get("status", "success")})
    manifest["output_schema_hash"] = data.get("schema_final_hash")
    manifest["extraction_paths"] = sorted({
        item.get("provenance", {}).get("method") for item in result.values()
        if isinstance(item, dict) and isinstance(item.get("provenance"), dict)
        and item["provenance"].get("method")
    })
    relative = Path("runs") / f"{run_id}.json"
    atomic_write_json(Path("projects") / project_id / relative, {
        "run_id": run_id, "event_type": event_type, "project_id": project_id, **sanitize_metadata(data)
    })
    global_data = {key: sanitize_metadata(value) for key, value in data.items()
                   if key not in {"schema_initial", "schema_final", "result"}}
    global_data.update({"inserted_count": inserted, "skipped_count": skipped, "failed_count": failed,
                        "run_artifact": str(relative).replace("\\", "/")})
    return logger.log_event(event_type, project_id, global_data, run_id=run_id)


def tracked_worker_run(event_type: str, template_version: str):
    """Record worker success/failure through the same artifact utility as HTTP runs."""
    def decorate(function):
        @functools.wraps(function)
        def wrapped(task_self, project_id, *args, **kwargs):
            from app.services.interaction_logger import interaction_logger
            started = utc_now()
            run_id = new_run_id()
            supplied_context = kwargs.get("run_context")
            if supplied_context is None and args and isinstance(args[-1], dict):
                supplied_context = args[-1]
            supplied_context = sanitize_metadata(supplied_context or {})
            allowed_context = {key: supplied_context.get(key) for key in (
                "condition", "session_id", "participant_id", "prompt_hash", "document_hashes",
                "schema_input_hash", "population_input_hash", "provider", "model", "parameters"
            ) if supplied_context.get(key) is not None}
            try:
                from app.core.llm import get_llm_run_metadata
                if event_type.startswith("schema_") and args and isinstance(args[0], str):
                    allowed_context = {**get_llm_run_metadata(0.1, args[0], allowed_context.get("document_hashes", [])), **allowed_context}
                elif event_type.startswith("population") and len(args) > 1 and isinstance(args[1], dict):
                    allowed_context = {**get_llm_run_metadata(
                        0.0, json.dumps(args[1], sort_keys=True), allowed_context.get("document_hashes", []),
                        input_label="population_input"
                    ), "schema_input_hash": stable_hash(args[1]), **allowed_context}
            except Exception:
                pass
            try:
                output = function(task_self, project_id, *args, **kwargs)
                result_tables = output.get("results", {}) if isinstance(output, dict) else {}
                snapshot = output.pop("_schema_snapshot", None) if isinstance(output, dict) else None
                runtime_metadata = output.pop("_run_metadata", {}) if isinstance(output, dict) else {}
                schema_hash = stable_hash(snapshot) if snapshot else None
                merged_metadata = {**allowed_context, **sanitize_metadata(runtime_metadata)}
                context_object = type("RunContext", (), merged_metadata)()
                record_run(interaction_logger, project_id, event_type, run_id, {
                    "status": "success", "result": result_tables,
                    "schema_initial": snapshot, "schema_final": snapshot,
                    "schema_initial_hash": schema_hash, "schema_final_hash": schema_hash,
                    **merged_metadata, "warnings": [], "run_manifest": run_manifest(
                        started, template_version, context_object,
                        {key: value for key, value in merged_metadata.items() if key.endswith("hash") or key == "document_hashes"},
                    ),
                })
                return output
            except Exception as exc:
                record_run(interaction_logger, project_id, f"{event_type}_failed", run_id, {
                    "status": "failed", "warnings": [{"category": "worker_error", "error_type": type(exc).__name__}],
                    **allowed_context, "run_manifest": run_manifest(
                        started, template_version, type("RunContext", (), allowed_context)(),
                        {key: value for key, value in allowed_context.items() if key.endswith("hash") or key == "document_hashes"},
                    ),
                })
                raise
        return wrapped
    return decorate
