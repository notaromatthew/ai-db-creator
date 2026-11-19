"""Frozen functional-query evaluation for RQ2 database populations."""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from app.utils.research import sha256_file, stable_hash


def load_evaluation_spec(dataset_dir: str | Path) -> tuple[dict, str | None]:
    path = Path(dataset_dir) / "evaluation_spec.json"
    if not path.is_file():
        return {}, None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or not isinstance(value.get("functional_queries", []), list):
        raise ValueError(f"Invalid RQ2 evaluation specification: {path}")
    query_ids = [str(query.get("id") or "").strip()
                 for query in value.get("functional_queries", []) if isinstance(query, dict)]
    if len(query_ids) != len(value.get("functional_queries", [])) or any(not item for item in query_ids):
        raise ValueError(f"Functional query IDs must be non-empty: {path}")
    if len(query_ids) != len(set(query_ids)):
        raise ValueError(f"Functional query IDs must be unique: {path}")
    for query in value.get("functional_queries", []):
        _read_only_sql(str(query.get("sql") or ""))
        if query.get("generated_sql"):
            _read_only_sql(str(query["generated_sql"]))
    thresholds = value.get("functional_equivalence") or {}
    for key in ("min_overall_query_pass_rate", "min_critical_query_pass_rate",
                "overall_query_pass_rate", "critical_query_pass_rate"):
        if key in thresholds and not 0 <= float(thresholds[key]) <= 1:
            raise ValueError(f"{key} must be between 0 and 1: {path}")
    return value, sha256_file(path)


def _read_only_sql(sql: str) -> str:
    statement = sql.strip().rstrip(";").strip()
    lowered = re.sub(r"\s+", " ", statement.lower())
    if not (lowered.startswith("select ") or lowered.startswith("with ")):
        raise ValueError("functional queries must be SELECT/CTE statements")
    if ";" in statement or re.search(
        r"\b(insert|update|delete|drop|alter|create|attach|detach|pragma|vacuum|replace)\b",
        lowered,
    ):
        raise ValueError("functional queries must be read-only")
    return statement


def rewrite_query(sql: str, alignment: dict | None) -> str:
    alignment = alignment or {}
    tables = alignment.get("tables") or {}
    columns = alignment.get("columns") or {}
    rewritten = sql
    aliases: dict[str, str] = {}
    for gold_table in tables:
        match = re.search(
            rf"\b(?:from|join)\s+{re.escape(gold_table)}(?:\s+(?:as\s+)?([A-Za-z_]\w*))?",
            sql, flags=re.IGNORECASE,
        )
        alias = match.group(1) if match and match.group(1) \
            and match.group(1).lower() not in {"on", "where", "group", "order", "join"} \
            else gold_table
        aliases[gold_table] = alias
    for gold_table, alias in aliases.items():
        for gold_column, generated_column in sorted(
            (columns.get(gold_table) or {}).items(), key=lambda item: -len(item[0])
        ):
            rewritten = re.sub(
                rf"\b{re.escape(alias)}\s*\.\s*{re.escape(gold_column)}\b",
                f"[{alias}].[{generated_column}]", rewritten, flags=re.IGNORECASE,
            )
    for gold_table, generated_table in sorted(tables.items(), key=lambda item: -len(item[0])):
        for gold_column, generated_column in sorted(
            (columns.get(gold_table) or {}).items(), key=lambda item: -len(item[0])
        ):
            pattern = rf"\b{re.escape(gold_table)}\s*\.\s*{re.escape(gold_column)}\b"
            rewritten = re.sub(pattern, f"[{generated_table}].[{generated_column}]", rewritten,
                               flags=re.IGNORECASE)
    for gold_table, generated_table in sorted(tables.items(), key=lambda item: -len(item[0])):
        rewritten = re.sub(rf"\b{re.escape(gold_table)}\b", f"[{generated_table}]", rewritten,
                           flags=re.IGNORECASE)
    unambiguous: dict[str, str] = {}
    ambiguous: set[str] = set()
    for mapping in columns.values():
        for gold_column, generated_column in mapping.items():
            if gold_column in unambiguous and unambiguous[gold_column] != generated_column:
                ambiguous.add(gold_column)
            else:
                unambiguous[gold_column] = generated_column
    for gold_column in ambiguous:
        unambiguous.pop(gold_column, None)
    for gold_column, generated_column in sorted(unambiguous.items(), key=lambda item: -len(item[0])):
        rewritten = re.sub(rf"(?<![.\w]){re.escape(gold_column)}\b", f"[{generated_column}]",
                           rewritten, flags=re.IGNORECASE)
    return rewritten


def _canonical_value(value: Any, rules: dict, column_name: str = "") -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.hex()
    if isinstance(value, str):
        unicode_form = str(rules.get("unicode") or "").strip()
        if unicode_form:
            value = unicodedata.normalize(unicode_form, value)
        text_rules = rules.get("text") or {}
        if text_rules.get("trim", rules.get("trim_strings", True)):
            value = value.strip()
        if text_rules.get("collapse_whitespace", False):
            value = re.sub(r"\s+", " ", value)
        if value.casefold() in {str(v).casefold() for v in rules.get("null_tokens", [])}:
            return None
        for fmt in rules.get("date_formats", ["%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"]):
            try:
                parsed = datetime.strptime(value, fmt)
                return {"date": parsed.isoformat(sep=" ") if "%H" in fmt else parsed.date().isoformat()}
            except ValueError:
                pass
        insensitive = {str(item).casefold() for item in rules.get("case_insensitive_columns", [])}
        case_sensitive = text_rules.get("case_sensitive", not rules.get("casefold_strings", False))
        if not case_sensitive or column_name.casefold() in insensitive:
            value = value.casefold()
    if isinstance(value, (int, float, Decimal)) or (
        isinstance(value, str) and re.fullmatch(r"[-+]?\d+(?:\.\d+)?", value)
    ):
        try:
            number = Decimal(str(value))
            numeric_rules = rules.get("numeric") or {}
            tolerance = Decimal(str(numeric_rules.get(
                "absolute_tolerance", rules.get("numeric_tolerance", "0")
            )))
            if tolerance > 0:
                number = (number / tolerance).quantize(Decimal("1")) * tolerance
            return {"number": format(number.normalize(), "f")}
        except (InvalidOperation, ValueError):
            pass
    return value


def _query_rows(conn: sqlite3.Connection, sql: str, rules: dict) -> list[list[Any]]:
    cursor = conn.execute(_read_only_sql(sql))
    columns = [item[0] for item in cursor.description]
    rows = [[_canonical_value(value, rules, columns[index]) for index, value in enumerate(row)]
            for row in cursor.fetchall()]
    return sorted(rows, key=lambda row: json.dumps(row, sort_keys=True, ensure_ascii=False))


def _row_differences(gold_rows: list[list[Any]], generated_rows: list[list[Any]]) -> tuple[list, list]:
    def encoded(rows):
        return Counter(json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows)

    gold = encoded(gold_rows)
    generated = encoded(generated_rows)
    missing = [json.loads(row) for row, count in (gold - generated).items() for _ in range(count)]
    extra = [json.loads(row) for row, count in (generated - gold).items() for _ in range(count)]
    return missing, extra


def _quote_identifier(value: str) -> str:
    return "[" + value.replace("]", "]]") + "]"


def _integrity_checks(conn: sqlite3.Connection, spec: dict,
                      alignment: dict | None) -> dict:
    alignment = alignment or {}
    tables = alignment.get("tables") or {}
    columns = alignment.get("columns") or {}
    fk_violations = [list(row) for row in conn.execute("PRAGMA foreign_key_check").fetchall()]
    duplicate_groups: list[dict] = []
    errors: list[str] = []
    for gold_table, gold_columns in (spec.get("natural_keys") or {}).items():
        table = tables.get(gold_table, gold_table)
        mapped = [columns.get(gold_table, {}).get(column, column) for column in gold_columns]
        try:
            selected = ", ".join(_quote_identifier(column) for column in mapped)
            sql = (
                f"SELECT {selected}, COUNT(*) AS duplicate_count "
                f"FROM {_quote_identifier(table)} GROUP BY {selected} HAVING COUNT(*) > 1"
            )
            for row in conn.execute(sql).fetchall():
                duplicate_groups.append({
                    "table": gold_table,
                    "key_columns": list(gold_columns),
                    "key": list(row[:-1]),
                    "count": row[-1],
                })
        except sqlite3.Error as exc:
            errors.append(f"{gold_table}: {type(exc).__name__}: {exc}")
    return {
        "foreign_key_violations": fk_violations,
        "natural_key_duplicate_groups": duplicate_groups,
        "errors": errors,
        "violation_count": len(fk_violations) + len(duplicate_groups) + len(errors),
    }


def evaluate_functional_queries(generated_conn: sqlite3.Connection,
                                ground_conn: sqlite3.Connection,
                                spec: dict, alignment: dict | None = None) -> dict:
    rules = spec.get("canonicalization") or {}
    results: list[dict] = []
    for query in spec.get("functional_queries", []):
        query_id = str(query.get("id") or "").strip()
        sql = str(query.get("sql") or "").strip()
        critical = bool(query.get("critical", False))
        result = {"id": query_id, "critical": critical, "passed": False,
                  "gold_sql": sql, "generated_sql": None, "error": None}
        try:
            generated_sql = str(query.get("generated_sql") or "").strip() \
                or rewrite_query(sql, alignment)
            result["generated_sql"] = generated_sql
            gold_rows = _query_rows(ground_conn, sql, rules)
            generated_rows = _query_rows(generated_conn, generated_sql, rules)
            missing_rows, extra_rows = _row_differences(gold_rows, generated_rows)
            result.update({
                "passed": generated_rows == gold_rows,
                "gold_rows": gold_rows,
                "generated_rows": generated_rows,
                "gold_result_hash": stable_hash(gold_rows),
                "generated_result_hash": stable_hash(generated_rows),
                "gold_row_count": len(gold_rows),
                "generated_row_count": len(generated_rows),
                "missing_rows": missing_rows,
                "extra_rows": extra_rows,
            })
        except (sqlite3.Error, ValueError) as exc:
            result["error"] = f"{type(exc).__name__}: {exc}"
        results.append(result)

    critical_results = [item for item in results if item["critical"]]
    passed = sum(1 for item in results if item["passed"])
    critical_passed = sum(1 for item in critical_results if item["passed"])
    overall_rate = passed / len(results) if results else None
    critical_rate = critical_passed / len(critical_results) if critical_results else None
    thresholds = spec.get("functional_equivalence") or {}
    min_overall = float(thresholds.get(
        "min_overall_query_pass_rate", thresholds.get("overall_query_pass_rate", 0.9)
    ))
    min_critical = float(thresholds.get(
        "min_critical_query_pass_rate", thresholds.get("critical_query_pass_rate", 1.0)
    ))
    integrity = _integrity_checks(generated_conn, spec, alignment)
    max_integrity = int(thresholds.get("max_critical_integrity_violations", 0))
    decision = None if not results else (
        overall_rate >= min_overall
        and (critical_rate is None or critical_rate >= min_critical)
        and integrity["violation_count"] <= max_integrity
    )
    return {
        "spec_version": spec.get("version"),
        "queries": results,
        "total_queries": len(results),
        "passed_queries": passed,
        "overall_query_pass_rate": overall_rate,
        "critical_query_pass_rate": critical_rate,
        "thresholds": {
            "min_overall_query_pass_rate": min_overall,
            "min_critical_query_pass_rate": min_critical,
            "max_critical_integrity_violations": max_integrity,
        },
        "integrity": integrity,
        "functionally_equivalent": decision,
    }
