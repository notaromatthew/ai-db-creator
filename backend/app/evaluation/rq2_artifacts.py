"""Self-contained, auditable artifact bundles for RQ2 benchmark runs."""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Any

from app.utils.research import atomic_write_json, sanitize_metadata, sha256_file


def write_discrepancies(path: str | Path, evaluation: dict,
                        record: dict | None = None) -> int:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    record = record or {}
    fields = [
        "dataset", "source_format", "condition", "run", "table",
        "natural_key", "row_key_columns", "column", "source_value",
        "generated_value", "gold_value", "error_type", "source_document",
        "source_location", "alignment_method",
    ]
    count = 0
    with target.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for table, metrics in (evaluation.get("per_table") or {}).items():
            for item in metrics.get("discrepancies", []):
                writer.writerow({
                    "dataset": record.get("dataset"),
                    "source_format": record.get("source_format"),
                    "condition": record.get("condition"),
                    "run": record.get("run"),
                    "table": table,
                    "natural_key": json.dumps(item.get("row_key"), ensure_ascii=False),
                    "row_key_columns": json.dumps(metrics.get("row_key_columns"), ensure_ascii=False),
                    "column": item.get("column"),
                    "source_value": "",
                    "error_type": item.get("error_type"),
                    "generated_value": json.dumps(item.get("generated_value"), ensure_ascii=False, default=str),
                    "gold_value": json.dumps(item.get("ground_value"), ensure_ascii=False, default=str),
                    "source_document": "",
                    "source_location": "",
                    "alignment_method": "declared_row_key",
                })
                count += 1
    return count


def write_run_bundle(bundle_dir: str | Path, *, database_path: str | Path | None,
                     generated_schema: Any | None, evaluation: dict | None,
                     alignment: dict | None, functional_evaluation: dict | None,
                     manifest: dict, record: dict) -> dict[str, str | None]:
    target = Path(bundle_dir)
    target.mkdir(parents=True, exist_ok=True)
    safe_record = sanitize_metadata(record)
    safe_manifest = sanitize_metadata(manifest)
    artifacts: dict[str, Path] = {}
    if database_path and Path(database_path).is_file():
        artifacts["generated_database"] = target / "generated.db"
        shutil.copy2(database_path, artifacts["generated_database"])
    if generated_schema is not None:
        artifacts["generated_schema"] = target / "generated_schema.json"
        payload = generated_schema.model_dump(mode="json") \
            if hasattr(generated_schema, "model_dump") else generated_schema
        atomic_write_json(artifacts["generated_schema"], payload)
    if evaluation is not None:
        artifacts["evaluation"] = target / "evaluation.json"
        atomic_write_json(artifacts["evaluation"], evaluation)
        artifacts["cell_discrepancies"] = target / "cell_discrepancies.csv"
        write_discrepancies(artifacts["cell_discrepancies"], evaluation, record)
    if alignment is not None:
        artifacts["alignment"] = target / "alignment.json"
        atomic_write_json(artifacts["alignment"], alignment)
    if functional_evaluation is not None:
        artifacts["functional_query_results"] = target / "functional_query_results.json"
        atomic_write_json(artifacts["functional_query_results"], functional_evaluation)
    artifacts["run_record"] = target / "run.json"
    atomic_write_json(artifacts["run_record"], safe_record)
    hashes = {name: sha256_file(path) for name, path in artifacts.items()}
    manifest = {**safe_manifest, "status": safe_record.get("status"), "artifacts": {
        name: {"path": path.name, "sha256": hashes[name]} for name, path in artifacts.items()
    }}
    atomic_write_json(target / "manifest.json", manifest)
    return {name: value for name, value in hashes.items()}
