import json
import sqlite3

from app.evaluation.canonical_facts import evaluate_canonical_facts
from app.evaluation.population_evaluation import load_gold_schema


SCHEMA = {
    "tables": [
        {"name": "students", "columns": [
            {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
            {"name": "email", "data_type": "TEXT", "is_unique": True},
            {"name": "name", "data_type": "TEXT"},
        ]},
        {"name": "visits", "columns": [
            {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
            {"name": "student_id", "data_type": "INTEGER", "is_foreign_key": True,
             "foreign_key_table": "students", "foreign_key_column": "id"},
            {"name": "visited_on", "data_type": "DATE"},
        ]},
    ], "relationships": [], "description": "canonical test"
}
CONFIG = {
    "version": "test-v1",
    "entity_keys": {"students": ["email"], "visits": ["student_id", "visited_on"]},
    "surrogate_keys": {"students": ["id"], "visits": ["id"]},
    "alignments": {
        "full_llm": {
            "mode": "identity_with_frozen_overrides",
            "tables": {"students": "people", "visits": "events"},
            "columns": {
                "students": {"id": "sid", "email": "mail", "name": "full_name"},
                "visits": {"id": "eid", "student_id": "person_ref", "visited_on": "event_date"},
            },
        },
        "baseline": {"mode": "identity_with_frozen_overrides", "tables": {}, "columns": {}},
    },
}


def _db(path, schema_sql, statements):
    conn = sqlite3.connect(path)
    conn.executescript(schema_sql)
    for sql, values in statements:
        conn.executemany(sql, values)
    conn.commit()
    conn.close()


def test_synthetic_keys_table_names_and_value_representations_are_canonically_equivalent(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    _db(tmp_path / "gold.db", "CREATE TABLE students(id INTEGER, email TEXT, name TEXT); CREATE TABLE visits(id INTEGER, student_id INTEGER, visited_on DATE);", [
        ("INSERT INTO students VALUES(?,?,?)", [(1, "ada@example.test", "Ada")]),
        ("INSERT INTO visits VALUES(?,?,?)", [(10, 1, "2026-1-5")]),
    ])
    _db(tmp_path / "gen.db", "CREATE TABLE people(sid INTEGER, mail TEXT, full_name TEXT); CREATE TABLE events(eid INTEGER, person_ref INTEGER, event_date DATE);", [
        ("INSERT INTO people VALUES(?,?,?)", [(99, "ada@example.test", "Ada")]),
        ("INSERT INTO events VALUES(?,?,?)", [(500, 99, "2026-01-05")]),
    ])
    with sqlite3.connect(tmp_path / "gen.db") as generated, sqlite3.connect(tmp_path / "gold.db") as ground:
        result = evaluate_canonical_facts(generated, ground, schema, CONFIG, "full_llm")
    assert result["status"] == "ok"
    assert result["global"] == {"tp": 4, "fp": 0, "fn": 0, "precision": 1.0, "recall": 1.0, "f1": 1.0}


def test_missing_and_extra_entities_become_fact_level_fn_and_fp(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    sql = "CREATE TABLE students(id INTEGER, email TEXT, name TEXT); CREATE TABLE visits(id INTEGER, student_id INTEGER, visited_on DATE);"
    _db(tmp_path / "gold.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(1, "ada@x", "Ada")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    _db(tmp_path / "gen.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(2, "bob@x", "Bob")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    with sqlite3.connect(tmp_path / "gen.db") as generated, sqlite3.connect(tmp_path / "gold.db") as ground:
        result = evaluate_canonical_facts(generated, ground, schema, CONFIG, "baseline")
    assert result["global"]["tp"] == 0
    assert result["global"]["fp"] == 2
    assert result["global"]["fn"] == 2


def test_missing_entity_key_manifest_is_not_evaluable(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    conn = sqlite3.connect(":memory:")
    result = evaluate_canonical_facts(conn, conn, schema, {"entity_keys": {"students": ["email"]}}, "baseline")
    assert result["status"] == "not_evaluable"


def test_primary_rejects_run_dependent_heuristic_mapping_when_frozen_mapping_does_not_apply(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    generated = sqlite3.connect(":memory:")
    ground = sqlite3.connect(":memory:")
    generated.executescript("CREATE TABLE student_records(id INTEGER, email TEXT, name TEXT); CREATE TABLE visit_records(id INTEGER, student_id INTEGER, visited_on DATE);")
    ground.executescript("CREATE TABLE students(id INTEGER, email TEXT, name TEXT); CREATE TABLE visits(id INTEGER, student_id INTEGER, visited_on DATE);")
    result = evaluate_canonical_facts(generated, ground, schema, CONFIG, "baseline")
    assert result["status"] == "not_evaluable"
    assert result["alignment_status"] == "frozen_mapping_not_applicable"


def test_wrong_value_is_one_false_positive_and_one_false_negative(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    sql = "CREATE TABLE students(id INTEGER, email TEXT, name TEXT); CREATE TABLE visits(id INTEGER, student_id INTEGER, visited_on DATE);"
    _db(tmp_path / "gold.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(1, "ada@x", "Ada")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    _db(tmp_path / "gen.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(99, "ada@x", "Wrong")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    with sqlite3.connect(tmp_path / "gen.db") as generated, sqlite3.connect(tmp_path / "gold.db") as ground:
        result = evaluate_canonical_facts(generated, ground, schema, CONFIG, "baseline")
    assert result["global"]["tp"] == 1
    assert result["global"]["fp"] == 1
    assert result["global"]["fn"] == 1


def test_duplicate_rows_are_counted_as_extra_canonical_facts(tmp_path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps(SCHEMA), encoding="utf-8")
    schema = load_gold_schema(schema_path)
    sql = "CREATE TABLE students(id INTEGER, email TEXT, name TEXT); CREATE TABLE visits(id INTEGER, student_id INTEGER, visited_on DATE);"
    _db(tmp_path / "gold.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(1, "ada@x", "Ada")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    _db(tmp_path / "gen.db", sql, [("INSERT INTO students VALUES(?,?,?)", [(7, "ada@x", "Ada"), (8, "ada@x", "Ada")]), ("INSERT INTO visits VALUES(?,?,?)", [])])
    with sqlite3.connect(tmp_path / "gen.db") as generated, sqlite3.connect(tmp_path / "gold.db") as ground:
        result = evaluate_canonical_facts(generated, ground, schema, CONFIG, "baseline")
    assert result["global"]["tp"] == 2
    assert result["global"]["fp"] == 2
    assert result["global"]["fn"] == 0
