"""Privacy-safe RQ4 event taxonomy and participant-log export."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from pathlib import Path

from app.utils.research import atomic_write_json

TAXONOMY_VERSION = "rq4-taxonomy-v1"
EVENT_TYPES = {
    "rename_column", "add_constraint", "remove_constraint", "ignore_suggestion",
    "accept_suggestion", "navigation", "schema_save", "population_start",
    "population_complete", "validation_error", "task_abandon", "task_complete",
}
ACTION_TYPES = {"open", "close", "add", "remove", "rename", "accept", "ignore", "start", "complete", "retry"}
PHASE_TYPES = {"onboarding", "schema", "population", "validation", "survey", "completion"}
ALLOWED_KEYS = {"type", "target_type", "target_name", "action", "phase", "outcome", "error_code",
                "event_id", "sequence_no", "monotonic_ms", "operation_id", "duration_ms", "app_revision", "payload_schema_version"}
FORBIDDEN_KEYS = {"prompt", "document", "cell", "email", "name", "ip", "filename", "sql", "query", "value", "content"}


def _target_hash(value: str) -> str:
    salt = os.getenv("RQ4_HASH_SALT", "development-only-change-me")
    return hashlib.sha256(f"{salt}:{value}".encode()).hexdigest()[:20]


def normalise_event(payload: dict, session: dict | None = None) -> dict:
    unknown = set(payload) - ALLOWED_KEYS
    forbidden = {key for key in payload if key.lower() in FORBIDDEN_KEYS}
    if (unknown or forbidden or payload.get("type") not in EVENT_TYPES
            or (payload.get("action") is not None and payload["action"] not in ACTION_TYPES)
            or (payload.get("phase") is not None and payload["phase"] not in PHASE_TYPES)):
        raise ValueError("event violates RQ4 taxonomy")
    result = {
        "taxonomy_version": TAXONOMY_VERSION,
        "payload_schema_version": payload.get("payload_schema_version"),
        "event_id": payload.get("event_id"), "sequence_no": payload.get("sequence_no"),
        "monotonic_ms": payload.get("monotonic_ms"), "operation_id": payload.get("operation_id"),
        "duration_ms": payload.get("duration_ms"), "app_revision": payload.get("app_revision"),
        "type": payload["type"],
        "target_type": payload.get("target_type"),
        "target_hash": _target_hash(payload.get("target_name", "")) if payload.get("target_name") else None,
        "action": payload.get("action"), "phase": payload.get("phase"),
        "outcome": payload.get("outcome"), "error_code": payload.get("error_code"),
    }
    if session:
        result.update({"participant_id": session["participant_id"], "session_id": session["session_id"],
                       "condition": session["condition"], "protocol_version": session["protocol_version"]})
    if (payload.get("payload_schema_version") != "rq4-envelope-v1" or not isinstance(payload.get("event_id"), str)
            or not payload["event_id"] or type(payload.get("sequence_no")) is not int or payload["sequence_no"] < 1
            or type(payload.get("monotonic_ms")) not in {int, float} or payload["monotonic_ms"] < 0
            or not isinstance(payload.get("operation_id"), str) or not payload["operation_id"]
            or type(payload.get("duration_ms")) not in {int, float} or payload["duration_ms"] < 0
            or not isinstance(payload.get("app_revision"), str) or not payload["app_revision"]):
        raise ValueError("invalid RQ4 envelope")
    return {key: value for key, value in result.items() if value is not None}


def export_participant_events(events: list[dict], output_stem: Path) -> dict:
    safe = []
    for event in events:
        data = event.get("data", {})
        if data.get("taxonomy_version") != TAXONOMY_VERSION:
            continue
        safe.append({"timestamp": event.get("timestamp"), "project_id_hash": _target_hash(event.get("project_id", "")), **data})
    json_path = output_stem.with_suffix(".json")
    csv_path = output_stem.with_suffix(".csv")
    atomic_write_json(json_path, safe)
    fields = sorted({key for event in safe for key in event})
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        writer.writerows(safe)
    return {"count": len(safe), "json": str(json_path), "csv": str(csv_path)}
