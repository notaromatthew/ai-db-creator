"""Exploratory condition analysis for the consensus-amended RQ2 v2 matrix."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from scipy.stats import spearmanr

from analyze_rq2_final_matrix import (
    bootstrap_difference_ci,
    exact_permutation_p,
    hedges_g,
    holm_adjust,
    sha256_file,
)


METRICS = ("global_precision", "global_recall", "global_f1", "functional_query_pass_rate")
COMPARISON_METRICS = ("global_f1", "functional_query_pass_rate")


def describe(values: list[float]) -> dict:
    return {
        "n": len(values),
        "mean": statistics.fmean(values),
        "median": statistics.median(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def analyze(matrix: Path, output: Path, seed: int = 20261121) -> dict:
    rows = []
    run_hashes = {}
    for path in sorted(matrix.glob("*/*/run??/run.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") != "ok" or row.get("population_mode") != "llm":
            raise ValueError(f"Non-evaluable run: {path}")
        if any(row.get(metric) is None for metric in METRICS):
            raise ValueError(f"Missing metric: {path}")
        rows.append(row)
        run_hashes[path.relative_to(matrix).as_posix()] = sha256_file(path)
    if len(rows) != 30:
        raise ValueError(f"Expected 30 runs, found {len(rows)}")

    grouped = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["condition"])].append(row)

    cells = {}
    for (dataset, condition), cell in sorted(grouped.items()):
        cells[f"{dataset} | {condition}"] = {
            metric: describe([float(row[metric]) for row in cell]) for metric in METRICS
        } | {
            "functionally_equivalent_count": sum(bool(row["functionally_equivalent"]) for row in cell)
        }

    comparisons = []
    for dataset_index, dataset in enumerate(sorted({row["dataset"] for row in rows})):
        baseline = grouped[(dataset, "baseline")]
        full_llm = grouped[(dataset, "full_llm")]
        for metric_index, metric in enumerate(COMPARISON_METRICS):
            left = [float(row[metric]) for row in baseline]
            right = [float(row[metric]) for row in full_llm]
            comparisons.append(
                {
                    "dataset": dataset,
                    "metric": metric,
                    "baseline_mean": statistics.fmean(left),
                    "full_llm_mean": statistics.fmean(right),
                    "mean_difference_full_llm_minus_baseline": (
                        statistics.fmean(right) - statistics.fmean(left)
                    ),
                    "bootstrap_95_ci_mean_difference": bootstrap_difference_ci(
                        left, right, seed=seed + dataset_index * 10 + metric_index
                    ),
                    "hedges_g": hedges_g(left, right),
                    "exact_permutation_p": exact_permutation_p(left, right),
                }
            )
    adjusted = holm_adjust([row["exact_permutation_p"] for row in comparisons])
    for row, adjusted_p in zip(comparisons, adjusted):
        row["holm_adjusted_p_across_six_exploratory_tests"] = adjusted_p

    correlations = {}
    subsets = [("all_runs", rows)] + [
        (dataset, [row for row in rows if row["dataset"] == dataset])
        for dataset in sorted({row["dataset"] for row in rows})
    ]
    for label, subset in subsets:
        correlation = spearmanr(
            [float(row["global_f1"]) for row in subset],
            [float(row["functional_query_pass_rate"]) for row in subset],
        )
        correlations[label] = {
            "n": len(subset),
            "spearman_rho": float(correlation.statistic),
            "two_sided_p": float(correlation.pvalue),
        }

    result = {
        "analysis": "rq2_functional_v2_exploratory",
        "status": "complete_exploratory",
        "matrix": matrix.name,
        "run_count": len(rows),
        "bootstrap_seed": seed,
        "limitations": [
            "Five runs per dataset-condition cell; inference is exploratory.",
            "All runs were executed in one provider session, so provider-time drift is not independently estimable.",
            "The v2 gold standards differ from v1; results must not be pooled across versions.",
        ],
        "cells": cells,
        "condition_comparisons": comparisons,
        "f1_functional_query_correlations": correlations,
    }
    output.mkdir(parents=True, exist_ok=True)
    result_path = output / "rq2_v2_analysis.json"
    comparisons_path = output / "rq2_v2_condition_comparisons.csv"
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with comparisons_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    manifest = {
        "analysis": result["analysis"],
        "bootstrap_seed": seed,
        "inputs": {
            "execution_complete.json": sha256_file(matrix / "execution_complete.json"),
            "run_records": run_hashes,
        },
        "outputs": {
            result_path.name: sha256_file(result_path),
            comparisons_path.name: sha256_file(comparisons_path),
        },
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", type=int, default=20261121)
    args = parser.parse_args()
    result = analyze(args.matrix, args.output, args.seed)
    print(json.dumps(result["condition_comparisons"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
