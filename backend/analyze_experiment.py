"""Dependency-light statistical pipeline for synthetic/pilot experiment records."""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def sus_score(values: list[int]) -> float:
    if len(values) != 10 or any(type(value) is not int or value < 1 or value > 5 for value in values):
        raise ValueError("SUS requires ten integer responses in 1..5")
    return sum(value - 1 if index % 2 == 0 else 5 - value for index, value in enumerate(values)) * 2.5


def raw_nasa_tlx(values: dict) -> float:
    keys = {"mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration"}
    if set(values) != keys or any(type(value) not in {int, float} or value < 0 or value > 100 for value in values.values()):
        raise ValueError("Raw NASA-TLX requires six 0..100 responses")
    return statistics.mean(values.values())


def cohen_d(a: list[float], b: list[float]) -> float | None:
    if len(a) < 2 or len(b) < 2:
        return None
    pooled = math.sqrt(((len(a)-1)*statistics.variance(a) + (len(b)-1)*statistics.variance(b)) / (len(a)+len(b)-2))
    return round((statistics.mean(a)-statistics.mean(b))/pooled, 4) if pooled else 0.0


def welch_t(a: list[float], b: list[float]) -> dict:
    if len(a) < 2 or len(b) < 2:
        return {"status": "insufficient_data"}
    va, vb = statistics.variance(a), statistics.variance(b)
    se = math.sqrt(va/len(a) + vb/len(b))
    t = (statistics.mean(a)-statistics.mean(b))/se if se else 0.0
    # Normal approximation is labelled; scipy is intentionally optional.
    p = math.erfc(abs(t)/math.sqrt(2))
    return {"status": "ok", "t": round(t, 4), "p_normal_approx": round(p, 6),
            "assumption_tests": "not_run_dependency_free"}


def mann_whitney(a: list[float], b: list[float]) -> dict:
    combined = sorted([(value, 0) for value in a] + [(value, 1) for value in b])
    ranks = []
    index = 0
    while index < len(combined):
        end = index
        while end + 1 < len(combined) and combined[end + 1][0] == combined[index][0]:
            end += 1
        rank = (index + end + 2) / 2
        ranks.extend((combined[pos][1], rank) for pos in range(index, end + 1))
        index = end + 1
    rank_a = sum(rank for group, rank in ranks if group == 0)
    u = rank_a - len(a)*(len(a)+1)/2
    return {"u": round(u, 4)}


def holm(p_values: list[float]) -> list[float]:
    ordered = sorted(enumerate(p_values), key=lambda item: item[1])
    adjusted = [0.0] * len(p_values)
    previous = 0.0
    for rank, (index, value) in enumerate(ordered):
        previous = max(previous, min(1.0, (len(p_values)-rank)*value))
        adjusted[index] = previous
    return adjusted


def ordinal_krippendorff_alpha(items: list[list[int]]) -> float | None:
    pairs = [(a, b) for ratings in items for i, a in enumerate(ratings) for b in ratings[i+1:]]
    values = [value for ratings in items for value in ratings]
    if not pairs or len(set(values)) < 2:
        return None
    low, high = min(values), max(values)
    distance = lambda a, b: ((a-b)/(high-low))**2
    observed = statistics.mean(distance(a, b) for a, b in pairs)
    counts = Counter(values)
    total = len(values)
    expected = sum((counts[a]/total)*(counts[b]/total)*distance(a, b) for a in counts for b in counts)
    return round(1-observed/expected, 4) if expected else None


def bootstrap_alpha_ci(items: list[list[int]], runs: int = 1000) -> list[float] | None:
    if len(items) < 2 or ordinal_krippendorff_alpha(items) is None:
        return None
    rng = random.Random(20260812)
    values = [ordinal_krippendorff_alpha([rng.choice(items) for _ in items]) for _ in range(runs)]
    values = sorted(value for value in values if value is not None)
    if not values:
        return None
    return [values[int(.025 * len(values))], values[min(len(values) - 1, int(.975 * len(values)))]]


def bootstrap_mean_difference(records: list[dict], outcome: str, conditions: tuple[str, str], runs=1000) -> dict:
    rng = random.Random(20260812)
    groups = {condition: [record[outcome] for record in records if record.get("condition") == condition and outcome in record]
              for condition in conditions}
    if any(not values for values in groups.values()):
        return {"status": "insufficient_data"}
    diffs = []
    for _ in range(runs):
        samples = {condition: [rng.choice(values) for _ in values] for condition, values in groups.items()}
        diffs.append(statistics.mean(samples[conditions[0]])-statistics.mean(samples[conditions[1]]))
    diffs.sort()
    return {"status": "ok", "mean_difference": round(statistics.mean(groups[conditions[0]])-statistics.mean(groups[conditions[1]]), 4),
            "ci95": [round(diffs[int(.025*runs)], 4), round(diffs[int(.975*runs)-1], 4)],
            "resampling_unit": "participant"}


def analyze(records: list[dict]) -> dict:
    included = [record for record in records if record.get("status") == "completed" and not record.get("excluded")]
    def has_valid_outcome(record: dict) -> bool:
        value = record.get("outcome")
        return type(value) in {int, float} and math.isfinite(value)

    analysis_records = [record for record in included if has_valid_outcome(record)]
    flow = {"total": len(records), "completed": sum(r.get("status") == "completed" for r in records),
            "withdrawn": sum(r.get("status") == "withdrawn" for r in records),
            "timed_out": sum(r.get("status") == "timed_out" for r in records), "analysis_n": len(analysis_records),
            "counting_rules": "noncompleted, missing_outcome, and excluded are descriptive flags and may overlap; analysis_n is exclusively completed, nonexcluded, finite-numeric outcome"}
    flow["by_arm"] = {condition: {
        "input": sum(r.get("condition") == condition for r in records),
        "completed": sum(r.get("condition") == condition and r.get("status") == "completed" for r in records),
        "noncompleted": sum(r.get("condition") == condition and r.get("status") != "completed" for r in records),
        "missing_outcome": sum(r.get("condition") == condition and r.get("status") == "completed" and not has_valid_outcome(r) for r in records),
        "excluded": sum(r.get("condition") == condition and bool(r.get("excluded")) for r in records),
        "analysis_n": sum(r.get("condition") == condition and r in analysis_records for r in records),
    } for condition in ("manual", "ai_only", "ai_interface")}
    for record in included:
        if "sus" in record:
            record["sus_score"] = sus_score(record["sus"])
        if "nasa_tlx" in record:
            record["nasa_tlx_score"] = raw_nasa_tlx(record["nasa_tlx"])
    groups = defaultdict(list)
    for record in analysis_records:
        groups[record["condition"]].append(float(record["outcome"]))
    conditions = sorted(groups)
    comparisons = {}
    planned = (("manual", "ai_interface"), ("ai_only", "ai_interface"))
    p_values = []
    for a, b in planned:
        if a not in groups or b not in groups:
            comparisons[f"{a}_vs_{b}"] = {"status": "insufficient_data"}
            continue
        comparison = {"status": "exploratory_until_preregistered", "cohen_d": cohen_d(groups[a], groups[b]),
                      "analysis_n": {a: len(groups[a]), b: len(groups[b])},
                      "welch_t_normal_approximation": welch_t(groups[a], groups[b]),
                      "mann_whitney": mann_whitney(groups[a], groups[b]),
                      "bootstrap": bootstrap_mean_difference(analysis_records, "outcome", (a, b))}
        p_values.append((comparison, comparison["welch_t_normal_approximation"].get("p_normal_approx", 1.0)))
        comparisons[f"{a}_vs_{b}"] = comparison
    adjusted = holm([value for _, value in p_values])
    for (comparison, _), value in zip(p_values, adjusted):
        comparison["holm_adjusted_p_normal_approx"] = value
    alpha_items = [record["expert_ratings"] for record in included if record.get("expert_ratings")]
    rq4_events = [event for record in included for event in record.get("rq4_events", [])]
    frequencies = dict(Counter(event.get("type") for event in rq4_events if event.get("type")))
    by_outcome = defaultdict(list)
    for record in analysis_records:
        by_outcome[len(record.get("rq4_events", []))].append(record["outcome"])
    return {"analysis_status": "synthetic_or_exploratory", "inclusion_flow": flow,
            "descriptive": {condition: {"n": len(values), "mean": statistics.mean(values),
                                         "sd": statistics.stdev(values) if len(values)>1 else None}
                            for condition, values in groups.items()},
            "comparisons": comparisons, "ordinal_krippendorff_alpha": ordinal_krippendorff_alpha(alpha_items),
            "ordinal_krippendorff_alpha_bootstrap_ci95": bootstrap_alpha_ci(alpha_items),
            "rq4_exploratory": {"label": "exploratory_not_confirmatory", "event_frequencies": frequencies,
                                "outcome_by_event_count": {str(k): statistics.mean(v) for k, v in by_outcome.items()}},
            "records": analysis_records}


def write_outputs(result: dict, output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "analysis.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    with (output / "descriptive.csv").open("w", newline="", encoding="utf-8") as target:
        writer = csv.DictWriter(target, fieldnames=["condition", "n", "mean", "sd"])
        writer.writeheader()
        for condition, values in result["descriptive"].items():
            writer.writerow({"condition": condition, **values})
    rows = "\n".join(f"{key} & {value['n']} & {value['mean']:.3f} \\\\" for key, value in result["descriptive"].items())
    (output / "descriptive.tex").write_text("\\begin{tabular}{lrr}\nCondition & N & Mean \\\\ \n" + rows + "\n\\end{tabular}\n", encoding="utf-8")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = analyze(json.loads(args.input.read_text(encoding="utf-8")))
    write_outputs(result, args.output)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
