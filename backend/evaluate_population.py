"""CLI for cell-level population accuracy evaluation (RQ2).

Usage:
    python evaluate_population.py \
        --generated-db projects/{id}/database.sqlite \
        --ground-truth data/datasets/{dataset}/ground_truth.db \
        --gold-schema data/datasets/{dataset}/gold_schema.json \
        --output reports/{id}_report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.evaluation.population_evaluation import (
    connect_database,
    evaluate_generated,
    load_gold_schema,
)
from app.utils.research import atomic_write_json


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Cell-level population accuracy evaluation (RQ2).")
    parser.add_argument("--generated-db", required=True, help="Path to the generated SQLite database.")
    parser.add_argument("--ground-truth", required=True, help="Path to the ground-truth SQLite database.")
    parser.add_argument("--gold-schema", required=True, help="Path to the gold-standard NormalizedSchema JSON.")
    parser.add_argument("--output", required=True, help="Path where the JSON report will be written.")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    schema = load_gold_schema(args.gold_schema)
    with connect_database(args.generated_db) as generated_conn, connect_database(args.ground_truth) as ground_conn:
        result = evaluate_generated(generated_conn, ground_conn, schema)
    report = {
        "generated_db": str(Path(args.generated_db)),
        "ground_truth": str(Path(args.ground_truth)),
        "gold_schema": str(Path(args.gold_schema)),
        "dataset": Path(args.ground_truth).parent.name,
        **result,
    }
    atomic_write_json(args.output, report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())