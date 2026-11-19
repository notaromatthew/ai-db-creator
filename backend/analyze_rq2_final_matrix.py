"""Exploratory final analysis of the frozen 30-run RQ2 matrix."""
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from scipy.stats import spearmanr


METRICS = ("global_precision", "global_recall", "global_f1", "functional_query_pass_rate")
COMPARISON_METRICS = ("global_f1", "functional_query_pass_rate")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mean(values: list[float]) -> float:
    return statistics.fmean(values)


def describe(values: list[float]) -> dict[str, float | int]:
    return {
        "n": len(values),
        "mean": _mean(values),
        "median": statistics.median(values),
        "sd": statistics.stdev(values) if len(values) > 1 else 0.0,
        "min": min(values),
        "max": max(values),
    }


def exact_permutation_p(left: list[float], right: list[float]) -> float:
    combined = left + right
    n_left = len(left)
    observed = abs(_mean(right) - _mean(left))
    extreme = 0
    total = 0
    indices = range(len(combined))
    for chosen in itertools.combinations(indices, n_left):
        chosen_set = set(chosen)
        perm_left = [combined[index] for index in indices if index in chosen_set]
        perm_right = [combined[index] for index in indices if index not in chosen_set]
        if abs(_mean(perm_right) - _mean(perm_left)) >= observed - 1e-12:
            extreme += 1
        total += 1
    return extreme / total


def hedges_g(left: list[float], right: list[float]) -> float | None:
    n_left, n_right = len(left), len(right)
    if n_left < 2 or n_right < 2:
        return None
    pooled_variance = (
        (n_left - 1) * statistics.variance(left)
        + (n_right - 1) * statistics.variance(right)
    ) / (n_left + n_right - 2)
    if pooled_variance == 0:
        return None
    correction = 1 - 3 / (4 * (n_left + n_right) - 9)
    return ((_mean(right) - _mean(left)) / math.sqrt(pooled_variance)) * correction


def bootstrap_difference_ci(left: list[float], right: list[float], *, seed: int,
                            iterations: int = 10_000) -> list[float]:
    rng = random.Random(seed)
    differences = []
    for _ in range(iterations):
        sampled_left = [rng.choice(left) for _ in left]
        sampled_right = [rng.choice(right) for _ in right]
        differences.append(_mean(sampled_right) - _mean(sampled_left))
    differences.sort()
    lower = differences[int(0.025 * iterations)]
    upper = differences[min(iterations - 1, int(0.975 * iterations))]
    return [lower, upper]


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    running = 0.0
    m = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (m - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def load_runs(matrix_dir: Path) -> list[dict[str, Any]]:
    day_lookup: dict[tuple[str, str, int], str] = {}
    for path in sorted(matrix_dir.glob("execution_day*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for cell in payload["cells"]:
            for run in cell["runs"]:
                day_lookup[(cell["dataset"], cell["condition"], int(run))] = payload["date"]
    rows = []
    for path in sorted(matrix_dir.glob("*/*/run??/run.json")):
        row = json.loads(path.read_text(encoding="utf-8"))
        if row.get("status") != "ok" or row.get("population_mode") != "llm":
            raise ValueError(f"Non-evaluable primary run: {path}")
        key = (row["dataset"], row["condition"], int(row["run"]))
        if key not in day_lookup:
            raise ValueError(f"Missing day provenance for {key}")
        for metric in METRICS:
            if row.get(metric) is None:
                raise ValueError(f"Missing {metric} for {key}")
        rows.append({**row, "execution_day": day_lookup[key]})
    if len(rows) != 30:
        raise ValueError(f"Expected 30 successful runs, found {len(rows)}")
    return rows


def analyze(matrix_dir: Path, adjudication_summary_path: Path,
            output_dir: Path, seed: int = 20261119) -> dict[str, Any]:
    rows = load_runs(matrix_dir)
    adjudication = json.loads(adjudication_summary_path.read_text(encoding="utf-8"))
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[(row["dataset"], row["condition"])].append(row)

    cells: dict[str, Any] = {}
    for (dataset, condition), cell_rows in sorted(grouped.items()):
        cells[f"{dataset} | {condition}"] = {
            metric: describe([float(row[metric]) for row in cell_rows]) for metric in METRICS
        } | {
            "functionally_equivalent_count": sum(bool(row["functionally_equivalent"]) for row in cell_rows),
            "execution_day_counts": dict(sorted(
                (day, sum(row["execution_day"] == day for row in cell_rows))
                for day in {row["execution_day"] for row in cell_rows}
            )),
        }

    comparisons = []
    for dataset_index, dataset in enumerate(sorted({row["dataset"] for row in rows})):
        baseline = grouped[(dataset, "baseline")]
        full_llm = grouped[(dataset, "full_llm")]
        for metric_index, metric in enumerate(COMPARISON_METRICS):
            left = [float(row[metric]) for row in baseline]
            right = [float(row[metric]) for row in full_llm]
            comparisons.append({
                "dataset": dataset,
                "metric": metric,
                "baseline_mean": _mean(left),
                "full_llm_mean": _mean(right),
                "mean_difference_full_llm_minus_baseline": _mean(right) - _mean(left),
                "bootstrap_95_ci_mean_difference": bootstrap_difference_ci(
                    left, right, seed=seed + dataset_index * 10 + metric_index
                ),
                "hedges_g": hedges_g(left, right),
                "exact_permutation_p": exact_permutation_p(left, right),
            })
    adjusted = holm_adjust([row["exact_permutation_p"] for row in comparisons])
    for row, value in zip(comparisons, adjusted):
        row["holm_adjusted_p_across_six_exploratory_tests"] = value

    correlations = {}
    for label, subset in [("all_runs", rows)] + [
        (dataset, [row for row in rows if row["dataset"] == dataset])
        for dataset in sorted({row["dataset"] for row in rows})
    ]:
        result = spearmanr(
            [float(row["global_f1"]) for row in subset],
            [float(row["functional_query_pass_rate"]) for row in subset],
        )
        correlations[label] = {
            "n": len(subset),
            "spearman_rho": float(result.statistic),
            "two_sided_p": float(result.pvalue),
        }

    day_effects = {}
    for (dataset, condition), cell_rows in sorted(grouped.items()):
        by_day: dict[str, list[float]] = defaultdict(list)
        for row in cell_rows:
            by_day[row["execution_day"]].append(float(row["global_f1"]))
        ordered_days = sorted(by_day)
        day_effects[f"{dataset} | {condition}"] = {
            "days": {day: describe(by_day[day]) for day in ordered_days},
            "second_minus_first_mean_f1": _mean(by_day[ordered_days[1]]) - _mean(by_day[ordered_days[0]]),
        }

    result = {
        "analysis": "rq2_final_matrix_exploratory_v1",
        "status": "complete_exploratory",
        "matrix": matrix_dir.name,
        "run_count": len(rows),
        "limitations": [
            "Five runs per dataset-condition cell; inference is exploratory.",
            "Sources were loaded jointly, so results cannot identify a causal document-format effect.",
            "Execution spans two provider days with two or three runs per cell per day.",
            "Adjudication classifies flagged discrepancy records and does not replace cell-level metrics.",
        ],
        "cells": cells,
        "condition_comparisons": comparisons,
        "f1_functional_query_correlations": correlations,
        "execution_day_sensitivity": day_effects,
        "adjudication": {
            "status": adjudication["status"],
            "item_count": adjudication["item_count"],
            "final_decision_counts": adjudication["final_decision_counts"],
            "by_condition": adjudication["by_condition"],
        },
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = output_dir / "rq2_final_analysis.json"
    comparisons_path = output_dir / "rq2_condition_comparisons.csv"
    analysis_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    with comparisons_path.open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(comparisons[0]))
        writer.writeheader()
        writer.writerows(comparisons)
    manifest = {
        "analysis": result["analysis"],
        "status": result["status"],
        "bootstrap_seed": seed,
        "inputs": {
            "protocol_manifest.json": sha256_file(matrix_dir / "protocol_manifest.json"),
            adjudication_summary_path.name: sha256_file(adjudication_summary_path),
        },
        "outputs": {
            analysis_path.name: sha256_file(analysis_path),
            comparisons_path.name: sha256_file(comparisons_path),
        },
    }
    (output_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("matrix_dir", type=Path)
    parser.add_argument("adjudication_summary", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--seed", type=int, default=20261119)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    result = analyze(args.matrix_dir, args.adjudication_summary, args.output_dir, args.seed)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
