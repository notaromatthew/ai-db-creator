import json
from pathlib import Path

import run_benchmark
from app.models.schema_models import NormalizedSchema


def test_main_counts_successful_and_failed_runs_by_status(monkeypatch, capsys, tmp_path):
    class FakeRunner:
        def __init__(self, *_args, **_kwargs):
            self.output_dir = Path(tmp_path)
            self.temperature = 0.1

        async def run(self):
            return [
                {"status": "ok"},
                {"status": "error", "error": "provider unavailable"},
                {"status": "error", "error": "invalid schema"},
            ]

    monkeypatch.setattr(run_benchmark, "BenchmarkRunner", FakeRunner)

    assert run_benchmark.main(["--datasets", "university", "--runs", "1"]) == 0
    summary = json.loads(capsys.readouterr().out)

    assert summary["n_runs"] == 3
    assert summary["ok"] == 1
    assert summary["error"] == 2


def test_software_revision_is_explicit_when_unavailable(monkeypatch):
    monkeypatch.delenv("SOFTWARE_REVISION", raising=False)
    monkeypatch.setattr(run_benchmark.subprocess, "run", lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError()))
    assert run_benchmark.software_revision() == {"value": None, "source": "unavailable"}


def test_software_revision_prefers_configured_value(monkeypatch):
    monkeypatch.setenv("SOFTWARE_REVISION", "commit-123")
    assert run_benchmark.software_revision() == {"value": "commit-123", "source": "SOFTWARE_REVISION"}


def test_runner_marks_primary_not_evaluable_when_frozen_mapping_cannot_resolve_ambiguous_candidate(tmp_path, monkeypatch):
    dataset_dir = tmp_path / "data" / "ambiguous"
    dataset_dir.mkdir(parents=True)
    schema_payload = {
        "tables": [{"name": "students", "columns": [
            {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
            {"name": "email", "data_type": "TEXT"},
        ]}], "relationships": [], "description": "test",
    }
    (dataset_dir / "gold_schema.json").write_text(json.dumps(schema_payload), encoding="utf-8")
    (dataset_dir / "rq2_alignment.json").write_text(json.dumps({
        "entity_keys": {"students": ["email"]}, "surrogate_keys": {"students": ["id"]},
        "alignments": {"full_llm": {"mode": "identity_with_frozen_overrides", "tables": {}, "columns": {}}},
    }), encoding="utf-8")
    import sqlite3
    ground = sqlite3.connect(dataset_dir / "ground_truth.db")
    ground.execute("CREATE TABLE students(id INTEGER, email TEXT)")
    ground.execute("INSERT INTO students VALUES(1, 'ada@x')")
    ground.commit(); ground.close()
    generated_path = tmp_path / "generated.db"
    generated = sqlite3.connect(generated_path)
    generated.executescript("CREATE TABLE student_records(id INTEGER, email TEXT); CREATE TABLE student_archive(id INTEGER, email TEXT);")
    generated.commit(); generated.close()

    runner = run_benchmark.BenchmarkRunner.__new__(run_benchmark.BenchmarkRunner)
    project = type("Project", (), {"db_path": str(generated_path)})()
    schema = NormalizedSchema.model_validate(schema_payload)
    runner.schema_svc = type("SchemaService", (), {
        "get_project": lambda _self, _project_id: project,
        "get_schema": lambda _self, _project_id: schema,
    })()
    monkeypatch.setattr(run_benchmark, "DATASETS_DIR", tmp_path / "data")
    heuristic = {"tables": {}, "columns": {}, "unmatched_tables": ["students"],
                 "unmatched_columns": {}, "ambiguous_tables": {"students": ["student_archive", "student_records"]},
                 "ambiguous_columns": {}, "via_registry": [], "method_version": "deterministic-alignment-v2"}
    _project, result, _generated_rows, _ground_rows = runner._evaluate("p1", "ambiguous", "full_llm", heuristic)
    assert result["primary"]["status"] == "not_evaluable"
    assert result["primary"]["alignment_status"] == "frozen_mapping_not_applicable"
