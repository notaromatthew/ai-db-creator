"""Cell-level population accuracy evaluation (RQ2).

Implements the methodology in ``docs/11-benchmark-protocol.md`` sections 4-6:
cell-by-cell comparison of a generated database against a ground-truth
database, using the gold-standard schema for table and column alignment.

Error codes (see protocol section 5):
- OK   exact match after type-appropriate normalisation
- TC   type-consistent (different representation, same value)
- NS   NULL in source (generated NULL where ground truth has a value)
- WV   wrong value (different non-null, non-consistent value)
- MR   missing row (ground-truth PK absent from generated)
- ER   extra row (generated PK absent from ground truth)
- FK   foreign-key violation (FK value with no matching PK in the referenced table)
- TM   type mismatch (value present but wrong data type)
"""
from __future__ import annotations

import json
import math
import sqlite3
from pathlib import Path
from typing import Any

from app.models.schema_models import NormalizedSchema

BOOLEAN_TRUE = {"true", "t", "1", "yes", "1.0"}
BOOLEAN_FALSE = {"false", "f", "0", "no", "0.0"}

NUMERIC_TYPES = {"INTEGER", "REAL", "NUMERIC", "FLOAT", "DOUBLE"}
DATETIME_TYPES = {"DATE", "DATETIME", "TIMESTAMP"}


def load_gold_schema(path: str | Path) -> NormalizedSchema:
    with Path(path).open(encoding="utf-8") as source:
        return NormalizedSchema.model_validate(json.load(source))


def connect_database(path: str | Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{Path(path).resolve().as_uri()}?mode=ro", uri=True)


def _normalise_numeric(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return str(int(number))
    return repr(number)


def _normalise_datetime(value: str) -> str | None:
    compact = value.strip().replace(" 00:00:00", "")
    if "-" not in compact:
        return None
    parts = compact.split(" ")[0].split("-")
    if len(parts) != 3:
        return None
    try:
        return f"{int(parts[0])}-{int(parts[1]):02d}-{int(parts[2]):02d}"
    except (TypeError, ValueError):
        return None


def normalise_value(value: Any, data_type: str) -> str | None:
    """Normalise a cell for comparison per protocol section 4.2."""
    if value is None:
        return None
    if isinstance(value, str):
        value = value.strip()
    upper_type = (data_type or "").upper()
    if upper_type in NUMERIC_TYPES:
        return _normalise_numeric(value)
    if upper_type == "BOOLEAN":
        lowered = str(value).strip().lower()
        if lowered in BOOLEAN_TRUE:
            return "true"
        if lowered in BOOLEAN_FALSE:
            return "false"
        return lowered
    if upper_type in DATETIME_TYPES:
        return _normalise_datetime(str(value))
    return value if isinstance(value, str) else str(value)


def _is_null(value: Any) -> bool:
    return value is None


def classify_cell(generated: Any, ground: Any, data_type: str) -> str:
    """Classify a single generated cell against the ground-truth cell."""
    if _is_null(generated) and _is_null(ground):
        return "OK"
    if _is_null(generated):
        return "NS"
    if _is_null(ground):
        return "WV"
    generated_normalised = normalise_value(generated, data_type)
    ground_normalised = normalise_value(ground, data_type)
    if generated_normalised is not None and generated_normalised == ground_normalised:
        return "OK" if generated == ground else "TC"
    upper_type = (data_type or "").upper()
    if upper_type in NUMERIC_TYPES | DATETIME_TYPES or upper_type == "BOOLEAN":
        if generated_normalised is None:
            return "TM"
    return "WV"


def wilson_ci(rate: float, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval for a proportion, per protocol section 7.3."""
    if n == 0:
        return (0.0, 1.0)
    p = rate
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * n)) / n) / denom
    return (centre - margin, centre + margin)


def _round_ci(ci: tuple[float, float]) -> list[float]:
    return [round(ci[0], 4), round(ci[1], 4)]


def read_rows(conn: sqlite3.Connection, table: Any,
              column_aliases: dict[str, str] | None = None,
              table_name: str | None = None) -> list[dict]:
    """Read all rows of a table as dicts keyed by column name.

    ``column_aliases`` maps gold column names to the column actually present in
    the database (used when a generated schema has diverged from the gold
    schema). Each aliased column is selected by its generated name but emitted
    under the gold name so downstream comparison keeps using gold names.
    """
    aliases = column_aliases or {}
    source_table = table_name or table.name
    selected = [(column.name, aliases.get(column.name, column.name))
                for column in table.columns]
    present = [name for name in _table_columns(conn, source_table)]
    usable = [(gold, gen) for gold, gen in selected if gen in present]
    if not usable:
        return []
    placeholders = ", ".join(f"[{gen}]" for _, gen in usable)
    cursor = conn.execute(f"SELECT {placeholders} FROM [{source_table}]")
    header = [description[0] for description in cursor.description]
    gold_names = [gold for gold, _ in usable]
    return [dict(zip(gold_names, row)) for row in cursor.fetchall()]


def _table_columns(conn: sqlite3.Connection, table_name: str) -> list[str]:
    return [row[1] for row in conn.execute(f"PRAGMA table_info([{table_name}])")]


def _build_fk_targets(conn: sqlite3.Connection, schema: NormalizedSchema) -> set[tuple[str, str, str]]:
    """Collect all valid (referenced_table, referenced_column, value) PKs for FK checks."""
    targets: set[tuple[str, str, str]] = set()
    for table in schema.tables:
        pk_columns = [c.name for c in table.columns if c.is_primary_key]
        for column in pk_columns:
            cursor = conn.execute(f"SELECT DISTINCT [{column}] FROM [{table.name}]")
            for (value,) in cursor.fetchall():
                if value is not None:
                    targets.add((table.name, column, str(value)))
    return targets


def _is_fk_violation(value: Any, fk_column: str, fk_table: str, targets: set[tuple[str, str, str]]) -> bool:
    if value is None:
        return False
    return (fk_table, fk_column, str(value)) not in targets


_BUSINESS_KEY_MARKER = "__business_key__"


def _row_key_value(value: Any, data_type: str) -> str:
    if isinstance(value, tuple) and value and value[0] == _BUSINESS_KEY_MARKER:
        return json.dumps(value, ensure_ascii=False, default=str)
    return _as_sortable(normalise_value(value, data_type))


def _foreign_key_business_maps(conn: sqlite3.Connection, schema: NormalizedSchema,
                               natural_keys: dict[str, list[str]],
                               column_aliases: dict[str, dict[str, str]],
                               table_aliases: dict[str, str]) -> dict[tuple[str, str], dict[str, tuple]]:
    maps: dict[tuple[str, str], dict[str, tuple]] = {}
    for table in schema.tables:
        business_columns = natural_keys.get(table.name) or []
        if not business_columns:
            continue
        schema_columns = {column.name: column for column in table.columns}
        if any(column not in schema_columns for column in business_columns):
            raise ValueError(f"Unknown natural-key columns for {table.name}: {business_columns}")
        primary_columns = [column for column in table.columns if column.is_primary_key]
        rows = read_rows(
            conn,
            table,
            column_aliases.get(table.name, {}),
            table_aliases.get(table.name, table.name),
        )
        for primary in primary_columns:
            values: dict[str, tuple] = {}
            for row in rows:
                raw_primary = row.get(primary.name)
                primary_key = _row_key_value(raw_primary, primary.data_type or "TEXT")
                business_key = tuple(
                    _row_key_value(row.get(name), schema_columns[name].data_type or "TEXT")
                    for name in business_columns
                )
                values[primary_key] = (_BUSINESS_KEY_MARKER, *business_key)
            maps[(table.name, primary.name)] = values
    return maps


def _replace_foreign_keys(rows: list[dict], table: Any,
                          business_maps: dict[tuple[str, str], dict[str, tuple]]) -> list[dict]:
    replaced: list[dict] = []
    for source_row in rows:
        row = dict(source_row)
        for column in table.columns:
            if not column.is_foreign_key:
                continue
            mapping = business_maps.get((column.foreign_key_table, column.foreign_key_column))
            if not mapping:
                continue
            lookup = _row_key_value(row.get(column.name), column.data_type or "TEXT")
            if lookup in mapping:
                row[column.name] = mapping[lookup]
        replaced.append(row)
    return replaced


def evaluate_table(generated_rows: list[dict], ground_rows: list[dict], table: Any,
                   fk_targets: set[tuple[str, str, str]],
                   natural_key_columns: list[str] | None = None,
                   observable_columns: list[str] | None = None,
                   observable_row_keys: list[list[Any]] | None = None) -> dict:
    """Compare rows of one table, keyed by primary key columns."""
    pk_columns = [column.name for column in table.columns if column.is_primary_key]
    schema_columns = [column.name for column in table.columns]
    if observable_columns is not None:
        invalid_columns = sorted(set(observable_columns) - set(schema_columns))
        if invalid_columns:
            raise ValueError(f"Unknown observable columns for {table.name}: {invalid_columns}")
        all_columns = list(observable_columns)
    else:
        all_columns = schema_columns
    column_types = {column.name: column.data_type for column in table.columns}
    fk_columns = {column.name: (column.foreign_key_table, column.foreign_key_column)
                  for column in table.columns if column.is_foreign_key}

    requested_keys = natural_key_columns or []
    invalid_keys = sorted(set(requested_keys) - set(schema_columns))
    if invalid_keys:
        raise ValueError(f"Unknown row-key columns for {table.name}: {invalid_keys}")
    key_cols = requested_keys or pk_columns or all_columns

    def row_key(row: dict) -> tuple:
        return tuple(_row_key_value(row.get(c), column_types.get(c) or "TEXT") for c in key_cols)

    if observable_row_keys is not None:
        allowed_keys = {
            tuple(_as_sortable(normalise_value(value, column_types.get(column) or "TEXT"))
                  for column, value in zip(key_cols, values))
            for values in observable_row_keys
        }
        generated_rows = [row for row in generated_rows if row_key(row) in allowed_keys]
        ground_rows = [row for row in ground_rows if row_key(row) in allowed_keys]

    generated_by_pk: dict[tuple, dict] = {}
    duplicate_generated: list[tuple[tuple, dict]] = []
    for row in generated_rows:
        key = row_key(row)
        if key in generated_by_pk:
            duplicate_generated.append((key, row))
        else:
            generated_by_pk[key] = row
    ground_by_pk: dict[tuple, dict] = {}
    duplicate_ground: list[tuple[tuple, dict]] = []
    for row in ground_rows:
        key = row_key(row)
        if key in ground_by_pk:
            duplicate_ground.append((key, row))
        else:
            ground_by_pk[key] = row

    matching_keys = set(generated_by_pk) & set(ground_by_pk)
    missing_keys = set(ground_by_pk) - matching_keys
    extra_keys = set(generated_by_pk) - matching_keys
    missing_rows = len(missing_keys)
    extra_rows = len(extra_keys) + len(duplicate_generated)
    discrepancies: list[dict] = []
    for key in sorted(missing_keys):
        discrepancies.append({
            "row_key": list(key), "column": None, "error_type": "MR",
            "generated_value": None, "ground_value": ground_by_pk[key],
        })
    for key in sorted(extra_keys):
        discrepancies.append({
            "row_key": list(key), "column": None, "error_type": "ER",
            "generated_value": generated_by_pk[key], "ground_value": None,
        })
    for key, row in duplicate_generated:
        discrepancies.append({
            "row_key": list(key), "column": None, "error_type": "DUPLICATE_KEY",
            "generated_value": row, "ground_value": generated_by_pk[key],
        })
    for key, row in duplicate_ground:
        discrepancies.append({
            "row_key": list(key), "column": None,
            "error_type": "AMBIGUOUS_GOLD_KEY", "generated_value": None,
            "ground_value": row,
        })

    counts = {"OK": 0, "TC": 0, "NS": 0, "WV": 0, "FK": 0, "TM": 0}
    total_cells = 0
    for key in matching_keys:
        generated = generated_by_pk[key]
        ground = ground_by_pk[key]
        for column in all_columns:
            total_cells += 1
            g_val = generated.get(column)
            t_val = ground.get(column)
            fk = fk_columns.get(column)
            if fk and not (isinstance(g_val, tuple) and g_val and g_val[0] == _BUSINESS_KEY_MARKER) \
                    and _is_fk_violation(g_val, fk[1], fk[0], fk_targets):
                counts["FK"] += 1
                discrepancies.append({
                    "row_key": list(key), "column": column, "error_type": "FK",
                    "generated_value": g_val, "ground_value": t_val,
                })
                continue
            classification = classify_cell(g_val, t_val, column_types.get(column) or "TEXT")
            counts[classification] += 1
            if classification != "OK":
                discrepancies.append({
                    "row_key": list(key), "column": column,
                    "error_type": classification, "generated_value": g_val,
                    "ground_value": t_val,
                })

    exact = counts["OK"]
    type_consistent = counts["TC"]
    tp = exact + type_consistent
    fp = counts["WV"] + counts["FK"] + counts["TM"]
    fn = counts["NS"] + missing_rows
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "exact": exact,
        "type_consistent": type_consistent,
        "null_in_source": counts["NS"],
        "wrong_value": counts["WV"],
        "fk_violations": counts["FK"],
        "type_mismatch": counts["TM"],
        "missing_rows": missing_rows,
        "extra_rows": extra_rows,
        "duplicate_generated_keys": len(duplicate_generated),
        "duplicate_ground_keys": len(duplicate_ground),
        "total_cells": total_cells,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "ci95_precision": _round_ci(wilson_ci(precision, tp + fp)),
        "ci95_recall": _round_ci(wilson_ci(recall, tp + fn)),
        "ci95_f1": _round_ci((f1, f1)),
        "row_key_columns": key_cols,
        "discrepancies": discrepancies,
    }


def _as_sortable(value: Any) -> str:
    if value is None:
        return "\x00"
    return str(value)


def evaluate_generated(generated_conn: sqlite3.Connection, ground_conn: sqlite3.Connection,
                       schema: NormalizedSchema,
                       column_aliases: dict[str, dict[str, str]] | None = None,
                       table_aliases: dict[str, str] | None = None,
                       natural_keys: dict[str, list[str]] | None = None,
                       observable_scope: dict | None = None) -> dict:
    """Run the full cell-level comparison over all tables in the gold schema.

    ``column_aliases`` maps ``gold_table -> {gold_column: generated_column}``
    so a generated schema whose names diverge from the gold schema (full-LLM
    condition) can still be compared cell-by-cell; see app/evaluation/
    schema_alignment.py. Tables/columns without an alias use gold names.
    """
    column_aliases = column_aliases or {}
    table_aliases = table_aliases or {}
    natural_keys = natural_keys or {}
    scope_tables = ((observable_scope or {}).get("tables") or {})
    excluded_tables = ((observable_scope or {}).get("excluded") or {})
    fk_targets = _build_fk_targets(ground_conn, schema)
    generated_business_maps = {}
    ground_business_maps = {}
    if observable_scope and natural_keys:
        generated_business_maps = _foreign_key_business_maps(
            generated_conn, schema, natural_keys, column_aliases, table_aliases
        )
        ground_business_maps = _foreign_key_business_maps(
            ground_conn, schema, natural_keys, {}, {}
        )
    per_table: dict[str, dict] = {}
    for table in schema.tables:
        if table.name in excluded_tables:
            continue
        scope = scope_tables.get(table.name, {})
        aliases = column_aliases.get(table.name, {})
        generated_rows = read_rows(
            generated_conn, table, aliases, table_aliases.get(table.name, table.name)
        )
        ground_rows = read_rows(ground_conn, table)
        if observable_scope and natural_keys:
            generated_rows = _replace_foreign_keys(generated_rows, table, generated_business_maps)
            ground_rows = _replace_foreign_keys(ground_rows, table, ground_business_maps)
        per_table[table.name] = evaluate_table(
            generated_rows, ground_rows, table, fk_targets,
            scope.get("key_columns") or natural_keys.get(table.name),
            scope.get("columns"), scope.get("row_keys"),
        )

    precisions = [t["precision"] for t in per_table.values()]
    recalls = [t["recall"] for t in per_table.values()]
    f1s = [t["f1"] for t in per_table.values()]

    def average(values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    return {
        "per_table": per_table,
        "global": {
            "precision": round(average(precisions), 4),
            "recall": round(average(recalls), 4),
            "f1": round(average(f1s), 4),
            "total_cells": sum(t["total_cells"] for t in per_table.values()),
            "missing_rows": sum(t["missing_rows"] for t in per_table.values()),
            "extra_rows": sum(t["extra_rows"] for t in per_table.values()),
        },
        "scope": {
            "mode": "observable" if observable_scope else "full_gold",
            "excluded_tables": excluded_tables,
        },
    }
