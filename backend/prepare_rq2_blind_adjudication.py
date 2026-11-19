"""Prepare blinded RQ2 discrepancy records and a private coordinator mapping."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from typing import Any


DECISIONS = [
    "errore",
    "rappresentazione equivalente",
    "alias valido",
    "gold ambiguo",
    "non determinabile",
]
CONFIDENCE_LEVELS = ["bassa", "media", "alta"]
REVIEW_FIELDS = [
    "item_id",
    "dataset",
    "table",
    "natural_key",
    "row_key_columns",
    "column",
    "candidate_value",
    "reference_value",
    "machine_discrepancy_type",
    "alignment_method",
    "decision",
    "confidence",
    "notes",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_item_id(row: dict[str, str], source: Path) -> str:
    identity = {
        "source": source.as_posix(),
        "dataset": row.get("dataset", ""),
        "condition": row.get("condition", ""),
        "run": row.get("run", ""),
        "table": row.get("table", ""),
        "natural_key": row.get("natural_key", ""),
        "column": row.get("column", ""),
        "generated_value": row.get("generated_value", ""),
        "gold_value": row.get("gold_value", ""),
        "error_type": row.get("error_type", ""),
    }
    payload = json.dumps(identity, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return f"RQ2-{hashlib.sha256(payload).hexdigest()[:16].upper()}"


def collect_items(matrix_dir: Path) -> tuple[list[dict[str, str]], list[dict[str, Any]]]:
    discrepancy_files = sorted(matrix_dir.glob("*/*/run??/cell_discrepancies.csv"))
    if len(discrepancy_files) != 30:
        raise ValueError(f"Expected 30 discrepancy ledgers, found {len(discrepancy_files)}")

    public_items: list[dict[str, str]] = []
    private_mapping: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for source in discrepancy_files:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            for row_number, row in enumerate(csv.DictReader(handle), start=2):
                item_id = _stable_item_id(row, source.relative_to(matrix_dir))
                if item_id in seen_ids:
                    raise ValueError(f"Duplicate item id {item_id}")
                seen_ids.add(item_id)
                public_items.append({
                    "item_id": item_id,
                    "dataset": row.get("dataset", ""),
                    "table": row.get("table", ""),
                    "natural_key": row.get("natural_key", ""),
                    "row_key_columns": row.get("row_key_columns", ""),
                    "column": row.get("column", ""),
                    "candidate_value": row.get("generated_value", ""),
                    "reference_value": row.get("gold_value", ""),
                    "machine_discrepancy_type": row.get("error_type", ""),
                    "alignment_method": row.get("alignment_method", ""),
                    "decision": "",
                    "confidence": "",
                    "notes": "",
                })
                private_mapping.append({
                    "item_id": item_id,
                    "condition": row.get("condition", ""),
                    "run": int(row["run"]),
                    "source_format": row.get("source_format", ""),
                    "source_ledger": source.relative_to(matrix_dir).as_posix(),
                    "source_row": row_number,
                    "source_ledger_sha256": sha256_file(source),
                })
    return public_items, private_mapping


def _ordered(items: list[dict[str, str]], seed: int) -> list[dict[str, str]]:
    result = [dict(item) for item in items]
    random.Random(seed).shuffle(result)
    return result


def prepare_package(matrix_dir: Path, output_dir: Path, seed: int = 20261118) -> dict[str, Any]:
    matrix_dir = matrix_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    items, mapping = collect_items(matrix_dir)
    reviewer_a = _ordered(items, seed)
    reviewer_b = _ordered(items, seed + 1)
    order_a = {item["item_id"]: index for index, item in enumerate(reviewer_a, start=1)}
    order_b = {item["item_id"]: index for index, item in enumerate(reviewer_b, start=1)}
    for entry in mapping:
        entry["reviewer_a_order"] = order_a[entry["item_id"]]
        entry["reviewer_b_order"] = order_b[entry["item_id"]]

    files = {
        "reviewer_a_items.json": reviewer_a,
        "reviewer_b_items.json": reviewer_b,
        "private_mapping.json": mapping,
    }
    for name, payload in files.items():
        (output_dir / name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    counts = Counter(item["machine_discrepancy_type"] for item in items)
    manifest = {
        "protocol": "rq2_blind_adjudication_v1",
        "status": "prepared_awaiting_two_independent_human_reviews",
        "source_matrix": matrix_dir.name,
        "source_matrix_manifest_sha256": sha256_file(matrix_dir / "protocol_manifest.json"),
        "selection_rule": "all discrepancies from all 30 primary matrix runs",
        "item_count": len(items),
        "run_count": 30,
        "reviewer_count_required": 2,
        "blinded_fields": ["condition", "run", "provider", "model", "scores"],
        "reviewer_a_seed": seed,
        "reviewer_b_seed": seed + 1,
        "decision_values": DECISIONS,
        "confidence_values": CONFIDENCE_LEVELS,
        "machine_discrepancy_counts": dict(sorted(counts.items())),
        "inputs": {
            path.relative_to(matrix_dir).as_posix(): sha256_file(path)
            for path in sorted(matrix_dir.glob("*/*/run??/cell_discrepancies.csv"))
        },
        "prepared_outputs": {
            name: sha256_file(output_dir / name) for name in sorted(files)
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def finalize_package(output_dir: Path) -> dict[str, Any]:
    manifest_path = output_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    names = ["reviewer_a.xlsx", "reviewer_b.xlsx", "coordinator_private_mapping.xlsx"]
    missing = [name for name in names if not (output_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing adjudication workbooks: {missing}")
    manifest["workbooks"] = {
        name: sha256_file(output_dir / name) for name in names
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", type=int, default=20261118)
    parser.add_argument("--finalize", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = finalize_package(args.output_dir) if args.finalize else prepare_package(
        args.matrix_dir, args.output_dir, args.seed
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
