"""Validate and analyse the separate RQ1 expert panel."""
from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats

from analyze_rq1_ratings import (
    DIMENSIONS,
    git_revision,
    load_mapping,
    ordinal_alpha,
    percentile_interval,
    score_matrix,
    sha256_file,
    summary_record,
    validate_rows,
    write_csv,
)


SOURCE_COLUMNS = [
    "evaluator",
    "code",
    "dataset",
    "condition",
    "run",
    *DIMENSIONS,
    "comment",
    "updated_at",
]


def read_source(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    parsed = list(csv.reader(text.splitlines(), dialect=dialect))
    if not parsed:
        raise ValueError("ratings file is empty")
    if parsed[0] == SOURCE_COLUMNS:
        parsed = parsed[1:]
    if any(len(row) != len(SOURCE_COLUMNS) for row in parsed):
        raise ValueError(f"expected {len(SOURCE_COLUMNS)} columns in every source row")
    return [dict(zip(SOURCE_COLUMNS, row)) for row in parsed]


def finite_holm(values: list[float | None]) -> list[float | None]:
    finite_indices = [
        index for index, value in enumerate(values)
        if value is not None and math.isfinite(value)
    ]
    result: list[float | None] = [None] * len(values)
    order = sorted(finite_indices, key=lambda index: float(values[index]))
    running = 0.0
    total = len(order)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * float(values[index])))
        result[index] = running
    return result


def agreement_record(
    label: str,
    combined: np.ndarray,
    schema_width: int,
    rng: np.random.Generator,
    resamples: int,
) -> dict[str, object]:
    spread = np.ptp(combined, axis=0)
    constant = bool(np.ptp(combined) == 0)
    alpha = None if constant else ordinal_alpha(combined)
    boot: list[float] = []
    if not constant:
        dimension_count = combined.shape[1] // schema_width
        matrices = np.split(combined, dimension_count, axis=1)
        for _ in range(resamples):
            sampled = rng.integers(0, schema_width, size=schema_width)
            candidate = np.concatenate([matrix[:, sampled] for matrix in matrices], axis=1)
            if np.ptp(candidate) == 0:
                continue
            try:
                value = ordinal_alpha(candidate)
            except (ValueError, ZeroDivisionError):
                continue
            if math.isfinite(value):
                boot.append(value)
    low, high = percentile_interval(boot)
    return {
        "dimension": label,
        "alpha_ordinal": alpha,
        "bootstrap_low": None if not math.isfinite(low) else low,
        "bootstrap_high": None if not math.isfinite(high) else high,
        "bootstrap_resamples_valid": len(boot),
        "exact_agreement_pct": float(np.mean(spread == 0) * 100),
        "adjacent_agreement_pct": float(np.mean(spread <= 1) * 100),
        "n_evaluators": int(combined.shape[0]),
        "n_units": int(combined.shape[1]),
        "undefined_reason": "no_between_unit_variation" if constant else "",
    }


def bootstrap_difference(
    left: np.ndarray,
    right: np.ndarray,
    rng: np.random.Generator,
    resamples: int,
) -> tuple[float, float]:
    values = [
        float(
            np.mean(rng.choice(right, size=len(right), replace=True))
            - np.mean(rng.choice(left, size=len(left), replace=True))
        )
        for _ in range(resamples)
    ]
    return percentile_interval(values)


def condition_comparisons(
    rows: list[dict[str, str]],
    mapping: dict[str, dict[str, str]],
    rng: np.random.Generator,
    resamples: int,
) -> list[dict[str, object]]:
    by_code: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_code.setdefault(row["code"].strip(), []).append(row)
    records: list[dict[str, object]] = []
    p_values: list[float | None] = []
    for dimension in DIMENSIONS:
        baseline = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[code])
            for code, meta in mapping.items() if meta["condition"] == "baseline"
        ], dtype=float)
        full_llm = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[code])
            for code, meta in mapping.items() if meta["condition"] == "full_llm"
        ], dtype=float)
        constant = bool(np.ptp(np.concatenate([baseline, full_llm])) == 0)
        low, high = bootstrap_difference(baseline, full_llm, rng, resamples)
        if constant:
            t_statistic = t_p = mann_u = mann_p = effect = None
        else:
            mann = stats.mannwhitneyu(baseline, full_llm, alternative="two-sided")
            variance_left = float(np.var(baseline, ddof=1))
            variance_right = float(np.var(full_llm, ddof=1))
            standard_error_sq = variance_left / len(baseline) + variance_right / len(full_llm)
            if standard_error_sq:
                t_statistic = float((np.mean(baseline) - np.mean(full_llm)) / math.sqrt(standard_error_sq))
                numerator = standard_error_sq ** 2
                denominator = (
                    (variance_left / len(baseline)) ** 2 / (len(baseline) - 1)
                    + (variance_right / len(full_llm)) ** 2 / (len(full_llm) - 1)
                )
                degrees_freedom = numerator / denominator
                t_p = float(2 * stats.t.sf(abs(t_statistic), degrees_freedom))
            else:
                t_statistic = t_p = None
            pooled = math.sqrt(
                ((len(baseline) - 1) * variance_left
                 + (len(full_llm) - 1) * variance_right)
                / (len(baseline) + len(full_llm) - 2)
            )
            mann_u = float(mann.statistic)
            mann_p = float(mann.pvalue)
            effect = float((np.mean(full_llm) - np.mean(baseline)) / pooled) if pooled else None
        p_values.append(t_p)
        records.append({
            "dimension": dimension,
            "unit": "schema_mean",
            "n_baseline_schemas": len(baseline),
            "n_full_llm_schemas": len(full_llm),
            "baseline_mean": float(np.mean(baseline)),
            "full_llm_mean": float(np.mean(full_llm)),
            "mean_difference_full_minus_baseline": float(np.mean(full_llm) - np.mean(baseline)),
            "bootstrap_low": low,
            "bootstrap_high": high,
            "welch_t_statistic": t_statistic,
            "welch_t_p": t_p,
            "welch_t_p_holm": None,
            "mann_whitney_u": mann_u,
            "mann_whitney_p": mann_p,
            "cohen_d": effect,
            "undefined_reason": "no_between_unit_variation" if constant else "",
        })
    for record, adjusted in zip(records, finite_holm(p_values)):
        record["welch_t_p_holm"] = adjusted
    return records


def display(value: object, digits: int = 3) -> str:
    if value is None or (isinstance(value, float) and not math.isfinite(value)):
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def render_report(
    manifest: dict[str, object],
    agreement: list[dict[str, object]],
    comparisons: list[dict[str, object]],
) -> str:
    lines = [
        "# RQ1 — pannello esperto separato",
        "",
        "## Stato del pannello",
        "",
        "- Replica osservata separata dalle 1.350 valutazioni dei 45 trained student raters; nessun pooling.",
        f"- Il protocollo pianificava {manifest['planned_evaluators']} esperti; il pannello osservato ne contiene {manifest['n_evaluators']}.",
        "- Per i primi due esperti, indipendenza, assenza di confronto/accesso ai punteggi reciproci e cecità alle condizioni sono attestazioni dell'utente, non inferenze dai dati.",
        "- Per il terzo esperto l'idoneità è attestata dall'utente; indipendenza e cecità alle condizioni restano da confermare esplicitamente.",
        f"- L'accordo esatto osservato è {manifest['exact_score_cell_agreement']} celle e {manifest['exact_schema_vector_agreement']} vettori-schema.",
        "",
        "## Accordo",
        "",
        "| Dimensione | Alpha ordinale | IC bootstrap 95% | Esatto | Adiacente |",
        "|---|---:|---:|---:|---:|",
    ]
    for record in agreement:
        interval = f"[{display(record['bootstrap_low'])}, {display(record['bootstrap_high'])}]"
        lines.append(
            f"| {record['dimension']} | {display(record['alpha_ordinal'])} | {interval} | "
            f"{display(record['exact_agreement_pct'], 1)}% | {display(record['adjacent_agreement_pct'], 1)}% |"
        )
    lines.extend([
        "",
        "## Confronto descrittivo fra condizioni",
        "",
        f"L'unità è lo schema (15 per condizione); i {manifest['n_evaluators']} giudizi sono aggregati per schema.",
        "",
        "| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for record in comparisons:
        lines.append(
            f"| {record['dimension']} | {display(record['baseline_mean'])} | "
            f"{display(record['full_llm_mean'])} | {display(record['mean_difference_full_minus_baseline'])} | "
            f"[{display(record['bootstrap_low'])}, {display(record['bootstrap_high'])}] | "
            f"{display(record['welch_t_p_holm'], 4)} | {display(record['cohen_d'])} |"
        )
    lines.extend([
        "",
        "Il pannello raggiunge la numerosità pianificata di tre esperti e resta separato dal campione studentesco. L'evidenza procedurale del terzo esperto deve essere completata prima di descrivere l'intero pannello come indipendente e cieco alle condizioni.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--mapping", type=Path, default=Path("reports/rq1_expert_package/mapping.csv"))
    parser.add_argument("--output", type=Path, default=Path("reports/rq1_expert_replication"))
    parser.add_argument("--seed", type=int, default=20261114)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    args = parser.parse_args(argv)

    rows = []
    for source_path in args.input:
        rows.extend(read_source(source_path))
    mapping = load_mapping(args.mapping)
    evaluators, codes = validate_rows(rows, mapping)
    if len(evaluators) != 3 or len(codes) != 30:
        raise ValueError("expert panel requires exactly 3 evaluators x 30 schemas")
    args.output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)
    matrices = {
        dimension: score_matrix(rows, evaluators, codes, dimension)
        for dimension in DIMENSIONS
    }
    agreement = [
        agreement_record(dimension, matrices[dimension], len(codes), rng, args.bootstrap_resamples)
        for dimension in DIMENSIONS
    ]
    agreement.append(agreement_record(
        "overall", np.concatenate(list(matrices.values()), axis=1), len(codes), rng, args.bootstrap_resamples
    ))

    summaries: list[dict[str, object]] = []
    groups = [("overall", "all", "all")]
    groups.extend(("condition", "all", condition) for condition in sorted({row["condition"] for row in rows}))
    groups.extend(("dataset", dataset, "all") for dataset in sorted({row["dataset"] for row in rows}))
    for group_type, dataset, condition in groups:
        for dimension in DIMENSIONS:
            summaries.append(summary_record(rows, group_type, dataset, condition, dimension))
    comparisons = condition_comparisons(rows, mapping, rng, args.bootstrap_resamples)

    evaluator_ids = {evaluator: f"X{index:03d}" for index, evaluator in enumerate(evaluators, 1)}
    canonical = [{
        "evaluator_id": evaluator_ids[row["evaluator"].strip()],
        "code": row["code"].strip(),
        "dataset": row["dataset"].strip(),
        "condition": row["condition"].strip(),
        "run": row["run"].strip(),
        **{dimension: int(row[dimension]) for dimension in DIMENSIONS},
    } for row in sorted(rows, key=lambda item: (evaluator_ids[item["evaluator"].strip()], item["code"].strip()))]
    canonical_path = args.output / "ratings_canonical_pseudonymized.csv"
    write_csv(canonical_path, canonical)

    exact_cells = 0
    exact_vectors = 0
    for code in codes:
        code_rows = [row for row in rows if row["code"].strip() == code]
        exact_dimensions = [
            len({int(row[dimension]) for row in code_rows}) == 1
            for dimension in DIMENSIONS
        ]
        exact_cells += sum(exact_dimensions)
        exact_vectors += int(all(exact_dimensions))

    repository_root = Path(__file__).resolve().parent.parent
    manifest = {
        "artifact_status": "observed_three_expert_panel_separate_not_pooled",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_files": [path.name for path in args.input],
        "original_source_sha256": {
            path.name: sha256_file(path) for path in args.input
        },
        "canonical_input_sha256": sha256_file(canonical_path),
        "mapping_sha256": sha256_file(args.mapping),
        "analysis_script_sha256": sha256_file(Path(__file__)),
        "software_revision": git_revision(repository_root),
        "seed": args.seed,
        "bootstrap_resamples": args.bootstrap_resamples,
        "score_scale": "1-5",
        "n_ratings": len(rows),
        "n_score_cells": len(rows) * len(DIMENSIONS),
        "n_evaluators": len(evaluators),
        "planned_evaluators": 3,
        "n_schemas": len(codes),
        "conditions": sorted({row["condition"].strip() for row in rows}),
        "datasets": sorted({row["dataset"].strip() for row in rows}),
        "exact_score_cell_agreement": f"{exact_cells}/{len(codes) * len(DIMENSIONS)}",
        "exact_schema_vector_agreement": f"{exact_vectors}/{len(codes)}",
        "expert_eligibility": "user_attested_sector_experts",
        "independence": "first_two_user_attested; third_not_yet_explicitly_attested",
        "condition_blinding": "first_two_user_attested; third_not_yet_explicitly_attested",
        "attestation_recorded_on": {
            "first_two_procedure": "2026-11-14",
            "third_expert_eligibility": "2026-11-18",
        },
        "comments_included": any((row.get("comment") or "").strip() for row in rows),
        "evaluation_timestamps_published": False,
        "responses_marked_as_imputed": False,
        "raw_evaluator_names_persisted": False,
    }
    write_csv(args.output / "descriptive_summary.csv", summaries)
    write_csv(args.output / "agreement.csv", agreement)
    write_csv(args.output / "condition_comparison.csv", comparisons)
    (args.output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.output / "REPORT.md").write_text(
        render_report(manifest, agreement, comparisons), encoding="utf-8"
    )
    print(json.dumps({
        "output": str(args.output.resolve()),
        "n_ratings": len(rows),
        "n_evaluators": len(evaluators),
        "n_schemas": len(codes),
        "original_source_sha256": manifest["original_source_sha256"],
        "canonical_input_sha256": manifest["canonical_input_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
