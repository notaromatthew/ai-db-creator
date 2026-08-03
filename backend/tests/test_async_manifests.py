import json
import pytest

from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef


def simple_schema():
    return NormalizedSchema(tables=[TableDef(name="items", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True)
    ])], relationships=[])


def test_real_generate_task_records_complete_success_and_failure_manifests(client, project, monkeypatch, tmp_path):
    _, routes = client
    from app import tasks
    async def success(*args, **kwargs): return simple_schema()
    monkeypatch.setattr(tasks, "generate_schema", success)
    output = tasks.generate_schema_task.run(project["id"], "safe prompt", [], {"condition": "ai", "session_id": "s1"})
    assert output["tables"] == 1
    event = next(item for item in routes.interaction_logger.get_events(project["id"]) if item["event_type"] == "schema_generated_async")
    manifest = event["data"]["run_manifest"]
    assert manifest["output_schema_hash"]
    assert manifest["condition"] == "ai"
    assert event["data"]["provider"] and event["data"]["model"]
    artifact = tmp_path / "projects" / project["id"] / event["data"]["run_artifact"]
    assert json.loads(artifact.read_text(encoding="utf-8"))["schema_final"]["tables"]

    async def failure(*args, **kwargs): raise RuntimeError("provider raw error")
    monkeypatch.setattr(tasks, "generate_schema", failure)
    with pytest.raises(RuntimeError):
        tasks.generate_schema_task.run(project["id"], "safe prompt", [], {"prompt_hash": "known"})
    failed = next(item for item in routes.interaction_logger.get_events(project["id"]) if item["event_type"] == "schema_generated_async_failed")
    assert failed["data"]["run_manifest"]["status"] == "failed"


def test_real_population_task_records_counts_and_extraction_paths(client, project, monkeypatch):
    _, routes = client
    from app import tasks
    from app.services.population_service import PopulationService
    async def populated(*args, **kwargs):
        return {"items": {"inserted": 2, "skipped": 1, "failed": 1, "warnings": [{"category": "row"}],
                          "provenance": {"method": "hybrid"}}}
    monkeypatch.setattr(PopulationService, "populate", populated)
    schema_json = simple_schema().model_dump(mode="json")
    tasks.populate_data_task.run(project["id"], "database.sqlite", schema_json, [], {"participant_id": "u1"})
    event = next(item for item in routes.interaction_logger.get_events(project["id"]) if item["event_type"] == "population_async")
    manifest = event["data"]["run_manifest"]
    assert (manifest["inserted_count"], manifest["skipped_count"], manifest["failed_count"]) == (2, 1, 1)
    assert manifest["extraction_paths"] == ["hybrid"]
    assert manifest["participant_id"] == "u1"
