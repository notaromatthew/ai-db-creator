from sqlalchemy import create_engine, MetaData, Table, Column as SAColumn, Integer, String, Float, Boolean, Date, DateTime, Text, ForeignKey, UniqueConstraint, inspect, text
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef
from app.utils.exceptions import AppException
from app.utils.logger import log
from pathlib import Path
import os

TYPE_MAP = {
    "integer": Integer, "int": Integer, "text": Text, "varchar": String,
    "string": String, "real": Float, "float": Float, "double": Float,
    "boolean": Boolean, "bool": Boolean, "date": Date, "datetime": DateTime,
    "timestamp": DateTime,
}


def _map_type(sql_type: str):
    key = sql_type.lower().split("(")[0].strip()
    if key in TYPE_MAP:
        col_type = TYPE_MAP[key]
        if col_type == String and "(" in sql_type:
            length = int(sql_type.split("(")[1].split(")")[0])
            return String(length)
        return col_type
    return Text


def create_database_from_schema(schema: NormalizedSchema, db_path: str) -> str:
    log.info(f"Creating database at {db_path} with {len(schema.tables)} tables")
    engine = create_engine(f"sqlite:///{db_path}")
    metadata = MetaData()
    sqlalchemy_tables = []

    for table_def in schema.tables:
        cols = []
        for col_def in table_def.columns:
            col_type = _map_type(col_def.data_type)
            col_kwargs = {}
            if col_def.is_primary_key:
                col_kwargs["primary_key"] = True
            if col_def.is_foreign_key and col_def.foreign_key_table and col_def.foreign_key_column:
                col_kwargs["foreign_key"] = ForeignKey(f"{col_def.foreign_key_table}.{col_def.foreign_key_column}")
            if col_def.is_unique:
                col_kwargs["unique"] = True
            if col_def.is_not_null:
                col_kwargs["nullable"] = False
            col_type_kwargs = {**col_kwargs}
            cols.append(SAColumn(col_def.name, col_type, **col_type_kwargs))

        table = Table(table_def.name, metadata, *cols)
        sqlalchemy_tables.append(table)

    metadata.create_all(engine)
    engine.dispose()
    log.info(f"Created {len(sqlalchemy_tables)} tables")
    return db_path


def migrate_database(old_schema: NormalizedSchema, new_schema: NormalizedSchema, db_path: str) -> list[str]:
    """Migrate existing database from old_schema to new_schema, preserving data."""
    log.info(f"Migrating database at {db_path}")
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    changes = []

    new_table_names = {t.name for t in new_schema.tables}
    old_table_names = {t.name for t in old_schema.tables}

    with engine.connect() as conn:
        for table_def in new_schema.tables:
            if table_def.name not in existing_tables:
                metadata = MetaData()
                cols = []
                for col_def in table_def.columns:
                    col_type = _map_type(col_def.data_type)
                    col_kwargs = {}
                    if col_def.is_primary_key:
                        col_kwargs["primary_key"] = True
                    if col_def.is_foreign_key and col_def.foreign_key_table and col_def.foreign_key_column:
                        col_kwargs["foreign_key"] = ForeignKey(f"{col_def.foreign_key_table}.{col_def.foreign_key_column}")
                    if col_def.is_unique:
                        col_kwargs["unique"] = True
                    if col_def.is_not_null:
                        col_kwargs["nullable"] = False
                    cols.append(SAColumn(col_def.name, col_type, **col_kwargs))
                table = Table(table_def.name, metadata, *cols)
                metadata.create_all(engine)
                changes.append(f"Created table [{table_def.name}]")

            else:
                existing_cols = {c["name"] for c in inspector.get_columns(table_def.name)}
                for col_def in table_def.columns:
                    if col_def.name not in existing_cols:
                        col_type = _map_type(col_def.data_type)
                        nullable = not col_def.is_not_null
                        alter = f"ALTER TABLE [{table_def.name}] ADD COLUMN [{col_def.name}] {col_def.data_type}"
                        if not nullable:
                            alter += " NOT NULL DEFAULT ''"
                        conn.execute(text(alter))
                        changes.append(f"Added column [{col_def.name}] to [{table_def.name}]")

        conn.commit()

    log.info(f"Migration completed with {len(changes)} changes")
    return changes
