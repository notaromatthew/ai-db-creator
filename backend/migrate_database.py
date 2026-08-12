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
INITIAL_COLUMNS = {
    "projects": {"id", "name", "prompt", "schema_json", "db_path", "created_at", "updated_at"},
    "documents": {"id", "project_id", "filename", "file_type", "file_path", "content_summary", "created_at"},
}


def _config(database_url: str) -> Config:
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["database_url"] = database_url
    return config


def _columns(inspector, table: str) -> set[str]:
    return {column["name"] for column in inspector.get_columns(table)}


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

    is_current = application_tables <= tables and all(
        set(Base.metadata.tables[table].columns.keys()) <= _columns(inspector, table)
        for table in application_tables
    )
    if is_current:
        command.stamp(config, "head")
        return "stamped_current"

    is_historical_initial = present_application_tables == set(INITIAL_COLUMNS) and all(
        _columns(inspector, table) == expected for table, expected in INITIAL_COLUMNS.items()
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
