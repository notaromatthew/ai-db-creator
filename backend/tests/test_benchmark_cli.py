import asyncio
import json
from pathlib import Path

import pytest

import aggregate_benchmark
import run_benchmark
from app.config import settings
from app.core import llm


def _record(status, **values):
    return {
        "dataset": "university", "condition": "full_llm", "source_format": "combined",
        "temperature": 0.1, "status": status, "error": values.pop("error", None),
        "adjudication": None, "global_precision": None, "global_recall": None,
        "global_f1": None, "total_cells": None, "missing_rows": None,
        "extra_rows": None, "functional_query_pass_rate": None, **values,
    }


def test_aggregate_mixed_outcomes_uses_descriptive_range_without_wilson():
    runner = run_benchmark.BenchmarkRunner.__new__(run_benchmark.BenchmarkRunner)
    summary = runner._aggregate([
        _record("ok", global_f1=0.5, global_precision=0.6, global_recall=0.4,
                total_cells=10, missing_rows=1, extra_rows=0),
        _record("ok", global_f1=0.9, global_precision=0.9, global_recall=0.9,
                total_cells=20, missing_rows=0, extra_rows=1),
        _record("not_evaluable", error="frozen mapping unavailable"),
        _record("error", error="provider unavailable"),
    ])
    assert (summary["n_evaluable"], summary["n_not_evaluable"], summary["n_error"]) == (2, 1, 1)
    assert summary["mean_total_cells"] == 15.0
    assert summary["f1_observed_range"] == [0.5, 0.9]
    assert "ci95_f1" not in summary


def test_main_returns_nonzero_when_a_run_errors(monkeypatch, capsys, tmp_path):
    class FakeRunner:
        def __init__(self, *_args, **_kwargs):
            self.output_dir = tmp_path
            self.temperature = 0.1

        async def run(self):
            return [_record("ok"), _record("not_evaluable"), _record("error")]

    monkeypatch.setattr(run_benchmark, "BenchmarkRunner", FakeRunner)
    assert run_benchmark.main(["--runs", "1"]) == 1
    output = json.loads(capsys.readouterr().out)
    assert (output["ok"], output["not_evaluable"], output["failed"]) == (1, 1, 1)


def test_parse_explicit_run_indices():
    assert run_benchmark.parse_run_indices("5,1,5") == [1, 5]
    assert run_benchmark.parse_run_indices("") is None
    with pytest.raises(ValueError):
        run_benchmark.parse_run_indices("0,2")


def test_provider_selection_and_google_dependency_fail_closed(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "unknown-provider")
    with pytest.raises(ValueError, match="Unsupported LLM provider"):
        llm.get_llm_info()
    monkeypatch.setattr(settings, "llm_provider", "google")
    real_import = __import__

    def reject_google(name, *args, **kwargs):
        if name == "langchain_google_genai":
            raise ImportError("missing for test")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", reject_google)
    with pytest.raises(RuntimeError, match="Google provider requested"):
        llm._get_llm()


def test_runtime_rate_limit_is_applied(monkeypatch):
    class Chain:
        async def ainvoke(self, payload):
            return payload

    monkeypatch.setattr(settings, "llm_cache_enabled", False)
    monkeypatch.setattr(settings, "llm_max_requests_per_minute", 3)
    assert asyncio.run(llm._invoke(Chain(), {"ok": True})) == {"ok": True}
    assert llm._llm_rate_limiter.max_per_minute == 3


def test_aggregate_export_uses_runner_cell_name_and_observed_range(tmp_path, capsys):
    reports = tmp_path / "reports" / "university"
    run_dir = reports / "full_llm"
    run_dir.mkdir(parents=True)
    (reports / "full_llm_summary.json").write_text(json.dumps({
        "dataset": "university", "condition": "full_llm", "n_runs": 1,
        "mean_f1": 0.75, "mean_precision": 0.8, "mean_recall": 0.7,
        "mean_total_cells": 42, "f1_observed_range": [0.75, 0.75],
    }), encoding="utf-8")
    (run_dir / "run01.json").write_text(json.dumps({
        "run": 1, "status": "ok", "global_f1": 0.75, "project_id": None,
    }), encoding="utf-8")
    output = tmp_path / "aggregate.json"
    assert aggregate_benchmark.main([
        "--reports", str(tmp_path / "reports"), "--output", str(output),
        "--projects", str(tmp_path / "projects"),
    ]) == 0
    payload = json.loads(output.read_text(encoding="utf-8"))["university/full_llm"]
    assert payload["mean_cells"] == 42
    assert payload["f1_observed_range"] == [0.75, 0.75]
    assert "ci95_f1" not in payload


def test_failure_manifest_keeps_precomputed_source_hashes(tmp_path, monkeypatch):
    dataset_root = tmp_path / "datasets" / "demo"
    source = dataset_root / "source"
    source.mkdir(parents=True)
    (source / "input.txt").write_text("source facts", encoding="utf-8")
    (dataset_root / "evaluation_spec.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(run_benchmark, "DATASETS_DIR", tmp_path / "datasets")
    runner = run_benchmark.BenchmarkRunner.__new__(run_benchmark.BenchmarkRunner)
    runner.output_dir = tmp_path / "output"
    runner.temperature = 0.1
    runner.adjudicate = False

    async def fail_before_return(*_args, **_kwargs):
        raise RuntimeError("schema provider failed")

    runner._create_populated_project = fail_before_return
    record = asyncio.run(runner._run_one("demo", "full_llm", 1))
    manifest = json.loads((tmp_path / "output/demo/full_llm/run01/manifest.json").read_text(encoding="utf-8"))
    assert record["status"] == "error"
    assert manifest["source_files"] == [{
        "path": "source/input.txt",
        "sha256": run_benchmark.sha256_file(source / "input.txt"),
    }]


def _write_resumable_run(root, run_index, status, provider, model, temperature=0.1):
    run_dir = root / "university" / "full_llm"
    bundle = run_dir / f"run{run_index:02d}"
    bundle.mkdir(parents=True, exist_ok=True)
    record = _record(status, run=run_index)
    (run_dir / f"run{run_index:02d}.json").write_text(json.dumps(record), encoding="utf-8")
    (bundle / "manifest.json").write_text(json.dumps({
        "dataset": "university", "condition": "full_llm",
        "source_format": "combined", "run_index": run_index,
        "provider": provider, "model": model,
        "parameters": {"temperature": temperature},
    }), encoding="utf-8")


def test_retry_failed_preserves_ok_and_not_evaluable_and_reruns_only_error(tmp_path, monkeypatch):
    info = llm.get_llm_info()
    for run_index, status in enumerate(("ok", "not_evaluable", "error"), 1):
        _write_resumable_run(tmp_path, run_index, status, info["provider"], info["model"])
    runner = run_benchmark.BenchmarkRunner.__new__(run_benchmark.BenchmarkRunner)
    runner.datasets = ["university"]
    runner.conditions = ["full_llm"]
    runner.source_formats = ["combined"]
    runner.runs = 3
    runner.output_dir = tmp_path
    runner.temperature = 0.1
    runner.resume = True
    runner.retry_failed = True
    runner.schedule = "blocked"
    runner.parallel = 1
    calls = []

    async def rerun(dataset, condition, run_index, source_format):
        calls.append((dataset, condition, run_index, source_format))
        return _record("ok", run=run_index)

    runner._run_one = rerun
    monkeypatch.setattr(runner, "_write_summary", lambda *_args: None)
    results = asyncio.run(runner.run())
    assert calls == [("university", "full_llm", 3, "combined")]
    assert sorted((record["run"], record["status"]) for record in results) == [
        (1, "ok"), (2, "not_evaluable"), (3, "ok"),
    ]


def test_retry_failed_validates_manifest_before_scheduling(tmp_path):
    info = llm.get_llm_info()
    _write_resumable_run(tmp_path, 1, "error", info["provider"], "wrong-model")
    runner = run_benchmark.BenchmarkRunner.__new__(run_benchmark.BenchmarkRunner)
    runner.datasets = ["university"]
    runner.conditions = ["full_llm"]
    runner.source_formats = ["combined"]
    runner.runs = 1
    runner.output_dir = tmp_path
    runner.temperature = 0.1
    runner.resume = True
    runner.retry_failed = True
    runner.schedule = "blocked"
    runner.parallel = 1
    with pytest.raises(ValueError, match="Resume configuration mismatch"):
        asyncio.run(runner.run())


def test_retry_failed_requires_resume(capsys):
    with pytest.raises(SystemExit) as error:
        run_benchmark.main(["--retry-failed"])
    assert error.value.code == 2
    assert "requires --resume" in capsys.readouterr().err
