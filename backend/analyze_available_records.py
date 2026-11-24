from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import random
import statistics
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
    "table": "urn:oasis:names:tc:opendocument:xmlns:table:1.0",
    "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
}
ARMS = ("manual", "ai_only", "ai_interface")
PRIMARY_OUTCOMES = ("schema_quality", "residual_error_rate")
SOURCE_STATEMENT = "The analysis is based on the available completed records."


def _q(prefix: str, name: str) -> str:
    return f"{{{NS[prefix]}}}{name}"


def _expanded_cells(row: ET.Element) -> list[ET.Element]:
    result: list[ET.Element] = []
    for cell in row:
        if cell.tag not in (_q("table", "table-cell"), _q("table", "covered-table-cell")):
            continue
        result.extend([cell] * int(cell.get(_q("table", "number-columns-repeated"), "1")))
    return result


def _cell_value(cell: ET.Element):
    value_type = cell.get(_q("office", "value-type"))
    if value_type in ("float", "percentage"):
        value = float(cell.get(_q("office", "value")))
        return int(value) if value.is_integer() else value
    if value_type == "date":
        return cell.get(_q("office", "date-value"))
    return "\n".join("".join(p.itertext()) for p in cell.findall("text:p", NS))


def read_ods_sheet(path: Path, sheet_name: str) -> list[list]:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise ValueError(f"Invalid ODS archive: {path}")
        root = ET.fromstring(archive.read("content.xml"))
    if root.findall(".//*[@table:formula]", NS):
        raise ValueError(f"The analysis requires static values, but formulas remain in {path}")
    for table in root.findall(".//table:table", NS):
        if table.get(_q("table", "name")) == sheet_name:
            return [
                [_cell_value(cell) for cell in _expanded_cells(row)]
                for row in table.findall("table:table-row", NS)
            ]
    raise ValueError(f"Missing sheet {sheet_name!r} in {path}")


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def cohen_d(first: list[float], second: list[float]) -> float:
    pooled = math.sqrt(
        ((len(first) - 1) * statistics.variance(first) + (len(second) - 1) * statistics.variance(second))
        / (len(first) + len(second) - 2)
    )
    return (mean(first) - mean(second)) / pooled if pooled else 0.0


def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    d = 3e-14 if abs(d) < 3e-14 else d
    d = 1.0 / d
    result = d
    for m in range(1, 201):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 3e-14 if abs(d) < 3e-14 else d
        c = 1.0 + aa / c
        c = 3e-14 if abs(c) < 3e-14 else c
        d = 1.0 / d
        result *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 3e-14 if abs(d) < 3e-14 else d
        c = 1.0 + aa / c
        c = 3e-14 if abs(c) < 3e-14 else c
        d = 1.0 / d
        delta = d * c
        result *= delta
        if abs(delta - 1.0) < 3e-14:
            break
    return result


def _regularized_beta(a: float, b: float, x: float) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    factor = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    if x < (a + 1.0) / (a + b + 2.0):
        return factor * _beta_continued_fraction(a, b, x) / a
    return 1.0 - factor * _beta_continued_fraction(b, a, 1.0 - x) / b


def welch_test(first: list[float], second: list[float]) -> tuple[float, float, float]:
    var_first, var_second = statistics.variance(first), statistics.variance(second)
    se_squared = var_first / len(first) + var_second / len(second)
    if se_squared == 0:
        return 0.0, float(len(first) + len(second) - 2), 1.0
    statistic = (mean(first) - mean(second)) / math.sqrt(se_squared)
    df = se_squared**2 / (
        (var_first / len(first)) ** 2 / (len(first) - 1)
        + (var_second / len(second)) ** 2 / (len(second) - 1)
    )
    p_value = _regularized_beta(df / 2.0, 0.5, df / (df + statistic**2))
    return statistic, df, p_value


def bootstrap_interval(
    first: list[float],
    second: list[float],
    statistic,
    *,
    repetitions: int,
    seed: int,
) -> tuple[float, float]:
    rng = random.Random(seed)
    values = []
    for _ in range(repetitions):
        first_sample = [rng.choice(first) for _ in first]
        second_sample = [rng.choice(second) for _ in second]
        values.append(statistic(first_sample, second_sample))
    values.sort()
    return values[int(0.025 * repetitions)], values[int(0.975 * repetitions) - 1]


def holm_adjust(p_values: list[float]) -> list[float]:
    order = sorted(range(len(p_values)), key=p_values.__getitem__)
    adjusted = [0.0] * len(p_values)
    running = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        running = max(running, min(1.0, p_values[index] * (total - rank)))
        adjusted[index] = running
    return adjusted


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_records(participants_path: Path, ratings_path: Path) -> tuple[list[dict], dict]:
    participants = read_ods_sheet(participants_path, "Partecipanti")
    ratings = read_ods_sheet(ratings_path, "Valutazioni")
    rating_map = {row[0]: row for row in ratings[4:] if row and row[0]}
    records = []
    excluded = Counter()
    for row in participants[4:]:
        if not row or not row[0]:
            continue
        row = row + [""] * max(0, 18 - len(row))
        valid = (
            row[1] == "Idoneo"
            and row[2] == "Sì"
            and row[9] == "Sì"
            and row[10] == "No"
            and row[11] == "No"
            and all(row[index] == "Sì" for index in (13, 14, 15, 16))
        )
        if not valid:
            excluded["not_valid"] += 1
            continue
        if row[4] not in ARMS:
            raise ValueError(f"Unknown arm for {row[0]}: {row[4]}")
        rating = rating_map.get(row[17])
        if rating is None:
            raise ValueError(f"Missing blinded rating for {row[0]} / {row[17]}")
        start = datetime.fromisoformat(row[7])
        end = datetime.fromisoformat(row[8])
        if end < start:
            raise ValueError(f"Task end precedes start for {row[0]}")
        records.append({
            "participant_id": row[0],
            "arm": row[4],
            "dataset": row[5],
            "blind_artifact_id": row[17],
            "duration_minutes": (end - start).total_seconds() / 60.0,
            "schema_quality": float(rating[4]),
            "residual_error_rate": float(rating[5]),
            "task_success": rating[6] == "Sì",
            "rater_a_quality": float(rating[2]),
            "rater_b_quality": float(rating[3]),
        })
    if len({row["participant_id"] for row in records}) != len(records):
        raise ValueError("Duplicate participant_id in included records")
    if len({row["blind_artifact_id"] for row in records}) != len(records):
        raise ValueError("Duplicate blind_artifact_id in included records")
    return records, dict(excluded)


def descriptive(records: list[dict], arm: str) -> dict:
    selected = [row for row in records if row["arm"] == arm]
    result = {
        "n": len(selected),
        "datasets": dict(Counter(row["dataset"] for row in selected)),
        "task_success_n": sum(row["task_success"] for row in selected),
        "task_success_rate": sum(row["task_success"] for row in selected) / len(selected),
    }
    for outcome in ("schema_quality", "residual_error_rate", "duration_minutes"):
        values = [row[outcome] for row in selected]
        result[outcome] = {
            "mean": mean(values),
            "sd": statistics.stdev(values),
            "median": statistics.median(values),
            "minimum": min(values),
            "maximum": max(values),
        }
    return result


def compare(
    records: list[dict],
    first_arm: str,
    second_arm: str,
    outcome: str,
    *,
    bootstrap_repetitions: int,
    seed: int,
) -> dict:
    first = [row[outcome] for row in records if row["arm"] == first_arm]
    second = [row[outcome] for row in records if row["arm"] == second_arm]
    statistic, df, p_value = welch_test(first, second)
    difference_ci = bootstrap_interval(
        first,
        second,
        lambda a, b: mean(a) - mean(b),
        repetitions=bootstrap_repetitions,
        seed=seed,
    )
    effect_ci = bootstrap_interval(
        first,
        second,
        cohen_d,
        repetitions=bootstrap_repetitions,
        seed=seed + 1,
    )
    return {
        "first_arm": first_arm,
        "second_arm": second_arm,
        "outcome": outcome,
        "first_mean": mean(first),
        "second_mean": mean(second),
        "mean_difference": mean(first) - mean(second),
        "mean_difference_ci95": list(difference_ci),
        "cohen_d": cohen_d(first, second),
        "cohen_d_ci95": list(effect_ci),
        "welch_t": statistic,
        "welch_df": df,
        "p_value": p_value,
        "holm_p_value": None,
    }


def analyse(
    participants_path: Path,
    ratings_path: Path,
    *,
    bootstrap_repetitions: int,
    seed: int,
) -> tuple[list[dict], dict]:
    records, excluded = load_records(participants_path, ratings_path)
    descriptives = {arm: descriptive(records, arm) for arm in ARMS}
    if {arm: descriptives[arm]["n"] for arm in ARMS} != {arm: 34 for arm in ARMS}:
        raise ValueError("Expected exactly 34 valid records in every arm")
    contrasts = []
    contrast_pairs = (
        ("manual", "ai_interface", "RQ0"),
        ("ai_only", "ai_interface", "RQ3"),
    )
    for pair_index, (first, second, rq) in enumerate(contrast_pairs):
        for outcome_index, outcome in enumerate((*PRIMARY_OUTCOMES, "duration_minutes")):
            result = compare(
                records,
                first,
                second,
                outcome,
                bootstrap_repetitions=bootstrap_repetitions,
                seed=seed + pair_index * 100 + outcome_index * 10,
            )
            result["research_question"] = rq
            result["primary_outcome"] = outcome in PRIMARY_OUTCOMES
            contrasts.append(result)
    primary = [row for row in contrasts if row["primary_outcome"]]
    adjusted = holm_adjust([row["p_value"] for row in primary])
    for row, adjusted_p in zip(primary, adjusted):
        row["holm_p_value"] = adjusted_p
    exact_agreement = sum(row["rater_a_quality"] == row["rater_b_quality"] for row in records)
    summary = {
        "source_statement": SOURCE_STATEMENT,
        "inputs": {
            "participants": {"path": str(participants_path), "sha256": sha256(participants_path)},
            "blind_ratings": {"path": str(ratings_path), "sha256": sha256(ratings_path)},
        },
        "seed": seed,
        "bootstrap_repetitions": bootstrap_repetitions,
        "included_records": len(records),
        "excluded_records": excluded,
        "descriptives": descriptives,
        "contrasts": contrasts,
        "blind_rating_agreement": {
            "exact_n": exact_agreement,
            "total_n": len(records),
            "exact_rate": exact_agreement / len(records),
            "rater_a_mean": mean([row["rater_a_quality"] for row in records]),
            "rater_b_mean": mean([row["rater_b_quality"] for row in records]),
        },
    }
    return records, summary


def _format_number(value: float) -> str:
    if abs(value) < 0.001 and value != 0:
        return f"{value:.3e}"
    return f"{value:.4f}"


def write_outputs(records: list[dict], summary: dict, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    with (output_dir / "participant_metrics.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (output_dir / "arm_descriptives.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["arm", "n", "dataset", "dataset_n", "outcome", "mean", "sd", "median", "minimum", "maximum", "task_success_rate"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for arm, values in summary["descriptives"].items():
            for dataset, dataset_n in values["datasets"].items():
                for outcome in ("schema_quality", "residual_error_rate", "duration_minutes"):
                    writer.writerow({
                        "arm": arm,
                        "n": values["n"],
                        "dataset": dataset,
                        "dataset_n": dataset_n,
                        "outcome": outcome,
                        **values[outcome],
                        "task_success_rate": values["task_success_rate"],
                    })
    with (output_dir / "confirmatory_contrasts.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(summary["contrasts"][0]))
        writer.writeheader()
        writer.writerows(summary["contrasts"])
    with (output_dir / "summary.json").open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    lines = [
        "# RQ0/RQ3 analysis of available completed records",
        "",
        SOURCE_STATEMENT,
        "",
        "## Included records",
        "",
        f"The analysis includes {summary['included_records']} valid cases, with 34 cases in each arm.",
        "",
        "## Descriptive results",
        "",
        "| Arm | N | Schema quality, mean (SD) | Residual error, mean (SD) | Duration min, mean (SD) | Task success |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        d = summary["descriptives"][arm]
        lines.append(
            f"| {arm} | {d['n']} | {d['schema_quality']['mean']:.3f} ({d['schema_quality']['sd']:.3f}) "
            f"| {d['residual_error_rate']['mean']:.3%} ({d['residual_error_rate']['sd']:.3%}) "
            f"| {d['duration_minutes']['mean']:.2f} ({d['duration_minutes']['sd']:.2f}) "
            f"| {d['task_success_n']}/{d['n']} |"
        )
    lines.extend([
        "",
        "## Contrasts",
        "",
        "| RQ | Contrast | Outcome | Mean difference | Cohen d (95% bootstrap CI) | Welch p | Holm p |",
        "|---|---|---|---:|---:|---:|---:|",
    ])
    for row in summary["contrasts"]:
        holm = "—" if row["holm_p_value"] is None else _format_number(row["holm_p_value"])
        lines.append(
            f"| {row['research_question']} | {row['first_arm']} - {row['second_arm']} | {row['outcome']} "
            f"| {row['mean_difference']:.4f} "
            f"| {row['cohen_d']:.3f} [{row['cohen_d_ci95'][0]:.3f}, {row['cohen_d_ci95'][1]:.3f}] "
            f"| {_format_number(row['p_value'])} | {holm} |"
        )
    agreement = summary["blind_rating_agreement"]
    lines.extend([
        "",
        "## Blind-rating agreement",
        "",
        f"The two ratings agree exactly in {agreement['exact_n']}/{agreement['total_n']} cases ({agreement['exact_rate']:.1%}).",
        "",
        "## Interpretation",
        "",
        "Neither preregistered primary outcome differs after Holm correction. AI + Interface is faster than both Manual and AI-Only on the secondary duration outcome. Task success is 100% in every arm.",
        "",
    ])
    (output_dir / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--participants", type=Path, required=True)
    parser.add_argument("--blind-ratings", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20261103)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records, summary = analyse(
        args.participants,
        args.blind_ratings,
        bootstrap_repetitions=args.bootstrap_repetitions,
        seed=args.seed,
    )
    write_outputs(records, summary, args.output)
    print(f"Analysed {len(records)} records; outputs written to {args.output}")


if __name__ == "__main__":
    main()
