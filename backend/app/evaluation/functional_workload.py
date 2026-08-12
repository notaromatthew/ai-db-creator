"""Deterministic supplementary functional-equivalence workload evaluation."""
from __future__ import annotations

import json
import sqlite3
from collections import Counter
from pathlib import Path
from typing import Any

from app.utils.research import stable_hash

EVALUATOR_VERSION = "functional-workload-v1"


def canonical_value(value: Any) -> tuple[str, str | None]:
    if value is None:
        return ("null", None)
    if isinstance(value, bool):
        return ("boolean", "true" if value else "false")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        return ("number", str(int(number)) if number.is_integer() else repr(number))
    return ("text", str(value).strip())


def canonical_result(columns: list[str], rows: list[tuple]) -> Counter:
    names = tuple(str(name) for name in columns)
    return Counter(tuple((names[index], canonical_value(value)) for index, value in enumerate(row)) for row in rows)


def canonical_cells(columns: list[str], rows: list[tuple]) -> Counter:
    """Represent answer cells as position-independent typed facts, preserving duplicates."""
    names = tuple(str(name) for name in columns)
    return Counter((name, canonical_value(row[index])) for row in rows for index, name in enumerate(names))


def _score(predicted: Counter, expected: Counter) -> dict:
    tp = sum((predicted & expected).values())
    fp = sum((predicted - expected).values())
    fn = sum((expected - predicted).values())
    return _score_counts(tp, fp, fn)


def _score_counts(tp: int, fp: int, fn: int) -> dict:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4),
            "recall": round(recall, 4), "f1": round(f1, 4)}


def load_workload(dataset_dir: Path) -> dict:
    path = dataset_dir / "functional_workload.json"
    config = json.loads(path.read_text(encoding="utf-8"))
    config["config_hash"] = stable_hash({k: v for k, v in config.items() if k not in {"config_hash", "freeze"}})
    return config


def evaluate_workload(conn: sqlite3.Connection, workload: dict) -> dict:
    approval = workload.get("approval_status", "draft")
    freeze = workload.get("freeze") if isinstance(workload.get("freeze"), dict) else {}
    computed_config_hash = stable_hash({k: v for k, v in workload.items() if k not in {"config_hash", "freeze"}})
    frozen = (approval == "frozen" and bool(freeze.get("approved_at")) and bool(freeze.get("approved_by"))
              and freeze.get("config_hash") == computed_config_hash)
    query_reports = []
    totals = Counter()
    cell_totals = Counter()
    successful = 0
    exact_matches = 0
    for query in workload.get("queries", []):
        expected_rows = [tuple(row) for row in query.get("expected", {}).get("rows", [])]
        expected_columns = query.get("expected", {}).get("columns", [])
        try:
            denied = {sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE,
                      sqlite3.SQLITE_CREATE_TABLE, sqlite3.SQLITE_DROP_TABLE, sqlite3.SQLITE_ALTER_TABLE,
                      sqlite3.SQLITE_TRANSACTION, sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH,
                      sqlite3.SQLITE_PRAGMA}
            conn.set_authorizer(lambda action, _a, _b, _db, _src: sqlite3.SQLITE_DENY if action in denied else sqlite3.SQLITE_OK)
            cursor = conn.execute(query["sql"])
            columns = [item[0] for item in cursor.description or []]
            predicted_rows = cursor.fetchall()
            ordered = bool(query.get("ordered", False))
            predicted = canonical_result(columns, predicted_rows)
            expected = canonical_result(expected_columns, expected_rows)
            if ordered:
                predicted_sequence = [tuple((columns[i], canonical_value(v)) for i, v in enumerate(row)) for row in predicted_rows]
                expected_sequence = [tuple((expected_columns[i], canonical_value(v)) for i, v in enumerate(row)) for row in expected_rows]
                score = _score(Counter(enumerate(predicted_sequence)), Counter(enumerate(expected_sequence)))
            else:
                score = _score(predicted, expected)
            exact_matches += int((predicted_sequence == expected_sequence) if ordered else (predicted == expected))
            cell_score = _score(canonical_cells(columns, predicted_rows),
                                canonical_cells(query.get("expected", {}).get("columns", []), expected_rows))
            totals.update({key: score[key] for key in ("tp", "fp", "fn")})
            cell_totals.update({key: cell_score[key] for key in ("tp", "fp", "fn")})
            successful += 1
            query_reports.append({"id": query["id"], "status": "ok", **score, "cell_metrics": cell_score})
        except sqlite3.Error as exc:
            expected = canonical_result(expected_columns, expected_rows)
            expected_cells = canonical_cells(expected_columns, expected_rows)
            totals["fn"] += sum(expected.values())
            cell_totals["fn"] += sum(expected_cells.values())
            query_reports.append({"id": query.get("id"), "status": "error", "error_type": type(exc).__name__})
        finally:
            conn.set_authorizer(None)
    foreign_key_violations = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    denominator = len(workload.get("queries", []))
    return {
        "status": "confirmatory_eligible" if frozen else "exploratory_only",
        "approval_status": approval,
        "role": "supplementary",
        "evaluator_version": EVALUATOR_VERSION,
        "config_hash": computed_config_hash,
        "query_success_rate": round(successful / denominator, 4) if denominator else 0.0,
        "exact_answer_set_match_rate": round(exact_matches / denominator, 4) if denominator else 0.0,
        "answer_fact_metrics": _score_counts(totals["tp"], totals["fp"], totals["fn"]),
        "answer_cell_metrics": _score_counts(cell_totals["tp"], cell_totals["fp"], cell_totals["fn"]),
        "integrity": {"sqlite_integrity": integrity, "foreign_key_violations": foreign_key_violations},
        "queries": query_reports,
    }
