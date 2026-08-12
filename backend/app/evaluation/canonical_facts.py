"""Deterministic RQ2 content evaluation over source-grounded canonical facts."""
from __future__ import annotations

from collections import Counter
from typing import Any

from app.evaluation.population_evaluation import normalise_value, read_rows
from app.evaluation.schema_alignment import inspect_generated_tables
from app.utils.research import stable_hash

EVALUATOR_VERSION = "rq2-canonical-facts-v1"


def _table(schema, name: str):
    return next(table for table in schema.tables if table.name == name)


def _normalised(value: Any, data_type: str) -> str | None:
    return normalise_value(value, data_type)


def _canonical_side(conn, schema, config: dict, table_aliases: dict[str, str],
                    column_aliases: dict[str, dict[str, str]]) -> tuple[Counter, dict[str, Counter], list[str]]:
    rows_by_table = {
        table.name: read_rows(conn, table, column_aliases.get(table.name), table_aliases.get(table.name))
        for table in schema.tables
    }
    entity_keys = config.get("entity_keys", {})
    surrogate_keys = config.get("surrogate_keys", {})
    errors: list[str] = []
    indexes: dict[tuple[str, str], dict[str, dict]] = {}
    for table in schema.tables:
        for column in table.columns:
            if column.is_primary_key:
                index: dict[str, dict] = {}
                for row in rows_by_table[table.name]:
                    key = _normalised(row.get(column.name), column.data_type)
                    if key is not None:
                        index[key] = row
                indexes[(table.name, column.name)] = index

    def canonical_value(table, column, value):
        if not column.is_foreign_key:
            return _normalised(value, column.data_type)
        target = _table(schema, column.foreign_key_table)
        target_column = next(c for c in target.columns if c.name == column.foreign_key_column)
        target_row = indexes.get((target.name, target_column.name), {}).get(
            _normalised(value, target_column.data_type)
        )
        target_keys = entity_keys.get(target.name)
        if target_row is None or not target_keys:
            return None
        return tuple(canonical_value(target, next(c for c in target.columns if c.name == key), target_row.get(key))
                     for key in target_keys)

    all_facts: Counter = Counter()
    per_table: dict[str, Counter] = {}
    for table in schema.tables:
        keys = entity_keys.get(table.name)
        if not keys:
            errors.append(f"missing entity_keys for {table.name}")
            continue
        facts: Counter = Counter()
        excluded = set(surrogate_keys.get(table.name, []))
        for row in rows_by_table[table.name]:
            identity = tuple(canonical_value(table, next(c for c in table.columns if c.name == key), row.get(key))
                             for key in keys)
            if any(value is None for value in identity):
                errors.append(f"unresolved entity key in {table.name}")
                continue
            for column in table.columns:
                if column.name in excluded:
                    continue
                value = canonical_value(table, column, row.get(column.name))
                facts[(table.name, identity, column.name, value)] += 1
        per_table[table.name] = facts
        all_facts.update(facts)
    return all_facts, per_table, sorted(set(errors))


def evaluate_canonical_facts(generated_conn, ground_conn, schema, config: dict,
                             condition: str) -> dict:
    """Compare canonical fact multisets; no LLM or inferred semantic mapping is used."""
    config_hash = config.get("config_hash") or stable_hash(config)
    required = {table.name for table in schema.tables}
    if set(config.get("entity_keys", {})) != required:
        return {"status": "not_evaluable", "reason": "entity_keys must cover every gold table",
                "evaluator_version": EVALUATOR_VERSION, "config_hash": config_hash}
    frozen = config.get("alignments", {}).get(condition)
    if not isinstance(frozen, dict) or frozen.get("mode") != "identity_with_frozen_overrides":
        return {"status": "not_evaluable", "reason": f"missing frozen alignment for condition {condition}",
                "evaluator_version": EVALUATOR_VERSION, "config_hash": config_hash}
    table_aliases = {table.name: frozen.get("tables", {}).get(table.name, table.name)
                     for table in schema.tables}
    column_aliases = {
        table.name: {column.name: frozen.get("columns", {}).get(table.name, {}).get(column.name, column.name)
                     for column in table.columns}
        for table in schema.tables
    }
    generated_structure = inspect_generated_tables(generated_conn)
    missing_mapping = []
    for table in schema.tables:
        generated_table = table_aliases[table.name]
        if generated_table not in generated_structure:
            missing_mapping.append(f"table {table.name}->{generated_table}")
            continue
        for column in table.columns:
            generated_column = column_aliases[table.name][column.name]
            if generated_column not in generated_structure[generated_table]:
                missing_mapping.append(f"column {table.name}.{column.name}->{generated_table}.{generated_column}")
    if missing_mapping:
        return {"status": "not_evaluable", "reason": "frozen alignment missing in generated DB: " + "; ".join(missing_mapping),
                "evaluator_version": EVALUATOR_VERSION, "config_hash": config_hash,
                "alignment_status": "frozen_mapping_not_applicable"}
    generated, generated_tables, generated_errors = _canonical_side(
        generated_conn, schema, config, table_aliases, column_aliases
    )
    ground, ground_tables, ground_errors = _canonical_side(ground_conn, schema, config, {}, {})
    errors = sorted(set(generated_errors + ground_errors))
    if errors:
        return {"status": "not_evaluable", "reason": "; ".join(errors),
                "evaluator_version": EVALUATOR_VERSION, "config_hash": config_hash}

    def score(predicted: Counter, gold: Counter) -> dict:
        tp = sum((predicted & gold).values())
        fp = sum((predicted - gold).values())
        fn = sum((gold - predicted).values())
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        return {"tp": tp, "fp": fp, "fn": fn, "precision": round(precision, 4),
                "recall": round(recall, 4), "f1": round(f1, 4)}

    return {
        "status": "ok",
        "role": "primary",
        "metric": "canonical_fact_micro_f1",
        "evaluator_version": EVALUATOR_VERSION,
        "config_hash": config_hash,
        "global": score(generated, ground),
        "per_table": {name: score(generated_tables.get(name, Counter()), ground_tables.get(name, Counter()))
                      for name in sorted(required)},
    }
