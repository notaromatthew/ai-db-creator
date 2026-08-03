import re
from app.models.schema_models import NormalizedSchema, TableDef, ColumnDef, RelationshipDef
from app.utils.logger import log

TYPE_MAP = {
    "int": "INTEGER", "integer": "INTEGER", "tinyint": "INTEGER", "smallint": "INTEGER",
    "bigint": "INTEGER", "serial": "INTEGER", "bigserial": "INTEGER",
    "varchar": "TEXT", "char": "TEXT", "nchar": "TEXT", "nvarchar": "TEXT",
    "text": "TEXT", "longtext": "TEXT", "mediumtext": "TEXT", "clob": "TEXT",
    "real": "REAL", "float": "REAL", "double": "REAL", "numeric": "REAL",
    "decimal": "REAL", "number": "REAL", "money": "REAL", "smallmoney": "REAL",
    "boolean": "INTEGER", "bool": "INTEGER", "bit": "INTEGER",
    "date": "TEXT", "datetime": "TEXT", "timestamp": "TEXT", "time": "TEXT",
    "year": "TEXT", "smalldatetime": "TEXT", "datetime2": "TEXT",
    "blob": "TEXT", "varbinary": "TEXT", "image": "TEXT",
    "uuid": "TEXT", "uniqueidentifier": "TEXT",
    "json": "TEXT", "jsonb": "TEXT",
}


def split_sql_statements(sql: str) -> list[str]:
    """Split on statement delimiters while preserving delimiters inside quoted values."""
    statements = []
    current = []
    quote = None
    index = 0
    pairs = {"[": "]", "'": "'", '"': '"', "`": "`"}
    while index < len(sql):
        char = sql[index]
        if quote:
            current.append(char)
            closing = pairs[quote]
            if char == closing:
                # SQL escapes single/double/backtick quotes by doubling them.
                if index + 1 < len(sql) and sql[index + 1] == closing and quote != "[":
                    current.append(sql[index + 1])
                    index += 1
                else:
                    quote = None
        elif char in pairs:
            quote = char
            current.append(char)
        elif char == ";":
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
        else:
            current.append(char)
        index += 1
    trailing = "".join(current).strip()
    if trailing:
        statements.append(trailing)
    return statements

def _clean_sql(sql: str, dialect: str) -> str:
    sql = re.sub(r"--[^\n]*", "", sql)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = re.sub(r"ENGINE\s*=\s*\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"AUTO_INCREMENT", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"UNSIGNED", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"COLLATE\s+\S+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"CHARACTER\s+SET\s+\S+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"USING\s+\w+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"ON\s+UPDATE\s+CURRENT_(?:TIMESTAMP|DATE)", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"ON\s+DELETE\s+(?:CASCADE|SET\s+NULL|RESTRICT|NO\s+ACTION)", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"`", "", sql)
    sql = re.sub(r'\[(\w+)\]', r'\1', sql)
    sql = re.sub(r'"(\w+)"', r'\1', sql)
    return sql.strip()

def _clean_create(sql: str) -> str:
    sql = re.sub(r"IF\s+NOT\s+EXISTS\s+", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"TEMPORARY\s+", "", sql, flags=re.IGNORECASE)
    return sql.strip()

def _map_col_type(raw: str) -> str:
    raw = raw.strip().lower()
    raw = re.sub(r"\(.*?\)", "", raw).strip()
    for k, v in TYPE_MAP.items():
        if raw.startswith(k):
            return v
    return "TEXT"

def _parse_create_table(stmt: str) -> TableDef | None:
    stmt = _clean_create(stmt)
    m = re.match(r"CREATE\s+TABLE\s+(\S+)\s*\((.*)\)\s*;?\s*$", stmt, re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    table_name = m.group(1).strip()
    body = m.group(2).strip()
    lines = _split_column_defs(body)

    columns = []
    pk_cols = []
    fk_list = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("PRIMARY KEY"):
            pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", line, re.IGNORECASE)
            if pk_match:
                pk_cols = [c.strip().strip('"`[]') for c in pk_match.group(1).split(",")]
            continue

        if line.upper().startswith("FOREIGN KEY"):
            fk = _parse_fk(line)
            if fk:
                fk_list.append(fk)
            continue

        if line.upper().startswith("UNIQUE"):
            continue

        if line.upper().startswith("CHECK"):
            continue

        if line.upper().startswith("INDEX") or line.upper().startswith("KEY"):
            continue

        if line.upper().startswith("CONSTRAINT"):
            inner = re.sub(r"CONSTRAINT\s+\S+\s+", "", line, flags=re.IGNORECASE).strip()
            if inner.upper().startswith("FOREIGN KEY"):
                fk = _parse_fk(inner)
                if fk:
                    fk_list.append(fk)
            elif inner.upper().startswith("PRIMARY KEY"):
                pk_match = re.search(r"PRIMARY\s+KEY\s*\(([^)]+)\)", inner, re.IGNORECASE)
                if pk_match:
                    pk_cols = [c.strip().strip('"`[]') for c in pk_match.group(1).split(",")]
            continue

        col = _parse_column_def(line)
        if col:
            columns.append(col)

    for c in columns:
        if c.name in pk_cols:
            c.is_primary_key = True

    for fk in fk_list:
        for c in columns:
            if c.name == fk["col"]:
                c.is_foreign_key = True
                c.foreign_key_table = fk["ref_table"]
                c.foreign_key_column = fk["ref_col"]

    return TableDef(name=table_name, columns=columns)

def _parse_column_def(line: str) -> ColumnDef | None:
    m = re.match(r"(\w+)\s+(.+?)(?:\s+(NOT\s+NULL|NULL))?(?:\s+PRIMARY\s+KEY)?(?:\s+UNIQUE)?(?:\s+DEFAULT\s+(\S+))?(?:\s+REFERENCES\s+(\w+)\s*\((\w+)\))?\s*$", line, re.IGNORECASE)
    if not m:
        m2 = re.match(r"(\w+)\s+(.+?)(?:\s+(NOT\s+NULL|NULL))?\s*$", line, re.IGNORECASE)
        if not m2:
            return None
        col_name = m2.group(1)
        raw_type = m2.group(2)
        not_null = m2.group(3)
        col_type = _map_col_type(raw_type)
        return ColumnDef(
            name=col_name,
            data_type=col_type,
            is_not_null=not_null is not None and not_null.upper() == "NOT NULL",
        )

    col_name = m.group(1)
    raw_type = m.group(2)
    not_null = m.group(3)
    col_type = _map_col_type(raw_type)

    is_pk = "PRIMARY KEY" in line.upper()
    is_uq = "UNIQUE" in line.upper()

    default_raw = m.group(4) if m.lastindex >= 4 else None
    default_val = default_raw.strip("'\"") if default_raw else None

    ref_table = m.group(5) if m.lastindex >= 5 else None
    ref_col = m.group(6) if m.lastindex >= 6 else None

    nn = not_null is not None and not_null.upper() == "NOT NULL"

    return ColumnDef(
        name=col_name,
        data_type=col_type,
        is_primary_key=is_pk or False,
        is_not_null=nn or is_pk,
        is_unique=is_uq or False,
        default_value=default_val,
        is_foreign_key=bool(ref_table),
        foreign_key_table=ref_table,
        foreign_key_column=ref_col,
    )

def _parse_fk(line: str) -> dict | None:
    m = re.search(r"FOREIGN\s+KEY\s*\((\w+)\)\s*REFERENCES\s+(\w+)\s*\((\w+)\)", line, re.IGNORECASE)
    if m:
        return {"col": m.group(1), "ref_table": m.group(2), "ref_col": m.group(3)}
    return None

def _split_column_defs(body: str) -> list[str]:
    parts = []
    depth = 0
    cur = ""
    for ch in body:
        if ch in "(":
            depth += 1
        elif ch in ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts

def _build_relationships(tables: list[TableDef]) -> list[RelationshipDef]:
    rels = []
    for t in tables:
        for c in t.columns:
            if c.is_foreign_key and c.foreign_key_table and c.foreign_key_column:
                rels.append(RelationshipDef(
                    type="one_to_many",
                    from_table=c.foreign_key_table,
                    from_column=c.foreign_key_column,
                    to_table=t.name,
                    to_column=c.name,
                ))
    return rels

def extract_schema(sql: str, dialect: str) -> NormalizedSchema:
    sql = _clean_sql(sql, dialect)
    statements = split_sql_statements(sql)
    tables = []
    for stmt in statements:
        if re.match(r"CREATE\s+TABLE", stmt, re.IGNORECASE):
            td = _parse_create_table(stmt)
            if td:
                tables.append(td)
    rels = _build_relationships(tables)
    return NormalizedSchema(tables=tables, relationships=rels)

def clean_inserts(sql: str, dialect: str) -> str:
    sql = _clean_sql(sql, dialect)
    statements = split_sql_statements(sql)
    cleaned = []
    for stmt in statements:
        if re.match(r"INSERT\s+INTO", stmt, re.IGNORECASE):
            cleaned.append(stmt)
    return ";\n".join(cleaned) + ";"
