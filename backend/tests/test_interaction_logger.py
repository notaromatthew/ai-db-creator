import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.services.interaction_logger import InteractionLogger


def test_logger_is_atomic_utc_redacted_and_project_isolated(tmp_path):
    store = tmp_path / "events.json"
    logger = InteractionLogger(store)
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda index: logger.log_event("test", "p1" if index % 2 else "p2", {"token": "secret", "index": index}), range(20)))
    persisted = json.loads(store.read_text(encoding="utf-8"))
    assert len(persisted) == 20
    assert all(datetime.fromisoformat(event["timestamp"]).tzinfo is not None for event in persisted)
    assert all(event["data"]["token"] == "[REDACTED]" for event in persisted)
    export = tmp_path / "p1.json"
    assert logger.save_events(export, project_id="p1") == 10
    assert all(event["project_id"] == "p1" for event in json.loads(export.read_text(encoding="utf-8")))
    assert InteractionLogger(store).get_events("p2")


def test_logger_erases_only_target_project(tmp_path):
    logger = InteractionLogger(tmp_path / "events.json")
    logger.log_event("x", "p1", {})
    logger.log_event("x", "p2", {})
    assert logger.erase_project("p1") == 1
    assert logger.get_events("p1") == []
    assert len(logger.get_events("p2")) == 1


def test_logger_preserves_legacy_events_without_run_id(tmp_path):
    store = tmp_path / "events.json"
    store.write_text(json.dumps([{"timestamp": "old", "event_type": "legacy", "project_id": "p1", "data": {}}]), encoding="utf-8")
    logger = InteractionLogger(store)
    legacy_id = logger.get_events("p1")[0]["run_id"]
    logger.log_event("new", "p1", {})
    events = InteractionLogger(store).get_events("p1")
    assert len(events) == 2
    assert events[0]["run_id"] == legacy_id
