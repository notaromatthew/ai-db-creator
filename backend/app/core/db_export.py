from app.models.schema_models import NormalizedSchema
from app.utils.logger import log
from sqlalchemy import create_engine, inspect, text
from datetime import date, datetime

TYPE_MAP = {
    "integer":  {"sqlite": "INTEGER", "postgresql": "INTEGER", "mysql": "INT", "mssql": "INT"},
    "int":      {"sqlite": "INTEGER", "postgresql": "INTEGER", "mysql": "INT", "mssql": "INT"},
    "text":     {"sqlite": "TEXT",    "postgresql": "TEXT",    "mysql": "TEXT",   "mssql": "NVARCHAR(MAX)"},
    "varchar":  {"sqlite": "TEXT",    "postgresql": "VARCHAR", "mysql": "VARCHAR","mssql": "NVARCHAR"},
    "string":   {"sqlite": "TEXT",    "postgresql": "TEXT",    "mysql": "TEXT",   "mssql": "NVARCHAR(MAX)"},
    "real":     {"sqlite": "REAL",    "postgresql": "REAL",    "mysql": "FLOAT",  "mssql": "FLOAT"},
    "float":    {"sqlite": "REAL",    "postgresql": "REAL",    "mysql": "FLOAT",  "mssql": "FLOAT"},
    "double":   {"sqlite": "REAL",    "postgresql": "DOUBLE PRECISION", "mysql": "DOUBLE", "mssql": "FLOAT"},
    "boolean":  {"sqlite": "INTEGER", "postgresql": "BOOLEAN", "mysql": "TINYINT(1)", "mssql": "BIT"},
    "bool":     {"sqlite": "INTEGER", "postgresql": "BOOLEAN", "mysql": "TINYINT(1)", "mssql": "BIT"},
    "date":     {"sqlite": "TEXT",    "postgresql": "DATE",    "mysql": "DATE",   "mssql": "DATE"},
    "datetime": {"sqlite": "TEXT",    "postgresql": "TIMESTAMP", "mysql": "DATETIME", "mssql": "DATETIME2"},
    "timestamp":{"sqlite": "TEXT",    "postgresql": "TIMESTAMP", "mysql": "DATETIME", "mssql": "DATETIME2"},
}

def _resolve_type(raw: str, dialect: str) -> str:
    key = raw.lower().split("(")[0].strip()
    base = TYPE_MAP.get(key, TYPE_MAP["text"])
    mapped = base.get(dialect, base["sqlite"])

    if key in ("varchar", "string") and "(" in raw:
        try:
            length = raw.split("(")[1].split(")")[0]
            if dialect == "mssql" and key == "varchar":
                return f"NVARCHAR({length})"
            return f"{mapped}({length})"
        except (IndexError, ValueError):
            pass
    return mapped

def _escape_val(val, dialect: str) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, bool):
        if dialect == "postgresql":
            return "TRUE" if val else "FALSE"
        return "1" if val else "0"
    if isinstance(val, (int, float)):
        return str(val)
    if isinstance(val, (date, datetime)):
        s = val.isoformat()
        return f"'{s}'"
    s = str(val)
    if dialect in ("mysql", "mssql"):
        s = s.replace("'", "''").replace("\\", "\\\\")
    else:
        s = s.replace("'", "''")
    return f"'{s}'"

def _generate_create_table(table_def, dialect: str, schema: NormalizedSchema) -> str:
    lines = []
    pk_cols = []
    fk_lines = []

    for col in table_def.columns:
        col_type = _resolve_type(col.data_type, dialect)
        parts = [f"  {col.name} {col_type}"]
        if col.is_primary_key:
            pk_cols.append(col.name)
        if col.is_not_null:
            parts.append("NOT NULL")
        if col.is_unique and not col.is_primary_key:
            parts.append("UNIQUE")
        if col.default_value:
            default = col.default_value
            if default.upper() not in ("NULL", "CURRENT_TIMESTAMP", "CURRENT_DATE", "CURRENT_TIME"):
                default = f"'{default}'"
            parts.append(f"DEFAULT {default}")
        lines.append(" ".join(parts))

    if len(pk_cols) == 1:
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{pk_cols[0]} "):
                lines[i] += " PRIMARY KEY"
                break
    elif len(pk_cols) > 1:
        lines.append(f"  PRIMARY KEY ({', '.join(pk_cols)})")

    for col in table_def.columns:
        if col.is_foreign_key and col.foreign_key_table and col.foreign_key_column:
            fk = f"  FOREIGN KEY ({col.name}) REFERENCES {col.foreign_key_table}({col.foreign_key_column})"
            if dialect == "mssql":
                fk = f"  CONSTRAINT FK_{table_def.name}_{col.name} FOREIGN KEY ({col.name}) REFERENCES {col.foreign_key_table}({col.foreign_key_column})"
            fk_lines.append(fk)

    lines.extend(fk_lines)
    return f"CREATE TABLE {table_def.name} (\n" + ",\n".join(lines) + "\n);"

def export_full(dialect: str, db_path: str, schema: NormalizedSchema) -> str:
    engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(engine)
    parts = []

    parts.append(f"-- Exported for {dialect}")
    parts.append("")

    if dialect in ("postgresql", "mysql", "mssql"):
        parts.append("-- DROP existing tables (reverse FK order)")
        for t in reversed(schema.tables):
            parts.append(f"DROP TABLE IF EXISTS {t.name};")
        parts.append("")

    for table in schema.tables:
        parts.append(_generate_create_table(table, dialect, schema))
        parts.append("")

    with engine.connect() as conn:
        for table in schema.tables:
            rows = conn.execute(text(f"SELECT * FROM [{table.name}]")).fetchall()
            col_names = [c["name"] for c in inspector.get_columns(table.name)]
            if not rows:
                continue
            parts.append(f"-- Data for {table.name}")
            for row in rows:
                vals = ", ".join(_escape_val(v, dialect) for v in row)
                parts.append(f"INSERT INTO {table.name} ({', '.join(col_names)}) VALUES ({vals});")
            parts.append("")

    return "\n".join(parts)
