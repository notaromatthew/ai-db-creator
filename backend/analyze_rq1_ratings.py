"""Validate and analyse the condition-blind RQ1 expert ratings."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import krippendorff
import numpy as np
from scipy import stats


DIMENSIONS = [
    "d1_3nf",
    "d2_naming",
    "d3_constraints",
    "d4_relationships",
    "d5_domain",
]
REQUIRED = ["evaluator", "code", "dataset", "condition", "run", *DIMENSIONS]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_csv_auto(path: Path) -> list[dict[str, str]]:
    text = path.read_text(encoding="utf-8-sig")
    dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t")
    return list(csv.DictReader(text.splitlines(), dialect=dialect))


def load_mapping(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv_auto(path)
    return {row["code"].strip(): {
        "dataset": row["dataset"].strip(),
        "condition": row["condition"].strip(),
        "run": row["run"].strip(),
    } for row in rows}


def validate_rows(
    rows: list[dict[str, str]], mapping: dict[str, dict[str, str]]
) -> tuple[list[str], list[str]]:
    if not rows:
        raise ValueError("ratings file is empty")
    missing_headers = [name for name in REQUIRED if name not in rows[0]]
    if missing_headers:
        raise ValueError(f"missing columns: {', '.join(missing_headers)}")

    seen: set[tuple[str, str]] = set()
    evaluators: set[str] = set()
    for line, row in enumerate(rows, 2):
        for name in REQUIRED:
            if not str(row.get(name) or "").strip():
                raise ValueError(f"blank {name} at CSV line {line}")
        evaluator = row["evaluator"].strip()
        code = row["code"].strip()
        if code not in mapping:
            raise ValueError(f"unknown schema code {code} at CSV line {line}")
        expected = mapping[code]
        for name in ("dataset", "condition", "run"):
            if row[name].strip() != expected[name]:
                raise ValueError(
                    f"mapping mismatch for {code}/{name} at CSV line {line}"
                )
        pair = (evaluator, code)
        if pair in seen:
            raise ValueError(f"duplicate evaluator/schema pair at CSV line {line}")
        seen.add(pair)
        evaluators.add(evaluator)
        for dimension in DIMENSIONS:
            try:
                score = int(row[dimension])
            except ValueError as exc:
                raise ValueError(
                    f"non-integer {dimension} at CSV line {line}"
                ) from exc
            if score < 1 or score > 5:
                raise ValueError(f"out-of-range {dimension} at CSV line {line}")

    expected_pairs = {(evaluator, code) for evaluator in evaluators for code in mapping}
    missing_pairs = sorted(expected_pairs - seen)
    if missing_pairs:
        raise ValueError(f"incomplete evaluator/schema matrix: {len(missing_pairs)} missing")
    return sorted(evaluators), sorted(mapping)


def score_matrix(
    rows: list[dict[str, str]], evaluators: list[str], codes: list[str], dimension: str
) -> np.ndarray:
    by_pair = {(row["evaluator"].strip(), row["code"].strip()): row for row in rows}
    return np.array([
        [int(by_pair[(evaluator, code)][dimension]) for code in codes]
        for evaluator in evaluators
    ], dtype=float)


def ordinal_alpha(matrix: np.ndarray) -> float:
    value = krippendorff.alpha(
        reliability_data=matrix,
        value_domain=np.array([1, 2, 3, 4, 5]),
        level_of_measurement="ordinal",
    )
    return float(value)


def percentile_interval(values: Iterable[float]) -> tuple[float, float]:
    finite = np.array([value for value in values if math.isfinite(value)], dtype=float)
    if not len(finite):
        return math.nan, math.nan
    low, high = np.percentile(finite, [2.5, 97.5])
    return float(low), float(high)


def agreement_record(
    label: str,
    matrices: list[np.ndarray],
    rng: np.random.Generator,
    resamples: int,
) -> dict[str, object]:
    combined = np.concatenate(matrices, axis=1)
    n_schemas = matrices[0].shape[1]
    boot = []
    for _ in range(resamples):
        sampled = rng.integers(0, n_schemas, size=n_schemas)
        candidate = np.concatenate([matrix[:, sampled] for matrix in matrices], axis=1)
        try:
            boot.append(ordinal_alpha(candidate))
        except (ValueError, ZeroDivisionError):
            continue
    low, high = percentile_interval(boot)
    strict = np.mean(np.ptp(combined, axis=0) == 0) * 100
    adjacent = np.mean(np.ptp(combined, axis=0) <= 1) * 100
    return {
        "dimension": label,
        "alpha_ordinal": ordinal_alpha(combined),
        "bootstrap_low": low,
        "bootstrap_high": high,
        "bootstrap_resamples_valid": len(boot),
        "exact_agreement_pct": float(strict),
        "adjacent_agreement_pct": float(adjacent),
        "n_evaluators": int(combined.shape[0]),
        "n_units": int(combined.shape[1]),
    }


def summary_record(
    rows: list[dict[str, str]],
    group_type: str,
    dataset: str,
    condition: str,
    dimension: str,
) -> dict[str, object]:
    selected = [
        row for row in rows
        if (dataset == "all" or row["dataset"].strip() == dataset)
        and (condition == "all" or row["condition"].strip() == condition)
    ]
    scores = np.array([int(row[dimension]) for row in selected], dtype=float)
    return {
        "group_type": group_type,
        "dataset": dataset,
        "condition": condition,
        "dimension": dimension,
        "n_ratings": len(scores),
        "n_schemas": len({row["code"].strip() for row in selected}),
        "n_evaluators": len({row["evaluator"].strip() for row in selected}),
        "mean": float(np.mean(scores)),
        "sd": float(np.std(scores, ddof=1)),
        "median": float(np.median(scores)),
        "q1": float(np.percentile(scores, 25)),
        "q3": float(np.percentile(scores, 75)),
        "pct_score_5": float(np.mean(scores == 5) * 100),
    }


def cohen_d(left: np.ndarray, right: np.ndarray) -> float:
    pooled = math.sqrt(
        ((len(left) - 1) * np.var(left, ddof=1)
         + (len(right) - 1) * np.var(right, ddof=1))
        / (len(left) + len(right) - 2)
    )
    return float((np.mean(right) - np.mean(left)) / pooled) if pooled else math.nan


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=lambda index: p_values[index])
    adjusted = [math.nan] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, (total - rank) * p_values[index]))
        adjusted[index] = running
    return adjusted


def bootstrap_difference(
    left: np.ndarray,
    right: np.ndarray,
    rng: np.random.Generator,
    resamples: int,
) -> tuple[float, float]:
    values = []
    for _ in range(resamples):
        sampled_left = rng.choice(left, size=len(left), replace=True)
        sampled_right = rng.choice(right, size=len(right), replace=True)
        values.append(float(np.mean(sampled_right) - np.mean(sampled_left)))
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
    records = []
    for dimension in DIMENSIONS:
        baseline = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[code])
            for code, meta in mapping.items() if meta["condition"] == "baseline"
        ], dtype=float)
        full_llm = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[code])
            for code, meta in mapping.items() if meta["condition"] == "full_llm"
        ], dtype=float)
        shapiro_left = stats.shapiro(baseline)
        shapiro_right = stats.shapiro(full_llm)
        levene = stats.levene(baseline, full_llm, center="median")
        equal_var = bool(levene.pvalue >= 0.05)
        t_test = stats.ttest_ind(baseline, full_llm, equal_var=equal_var)
        mann = stats.mannwhitneyu(baseline, full_llm, alternative="two-sided")
        ci_low, ci_high = bootstrap_difference(
            baseline, full_llm, rng, resamples
        )
        records.append({
            "dimension": dimension,
            "unit": "schema_mean",
            "n_baseline_schemas": len(baseline),
            "n_full_llm_schemas": len(full_llm),
            "baseline_mean": float(np.mean(baseline)),
            "full_llm_mean": float(np.mean(full_llm)),
            "mean_difference_full_minus_baseline": float(np.mean(full_llm) - np.mean(baseline)),
            "bootstrap_low": ci_low,
            "bootstrap_high": ci_high,
            "shapiro_baseline_p": float(shapiro_left.pvalue),
            "shapiro_full_llm_p": float(shapiro_right.pvalue),
            "levene_p": float(levene.pvalue),
            "t_test": "student" if equal_var else "welch",
            "t_statistic": float(t_test.statistic),
            "t_p": float(t_test.pvalue),
            "mann_whitney_u": float(mann.statistic),
            "mann_whitney_p": float(mann.pvalue),
            "cohen_d": cohen_d(baseline, full_llm),
        })
    adjusted = holm_adjust([float(record["t_p"]) for record in records])
    for record, value in zip(records, adjusted):
        record["t_p_holm"] = value
    return records


def paired_sensitivity(
    rows: list[dict[str, str]],
    mapping: dict[str, dict[str, str]],
    rng: np.random.Generator,
    resamples: int,
) -> list[dict[str, object]]:
    by_code: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        by_code.setdefault(row["code"].strip(), []).append(row)
    lookup = {
        (meta["dataset"], meta["run"], meta["condition"]): code
        for code, meta in mapping.items()
    }
    pairs = sorted({(meta["dataset"], meta["run"]) for meta in mapping.values()})
    records = []
    for dimension in DIMENSIONS:
        baseline = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[lookup[(dataset, run, "baseline")]])
            for dataset, run in pairs
        ], dtype=float)
        full_llm = np.array([
            statistics.mean(int(row[dimension]) for row in by_code[lookup[(dataset, run, "full_llm")]])
            for dataset, run in pairs
        ], dtype=float)
        differences = full_llm - baseline
        boot = []
        for _ in range(resamples):
            boot.append(float(np.mean(rng.choice(differences, size=len(differences), replace=True))))
        low, high = percentile_interval(boot)
        paired_t = stats.ttest_rel(full_llm, baseline)
        try:
            wilcoxon = stats.wilcoxon(full_llm, baseline, alternative="two-sided")
            wilcoxon_stat = float(wilcoxon.statistic)
            wilcoxon_p = float(wilcoxon.pvalue)
        except ValueError:
            wilcoxon_stat = math.nan
            wilcoxon_p = math.nan
        records.append({
            "dimension": dimension,
            "unit": "dataset_run_pair",
            "n_pairs": len(pairs),
            "mean_difference_full_minus_baseline": float(np.mean(differences)),
            "bootstrap_low": low,
            "bootstrap_high": high,
            "paired_t_statistic": float(paired_t.statistic),
            "paired_t_p": float(paired_t.pvalue),
            "wilcoxon_statistic": wilcoxon_stat,
            "wilcoxon_p": wilcoxon_p,
        })
    adjusted = holm_adjust([float(record["paired_t_p"]) for record in records])
    for record, value in zip(records, adjusted):
        record["paired_t_p_holm"] = value
    return records


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def git_revision(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def render_report(
    manifest: dict[str, object],
    agreement: list[dict[str, object]],
    comparisons: list[dict[str, object]],
) -> str:
    lines = [
        "# Analisi RQ1 — valutazione degli schemi",
        "",
        "## Stato del dataset",
        "",
        f"- Valutazioni: {manifest['n_ratings']}",
        f"- Valutatori: {manifest['n_evaluators']}",
        f"- Schemi: {manifest['n_schemas']}",
        f"- Scala: Likert {manifest['score_scale']}",
        f"- SHA-256 sorgente: `{manifest['source_sha256']}`",
        "- Commenti esclusi dall'analisi; nessuna risposta è marcata come imputata.",
        "- Cinque timestamp mancanti sono metadati non usati negli outcome RQ1.",
        "",
        "## Accordo fra valutatori",
        "",
        "| Dimensione | Alpha ordinale | IC bootstrap 95% | Accordo esatto | Accordo adiacente |",
        "|---|---:|---:|---:|---:|",
    ]
    for record in agreement:
        lines.append(
            f"| {record['dimension']} | {record['alpha_ordinal']:.3f} | "
            f"[{record['bootstrap_low']:.3f}, {record['bootstrap_high']:.3f}] | "
            f"{record['exact_agreement_pct']:.1f}% | {record['adjacent_agreement_pct']:.1f}% |"
        )
    lines.extend([
        "",
        "## Confronto primario fra condizioni",
        "",
        "L'unità del confronto è lo schema: i 45 giudizi sono aggregati per schema "
        "prima del test, evitando di trattare 1.350 misure ripetute come indipendenti.",
        "",
        "| Dimensione | Baseline | Full LLM | Differenza | IC bootstrap 95% | p Holm | Cohen d |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ])
    for record in comparisons:
        lines.append(
            f"| {record['dimension']} | {record['baseline_mean']:.3f} | "
            f"{record['full_llm_mean']:.3f} | "
            f"{record['mean_difference_full_minus_baseline']:.3f} | "
            f"[{record['bootstrap_low']:.3f}, {record['bootstrap_high']:.3f}] | "
            f"{record['t_p_holm']:.4g} | {record['cohen_d']:.3f} |"
        )
    lines.extend([
        "",
        "## Deviazioni e limiti da riportare",
        "",
        "- Il piano descriveva tre esperti; il dataset osservato contiene 45 valutatori.",
        "- La scala effettiva e validata dall'applicazione è 1–5, non 0–4.",
        "- I punteggi mostrano un forte effetto soffitto; distribuzioni e percentuale di 5 "
        "devono accompagnare medie e test.",
        "- Le etichette osservate sono `baseline` e `full_llm`; la loro interpretazione "
        "deve rimanere coerente con il manifesto dei run originari.",
        "- La sensibilità appaiata per dataset/run è esportata separatamente e non "
        "sostituisce il confronto primario pianificato.",
        "",
        "Questo report è un artefatto analitico riproducibile, non una conferma "
        "retrospettiva della preregistrazione o dell'idoneità dei valutatori.",
        "",
    ])
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument(
        "--mapping", type=Path,
        default=Path("reports/rq1_expert_package/mapping.csv"),
    )
    parser.add_argument("--output", type=Path, default=Path("reports/rq1_analysis"))
    parser.add_argument("--seed", type=int, default=20261103)
    parser.add_argument("--bootstrap-resamples", type=int, default=5000)
    args = parser.parse_args(argv)

    rows = read_csv_auto(args.input)
    mapping = load_mapping(args.mapping)
    evaluators, codes = validate_rows(rows, mapping)
    args.output.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(args.seed)

    matrices = {
        dimension: score_matrix(rows, evaluators, codes, dimension)
        for dimension in DIMENSIONS
    }
    agreement = [
        agreement_record(dimension, [matrices[dimension]], rng, args.bootstrap_resamples)
        for dimension in DIMENSIONS
    ]
    agreement.append(
        agreement_record("overall", list(matrices.values()), rng, args.bootstrap_resamples)
    )

    summaries = []
    groups = [("overall", "all", "all")]
    groups.extend(("condition", "all", condition) for condition in sorted({row["condition"] for row in rows}))
    groups.extend(("dataset", dataset, "all") for dataset in sorted({row["dataset"] for row in rows}))
    groups.extend(
        ("dataset_condition", dataset, condition)
        for dataset in sorted({row["dataset"] for row in rows})
        for condition in sorted({row["condition"] for row in rows})
    )
    for group_type, dataset, condition in groups:
        for dimension in DIMENSIONS:
            summaries.append(summary_record(
                rows, group_type, dataset, condition, dimension
            ))

    comparisons = condition_comparisons(
        rows, mapping, rng, args.bootstrap_resamples
    )
    sensitivity = paired_sensitivity(
        rows, mapping, rng, args.bootstrap_resamples
    )

    evaluator_ids = {
        evaluator: f"E{index:03d}" for index, evaluator in enumerate(evaluators, 1)
    }
    pseudonymized = []
    for row in sorted(rows, key=lambda item: (evaluator_ids[item["evaluator"].strip()], item["code"].strip())):
        pseudonymized.append({
            "evaluator_id": evaluator_ids[row["evaluator"].strip()],
            "code": row["code"].strip(),
            "dataset": row["dataset"].strip(),
            "condition": row["condition"].strip(),
            "run": row["run"].strip(),
            **{dimension: int(row[dimension]) for dimension in DIMENSIONS},
            "updated_at": (row.get("updated_at") or "").strip(),
        })

    repository_root = Path(__file__).resolve().parent.parent
    manifest = {
        "artifact_status": "observed_analysis",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_file": args.input.name,
        "source_sha256": sha256_file(args.input),
        "mapping_sha256": sha256_file(args.mapping),
        "software_revision": git_revision(repository_root),
        "analysis_script_sha256": sha256_file(Path(__file__)),
        "seed": args.seed,
        "bootstrap_resamples": args.bootstrap_resamples,
        "score_scale": "1-5",
        "n_ratings": len(rows),
        "n_evaluators": len(evaluators),
        "n_schemas": len(codes),
        "conditions": sorted({row["condition"].strip() for row in rows}),
        "datasets": sorted({row["dataset"].strip() for row in rows}),
        "blank_updated_at": sum(not (row.get("updated_at") or "").strip() for row in rows),
        "comments_included": False,
        "responses_marked_as_imputed": False,
    }

    write_csv(args.output / "ratings_pseudonymized.csv", pseudonymized)
    write_csv(args.output / "descriptive_summary.csv", summaries)
    write_csv(args.output / "agreement.csv", agreement)
    write_csv(args.output / "condition_comparison.csv", comparisons)
    write_csv(args.output / "paired_sensitivity.csv", sensitivity)
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
        "source_sha256": manifest["source_sha256"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
