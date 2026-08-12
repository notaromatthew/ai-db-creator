import json

import aggregate_benchmark


def test_aggregate_reads_mean_total_cells_from_runner_summary(tmp_path, monkeypatch):
    reports = tmp_path / "reports" / "university"
    runs = reports / "baseline"
    runs.mkdir(parents=True)
    (reports / "baseline_summary.json").write_text(json.dumps({
        "dataset": "university", "condition": "baseline", "n_runs": 1,
        "reporting_status": "exploratory_descriptive",
        "mean_primary_f1": 1.0, "mean_primary_precision": 1.0,
        "mean_primary_recall": 1.0, "mean_strict_f1": 1.0,
        "mean_total_cells": 42, "mean_missing_rows": 0, "mean_extra_rows": 0,
    }), encoding="utf-8")
    (runs / "run01.json").write_text(json.dumps({
        "run": 1, "status": "ok", "project_id": "p1",
        "primary_f1": 1.0, "primary_precision": 1.0, "primary_recall": 1.0,
        "strict_f1": 1.0, "total_cells": 42, "missing_rows": 0, "extra_rows": 0,
    }), encoding="utf-8")
    output = tmp_path / "aggregate.json"
    monkeypatch.setattr(aggregate_benchmark, "duplicate_rate_for_db", lambda *_args: 0.0)
    assert aggregate_benchmark.main([
        "--reports", str(tmp_path / "reports"), "--output", str(output),
        "--projects", str(tmp_path / "projects"),
    ]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["university/baseline"]["mean_cells"] == 42
