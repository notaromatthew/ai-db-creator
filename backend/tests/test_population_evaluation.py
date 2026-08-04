import json
import sqlite3

from app.evaluation.population_evaluation import (
    classify_cell,
    connect_database,
    evaluate_generated,
    load_gold_schema,
    normalise_value,
    wilson_ci,
)

GOLD_SCHEMA = {
    "tables": [
        {
            "name": "students",
            "description": "students",
            "columns": [
                {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
                {"name": "name", "data_type": "TEXT"},
                {"name": "gpa", "data_type": "REAL"},
                {"name": "active", "data_type": "BOOLEAN"},
                {"name": "enrolled_on", "data_type": "DATE"},
            ],
        },
        {
            "name": "enrollments",
            "description": "enrollments",
            "columns": [
                {"name": "id", "data_type": "INTEGER", "is_primary_key": True},
                {"name": "student_id", "data_type": "INTEGER", "is_foreign_key": True,
                 "foreign_key_table": "students", "foreign_key_column": "id"},
            ],
        },
    ],
    "relationships": [],
    "description": "test",
}


def _make_db(path, sql, rows):
    conn = sqlite3.connect(str(path))
    conn.executescript(sql)
    for table, values in rows.items():
        placeholders = ", ".join("?" for _ in values[0])
        conn.executemany(f"INSERT INTO [{table}] VALUES ({placeholders})", values)
    conn.commit()
    conn.close()


def test_normalisation_rules():
    assert normalise_value("1.0", "REAL") == "1"
    assert normalise_value(1, "INTEGER") == "1"
    assert normalise_value("TRUE", "BOOLEAN") == "true"
    assert normalise_value("2024-01-05", "DATE") == "2024-01-05"
    assert normalise_value("2024-1-5", "DATE") == "2024-01-05"
    assert normalise_value(" Smith ", "TEXT") == "Smith"


def test_classify_cell_types():
    assert classify_cell(42, 42, "INTEGER") == "OK"
    assert classify_cell("1.0", 1, "REAL") == "OK"
    assert classify_cell(None, "Smith", "TEXT") == "NS"
    assert classify_cell("Smith", None, "TEXT") == "WV"
    assert classify_cell(1.5, "1.0", "REAL") == "TC"
    assert classify_cell("Jones", "Smith", "TEXT") == "WV"


def test_wilson_ci():
    lo, hi = wilson_ci(0.9, 100)
    assert 0.8 < lo < 0.9 < hi < 1.0


def test_evaluate_perfect_and_imperfect(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)

    ground_sql = """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, gpa REAL, active BOOLEAN, enrolled_on DATE);
        CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER);
    """
    _make_db(tmp_path / "ground.db", ground_sql, {
        "students": [(1, "Ada", 3.5, 1, "2024-01-05"), (2, "Bob", 2.9, 0, "2024-02-01")],
        "enrollments": [(1, 1), (2, 2)],
    })

    perfect_sql = """
        CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, gpa REAL, active BOOLEAN, enrolled_on DATE);
        CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER);
    """
    _make_db(tmp_path / "gen.db", perfect_sql, {
        "students": [(1, "Ada", "3.5", "TRUE", "2024-01-05"), (2, "Bob", 2.9, 0, "2024-02-01")],
        "enrollments": [(1, 1), (2, 2)],
    })

    with connect_database(tmp_path / "gen.db") as gc, connect_database(tmp_path / "ground.db") as gp:
        result = evaluate_generated(gc, gp, schema)

    assert result["per_table"]["students"]["missing_rows"] == 0
    assert result["per_table"]["students"]["extra_rows"] == 0
    assert result["per_table"]["students"]["f1"] == 1.0
    assert result["per_table"]["students"]["fk_violations"] == 0


def test_missing_extra_and_fk(tmp_path):
    gold = tmp_path / "gold.json"
    gold.write_text(json.dumps(GOLD_SCHEMA), encoding="utf-8")
    schema = load_gold_schema(gold)

    ground_sql = (
        "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, gpa REAL, active BOOLEAN, enrolled_on DATE);"
        "CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER);"
    )
    _make_db(tmp_path / "ground.db", ground_sql, {
        "students": [(1, "Ada", 3.0, 1, "2024-01-05"), (2, "Bob", 2.0, 0, "2024-02-01")],
        "enrollments": [(1, 1)],
    })

    gen_sql = (
        "CREATE TABLE students (id INTEGER PRIMARY KEY, name TEXT, gpa REAL, active BOOLEAN, enrolled_on DATE);"
        "CREATE TABLE enrollments (id INTEGER PRIMARY KEY, student_id INTEGER);"
    )
    _make_db(tmp_path / "gen.db", gen_sql, {
        "students": [(1, "WrongName", 3.0, 1, "2024-01-05"), (3, "Extra", 1.0, 1, "2024-01-01")],
        "enrollments": [(1, 99)],
    })

    with connect_database(tmp_path / "gen.db") as gc, connect_database(tmp_path / "ground.db") as gp:
        result = evaluate_generated(gc, gp, schema)

    students = result["per_table"]["students"]
    assert students["missing_rows"] == 1      # Bob (id 2) absent
    assert students["extra_rows"] == 1        # id 3 present
    assert students["wrong_value"] == 1       # "WrongName" vs "Ada"
    enrollments = result["per_table"]["enrollments"]
    assert enrollments["fk_violations"] == 1  # student_id 99 has no student
    assert result["global"]["missing_rows"] == 1
    assert result["global"]["extra_rows"] == 1