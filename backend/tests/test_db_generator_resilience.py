import pytest
from pathlib import Path
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef
from app.core.db_generator import create_database_from_schema
from app.services.chat_service import _normalize_schema


def test_create_database_case_insensitive_and_missing_fk(tmp_path):
    db_file = str(tmp_path / "test_case.sqlite")
    # Schema with table 'clienti' and column 'cli_id'
    # But table 'ordini' references 'Clienti.CLI_ID' (uppercase)
    schema = NormalizedSchema(
        tables=[
            TableDef(
                name="clienti",
                columns=[
                    ColumnDef(name="cli_id", data_type="INTEGER", is_primary_key=True),
                    ColumnDef(name="ragione_sociale", data_type="TEXT"),
                ],
            ),
            TableDef(
                name="ordini",
                columns=[
                    ColumnDef(name="id", data_type="INTEGER", is_primary_key=True),
                    ColumnDef(
                        name="cli_id",
                        data_type="INTEGER",
                        is_foreign_key=True,
                        foreign_key_table="Clienti",
                        foreign_key_column="CLI_ID",
                    ),
                    ColumnDef(
                        name="invalid_fk_col",
                        data_type="INTEGER",
                        is_foreign_key=True,
                        foreign_key_table="NonExistentTable",
                        foreign_key_column="foo",
                    ),
                ],
            ),
        ],
        relationships=[],
    )

    result_path = create_database_from_schema(schema, db_file)
    assert Path(result_path).exists()


def test_normalize_schema_reconciles_foreign_keys():
    raw_data = {
        "tables": [
            {
                "name": "Clienti",
                "columns": [
                    {"name": "CLI_ID", "data_type": "INTEGER", "primary_key": True},
                    {"name": "NOME", "data_type": "TEXT"},
                ],
            },
            {
                "name": "Ordini",
                "columns": [
                    {"name": "id", "data_type": "INTEGER", "pk": True},
                    {
                        "name": "cli_id",
                        "data_type": "INTEGER",
                        "foreign_key_table": "Clienti",
                        "foreign_key_column": "CLI_ID",
                    },
                    {
                        "name": "ghost_id",
                        "data_type": "INTEGER",
                        "foreign_key_table": "Fantasma",
                        "foreign_key_column": "id",
                    },
                ],
            },
        ],
        "relationships": [
            {
                "from_table": "Ordini",
                "from_column": "cli_id",
                "to_table": "Clienti",
                "to_column": "CLI_ID",
            }
        ],
    }

    norm = _normalize_schema(raw_data)
    assert norm["tables"][0]["name"] == "clienti"
    assert norm["tables"][1]["name"] == "ordini"

    # Foreign key to 'clienti' should be reconciled
    ordini_cols = {c["name"]: c for c in norm["tables"][1]["columns"]}
    assert ordini_cols["cli_id"]["is_foreign_key"] is True
    assert ordini_cols["cli_id"]["foreign_key_table"] == "clienti"
    assert ordini_cols["cli_id"]["foreign_key_column"] == "cli_id"

    # Ghost foreign key should be stripped
    assert ordini_cols["ghost_id"]["is_foreign_key"] is False
    assert ordini_cols["ghost_id"]["foreign_key_table"] is None

    # Relationship reconciled
    assert len(norm["relationships"]) == 1
    assert norm["relationships"][0]["from_table"] == "ordini"
    assert norm["relationships"][0]["to_table"] == "clienti"
    assert norm["relationships"][0]["to_column"] == "cli_id"
