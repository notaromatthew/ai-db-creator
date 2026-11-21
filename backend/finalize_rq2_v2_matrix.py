"""Verify and freeze a complete RQ2 v2 benchmark matrix."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import statistics
from collections import defaultdict
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DATASETS = REPO_ROOT / "data" / "datasets"
METRICS = (
    "global_precision",
    "global_recall",
    "global_f1",
    "functional_query_pass_rate",
    "missing_rows",
    "extra_rows",
)
SECRET_PATTERNS = (
    re.compile(rb"sk-[A-Za-z0-9_-]{16,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{20,}"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mean(rows: list[dict], name: str) -> float:
    return statistics.fmean(float(row[name]) for row in rows)


def finalize(matrix: Path) -> dict:
    matrix = matrix.resolve()
    protocol_path = matrix / "protocol_manifest.json"
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    manifests = sorted(matrix.glob("*/*/run??/manifest.json"))
    if len(manifests) != 30:
        raise ValueError(f"Expected 30 manifests, found {len(manifests)}")

    rows: list[dict] = []
    artifact_checked = artifact_failures = 0
    source_checked = source_failures = 0
    evaluation_checked = evaluation_failures = 0
    provenance = set()
    for manifest_path in manifests:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        run_root = manifest_path.parent
        run = json.loads((run_root / "run.json").read_text(encoding="utf-8"))
        if manifest.get("status") != "ok" or run.get("status") != "ok":
            raise ValueError(f"Non-successful run: {run_root}")
        if run.get("population_mode") != "llm":
            raise ValueError(f"Non-LLM population mode: {run_root}")
        if any(run.get(metric) is None for metric in METRICS):
            raise ValueError(f"Missing metric: {run_root}")

        provenance.add(
            (
                manifest["software_revision"],
                manifest["provider"],
                manifest["model"],
                manifest["parameters"]["temperature"],
                manifest["schema_output_contract"],
                manifest["source_format"],
                manifest["research_mode"],
            )
        )
        for metadata in manifest["artifacts"].values():
            artifact_checked += 1
            path = run_root / metadata["path"]
            if not path.exists() or sha256(path) != metadata["sha256"]:
                artifact_failures += 1
        dataset_root = DATASETS / manifest["dataset"]
        for source in manifest["source_files"]:
            source_checked += 1
            path = dataset_root / source["path"]
            if not path.exists() or sha256(path) != source["sha256"]:
                source_failures += 1
        evaluation_checked += 1
        if sha256(dataset_root / "evaluation_spec.json") != manifest["evaluation_spec_hash"]:
            evaluation_failures += 1
        rows.append(run)

    if len(provenance) != 1:
        raise ValueError(f"Mixed provenance configurations: {len(provenance)}")
    if artifact_failures or source_failures or evaluation_failures:
        raise ValueError(
            f"Hash failures: artifacts={artifact_failures}, sources={source_failures}, "
            f"evaluation_specs={evaluation_failures}"
        )

    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["condition"])].append(row)
    expected = {
        (dataset, condition)
        for dataset in ("university", "library", "hospital")
        for condition in ("baseline", "full_llm")
    }
    if set(grouped) != expected or any(len(cell) != 5 for cell in grouped.values()):
        raise ValueError("Matrix is not balanced at five runs per cell")

    cells = []
    for dataset, condition in sorted(grouped):
        cell = grouped[(dataset, condition)]
        cells.append(
            {
                "dataset": dataset,
                "condition": condition,
                "n": len(cell),
                "mean_precision": round(mean(cell, "global_precision"), 4),
                "mean_recall": round(mean(cell, "global_recall"), 4),
                "mean_f1": round(mean(cell, "global_f1"), 4),
                "mean_functional_query_pass_rate": round(
                    mean(cell, "functional_query_pass_rate"), 4
                ),
                "functionally_equivalent": sum(bool(row["functionally_equivalent"]) for row in cell),
                "mean_missing_rows": round(mean(cell, "missing_rows"), 2),
                "mean_extra_rows": round(mean(cell, "extra_rows"), 2),
            }
        )

    secret_files = []
    for path in matrix.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".db", ".sqlite", ".pdf", ".xlsx", ".zip"}:
            continue
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            secret_files.append(path.relative_to(matrix).as_posix())
    if secret_files:
        raise ValueError(f"Potential secrets found in {secret_files}")

    configuration = next(iter(provenance))
    result = {
        "label": "rq2_functional_v2_complete_matrix",
        "date": date.today().isoformat(),
        "protocol_manifest": "protocol_manifest.json",
        "planned_runs": 30,
        "completed_runs": 30,
        "ok": 30,
        "error": 0,
        "not_evaluable": 0,
        "fallback": 0,
        "success_rate": 1.0,
        "cells": cells,
        "provenance": {
            "git_revision": protocol["git_revision"],
            "software_revision": configuration[0],
            "provider": configuration[1],
            "model": configuration[2],
            "temperature": configuration[3],
            "schema_output_contract": configuration[4],
            "source_format": configuration[5],
            "research_mode": configuration[6],
            "schedule": protocol["schedule"],
        },
        "integrity": {
            "manifests": len(manifests),
            "artifact_hashes_checked": artifact_checked,
            "artifact_hash_failures": artifact_failures,
            "source_hashes_checked": source_checked,
            "source_hash_failures": source_failures,
            "evaluation_spec_hashes_checked": evaluation_checked,
            "evaluation_spec_hash_failures": evaluation_failures,
            "secret_files": len(secret_files),
        },
        "comparability": (
            "Primary v2 matrix for the consensus-amended gold standards. "
            "Do not pool with v1 matrices."
        ),
    }
    (matrix / "execution_complete.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    lines = [
        "# Matrice RQ2 v2 completa",
        "",
        "30/30 run riusciti, tutti con popolamento LLM e senza fallback.",
        "",
        "| Dataset | Condizione | n | Precision | Recall | F1 | Query funzionali | Equivalenti |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for cell in cells:
        lines.append(
            f"| {cell['dataset'].title()} | {cell['condition']} | {cell['n']} | "
            f"{cell['mean_precision']:.4f} | {cell['mean_recall']:.4f} | "
            f"{cell['mean_f1']:.4f} | {cell['mean_functional_query_pass_rate']:.4f} | "
            f"{cell['functionally_equivalent']}/{cell['n']} |"
        )
    lines.extend(
        [
            "",
            "La matrice usa i gold standard `rq2_functional_v2` approvati da GOLD-A e GOLD-B. ",
            "I risultati v1 sono storici e non vengono aggregati con questi valori.",
            "",
            "Tutti i run condividono revisione software, provider, modello, temperatura, formato sorgente e contratto di output. ",
            "L'esecuzione in un'unica sessione limita la separazione tra effetto del modello e possibile deriva temporale del provider.",
        ]
    )
    (matrix / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    args = parser.parse_args()
    result = finalize(args.matrix)
    print(json.dumps({"ok": result["ok"], "integrity": result["integrity"]}, indent=2))


if __name__ == "__main__":
    main()
