import asyncio
import pytest
from sqlalchemy import create_engine, inspect, text

from app.models.database import Document, get_session
from app.models.schema_models import ColumnDef, NormalizedSchema, TableDef
from app.services.population_service import PopulationService
from app.utils.exceptions import AppException
from app.utils.research import stable_hash


def schema():
    return NormalizedSchema(tables=[TableDef(name="persone", columns=[
        ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ColumnDef(name="nome", data_type="TEXT"),
    ])], relationships=[])


def add_csv(service, tmp_path, project_id, filename, header="id,nome"):
    path = tmp_path / filename
    path.write_text(f"{header}\n1,Ada\n", encoding="utf-8")
    session = get_session(service.engine)
    document = Document(project_id=project_id, filename=filename, file_type="csv", file_path=str(path), content_summary="")
    session.add(document); session.commit(); document_id = document.id; session.close()
    return document_id


def add_text(service, tmp_path, project_id, filename="source.txt", content="Ada vive a Roma"):
    path = tmp_path / filename
    path.write_text(content, encoding="utf-8")
    session = get_session(service.engine)
    document = Document(project_id=project_id, filename=filename, file_type="txt", file_path=str(path), content_summary="")
    session.add(document); session.commit(); document_id = document.id; session.close()
    return document_id


def test_deterministic_fallback_runs_when_llm_sql_is_empty_and_has_traceable_provenance(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_csv(service, tmp_path, "p1", "exact.csv")
    async def no_llm_sql(*args, **kwargs):
        return ""
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", no_llm_sql)
    async def forbidden(*args, **kwargs):
        raise AssertionError("LLM mapping must not run for exact headers")
    monkeypatch.setattr("app.services.population_service.map_columns_to_tables", forbidden)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    provenance = result["persone"]["provenance"]
    assert provenance["method"] == "deterministic"
    assert provenance["confidence"] is None
    assert provenance["mappings"][0]["source_header"] == "id"
    assert "source_row_index" in provenance["rows"][0]
    assert provenance["rows"][0]["outcome"] == "inserted"
    assert provenance["rows"][0]["identity_method"] == "primary_key"
    assert provenance["rows"][0]["target_row_key"] == stable_hash(("1",))
    assert {item["target_column"] for item in provenance["rows"][0]["target_columns"]} == {"id", "nome"}


def test_full_llm_is_called_for_structured_csv(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_csv(service, tmp_path, "p1", "structured.csv")
    captured = {}
    async def generated_sql(_schema, document_content):
        captured["content"] = document_content
        return "INSERT INTO persone (id, nome) VALUES (1, 'Ada');"
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", generated_sql)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    assert "structured.csv" in captured["content"]
    assert "Ada" in captured["content"]
    assert result["persone"]["inserted"] == 1
    assert result["persone"]["provenance"]["method"] == "llm"


def test_hybrid_mapping_marks_only_effective_semantic_columns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_csv(service, tmp_path, "p1", "hybrid.csv", header="id,nominativo")
    async def no_llm_sql(*args, **kwargs):
        return ""
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", no_llm_sql)
    async def semantic(*args, **kwargs):
        return {"persone": {1: "nome"}}
    monkeypatch.setattr("app.services.population_service.map_columns_to_tables", semantic)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    provenance = result["persone"]["provenance"]
    assert provenance["method"] == "hybrid"
    assert any(item["mapping_method"] == "llm_semantic" for item in provenance["mappings"])


def test_provenance_keeps_multiple_source_documents(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    ids = [add_csv(service, tmp_path, "p1", f"source-{index}.csv") for index in range(2)]
    async def no_llm_sql(*args, **kwargs):
        return ""
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", no_llm_sql)
    async def forbidden(*args, **kwargs):
        raise AssertionError("unexpected semantic mapping")
    monkeypatch.setattr("app.services.population_service.map_columns_to_tables", forbidden)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), ids))
    provenance = result["persone"]["provenance"]
    assert set(provenance["document_ids"]) == set(ids)
    assert len(provenance["sources"]) == 2
    assert {trace["outcome"] for trace in provenance["rows"]} == {"inserted", "skipped"}
    assert any(trace.get("reason") == "duplicate" for trace in provenance["rows"])


def test_failed_insert_has_separate_non_materialized_trace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_csv(service, tmp_path, "p1", "failure.csv")
    async def no_llm_sql(*args, **kwargs):
        return ""
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", no_llm_sql)
    failing_schema = schema()
    failing_schema.tables[0].columns.append(ColumnDef(name="required_value", data_type="TEXT", is_not_null=True))
    async def semantic(*args, **kwargs):
        return {}
    monkeypatch.setattr("app.services.population_service.map_columns_to_tables", semantic)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), failing_schema, [document_id]))
    assert result["persone"]["failed"] == 1
    trace = result["persone"]["provenance"]["rows"][0]
    assert trace["outcome"] == "failed"
    assert trace["reason"] == "constraint_or_type_error"


def test_cross_project_document_is_rejected_without_database_side_effects(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    foreign_document_id = add_csv(service, tmp_path, "other-project", "foreign.csv")
    database_path = tmp_path / "sentinel.sqlite"
    engine = create_engine(f"sqlite:///{database_path}")
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE sentinel (id INTEGER PRIMARY KEY, value TEXT)"))
        connection.execute(text("INSERT INTO sentinel (id, value) VALUES (1, 'unchanged')"))
    tables_before = inspect(engine).get_table_names()
    with engine.connect() as connection:
        rows_before = connection.execute(text("SELECT id, value FROM sentinel")).fetchall()

    with pytest.raises(AppException) as caught:
        asyncio.run(service.populate("target-project", str(database_path), schema(), [foreign_document_id]))

    assert caught.value.status_code == 404
    assert inspect(engine).get_table_names() == tables_before
    with engine.connect() as connection:
        assert connection.execute(text("SELECT id, value FROM sentinel")).fetchall() == rows_before


def test_unstructured_llm_sql_tracks_valid_and_failed_statements(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_text(service, tmp_path, "p1")
    async def generated_sql(*args, **kwargs):
        return "INSERT INTO persone (id, nome) VALUES (1, 'Ada'); INSERT INTO persone (missing) VALUES ('x');"
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", generated_sql)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    table = result["persone"]
    assert table["inserted"] == 1
    assert table["skipped"] == 0
    assert table["failed"] == 1
    assert {trace["outcome"] for trace in table["provenance"]["rows"]} == {"inserted", "failed"}
    failed = next(trace for trace in table["provenance"]["rows"] if trace["outcome"] == "failed")
    assert "target_row_key" not in failed
    assert table["warnings"][0]["category"] == "statement_execution_error"


def test_unstructured_llm_input_is_truncated_per_document_and_warned(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_text(service, tmp_path, "p1", content="Z" * 7000)
    captured = {}
    async def generated_sql(_schema, document_content):
        captured["content"] = document_content
        return "INSERT INTO persone (id, nome) VALUES (1, 'Ada');"
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", generated_sql)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    assert "Z" * 5000 in captured["content"]
    assert "Z" * 5001 not in captured["content"]
    warning = next(item for item in result["persone"]["warnings"] if item["category"] == "llm_input_truncated")
    assert warning["used_chars"] == 5000
    assert "Z" not in str(warning)


def test_parser_empty_is_propagated_as_warning(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_text(service, tmp_path, "p1", content="")
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    assert any(item["category"] == "parser_empty" for item in result["persone"]["warnings"])


def test_multi_row_llm_insert_is_rejected_without_execution(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    service = PopulationService()
    document_id = add_text(service, tmp_path, "p1")
    async def generated_sql(*args, **kwargs):
        return "INSERT INTO persone (id, nome) VALUES (1, 'Ada'), (2, 'Linus');"
    monkeypatch.setattr("app.services.population_service.generate_sql_for_population", generated_sql)
    result = asyncio.run(service.populate("p1", str(tmp_path / "database.sqlite"), schema(), [document_id]))
    table = result["persone"]
    assert table["inserted"] == 0 and table["failed"] == 1
    assert table["provenance"]["rows"][0]["reason"] == "multi_row_or_unsupported_insert"
    engine = create_engine(f"sqlite:///{tmp_path / 'database.sqlite'}")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM persone")).scalar() == 0


def test_foreign_keys_are_built_into_the_generated_database(tmp_path):
    from app.core.db_generator import create_database_from_schema
    from sqlalchemy import inspect
    schema = NormalizedSchema(tables=[
        TableDef(name="authors", columns=[
            ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
        ]),
        TableDef(name="books", columns=[
            ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
            ColumnDef(name="author_id", data_type="INTEGER",
                      is_foreign_key=True, foreign_key_table="authors",
                      foreign_key_column="id"),
        ]),
    ], relationships=[])
    db_path = str(tmp_path / "fk.sqlite")
    create_database_from_schema(schema, db_path)
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    books = inspector.get_foreign_keys("books")
    assert len(books) == 1
    assert books[0]["referred_table"] == "authors"
    assert books[0]["constrained_columns"] == ["author_id"]
    assert books[0]["referred_columns"] == ["id"]
