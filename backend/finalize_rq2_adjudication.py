"""Validate completed RQ2 consensus and build the unblinded final ledger."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from analyze_rq2_adjudication import read_review
from prepare_rq2_blind_adjudication import DECISIONS


CONSENSUS_COLUMNS = {
    "item_id", "dataset", "table", "natural_key", "candidate_value",
    "reference_value", "reviewer_a_decision", "reviewer_a_confidence",
    "reviewer_a_notes", "reviewer_b_decision", "reviewer_b_confidence",
    "reviewer_b_notes", "consensus_decision", "consensus_notes",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_consensus(path: Path) -> dict[str, dict[str, str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    if "Consenso" not in workbook.sheetnames:
        raise ValueError(f"{path.name}: missing Consenso sheet")
    rows = workbook["Consenso"].iter_rows(values_only=True)
    headers = [str(value or "").strip() for value in next(rows)]
    missing = CONSENSUS_COLUMNS - set(headers)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    result: dict[str, dict[str, str]] = {}
    for row_number, values in enumerate(rows, start=2):
        record = {header: str(value or "").strip() for header, value in zip(headers, values)}
        item_id = record["item_id"]
        if not item_id:
            continue
        if item_id in result:
            raise ValueError(f"{path.name}: duplicate item_id {item_id}")
        if record["consensus_decision"] not in DECISIONS:
            raise ValueError(f"{path.name}:{row_number}: invalid or missing consensus_decision")
        if not record["consensus_notes"]:
            raise ValueError(f"{path.name}:{row_number}: consensus_notes is required")
        result[item_id] = record
    return result


def _counts(rows: list[dict[str, Any]], keys: list[str]) -> dict[str, Any]:
    grouped: dict[tuple[str, ...], Counter[str]] = defaultdict(Counter)
    for row in rows:
        group = tuple(str(row[key]) for key in keys)
        grouped[group][row["final_decision"]] += 1
    output: dict[str, Any] = {}
    for group, decision_counts in sorted(grouped.items()):
        label = " | ".join(group)
        total = sum(decision_counts.values())
        evaluable = sum(decision_counts.get(value, 0) for value in (
            "errore", "rappresentazione equivalente", "alias valido"
        ))
        errors = decision_counts.get("errore", 0)
        output[label] = {
            "item_count": total,
            "decision_counts": dict(sorted(decision_counts.items())),
            "confirmed_error_proportion_all": errors / total if total else None,
            "evaluable_item_count": evaluable,
            "confirmed_error_rate_evaluable": errors / evaluable if evaluable else None,
        }
    return output


def finalize(reviewer_a_path: Path, reviewer_b_path: Path, consensus_path: Path,
             mapping_path: Path, output_dir: Path) -> dict[str, Any]:
    reviewer_a = read_review(reviewer_a_path)
    reviewer_b = read_review(reviewer_b_path)
    consensus = read_consensus(consensus_path)
    mapping_rows = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping = {row["item_id"]: row for row in mapping_rows}
    if set(reviewer_a) != set(mapping) or set(reviewer_b) != set(mapping):
        raise ValueError("Reviewer item IDs do not exactly match the private mapping")

    disagreements = {
        item_id for item_id in mapping
        if reviewer_a[item_id]["decision"] != reviewer_b[item_id]["decision"]
    }
    if set(consensus) != disagreements:
        raise ValueError("Consensus item IDs do not exactly match the independent disagreements")

    immutable_fields = [
        "dataset", "table", "natural_key", "candidate_value", "reference_value",
    ]
    for item_id, record in consensus.items():
        left = reviewer_a[item_id]
        right = reviewer_b[item_id]
        for field in immutable_fields:
            if record[field] != left[field] or record[field] != right[field]:
                raise ValueError(f"{consensus_path.name}: {item_id} changed {field}")
        reviewer_fields = [
            ("reviewer_a_decision", left["decision"]),
            ("reviewer_a_confidence", left["confidence"]),
            ("reviewer_a_notes", left["notes"]),
            ("reviewer_b_decision", right["decision"]),
            ("reviewer_b_confidence", right["confidence"]),
            ("reviewer_b_notes", right["notes"]),
        ]
        for field, expected in reviewer_fields:
            if record[field] != expected:
                raise ValueError(f"{consensus_path.name}: {item_id} changed {field}")

    final_rows: list[dict[str, Any]] = []
    for item_id in sorted(mapping):
        left = reviewer_a[item_id]
        right = reviewer_b[item_id]
        private = mapping[item_id]
        agreed = left["decision"] == right["decision"]
        final_rows.append({
            "item_id": item_id,
            "dataset": left["dataset"],
            "condition": private["condition"],
            "run": private["run"],
            "source_format": private["source_format"],
            "source_ledger": private["source_ledger"],
            "source_row": private["source_row"],
            "table": left["table"],
            "natural_key": left["natural_key"],
            "row_key_columns": left.get("row_key_columns", ""),
            "column": left.get("column", ""),
            "candidate_value": left["candidate_value"],
            "reference_value": left["reference_value"],
            "machine_discrepancy_type": left.get("machine_discrepancy_type", ""),
            "alignment_method": left.get("alignment_method", ""),
            "reviewer_a_decision": left["decision"],
            "reviewer_a_confidence": left["confidence"],
            "reviewer_a_notes": left["notes"],
            "reviewer_b_decision": right["decision"],
            "reviewer_b_confidence": right["confidence"],
            "reviewer_b_notes": right["notes"],
            "resolution": "independent_agreement" if agreed else "consensus",
            "final_decision": left["decision"] if agreed else consensus[item_id]["consensus_decision"],
            "final_notes": "" if agreed else consensus[item_id]["consensus_notes"],
        })

    decision_counts = Counter(row["final_decision"] for row in final_rows)
    evaluable = sum(decision_counts.get(value, 0) for value in (
        "errore", "rappresentazione equivalente", "alias valido"
    ))
    errors = decision_counts.get("errore", 0)
    summary = {
        "protocol": "rq2_blind_adjudication_v1",
        "status": "consensus_complete",
        "metric_scope": (
            "Human classification of the 1,294 machine-flagged discrepancy records; "
            "not a replacement for automated cell-level precision, recall, or F1."
        ),
        "source_sha256": {
            "reviewer_a": sha256_file(reviewer_a_path),
            "reviewer_b": sha256_file(reviewer_b_path),
            "consensus": sha256_file(consensus_path),
            "private_mapping": sha256_file(mapping_path),
        },
        "item_count": len(final_rows),
        "independent_agreement_count": len(final_rows) - len(disagreements),
        "consensus_count": len(disagreements),
        "final_decision_counts": dict(sorted(decision_counts.items())),
        "confirmed_error_proportion_all": errors / len(final_rows),
        "evaluable_item_count": evaluable,
        "confirmed_error_rate_evaluable": errors / evaluable if evaluable else None,
        "excluded_from_evaluable": {
            "gold_ambiguo": decision_counts.get("gold ambiguo", 0),
            "non_determinabile": decision_counts.get("non determinabile", 0),
        },
        "by_condition": _counts(final_rows, ["condition"]),
        "by_dataset_condition": _counts(final_rows, ["dataset", "condition"]),
        "by_dataset_condition_run": _counts(final_rows, ["dataset", "condition", "run"]),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    fields = list(final_rows[0])
    ledger_path = output_dir / "final_adjudication_ledger.csv"
    summary_path = output_dir / "final_adjudication_summary.json"
    with ledger_path.open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(final_rows)
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    manifest = {
        "protocol": summary["protocol"],
        "status": summary["status"],
        "source_sha256": summary["source_sha256"],
        "outputs": {
            ledger_path.name: sha256_file(ledger_path),
            summary_path.name: sha256_file(summary_path),
        },
    }
    (output_dir / "final_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("consensus", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(finalize(
        args.reviewer_a, args.reviewer_b, args.consensus, args.mapping, args.output_dir
    ), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
