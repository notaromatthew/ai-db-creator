import csv
import json

import pytest

from analyze_rq1_ratings import holm_adjust, main, validate_rows


DIMENSIONS = [
    "d1_3nf",
    "d2_naming",
    "d3_constraints",
    "d4_relationships",
    "d5_domain",
]


def _fixtures(tmp_path):
    mapping_path = tmp_path / "mapping.csv"
    ratings_path = tmp_path / "ratings.csv"
    mapping_rows = []
    for run in range(1, 4):
        mapping_rows.extend([
            {"code": f"B{run}", "dataset": "demo", "condition": "baseline", "run": f"run{run}"},
            {"code": f"F{run}", "dataset": "demo", "condition": "full_llm", "run": f"run{run}"},
        ])
    with mapping_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["code", "dataset", "condition", "run"])
        writer.writeheader()
        writer.writerows(mapping_rows)

    ratings = []
    for evaluator_index, evaluator in enumerate(["alice", "bob", "carol"]):
        for meta in mapping_rows:
            base = 1 if meta["condition"] == "baseline" else 2
            run_number = int(meta["run"].removeprefix("run"))
            score = min(5, base + run_number + (evaluator_index % 2))
            ratings.append({
                "evaluator": evaluator,
                **meta,
                **{dimension: score for dimension in DIMENSIONS},
                "comment": "removed",
                "updated_at": "",
            })
    with ratings_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(ratings[0]))
        writer.writeheader()
        writer.writerows(ratings)
    return ratings_path, mapping_path, ratings, {
        row["code"]: {key: row[key] for key in ("dataset", "condition", "run")}
        for row in mapping_rows
    }


def test_holm_adjustment_is_monotonic_in_rank_order():
    raw = [0.04, 0.001, 0.02, 0.8]
    adjusted = holm_adjust(raw)
    ranked = [adjusted[index] for index in sorted(range(len(raw)), key=raw.__getitem__)]
    assert ranked == sorted(ranked)
    assert adjusted[1] == pytest.approx(0.004)
    assert all(value >= raw[index] for index, value in enumerate(adjusted))


def test_validate_rejects_out_of_range_score(tmp_path):
    _, _, ratings, mapping = _fixtures(tmp_path)
    ratings[0]["d1_3nf"] = "0"
    with pytest.raises(ValueError, match="out-of-range"):
        validate_rows(ratings, mapping)


def test_analysis_writes_pseudonymized_reproducible_outputs(tmp_path):
    ratings_path, mapping_path, _, _ = _fixtures(tmp_path)
    output = tmp_path / "analysis"
    assert main([
        "--input", str(ratings_path),
        "--mapping", str(mapping_path),
        "--output", str(output),
        "--bootstrap-resamples", "50",
        "--seed", "7",
    ]) == 0

    with (output / "ratings_pseudonymized.csv").open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 18
    assert set(row["evaluator_id"] for row in rows) == {"E001", "E002", "E003"}
    assert "evaluator" not in rows[0]
    assert "imputed" not in rows[0]
    assert "comment" not in rows[0]

    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["n_ratings"] == 18
    assert manifest["n_evaluators"] == 3
    assert manifest["n_schemas"] == 6
    assert manifest["responses_marked_as_imputed"] is False
    assert (output / "agreement.csv").exists()
    assert (output / "condition_comparison.csv").exists()
    assert (output / "paired_sensitivity.csv").exists()
    assert (output / "REPORT.md").exists()
