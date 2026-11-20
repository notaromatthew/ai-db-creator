import json

import pytest

from analyze_rq2_format_matrix import load_matrix, main


def build_matrix(root):
    protocol = {
        "datasets": ["demo"], "source_formats": ["csv", "txt"],
        "conditions": ["baseline", "full_llm"], "run_indices": [1, 2],
        "runs_per_cell": 2, "provider": "Google Gemini", "model": "demo-model",
        "software_revision": "rev", "temperature": 0.1,
    }
    (root / "protocol_manifest.json").write_text(json.dumps(protocol), encoding="utf-8")
    for source_format in protocol["source_formats"]:
        for condition in protocol["conditions"]:
            for run_index in protocol["run_indices"]:
                run_dir = root / "demo" / source_format / condition
                bundle = run_dir / f"run{run_index:02d}"
                bundle.mkdir(parents=True, exist_ok=True)
                failed = source_format == "csv" and condition == "full_llm" and run_index == 1
                record = {
                    "dataset": "demo", "source_format": source_format,
                    "condition": condition, "run": run_index,
                    "status": "error" if failed else "ok",
                    "error": "LLMException" if failed else None,
                    "population_mode": None if failed else "llm",
                    "global_precision": None if failed else 1.0,
                    "global_recall": None if failed else 1.0,
                    "global_f1": None if failed else 1.0,
                    "functional_query_pass_rate": None if failed else 1.0,
                    "functionally_equivalent": None if failed else True,
                }
                (run_dir / f"run{run_index:02d}.json").write_text(json.dumps(record), encoding="utf-8")
                (bundle / "manifest.json").write_text(json.dumps({
                    "dataset": "demo", "source_format": source_format,
                    "condition": condition, "run_index": run_index,
                    "provider": "Google Gemini", "model": "demo-model",
                    "software_revision": "rev", "parameters": {"temperature": 0.1},
                }), encoding="utf-8")


def test_format_analysis_validates_and_summarizes_complete_matrix(tmp_path):
    reports = tmp_path / "reports"
    output = tmp_path / "analysis"
    reports.mkdir()
    build_matrix(reports)
    assert main(["--reports", str(reports), "--output", str(output)]) == 0
    result = json.loads((output / "rq2_format_analysis.json").read_text(encoding="utf-8"))
    assert (result["n_runs"], result["n_ok"], result["n_error"]) == (8, 7, 1)
    csv_full = next(row for row in result["summary"] if row["source_format"] == "csv" and row["condition"] == "full_llm")
    assert csv_full["technical_success_rate"] == 0.5
    assert (output / "manifest.json").exists()


def test_format_analysis_rejects_missing_bundle(tmp_path):
    build_matrix(tmp_path)
    (tmp_path / "demo" / "txt" / "baseline" / "run02" / "manifest.json").unlink()
    with pytest.raises(ValueError, match="missing run artifacts"):
        load_matrix(tmp_path)
