import hashlib
import json

import pytest

from analyze_rq2_format_recovered_sensitivity import load_post_recovery, main


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_bundle(root, source_format, run_index, status, protocol, value=1.0):
    run_dir = root / "demo" / source_format / "full_llm"
    bundle = run_dir / f"run{run_index:02d}"
    source = bundle / "source" / f"records.{source_format}"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("same facts", encoding="utf-8")
    record = {
        "dataset": "demo", "source_format": source_format, "condition": "full_llm", "run": run_index,
        "status": status, "error": "LLMException" if status == "error" else None,
        "population_mode": "llm" if status == "ok" else None,
        "global_precision": value if status == "ok" else None,
        "global_recall": value if status == "ok" else None,
        "global_f1": value if status == "ok" else None,
        "functional_query_pass_rate": value if status == "ok" else None,
        "functionally_equivalent": value == 1.0 if status == "ok" else None,
    }
    record_path = run_dir / f"run{run_index:02d}.json"
    record_path.write_text(json.dumps(record), encoding="utf-8")
    bundle_record = bundle / "run.json"
    bundle_record.write_text(json.dumps(record), encoding="utf-8")
    generated = bundle / "generated.db"
    if status == "ok":
        generated.write_bytes(b"sqlite-placeholder")
    artifacts = {"run_record": {"path": "run.json", "sha256": digest(bundle_record)}}
    if status == "ok":
        artifacts["generated_database"] = {"path": "generated.db", "sha256": digest(generated)}
    manifest = {
        "dataset": "demo", "source_format": source_format, "condition": "full_llm", "run_index": run_index,
        "provider": protocol["provider"], "model": protocol["model"],
        "software_revision": protocol["software_revision"], "schema_output_contract": protocol["schema_output_contract"],
        "parameters": {"temperature": protocol["temperature"]}, "status": status,
        "dataset_hash": "dataset", "prompts_hash": "prompt", "evaluation_spec_hash": "evaluation",
        "source_files": [{"path": f"source/records.{source_format}", "sha256": digest(source)}],
        "artifacts": artifacts,
    }
    (bundle / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return record_path, generated


def build_inputs(tmp_path):
    primary = tmp_path / "primary"
    recovery = tmp_path / "recovery"
    primary.mkdir()
    recovery.mkdir()
    protocol = {
        "datasets": ["demo"], "source_formats": ["csv", "xlsx"], "conditions": ["full_llm"],
        "run_indices": [1], "runs_per_cell": 1, "provider": "Google Gemini", "model": "demo-model",
        "software_revision": "rev", "temperature": 0.1, "schema_output_contract": "legacy-pydantic-v1",
        "max_output_tokens": 8192, "timeout_seconds": 120.0, "provider_retries": 0,
        "max_requests_per_minute": 8, "research_mode": True, "llm_cache_enabled": False,
        "parallel": 1, "adjudicate": False, "schedule": "interleaved",
    }
    (primary / "protocol_manifest.json").write_text(json.dumps(protocol), encoding="utf-8")
    entries = []
    for source_format in protocol["source_formats"]:
        primary_record, _ = write_bundle(primary, source_format, 1, "error", protocol)
        run_root = recovery / f"{source_format}_run01"
        recovery_protocol = dict(protocol)
        recovery_protocol.update({"source_formats": [source_format], "run_indices": [1], "runs_per_cell": 3})
        run_root.mkdir()
        (run_root / "protocol_manifest.json").write_text(json.dumps(recovery_protocol), encoding="utf-8")
        recovery_record, generated = write_bundle(run_root, source_format, 1, "ok", protocol, value=0.5)
        entries.append({
            "source_format": source_format, "run_index": 1,
            "primary_status": "error", "recovery_status": "ok", "population_mode": "llm",
            "global_f1": 0.5, "functional_query_pass_rate": 0.5, "functionally_equivalent": False,
            "primary_run_sha256": digest(primary_record), "recovery_run_sha256": digest(recovery_record),
            "generated_database_sha256": digest(generated),
        })
    provenance = {
        "recovery_type": "selective_failure_sensitivity", "primary_matrix": str(primary),
        "primary_result_remains": {"n_runs": 2, "ok": 0, "error": 2},
        "runs": entries, "interpretation": "technical recoverability only",
    }
    (recovery / "recovery_manifest.json").write_text(json.dumps(provenance), encoding="utf-8")
    return primary, recovery


def test_post_recovery_analysis_preserves_primary_and_overlays_errors(tmp_path):
    primary, recovery = build_inputs(tmp_path)
    output = tmp_path / "analysis"
    assert main(["--primary", str(primary), "--recovery", str(recovery), "--output", str(output)]) == 0
    result = json.loads((output / "rq2_format_post_recovery_sensitivity.json").read_text(encoding="utf-8"))
    assert result["primary_result_preserved"] == {"n_runs": 2, "n_ok": 0, "n_error": 2}
    assert result["post_recovery_result"] == {"n_runs": 2, "n_ok": 2, "n_error": 0}
    assert result["post_outcome"] is True
    assert "Analisi secondaria post-outcome" in (output / "REPORT.md").read_text(encoding="utf-8")


def test_post_recovery_analysis_rejects_tampered_recovery(tmp_path):
    primary, recovery = build_inputs(tmp_path)
    record = recovery / "csv_run01" / "demo" / "csv" / "full_llm" / "run01.json"
    record.write_text(record.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ValueError, match="recovery run hash"):
        load_post_recovery(primary, recovery)
