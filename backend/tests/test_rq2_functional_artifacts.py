import json
import sqlite3
from pathlib import Path

import pytest

from app.evaluation.functional_equivalence import (
    evaluate_functional_queries,
    load_evaluation_spec,
)
from app.evaluation.population_evaluation import (
    connect_database,
    evaluate_generated,
    load_gold_schema,
)
from app.evaluation.rq2_artifacts import write_run_bundle
from app.utils.research import sha256_file
from run_benchmark import BENCHMARK_OWNER_ID, BenchmarkRunner, build_parser


DATASETS = Path(__file__).resolve().parents[2] / "data" / "datasets"


@pytest.mark.parametrize(
    "dataset", ["university", "library", "hospital", "format_equivalence"]
)
def test_gold_against_itself_is_perfect_in_observable_scope(dataset):
    root = DATASETS / dataset
    spec, spec_hash = load_evaluation_spec(root)
    schema = load_gold_schema(root / "gold_schema.json")

    with connect_database(root / "ground_truth.db") as generated, \
            connect_database(root / "ground_truth.db") as ground:
        cell_result = evaluate_generated(
            generated,
            ground,
            schema,
            natural_keys=spec.get("natural_keys"),
            observable_scope=spec.get("observable_scope"),
        )
        functional_result = evaluate_functional_queries(generated, ground, spec)

    assert spec_hash == sha256_file(root / "evaluation_spec.json")
    assert cell_result["global"]["precision"] == 1.0
    assert cell_result["global"]["recall"] == 1.0
    assert cell_result["global"]["f1"] == 1.0
    assert cell_result["global"]["missing_rows"] == 0
    assert cell_result["global"]["extra_rows"] == 0
    assert functional_result["overall_query_pass_rate"] == 1.0
    assert functional_result["critical_query_pass_rate"] == 1.0
    assert functional_result["functionally_equivalent"] is True


def test_evaluation_spec_rejects_mutating_and_duplicate_queries(tmp_path):
    spec = {
        "functional_queries": [
            {"id": "Q1", "sql": "SELECT 1"},
            {"id": "Q1", "sql": "DELETE FROM t"},
        ]
    }
    (tmp_path / "evaluation_spec.json").write_text(json.dumps(spec), encoding="utf-8")
    with pytest.raises(ValueError):
        load_evaluation_spec(tmp_path)


def test_functional_evaluation_detects_wrong_result():
    ground = sqlite3.connect(":memory:")
    generated = sqlite3.connect(":memory:")
    try:
        ground.executescript("CREATE TABLE facts (id INTEGER, value TEXT); INSERT INTO facts VALUES (1, 'A');")
        generated.executescript("CREATE TABLE facts (id INTEGER, value TEXT); INSERT INTO facts VALUES (1, 'B');")
        spec = {
            "version": "test-v1",
            "functional_equivalence": {
                "critical_query_pass_rate": 1.0,
                "overall_query_pass_rate": 1.0,
            },
            "functional_queries": [
                {"id": "Q1", "critical": True, "sql": "SELECT id, value FROM facts"}
            ],
        }
        result = evaluate_functional_queries(generated, ground, spec)
    finally:
        generated.close()
        ground.close()

    assert result["passed_queries"] == 0
    assert result["functionally_equivalent"] is False
    assert result["queries"][0]["generated_rows"] != result["queries"][0]["gold_rows"]
    assert result["queries"][0]["gold_result_hash"] != result["queries"][0]["generated_result_hash"]
    assert result["queries"][0]["missing_rows"] == [[{"number": "1"}, "A"]]
    assert result["queries"][0]["extra_rows"] == [[{"number": "1"}, "B"]]


def test_functional_equivalence_fails_on_duplicate_natural_key():
    ground = sqlite3.connect(":memory:")
    generated = sqlite3.connect(":memory:")
    try:
        ground.executescript("CREATE TABLE people (id INTEGER, email TEXT); INSERT INTO people VALUES (1, 'a@test');")
        generated.executescript(
            "CREATE TABLE people (id INTEGER, email TEXT);"
            "INSERT INTO people VALUES (1, 'a@test'), (2, 'a@test');"
        )
        spec = {
            "version": "test-v1",
            "natural_keys": {"people": ["email"]},
            "functional_equivalence": {
                "critical_query_pass_rate": 0.0,
                "overall_query_pass_rate": 0.0,
                "max_critical_integrity_violations": 0,
            },
            "functional_queries": [
                {"id": "Q1", "critical": True, "sql": "SELECT 1 AS available"}
            ],
        }
        result = evaluate_functional_queries(generated, ground, spec)
    finally:
        generated.close()
        ground.close()

    assert result["queries"][0]["passed"] is True
    assert result["integrity"]["violation_count"] == 1
    assert result["functionally_equivalent"] is False


def test_observable_relationship_rows_align_through_business_keys(tmp_path):
    schema_payload = {
        "description": "business-key alignment",
        "tables": [
            {"name": "students", "description": "", "columns": [
                {"name": "student_id", "data_type": "INTEGER", "is_primary_key": True},
                {"name": "email", "data_type": "TEXT"},
            ]},
            {"name": "courses", "description": "", "columns": [
                {"name": "course_id", "data_type": "INTEGER", "is_primary_key": True},
                {"name": "course_code", "data_type": "TEXT"},
            ]},
            {"name": "enrollments", "description": "", "columns": [
                {"name": "student_id", "data_type": "INTEGER", "is_primary_key": True,
                 "is_foreign_key": True, "foreign_key_table": "students",
                 "foreign_key_column": "student_id"},
                {"name": "course_id", "data_type": "INTEGER", "is_primary_key": True,
                 "is_foreign_key": True, "foreign_key_table": "courses",
                 "foreign_key_column": "course_id"},
                {"name": "semester", "data_type": "TEXT", "is_primary_key": True},
                {"name": "grade", "data_type": "INTEGER"},
            ]},
        ],
        "relationships": [],
    }
    schema_file = tmp_path / "schema.json"
    schema_file.write_text(json.dumps(schema_payload), encoding="utf-8")
    schema = load_gold_schema(schema_file)

    def create(path, student_id, course_id):
        connection = sqlite3.connect(path)
        connection.executescript(
            "CREATE TABLE students (student_id INTEGER PRIMARY KEY, email TEXT);"
            "CREATE TABLE courses (course_id INTEGER PRIMARY KEY, course_code TEXT);"
            "CREATE TABLE enrollments (student_id INTEGER, course_id INTEGER, semester TEXT, grade INTEGER);"
        )
        connection.execute("INSERT INTO students VALUES (?, 'same@example.test')", (student_id,))
        connection.execute("INSERT INTO courses VALUES (?, 'DB-1')", (course_id,))
        connection.execute("INSERT INTO enrollments VALUES (?, ?, '2026-01', 28)",
                           (student_id, course_id))
        connection.commit()
        connection.close()

    create(tmp_path / "ground.db", 1, 10)
    create(tmp_path / "generated.db", 101, 210)
    scope = {"tables": {"enrollments": {
        "columns": ["semester", "grade"],
        "key_columns": ["student_id", "course_id", "semester"],
    }}, "excluded": {"students": {}, "courses": {}}}
    natural_keys = {"students": ["email"], "courses": ["course_code"]}

    with connect_database(tmp_path / "generated.db") as generated, \
            connect_database(tmp_path / "ground.db") as ground:
        result = evaluate_generated(
            generated, ground, schema,
            natural_keys=natural_keys,
            observable_scope=scope,
        )

    assert result["global"]["f1"] == 1.0
    assert result["global"]["missing_rows"] == 0
    assert result["global"]["extra_rows"] == 0


def test_run_bundle_is_self_contained_and_hashes_match(tmp_path):
    database = tmp_path / "source.db"
    connection = sqlite3.connect(database)
    connection.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, value TEXT)")
    connection.execute("INSERT INTO t VALUES (1, 'x')")
    connection.commit()
    connection.close()
    evaluation = {
        "per_table": {
            "t": {
                "row_key_columns": ["id"],
                "discrepancies": [{
                    "row_key": [1], "column": "value", "error_type": "WV",
                    "generated_value": "x", "ground_value": "y",
                }],
            }
        }
    }

    hashes = write_run_bundle(
        tmp_path / "bundle",
        database_path=database,
        generated_schema={"tables": []},
        evaluation=evaluation,
        alignment={"tables": {}},
        functional_evaluation={"functionally_equivalent": False},
        manifest={"dataset": "test"},
        record={"status": "ok", "run": 1},
    )
    manifest = json.loads((tmp_path / "bundle" / "manifest.json").read_text(encoding="utf-8"))

    expected = {
        "generated_database", "generated_schema", "evaluation",
        "cell_discrepancies", "alignment", "functional_query_results", "run_record",
    }
    assert set(hashes) == expected
    assert set(manifest["artifacts"]) == expected
    for name, metadata in manifest["artifacts"].items():
        assert metadata["sha256"] == sha256_file(tmp_path / "bundle" / metadata["path"])
    assert (tmp_path / "bundle" / "cell_discrepancies.csv").read_text(encoding="utf-8").count("WV") == 1


def test_run_bundle_redacts_secret_like_error_metadata(tmp_path):
    write_run_bundle(
        tmp_path / "bundle",
        database_path=None,
        generated_schema=None,
        evaluation=None,
        alignment=None,
        functional_evaluation=None,
        manifest={"dataset": "test", "api_key": "do-not-write"},
        record={"status": "error", "error": "token=do-not-write"},
    )
    run_text = (tmp_path / "bundle" / "run.json").read_text(encoding="utf-8")
    manifest_text = (tmp_path / "bundle" / "manifest.json").read_text(encoding="utf-8")
    assert "do-not-write" not in run_text
    assert "do-not-write" not in manifest_text


def test_source_format_filter_is_explicit_and_missing_xlsx_is_visible():
    csv_files = BenchmarkRunner._source_files("university", "csv")
    pdf_files = BenchmarkRunner._source_files("university", "pdf")
    xlsx_files = BenchmarkRunner._source_files("university", "xlsx")

    assert csv_files and all(path.suffix.lower() == ".csv" for path in csv_files)
    assert pdf_files and all(path.suffix.lower() == ".pdf" for path in pdf_files)
    assert xlsx_files == []


def test_benchmark_runner_uses_dedicated_owner(monkeypatch, tmp_path):
    import app.core.acl
    import app.services.document_service
    import app.services.population_service
    import app.services.schema_service

    seen = {}

    def fake_ensure_user(identity):
        seen.update(identity)
        return type("Owner", (), {"id": identity["sub"]})()

    monkeypatch.setattr(app.core.acl, "ensure_user", fake_ensure_user)
    monkeypatch.setattr(app.services.schema_service, "SchemaService", lambda: object())
    monkeypatch.setattr(app.services.document_service, "DocumentService", lambda: object())
    monkeypatch.setattr(app.services.population_service, "PopulationService", lambda: object())

    runner = BenchmarkRunner(["university"], ["baseline"], 1, tmp_path)

    assert runner.owner_id == BENCHMARK_OWNER_ID
    assert seen["sub"] == BENCHMARK_OWNER_ID


def test_population_mode_rejects_deterministic_fallback():
    llm = {
        "students": {"warnings": [], "provenance": {"method": "llm"}},
        "courses": {"warnings": [], "provenance": {"method": "llm"}},
    }
    fallback = {
        "students": {
            "warnings": [{"category": "fallback_sql_empty"}],
            "provenance": {"method": "deterministic"},
        }
    }

    assert BenchmarkRunner._population_mode(llm) == "llm"
    assert BenchmarkRunner._population_mode(fallback) == "fallback"


def test_benchmark_resume_flag_is_explicit():
    assert build_parser().parse_args(["--resume"]).resume is True
    assert build_parser().parse_args([]).resume is False
    assert build_parser().parse_args(["--schedule", "interleaved"]).schedule == "interleaved"
    assert build_parser().parse_args(["--run-indices", "1,5"]).run_indices == "1,5"
