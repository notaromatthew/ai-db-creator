"""Validate benchmark datasets and emit a machine-readable readiness report."""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path

from app.evaluation.functional_workload import evaluate_workload, load_workload
from app.evaluation.population_evaluation import load_gold_schema
from app.evaluation.schema_alignment import load_alignment_config
from app.utils.research import sha256_file, stable_hash


def _issue(code: str, severity: str, detail: str) -> dict:
    return {"code": code, "severity": severity, "detail": detail}


def validate_dataset(dataset_dir: Path, check_build: bool = False) -> dict:
    issues: list[dict] = []
    schema_path = dataset_dir / "gold_schema.json"
    database_path = dataset_dir / "ground_truth.db"
    source_dir = dataset_dir / "source"
    required = [schema_path, database_path, dataset_dir / "prompt.txt", dataset_dir / "rq2_alignment.json",
                dataset_dir / "functional_workload.json"]
    for path in required:
        if not path.exists():
            issues.append(_issue("missing_artifact", "error", path.name))
    if issues:
        return {"dataset": dataset_dir.name, "status": "invalid", "issues": issues}
    schema = load_gold_schema(schema_path)
    alignment = load_alignment_config(dataset_dir)
    conn = sqlite3.connect(database_path)
    conn.execute("PRAGMA foreign_keys=ON")
    db_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}
    for table in schema.tables:
        if table.name not in db_tables:
            issues.append(_issue("missing_table", "error", table.name))
            continue
        info = {row[1]: row for row in conn.execute(f"PRAGMA table_info([{table.name}])")}
        for column in table.columns:
            if column.name not in info:
                issues.append(_issue("missing_column", "error", f"{table.name}.{column.name}"))
            elif column.is_primary_key and not info[column.name][5]:
                issues.append(_issue("pk_mismatch", "error", f"{table.name}.{column.name}"))
        for key in alignment.get("entity_keys", {}).get(table.name, []):
            if key not in info:
                issues.append(_issue("invalid_natural_key", "error", f"{table.name}.{key}"))
                continue
            nulls = conn.execute(f"SELECT COUNT(*) FROM [{table.name}] WHERE [{key}] IS NULL OR TRIM(CAST([{key}] AS TEXT))='' ").fetchone()[0]
            if nulls:
                issues.append(_issue("null_natural_key", "error", f"{table.name}.{key}:{nulls}"))
        keys = alignment.get("entity_keys", {}).get(table.name, [])
        if keys:
            cols = ",".join(f"[{key}]" for key in keys)
            duplicates = conn.execute(f"SELECT COUNT(*) FROM (SELECT {cols},COUNT(*) n FROM [{table.name}] GROUP BY {cols} HAVING n>1)").fetchone()[0]
            if duplicates:
                issues.append(_issue("duplicate_natural_key", "error", f"{table.name}:{duplicates}"))
    fk_violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if fk_violations:
        issues.append(_issue("fk_violation", "error", str(len(fk_violations))))
    integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    if integrity != "ok":
        issues.append(_issue("integrity_check", "error", integrity))
    workload = load_workload(dataset_dir)
    workload_report = evaluate_workload(conn, workload)
    if workload_report["query_success_rate"] != 1 or workload_report["answer_fact_metrics"]["f1"] != 1:
        issues.append(_issue("workload_expected_mismatch", "error", "gold DB does not reproduce expected results"))
    conn.close()
    sources = sorted(path for path in source_dir.rglob("*") if path.is_file())
    if not sources:
        issues.append(_issue("missing_sources", "error", "source directory empty"))
    headers = {}
    for path in sources:
        if path.suffix.lower() == ".csv":
            with path.open(encoding="utf-8-sig", newline="") as source:
                headers[path.name] = next(csv.reader(source), [])
        if path.stat().st_size == 0:
            issues.append(_issue("empty_source", "error", path.name))
    build = {"checked": False, "deterministic": None}
    if check_build and (dataset_dir / "build_dataset.py").exists():
        hashes = []
        with tempfile.TemporaryDirectory() as temp:
            for index in range(2):
                target = Path(temp) / str(index) / dataset_dir.name
                shutil.copytree(dataset_dir, target)
                for generated in (target / "ground_truth.db", target / "source" / "description.pdf"):
                    if generated.exists():
                        generated.unlink()
                subprocess.run([__import__("sys").executable, "build_dataset.py"], cwd=target,
                               check=True, capture_output=True, timeout=120)
                hashes.append({name: sha256_file(target / name) for name in (
                    "ground_truth.db", "source/description.pdf")})
        build = {"checked": True, "deterministic": hashes[0] == hashes[1], "runs": hashes}
        if not build["deterministic"]:
            issues.append(_issue("nondeterministic_build", "error", "two isolated builds differ"))
    return {
        "dataset": dataset_dir.name,
        "status": "valid" if not any(item["severity"] == "error" for item in issues) else "invalid",
        "confirmatory_status": "eligible" if workload_report["status"] == "confirmatory_eligible" else "blocked_unfrozen",
        "technical_freeze_valid": workload_report["status"] == "confirmatory_eligible",
        "issues": issues, "source_headers": headers, "workload": workload_report, "build": build,
        "hashes": {path.relative_to(dataset_dir).as_posix(): sha256_file(path)
                   for path in [*required, *sources]},
        "report_hash": stable_hash({"issues": issues, "workload": workload_report, "build": build}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", type=Path, default=Path("../data/datasets"))
    parser.add_argument("--output", type=Path)
    parser.add_argument("--check-build", action="store_true")
    args = parser.parse_args(argv)
    reports = [validate_dataset(path, args.check_build) for path in sorted(args.datasets.iterdir()) if path.is_dir()]
    result = {"status": "valid" if all(item["status"] == "valid" for item in reports) else "invalid", "datasets": reports}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
