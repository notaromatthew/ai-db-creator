"""Prepare format-equivalent University facts from the frozen canonical source."""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATASETS = HERE.parent
CANONICAL = DATASETS / "university"
SOURCE = HERE / "source"
FIELDS = [
    "student_name", "student_email", "course_code", "course_title",
    "credits", "semester", "grade",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record_line(index: int, row: dict[str, str]) -> str:
    values = "; ".join(f"{field}={row[field]}" for field in FIELDS)
    return f"RECORD {index:03d}: {values}"


def prepare() -> int:
    SOURCE.mkdir(parents=True, exist_ok=True)
    shutil.copy2(CANONICAL / "source" / "enrollments.csv", SOURCE / "records.csv")
    shutil.copy2(CANONICAL / "gold_schema.json", HERE / "gold_schema.json")
    shutil.copy2(CANONICAL / "ground_truth.db", HERE / "ground_truth.db")
    shutil.copy2(CANONICAL / "column_alias.json", HERE / "column_alias.json")
    spec = json.loads((CANONICAL / "evaluation_spec.json").read_text(encoding="utf-8"))
    spec["dataset"] = "format_equivalence"
    (HERE / "evaluation_spec.json").write_text(
        json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = list(csv.DictReader((SOURCE / "records.csv").open(encoding="utf-8")))
    text = [
        "FORMAT-EQUIVALENT UNIVERSITY ENROLLMENT FACTS",
        "Each record contains one observable enrollment fact.",
        "",
        *[record_line(index, row) for index, row in enumerate(rows, start=1)],
        "",
    ]
    (SOURCE / "records.txt").write_text("\n".join(text), encoding="utf-8")
    return len(rows)


def finalize_manifest() -> dict:
    paths = [
        SOURCE / "records.csv", SOURCE / "records.xlsx", SOURCE / "records.txt",
        SOURCE / "records.pdf", HERE / "gold_schema.json", HERE / "ground_truth.db",
        HERE / "evaluation_spec.json", HERE / "prompt.txt",
    ]
    missing = [path.name for path in paths if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing fixture artifacts: {missing}")
    hashes = {}
    for path in paths:
        hashes[path.relative_to(HERE).as_posix()] = sha256_file(path)
    manifest = {
        "protocol": "rq2_format_equivalence_v1",
        "status": "fixture_frozen_before_format_comparison_runs",
        "canonical_source": "../university/source/enrollments.csv",
        "record_count": sum(1 for _ in csv.DictReader((SOURCE / "records.csv").open(encoding="utf-8"))),
        "formats": ["csv", "xlsx", "txt", "pdf"],
        "semantic_rule": "same 45 enrollment facts and seven named fields in every format",
        "hashes": hashes,
    }
    (HERE / "fixture_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


if __name__ == "__main__":
    print(f"records={prepare()}")
