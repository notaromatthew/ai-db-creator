import json
import sqlite3

from app.evaluation.population_evaluation import load_gold_schema
from app.evaluation.schema_alignment import (
    build_alignment,
    inspect_generated_tables,
    normalise_name,
)

GOLD_SCHEMA = {
    "tables": [
        {
            "name": "students",
            "description": "students",
            "columns": [
                {"name": "student_id", "data_type": "INTEGER", "is_primary_key": True},
                {"name": "name", "data_type": "TEXT"},
                {"name": "email", "data_type": "TEXT"},
            ],
        },
        {
            "name": "courses",
            "description": "courses",
            "columns": [
                {"name": "course_code", "data_type": "TEXT", "is_primary_key": True},
                {"name": "title", "data_type": "TEXT"},
                {"name": "credits", "data_type": "INTEGER"},
            ],
        },
    ],
    "relationships": [],
    "description": "test",
}


def _generated_conn(tmp_path):
    conn = sqlite3.connect(tmp_path / "gen.db")
    conn.executescript(
        "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, email TEXT);"
        "CREATE TABLE courses (code TEXT PRIMARY KEY, title TEXT, credits INTEGER);"
    )
    conn.commit()
    return conn


def test_normalise_name():
    assert normalise_name("Student_ID") == "student_id"
    assert normalise_name("course_code") == "course_code"
    assert normalise_name("Categories") == "category"
    assert normalise_name("students") == "student"


def test_inspect_generated_tables(tmp_path):
    with _generated_conn(tmp_path) as conn:
        tables = inspect_generated_tables(conn)
    assert tables["students"] == ["id", "name", "email"]
    assert tables["courses"] == ["code", "title", "credits"]


def test_build_alignment_maps_normalised_and_prefix_matches(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)
    with _generated_conn(tmp_path) as conn:
        alignment = build_alignment(schema, conn)

    assert alignment["tables"] == {"students": "students", "courses": "courses"}
    assert alignment["columns"]["students"] == {
        "name": "name", "email": "email",
    }
    # gold student_id -> generated "id" is too short for the heuristic (>=3);
    # it is resolved via the per-dataset registry instead.
    assert alignment["unmatched_columns"]["students"] == ["student_id"]
    assert alignment["columns"]["courses"] == {
        "course_code": "code", "title": "title", "credits": "credits",
    }
    assert alignment["unmatched_tables"] == []


def test_build_alignment_uses_registry_fallback(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)
    conn = sqlite3.connect(tmp_path / "gen.db")
    conn.execute("CREATE TABLE t (sid INTEGER, other INTEGER)")
    conn.commit()
    registry = {"t": {"student_id": "sid", "name": "other"}}
    # Table name 't' does not match 'students'; registry applies to generated
    # column names only after a table match, so both tables stay unmatched.
    with conn:
        alignment = build_alignment(schema, conn, registry)
    assert alignment["unmatched_tables"] == ["students", "courses"]
    conn.close()


def test_build_alignment_column_substring_requires_length_three(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)
    conn = sqlite3.connect(tmp_path / "gen.db")
    conn.execute("CREATE TABLE courses (code TEXT PRIMARY KEY, title TEXT, credits INTEGER)")
    conn.commit()
    with conn:
        alignment = build_alignment(schema, conn, {})
    # course_code -> code: both >=3 chars, "code" in "course_code" -> mapped.
    assert alignment["columns"]["courses"]["course_code"] == "code"
    assert alignment["columns"]["courses"]["title"] == "title"
    conn.close()


def test_build_alignment_short_generated_column_needs_registry(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)
    conn = sqlite3.connect(tmp_path / "gen.db")
    conn.execute("CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, email TEXT)")
    conn.commit()
    with conn:
        without = build_alignment(schema, conn, {})
        with_registry = build_alignment(schema, conn,
                                        {"students": {"student_id": "id"}})
    # "id" is too short for the heuristic substring match; the registry is required.
    assert "student_id" in without["unmatched_columns"]["students"]
    assert with_registry["columns"]["students"]["student_id"] == "id"
    assert with_registry["via_registry"] == [{
        "table": "students", "gold_column": "student_id", "generated_column": "id",
    }]
    conn.close()