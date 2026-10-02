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


def _resolve_foreign_keys(schema: NormalizedSchema):
    """Build case-insensitive resolution lookup for tables and columns."""
    valid_tables: dict[str, str] = {}
    valid_cols: dict[str, dict[str, str]] = {}
    table_pks: dict[str, str] = {}

    for table_def in schema.tables:
        t_key = table_def.name.strip().lower()
        valid_tables[t_key] = table_def.name
        valid_cols[t_key] = {}
        for col in table_def.columns:
            c_key = col.name.strip().lower()
            valid_cols[t_key][c_key] = col.name
            if col.is_primary_key and t_key not in table_pks:
                table_pks[t_key] = col.name
        if t_key not in table_pks and table_def.columns:
            table_pks[t_key] = table_def.columns[0].name

    return valid_tables, valid_cols, table_pks


def create_database_from_schema(schema: NormalizedSchema, db_path: str) -> str:
    log.info(f"Creating database at {db_path} with {len(schema.tables)} tables")
    valid_tables, valid_cols, table_pks = _resolve_foreign_keys(schema)

    def _build_metadata(include_fks: bool = True) -> tuple[MetaData, list[Table]]:
        metadata = MetaData()
        sqla_tables = []
        for table_def in schema.tables:
            cols = []
            for col_def in table_def.columns:
                col_type = _map_type(col_def.data_type)
                col_args = []
                col_kwargs = {}
                if col_def.is_primary_key:
                    col_kwargs["primary_key"] = True
                if include_fks and col_def.is_foreign_key and col_def.foreign_key_table and col_def.foreign_key_column:
                    fk_tbl_key = col_def.foreign_key_table.strip().lower()
                    fk_col_key = col_def.foreign_key_column.strip().lower()
                    if fk_tbl_key in valid_tables:
                        target_tbl = valid_tables[fk_tbl_key]
                        target_col = valid_cols[fk_tbl_key].get(fk_col_key) or table_pks.get(fk_tbl_key)
                        if target_col:
                            col_args.append(ForeignKey(f"{target_tbl}.{target_col}"))
                        else:
                            log.warning(f"FK target column '{col_def.foreign_key_column}' not found in table '{target_tbl}', omitting constraint")
                    else:
                        log.warning(f"FK target table '{col_def.foreign_key_table}' not found in schema, omitting constraint")
                if col_def.is_unique:
                    col_kwargs["unique"] = True
                if col_def.is_not_null:
                    col_kwargs["nullable"] = False
                cols.append(SAColumn(col_def.name, col_type, *col_args, **col_kwargs))

            table = Table(table_def.name, metadata, *cols)
            sqla_tables.append(table)
        return metadata, sqla_tables

    engine = create_engine(f"sqlite:///{db_path}")
    try:
        metadata, sqlalchemy_tables = _build_metadata(include_fks=True)
        metadata.create_all(engine)
    except Exception as e:
        log.warning(f"Error creating tables with foreign keys: {e}. Retrying without foreign keys.")
        metadata, sqlalchemy_tables = _build_metadata(include_fks=False)
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
                valid_tables, valid_cols, table_pks = _resolve_foreign_keys(new_schema)
                for col_def in table_def.columns:
                    col_type = _map_type(col_def.data_type)
                    col_args = []
                    col_kwargs = {}
                    if col_def.is_primary_key:
                        col_kwargs["primary_key"] = True
                    if col_def.is_foreign_key and col_def.foreign_key_table and col_def.foreign_key_column:
                        fk_tbl_key = col_def.foreign_key_table.strip().lower()
                        fk_col_key = col_def.foreign_key_column.strip().lower()
                        if fk_tbl_key in valid_tables:
                            target_tbl = valid_tables[fk_tbl_key]
                            target_col = valid_cols.get(fk_tbl_key, {}).get(fk_col_key) or table_pks.get(fk_tbl_key)
                            if target_col and (target_tbl in existing_tables or target_tbl == table_def.name):
                                col_args.append(ForeignKey(f"{target_tbl}.{target_col}"))
                    if col_def.is_unique:
                        col_kwargs["unique"] = True
                    if col_def.is_not_null:
                        col_kwargs["nullable"] = False
                    cols.append(SAColumn(col_def.name, col_type, *col_args, **col_kwargs))
                table = Table(table_def.name, metadata, *cols)
                try:
                    metadata.create_all(engine)
                except Exception as e:
                    log.warning(f"Failed to create table {table_def.name} with foreign keys: {e}. Retrying without FKs.")
                    metadata = MetaData()
                    cols_no_fk = [SAColumn(c.name, _map_type(c.data_type), primary_key=c.is_primary_key, unique=c.is_unique, nullable=not c.is_not_null) for c in table_def.columns]
                    Table(table_def.name, metadata, *cols_no_fk)
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
