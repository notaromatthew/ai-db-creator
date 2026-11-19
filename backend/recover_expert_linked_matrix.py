from __future__ import annotations

import argparse
import csv
import json
import random
import shutil
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.evaluation.functional_equivalence import (
    evaluate_functional_queries,
    load_evaluation_spec,
)
from app.evaluation.population_evaluation import (
    connect_database,
    evaluate_generated,
    load_gold_schema,
)
from app.evaluation.rq2_artifacts import write_discrepancies
from app.utils.research import atomic_write_json, sha256_file, stable_hash
from consolidate_rq1_schemas import _render_schema


DATASETS = ("university", "library", "hospital")
CONDITIONS = ("baseline", "full_llm")
MANIFEST_VERSION = "recovered-expert-linked-matrix-v1"
UNAVAILABLE_ORIGINAL_PROVENANCE = (
    "generation_provider_and_model",
    "software_revision",
    "research_mode",
    "population_mode",
    "source_file_hashes_before_generation",
    "per_run_protocol_manifest",
)


def _evaluator_hashes() -> dict[str, str]:
    backend = Path(__file__).resolve().parent
    paths = (
        backend / "app" / "evaluation" / "population_evaluation.py",
        backend / "app" / "evaluation" / "functional_equivalence.py",
        backend / "app" / "evaluation" / "rq2_artifacts.py",
        Path(__file__).resolve(),
    )
    return {path.relative_to(backend).as_posix(): sha256_file(path) for path in paths}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Recover the expert-linked historical matrix without altering newer matrices."
    )
    parser.add_argument("--source-backend", required=True, type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/benchmark_rq1_expert_linked_recovered_20261113"),
    )
    parser.add_argument("--datasets-root", type=Path, default=Path("../data/datasets"))
    parser.add_argument(
        "--current-expert-package",
        type=Path,
        default=Path("reports/rq1_expert_package"),
    )
    parser.add_argument("--overwrite", action="store_true")
    return parser


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def _structural_body(path: Path) -> str:
    return _structural_text(path.read_text(encoding="utf-8"))


def _structural_text(text: str) -> str:
    text = text.replace("\r\n", "\n")
    index = text.find("TABLE ")
    return (text[index:] if index >= 0 else text).strip()


def _tree_entries(root: Path) -> list[dict[str, Any]]:
    return [
        {
            "path": path.relative_to(root).as_posix(),
            "size": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in sorted(
            item for item in root.rglob("*")
            if item.is_file() and item.name != ".recovery-incomplete.json"
        )
    ]


def _copy_tree(source: Path, target: Path) -> None:
    if not source.is_dir():
        raise FileNotFoundError(source)
    shutil.copytree(source, target)


def _load_runs(benchmark: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for dataset in DATASETS:
        for condition in CONDITIONS:
            files = sorted((benchmark / dataset / condition).glob("run*.json"))
            if len(files) != 5:
                raise ValueError(
                    f"Expected five runs for {dataset}/{condition}, found {len(files)}"
                )
            for expected, path in enumerate(files, start=1):
                value = _read_json(path)
                observed = (value.get("dataset"), value.get("condition"), value.get("run"))
                if observed != (dataset, condition, expected):
                    raise ValueError(f"Unexpected run identity in {path}: {observed}")
                project_id = str(value.get("project_id") or "").strip()
                if not project_id:
                    raise ValueError(f"Missing project_id in {path}")
                rows.append({
                    "dataset": dataset,
                    "condition": condition,
                    "run": expected,
                    "project_id": project_id,
                    "record_path": path,
                    "record": value,
                })
    project_ids = [row["project_id"] for row in rows]
    if len(rows) != 30 or len(set(project_ids)) != 30:
        raise ValueError("The recovered matrix must contain 30 distinct project IDs")
    return rows


def _validate_app_db(app_db: Path, runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    with sqlite3.connect(app_db) as connection:
        connection.row_factory = sqlite3.Row
        columns = [row[1] for row in connection.execute("PRAGMA table_info(projects)")]
        if not {"id", "schema_json", "db_path"}.issubset(columns):
            raise ValueError(f"Unexpected projects table in {app_db}")
        result: dict[str, dict[str, Any]] = {}
        for run in runs:
            row = connection.execute(
                "SELECT id, name, schema_json, db_path FROM projects WHERE id = ?",
                (run["project_id"],),
            ).fetchone()
            if row is None:
                raise ValueError(f"Project missing from recovered app.db: {run['project_id']}")
            schema = json.loads(row["schema_json"])
            documents = [
                {
                    "id": document["id"],
                    "filename": document["filename"],
                    "file_type": document["file_type"],
                    "file_path": document["file_path"],
                    "created_at": document["created_at"],
                }
                for document in connection.execute(
                    "SELECT id, filename, file_type, file_path, created_at "
                    "FROM documents WHERE project_id = ? ORDER BY id",
                    (run["project_id"],),
                ).fetchall()
            ]
            result[run["project_id"]] = {
                "id": row["id"],
                "name": row["name"],
                "db_path": row["db_path"],
                "schema": schema,
                "documents": documents,
            }
        return result


def _validate_expert_linkage(
    recovered_package: Path,
    current_package: Path,
    runs: list[dict[str, Any]],
    projects: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    recovered_mapping = list(csv.DictReader((recovered_package / "mapping.csv").open(
        encoding="utf-8", newline=""
    )))
    current_mapping = list(csv.DictReader((current_package / "mapping.csv").open(
        encoding="utf-8", newline=""
    )))
    if recovered_mapping != current_mapping or len(recovered_mapping) != 30:
        raise ValueError("Recovered and current RQ1 mappings do not match exactly")
    run_lookup = {
        (run["dataset"], run["condition"], f"run{run['run']}"): run
        for run in runs
    }
    structural_matches: list[str] = []
    for row in recovered_mapping:
        code = row["code"]
        recovered = recovered_package / "schemas" / f"{code}.md"
        current = current_package / "schemas" / f"{code}.md"
        if _structural_body(recovered) != _structural_body(current):
            raise ValueError(f"Structural mismatch for expert schema {code}")
        key = (row["dataset"], row["condition"], row["run"])
        if key not in run_lookup:
            raise ValueError(f"Expert mapping references an unknown run: {key}")
        run = run_lookup[key]
        rendered = _render_schema(projects[run["project_id"]]["schema"])
        if _structural_body(recovered) != _structural_text(rendered):
            raise ValueError(
                f"Expert schema {code} does not match mapped project {run['project_id']}"
            )
        structural_matches.append(code)
    ordered_runs = sorted(runs, key=lambda run: run["record_path"].as_posix())
    codes = list(range(1, len(ordered_runs) + 1))
    random.Random(42).shuffle(codes)
    expected_mapping = [
        {
            "code": f"S{code:02d}",
            "dataset": run["dataset"],
            "condition": run["condition"],
            "run": f"run{run['run']}",
        }
        for run, code in zip(ordered_runs, codes)
    ]
    if recovered_mapping != expected_mapping:
        raise ValueError("Recovered RQ1 mapping is not reproducible with seed 42")
    return {
        "mapping_rows": len(recovered_mapping),
        "mapping_exact_match": True,
        "structural_schema_matches": len(structural_matches),
        "mapped_project_schema_matches": len(structural_matches),
        "seed_42_mapping_reproduced": True,
        "matched_codes": structural_matches,
    }


def _validate_output_path(output: Path, reports_root: Path, protected: Path) -> None:
    output = output.resolve()
    reports_root = reports_root.resolve()
    protected = protected.resolve()
    try:
        output.relative_to(reports_root)
    except ValueError as exc:
        raise ValueError(f"Output must be below {reports_root}: {output}") from exc
    if output == reports_root or output == protected or protected in output.parents:
        raise ValueError(f"Unsafe recovery output: {output}")


def _prepare_output(output: Path, reports_root: Path, protected: Path, overwrite: bool) -> None:
    _validate_output_path(output, reports_root, protected)
    if output.exists():
        if not overwrite:
            raise FileExistsError(f"Output already exists: {output}")
        manifest_path = output / "recovery_manifest.json"
        incomplete_path = output / ".recovery-incomplete.json"
        allowed = False
        for marker in (manifest_path, incomplete_path):
            if marker.is_file():
                try:
                    allowed = _read_json(marker).get("manifest_version") == MANIFEST_VERSION
                except (OSError, ValueError, json.JSONDecodeError):
                    allowed = False
                if allowed:
                    break
        if not allowed:
            raise ValueError(f"Refusing to overwrite an unrecognised directory: {output}")
        shutil.rmtree(output)
    output.mkdir(parents=True)
    atomic_write_json(output / ".recovery-incomplete.json", {
        "manifest_version": MANIFEST_VERSION,
        "status": "incomplete",
    })


def _evaluate_run(
    run: dict[str, Any], generated_db: Path, original_datasets_root: Path,
    current_datasets_root: Path,
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    original_dataset = original_datasets_root / run["dataset"]
    current_dataset = current_datasets_root / run["dataset"]
    schema = load_gold_schema(original_dataset / "gold_schema.json")
    spec, spec_hash = load_evaluation_spec(current_dataset)
    alignment = run["record"].get("alignment") if run["condition"] == "full_llm" else None
    column_aliases = (alignment or {}).get("columns") or None
    table_aliases = (alignment or {}).get("tables") or None
    natural_keys = spec.get("natural_keys") or None
    with connect_database(generated_db) as generated, connect_database(
        original_dataset / "ground_truth.db"
    ) as ground:
        full_gold = evaluate_generated(
            generated,
            ground,
            schema,
            column_aliases,
            table_aliases,
            natural_keys,
        )
        observable_scope = spec.get("observable_scope")
        evaluation = evaluate_generated(
            generated,
            ground,
            schema,
            column_aliases,
            table_aliases,
            natural_keys,
            observable_scope,
        ) if observable_scope else full_gold
        if observable_scope:
            evaluation["full_gold_sensitivity"] = full_gold
        functional = evaluate_functional_queries(generated, ground, spec, alignment) \
            if spec.get("functional_queries") else None
    return evaluation, functional, spec_hash


def _integrity(database: Path) -> dict[str, Any]:
    with sqlite3.connect(database) as connection:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
        foreign_keys = connection.execute("PRAGMA foreign_key_check").fetchall()
        tables = [
            row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        row_counts = {
            table: connection.execute(
                'SELECT COUNT(*) FROM "' + table.replace('"', '""') + '"'
            ).fetchone()[0]
            for table in tables
        }
    return {
        "integrity_check": integrity,
        "foreign_key_violation_count": len(foreign_keys),
        "table_count": len(tables),
        "row_count": sum(row_counts.values()),
        "rows_by_table": row_counts,
    }


def _run_manifest(
    run: dict[str, Any], run_dir: Path, source_record_hash: str,
    source_db_hash: str, spec_hash: str | None, integrity: dict[str, Any],
) -> dict[str, Any]:
    artifact_entries = _tree_entries(run_dir)
    return {
        "manifest_version": "recovered-expert-linked-run-v1",
        "classification": {
            "rq1": "primary_expert_linked",
            "rq2": "recovered_historical_secondary",
        },
        "original_observed": {
            "dataset": run["dataset"],
            "condition": run["condition"],
            "run": run["run"],
            "project_id": run["project_id"],
            "status": run["record"].get("status"),
            "reported_metrics": {
                key: run["record"].get(key)
                for key in (
                    "global_precision", "global_recall", "global_f1",
                    "total_cells", "missing_rows", "extra_rows",
                )
            },
            "unavailable_provenance": list(UNAVAILABLE_ORIGINAL_PROVENANCE),
        },
        "recovery_computed": {
            "source_run_record_sha256": source_record_hash,
            "source_generated_database_sha256": source_db_hash,
            "current_evaluation_spec_sha256": spec_hash,
            "current_evaluator_sha256": _evaluator_hashes(),
            "database_integrity": integrity,
        },
        "artifacts": artifact_entries,
    }


def recover(
    source_backend: Path,
    output: Path,
    datasets_root: Path,
    current_expert_package: Path,
    overwrite: bool = False,
) -> dict[str, Any]:
    source_backend = source_backend.resolve()
    output = output.resolve()
    datasets_root = datasets_root.resolve()
    current_expert_package = current_expert_package.resolve()
    source_benchmark = source_backend / "reports" / "benchmark"
    source_expert_package = source_backend / "reports" / "rq1_expert_package"
    source_app_db = source_backend / "app.db"
    original_datasets_root = source_backend.parent / "data" / "datasets"
    reports_root = Path(__file__).resolve().parent / "reports"
    _prepare_output(output, reports_root, current_expert_package, overwrite)

    runs = _load_runs(source_benchmark)
    projects = _validate_app_db(source_app_db, runs)
    snapshot = output / "source_snapshot"
    _copy_tree(source_benchmark, snapshot / "benchmark")
    _copy_tree(source_expert_package, snapshot / "rq1_expert_package")
    for dataset in DATASETS:
        _copy_tree(
            original_datasets_root / dataset,
            snapshot / "original_datasets" / dataset,
        )
        evaluation_spec = datasets_root / dataset / "evaluation_spec.json"
        evaluation_spec_target = snapshot / "current_evaluation_specs" / dataset / "evaluation_spec.json"
        evaluation_spec_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evaluation_spec, evaluation_spec_target)
    source_linkage: list[dict[str, Any]] = []
    copied_sources: set[tuple[str, str]] = set()
    for run in runs:
        for document in projects[run["project_id"]]["documents"]:
            upload = source_backend / Path(document["file_path"])
            canonical = original_datasets_root / run["dataset"] / "source" / document["filename"]
            if not upload.is_file() or not canonical.is_file():
                raise FileNotFoundError(upload if not upload.is_file() else canonical)
            upload_hash = sha256_file(upload)
            canonical_hash = sha256_file(canonical)
            if upload_hash != canonical_hash:
                raise ValueError(
                    f"Recovered upload differs from canonical source: {upload}"
                )
            source_linkage.append({
                "project_id": run["project_id"],
                "dataset": run["dataset"],
                "filename": document["filename"],
                "file_type": document["file_type"],
                "sha256_computed_at_recovery": upload_hash,
                "canonical_source_match": True,
            })
            source_key = (run["dataset"], document["filename"])
            if source_key not in copied_sources:
                destination = snapshot / "source_files" / run["dataset"] / document["filename"]
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(upload, destination)
                copied_sources.add(source_key)
    atomic_write_json(snapshot / "project_index.json", {
        "source_app_db_redistributed": False,
        "projects": [
            {
                "project_id": run["project_id"],
                "name": projects[run["project_id"]]["name"],
                "database_path": f"projects/{run['project_id']}/database.sqlite",
                "schema_sha256": stable_hash(projects[run["project_id"]]["schema"]),
                "documents": [
                    {
                        "id": document["id"],
                        "filename": document["filename"],
                        "file_type": document["file_type"],
                        "created_at": document["created_at"],
                    }
                    for document in projects[run["project_id"]]["documents"]
                ],
            }
            for run in runs
        ],
        "document_source_linkage": source_linkage,
    })
    linkage = _validate_expert_linkage(
        snapshot / "rq1_expert_package", current_expert_package, runs, projects
    )

    run_summaries: list[dict[str, Any]] = []
    for run in runs:
        source_project_db = source_backend / "projects" / run["project_id"] / "database.sqlite"
        if not source_project_db.is_file():
            raise FileNotFoundError(source_project_db)
        snapshot_project = snapshot / "projects" / run["project_id"]
        snapshot_project.mkdir(parents=True)
        shutil.copy2(source_project_db, snapshot_project / "database.sqlite")
        run_dir = output / "runs" / run["dataset"] / run["condition"] / f"run{run['run']:02d}"
        run_dir.mkdir(parents=True)
        generated_db = run_dir / "generated.db"
        shutil.copy2(source_project_db, generated_db)
        atomic_write_json(run_dir / "generated_schema.json", projects[run["project_id"]]["schema"])
        shutil.copy2(run["record_path"], run_dir / "original_run.json")
        if run["record"].get("alignment") is not None:
            atomic_write_json(run_dir / "original_alignment.json", run["record"]["alignment"])
        evaluation, functional, spec_hash = _evaluate_run(
            run,
            generated_db,
            snapshot / "original_datasets",
            datasets_root,
        )
        atomic_write_json(run_dir / "current_evaluation.json", evaluation)
        write_discrepancies(
            run_dir / "current_cell_discrepancies.csv",
            evaluation,
            {
                "dataset": run["dataset"],
                "condition": run["condition"],
                "run": run["run"],
                "source_format": "combined_historical",
            },
        )
        if functional is not None:
            atomic_write_json(run_dir / "current_functional_query_results.json", functional)
        integrity = _integrity(generated_db)
        manifest = _run_manifest(
            run,
            run_dir,
            sha256_file(run["record_path"]),
            sha256_file(source_project_db),
            spec_hash,
            integrity,
        )
        atomic_write_json(run_dir / "recovery_manifest.json", manifest)
        global_metrics = evaluation["global"]
        run_summaries.append({
            "dataset": run["dataset"],
            "condition": run["condition"],
            "run": run["run"],
            "project_id": run["project_id"],
            "original_status": run["record"].get("status"),
            "precision": global_metrics["precision"],
            "recall": global_metrics["recall"],
            "f1": global_metrics["f1"],
            "functional_query_pass_rate": (
                functional or {}
            ).get("overall_query_pass_rate"),
            "functionally_equivalent": (
                functional or {}
            ).get("functionally_equivalent"),
            "database_sha256": sha256_file(source_project_db),
            "database_integrity_ok": (
                integrity["integrity_check"] == "ok"
                and integrity["foreign_key_violation_count"] == 0
                and integrity["table_count"] > 0
                and integrity["row_count"] > 0
            ),
        })

    atomic_write_json(output / "rq2_recovered_results.json", {"runs": run_summaries})
    counts = Counter(
        (row["dataset"], row["condition"], row["original_status"])
        for row in run_summaries
    )
    recovered_at = datetime.now(timezone.utc).isoformat()
    top_manifest = {
        "manifest_version": MANIFEST_VERSION,
        "recovered_at": recovered_at,
        "classification": {
            "rq1": "primary_expert_linked",
            "rq2": "recovered_historical_secondary",
            "newer_rq2_matrices_replaced": False,
        },
        "original_observed": {
            "matrix_shape": {
                "datasets": list(DATASETS),
                "conditions": list(CONDITIONS),
                "runs_per_cell": 5,
                "total_runs": len(runs),
            },
            "status_counts": [
                {
                    "dataset": dataset,
                    "condition": condition,
                    "status": status,
                    "count": count,
                }
                for (dataset, condition, status), count in sorted(counts.items())
            ],
            "unavailable_provenance": list(UNAVAILABLE_ORIGINAL_PROVENANCE),
        },
        "expert_linkage": linkage,
        "recovery_computed": {
            "hashes_computed_at": recovered_at,
            "source_app_db_sha256": sha256_file(source_app_db),
            "source_app_db_redistributed": False,
            "source_app_db_note": (
                "The source database also contains unrelated projects and documents; "
                "only the 30 benchmark project records were extracted."
            ),
            "recovered_document_rows": len(source_linkage),
            "recovered_document_hashes_are_post_hoc": True,
            "canonical_source_hash_matches": sum(
                1 for row in source_linkage if row["canonical_source_match"]
            ),
            "deduplicated_source_files": len(copied_sources),
            "current_evaluator_sha256": _evaluator_hashes(),
            "snapshot_tree_hash": stable_hash(_tree_entries(snapshot)),
            "all_project_databases_integrity_ok": all(
                row["database_integrity_ok"] for row in run_summaries
            ),
            "rq2_run_count": len(run_summaries),
        },
        "recovery_inferences": {
            "probable_software_revision": "08f5897c6b44b8fbf5e8630df367a5f6e3b7712d",
            "basis": "old repository HEAD reflog interval covering benchmark file timestamps",
            "certainty": "probable_not_observed",
            "dirty_worktree_state": "unknown",
        },
        "artifacts": _tree_entries(output),
    }
    atomic_write_json(output / "recovery_manifest.json", top_manifest)
    (output / ".recovery-incomplete.json").unlink()
    atomic_write_json(output / "RECOVERY_COMPLETE.json", {
        "manifest_version": MANIFEST_VERSION,
        "status": "complete",
        "recovery_manifest_sha256": sha256_file(output / "recovery_manifest.json"),
    })
    return top_manifest


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = recover(
        args.source_backend,
        args.output,
        args.datasets_root,
        args.current_expert_package,
        args.overwrite,
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "rq1_classification": manifest["classification"]["rq1"],
        "rq2_classification": manifest["classification"]["rq2"],
        "run_count": manifest["original_observed"]["matrix_shape"]["total_runs"],
        "expert_structural_matches": manifest["expert_linkage"]["structural_schema_matches"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
