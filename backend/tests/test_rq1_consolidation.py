import json

from consolidate_rq1_schemas import _render_schema, collect_runs, load_schemas


def _sample_schema():
    return {
        "description": "A test domain",
        "tables": [{
            "name": "authors",
            "columns": [
                {"name": "author_id", "data_type": "INTEGER",
                 "is_primary_key": True, "is_foreign_key": False,
                 "foreign_key_table": None, "foreign_key_column": None,
                 "is_unique": False, "is_not_null": True},
                {"name": "book_id", "data_type": "INTEGER",
                 "is_primary_key": False, "is_foreign_key": True,
                 "foreign_key_table": "books", "foreign_key_column": "book_id",
                 "is_unique": False, "is_not_null": True},
            ],
        }],
        "relationships": [{
            "type": "one_to_many",
            "from_table": "books", "from_column": "book_id",
            "to_table": "authors", "to_column": "book_id",
        }],
    }


def test_render_schema_lists_constraints_and_relationships():
    out = _render_schema(_sample_schema())
    assert "TABLE authors" in out
    assert "author_id (INTEGER)  [PK, NN]" in out
    assert "book_id (INTEGER)  [NN, FK->books.book_id]" in out
    assert "RELATIONSHIPS" in out
    assert "books.book_id [one_to_many] authors.book_id" in out


def test_render_schema_annotates_pk_only_when_pk():
    out = _render_schema(_sample_schema())
    assert out.count("PK") == 1  # only author_id


def test_collect_runs_reads_dump_records(tmp_path):
    cond = tmp_path / "university" / "full_llm"
    cond.mkdir(parents=True)
    (cond / "run01.json").write_text(json.dumps(
        {"dataset": "university", "condition": "full_llm", "run": 1,
         "project_id": "abc", "status": "ok",
         "global_f1": 0.5}))
    (cond / "run02.json").write_text(json.dumps(
        {"dataset": "university", "condition": "full_llm", "run": 2,
         "project_id": "def", "status": "ok",
         "global_f1": 0.6}))
    runs = collect_runs(tmp_path)
    assert len(runs) == 2
    assert runs[0]["project_id"] == "abc"


def _db_with_schema(tmp_path):
    import sqlite3
    db = tmp_path / "app.db"
    con = sqlite3.connect(str(db))
    con.execute("CREATE TABLE projects (id TEXT, name TEXT, schema_json TEXT)")
    con.execute("INSERT INTO projects VALUES ('abc','x',?)",
                (json.dumps(_sample_schema()),))
    con.commit()
    con.close()
    return db


def test_load_schemas_reads_json_sqlite(tmp_path):
    db = _db_with_schema(tmp_path)
    runs = [{"project_id": "abc"}]
    out = load_schemas(runs, db)
    assert "abc" in out
    assert "TABLE authors" in out["abc"]