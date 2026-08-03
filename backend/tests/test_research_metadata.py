import json
import pytest
from app.services.interaction_logger import InteractionLogger
from app.utils.research import record_run, sanitize_metadata, stable_hash, tracked_worker_run


def test_research_metadata_redacts_secrets_and_hash_is_stable():
    cleaned = sanitize_metadata({
        "api_key": "secret-value",
        "message": "Authorization: Bearer abc123",
        "nested": {"password": "hidden"},
    })
    assert cleaned["api_key"] == "[REDACTED]"
    assert "abc123" not in cleaned["message"]
    assert cleaned["nested"]["password"] == "[REDACTED]"
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})


def test_manifest_aggregates_real_outcomes_and_keeps_snapshot_out_of_global_log(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    logger = InteractionLogger(tmp_path / "projects" / "interactions.json")
    record_run(logger, "p1", "population", "run-1", {
        "status": "success", "schema_final": {"tables": [{"name": "private"}]},
        "schema_final_hash": "hash", "result": {
            "a": {"inserted": 2, "skipped": 1, "failed": 1},
            "b": {"inserted": 3, "skipped": 0, "failed": 0},
        }, "run_manifest": {},
    })
    event = logger.get_events("p1")[0]
    assert event["data"]["inserted_count"] == 5
    assert event["data"]["skipped_count"] == 1
    assert event["data"]["failed_count"] == 1
    assert "schema_final" not in event["data"]
    artifact = json.loads((tmp_path / "projects" / "p1" / "runs" / "run-1.json").read_text(encoding="utf-8"))
    assert artifact["schema_final"]["tables"][0]["name"] == "private"


def test_worker_tracker_records_success_and_failure_artifacts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from app.services import interaction_logger as logger_module
    logger_module.interaction_logger.persist_path = tmp_path / "projects" / "interactions.json"
    logger_module.interaction_logger.events = []

    @tracked_worker_run("population_async", "population_prompt_v1")
    def success(_task, project_id):
        return {"results": {"t": {"inserted": 1, "skipped": 0, "failed": 0}}}

    @tracked_worker_run("population_async", "population_prompt_v1")
    def failure(_task, project_id):
        raise RuntimeError("raw secret must not leak")

    assert success(None, "p1")["results"]["t"]["inserted"] == 1
    with pytest.raises(RuntimeError):
        failure(None, "p1")
    events = logger_module.interaction_logger.get_events("p1")
    assert {event["data"]["run_manifest"]["status"] for event in events} == {"success", "failed"}
    assert "raw secret" not in json.dumps(events)
