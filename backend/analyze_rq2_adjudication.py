"""Validate two blinded RQ2 reviews and prepare consensus inputs."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from prepare_rq2_blind_adjudication import CONFIDENCE_LEVELS, DECISIONS


REQUIRED_COLUMNS = {
    "item_id", "decision", "confidence", "notes", "dataset", "table",
    "natural_key", "candidate_value", "reference_value",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_review(path: Path) -> dict[str, dict[str, str]]:
    workbook = load_workbook(path, read_only=True, data_only=True)
    if "Review" not in workbook.sheetnames:
        raise ValueError(f"{path.name}: missing Review sheet")
    rows = workbook["Review"].iter_rows(values_only=True)
    headers = [str(value or "").strip() for value in next(rows)]
    missing = REQUIRED_COLUMNS - set(headers)
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
        if record["decision"] not in DECISIONS:
            raise ValueError(f"{path.name}:{row_number}: invalid or missing decision")
        if record["confidence"] not in CONFIDENCE_LEVELS:
            raise ValueError(f"{path.name}:{row_number}: invalid or missing confidence")
        if record["decision"] in {"gold ambiguo", "non determinabile"} and not record["notes"]:
            raise ValueError(f"{path.name}:{row_number}: notes required for {record['decision']}")
        result[item_id] = record
    return result


def _agreement_statistics(labels_a: list[str], labels_b: list[str]) -> tuple[float | None, float | None]:
    if not labels_a:
        return None, None
    observed = sum(a == b for a, b in zip(labels_a, labels_b)) / len(labels_a)
    counts_a = Counter(labels_a)
    counts_b = Counter(labels_b)
    expected = sum(
        (counts_a[label] / len(labels_a)) * (counts_b[label] / len(labels_b))
        for label in DECISIONS
    )
    if expected == 1.0:
        return expected, 1.0 if observed == 1.0 else None
    return expected, (observed - expected) / (1.0 - expected)


def analyze(reviewer_a: Path, reviewer_b: Path, mapping_path: Path,
            output_dir: Path) -> dict[str, Any]:
    reviews_a = read_review(reviewer_a)
    reviews_b = read_review(reviewer_b)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping_by_id = {row["item_id"]: row for row in mapping}
    expected = set(mapping_by_id)
    if set(reviews_a) != expected or set(reviews_b) != expected:
        raise ValueError("Reviewer item IDs do not exactly match the private mapping")

    ordered_ids = sorted(expected)
    labels_a = [reviews_a[item_id]["decision"] for item_id in ordered_ids]
    labels_b = [reviews_b[item_id]["decision"] for item_id in ordered_ids]
    expected_agreement, cohen_kappa = _agreement_statistics(labels_a, labels_b)
    disagreements = []
    for item_id in ordered_ids:
        left = reviews_a[item_id]
        right = reviews_b[item_id]
        if left["decision"] == right["decision"]:
            continue
        disagreements.append({
            "item_id": item_id,
            "dataset": left["dataset"],
            "table": left["table"],
            "natural_key": left["natural_key"],
            "candidate_value": left["candidate_value"],
            "reference_value": left["reference_value"],
            "reviewer_a_decision": left["decision"],
            "reviewer_a_confidence": left["confidence"],
            "reviewer_a_notes": left["notes"],
            "reviewer_b_decision": right["decision"],
            "reviewer_b_confidence": right["confidence"],
            "reviewer_b_notes": right["notes"],
            "consensus_decision": "",
            "consensus_notes": "",
        })

    agreement_count = len(expected) - len(disagreements)
    summary = {
        "protocol": "rq2_blind_adjudication_v1",
        "source_sha256": {
            "reviewer_a": _sha256(reviewer_a),
            "reviewer_b": _sha256(reviewer_b),
            "private_mapping": _sha256(mapping_path),
        },
        "status": "awaiting_consensus" if disagreements else "complete_no_disagreements",
        "item_count": len(expected),
        "exact_agreement_count": agreement_count,
        "exact_agreement_rate": agreement_count / len(expected) if expected else None,
        "expected_agreement_rate": expected_agreement,
        "cohen_kappa_nominal": cohen_kappa,
        "disagreement_count": len(disagreements),
        "reviewer_a_decision_counts": dict(sorted(Counter(labels_a).items())),
        "reviewer_b_decision_counts": dict(sorted(Counter(labels_b).items())),
        "decision_pair_counts": {
            f"{left} | {right}": count
            for (left, right), count in sorted(Counter(zip(labels_a, labels_b)).items())
        },
        "reviewer_a_confidence_counts": dict(sorted(Counter(
            reviews_a[item_id]["confidence"] for item_id in ordered_ids
        ).items())),
        "reviewer_b_confidence_counts": dict(sorted(Counter(
            reviews_b[item_id]["confidence"] for item_id in ordered_ids
        ).items())),
        "consensus_required": bool(disagreements),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "agreement_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    fields = list(disagreements[0]) if disagreements else [
        "item_id", "dataset", "table", "natural_key", "candidate_value",
        "reference_value", "reviewer_a_decision", "reviewer_a_confidence",
        "reviewer_a_notes", "reviewer_b_decision", "reviewer_b_confidence",
        "reviewer_b_notes", "consensus_decision", "consensus_notes",
    ]
    with (output_dir / "consensus_required.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(disagreements)
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("reviewer_a", type=Path)
    parser.add_argument("reviewer_b", type=Path)
    parser.add_argument("mapping", type=Path)
    parser.add_argument("output_dir", type=Path)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(analyze(args.reviewer_a, args.reviewer_b, args.mapping, args.output_dir), indent=2))


if __name__ == "__main__":
    main()
