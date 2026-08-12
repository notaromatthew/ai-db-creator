"""Apply application migrations without guessing how to transform unknown schemas.

Databases created by the current pre-Alembic application are stamped only after
their complete metadata is verified. The one historical Alembic schema is
recognized exactly and upgraded. Any other legacy layout fails closed.
"""

from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config import settings
from app.models.database import Base


ROOT = Path(__file__).resolve().parent
INITIAL_SIGNATURES = {
    "projects": {
        "columns": {
            "id": {"type": "String", "nullable": False}, "name": {"type": "String", "nullable": False},
            "prompt": {"type": "Text", "nullable": True}, "schema_json": {"type": "JSON", "nullable": True},
            "db_path": {"type": "String", "nullable": True}, "created_at": {"type": "DateTime", "nullable": True},
            "updated_at": {"type": "DateTime", "nullable": True},
        },
        "pk": ("id",), "fks": [], "indexes": [],
    },
    "documents": {
        "columns": {
            "id": {"type": "String", "nullable": False}, "project_id": {"type": "String", "nullable": False},
            "filename": {"type": "String", "nullable": False}, "file_type": {"type": "String", "nullable": False},
            "file_path": {"type": "String", "nullable": False}, "content_summary": {"type": "Text", "nullable": True},
            "created_at": {"type": "DateTime", "nullable": True},
        },
        "pk": ("id",), "fks": [(('project_id',), 'projects', ('id',))], "indexes": [],
    },
}


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


def _signature(inspector, table: str) -> dict:
    columns = {
        item["name"]: {
            "type": item["type"]._type_affinity.__name__,
            "nullable": bool(item["nullable"]),
        }
        for item in inspector.get_columns(table)
    }
    return {
        "columns": columns,
        "pk": tuple(inspector.get_pk_constraint(table).get("constrained_columns") or ()),
        "fks": sorted(
            (tuple(item.get("constrained_columns") or ()), item.get("referred_table"), tuple(item.get("referred_columns") or ()))
            for item in inspector.get_foreign_keys(table)
        ),
        "indexes": sorted(tuple(item.get("column_names") or ()) for item in inspector.get_indexes(table)),
    }


def _metadata_signature(table) -> dict:
    return {
        "columns": {
            column.name: {"type": column.type._type_affinity.__name__, "nullable": bool(column.nullable)}
            for column in table.columns
        },
        "pk": tuple(column.name for column in table.primary_key.columns),
        "fks": sorted(
            ((column.name,), foreign.column.table.name, (foreign.column.name,))
            for column in table.columns for foreign in column.foreign_keys
        ),
        "indexes": sorted(tuple(column.name for column in index.columns) for index in table.indexes),
    }


def migrate(database_url: str | None = None) -> str:
    target = database_url or settings.database_url
    engine = create_engine(target)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    config = _config(target)

    if "alembic_version" in tables:
        command.upgrade(config, "head")
        return "upgraded"

    application_tables = set(Base.metadata.tables)
    present_application_tables = tables & application_tables
    if not present_application_tables:
        command.upgrade(config, "head")
        return "initialized"

    is_current = application_tables == (tables - {"alembic_version"}) and all(
        _metadata_signature(Base.metadata.tables[table]) == _signature(inspector, table)
        for table in application_tables
    )
    if is_current:
        command.stamp(config, "head")
        return "stamped_current"

    is_historical_initial = tables == set(INITIAL_SIGNATURES) and all(
        _signature(inspector, table) == expected for table, expected in INITIAL_SIGNATURES.items()
    )
    if is_historical_initial:
        command.stamp(config, "c25c5721cbb9")
        command.upgrade(config, "head")
        return "upgraded_historical_initial"

    raise RuntimeError(
        "Database layout is neither the current schema nor a recognized historical revision; "
        "automatic migration refused. Restore a backup and provide a reviewed migration."
    )


if __name__ == "__main__":
    print(migrate())
