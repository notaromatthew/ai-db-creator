import json
import sqlite3
import threading
import zipfile
from pathlib import Path

import pytest

from analyze_experiment import analyze, holm, raw_nasa_tlx, sus_score
from app.evaluation.functional_workload import evaluate_workload
from app.api.dependencies import endpoint_capability
from app.services.experiment_service import CAPABILITIES, ExperimentService
from app.services.rq4_events import export_participant_events, normalise_event
from export_benchmark_package import export_package, verify_package
from participant_simulator import simulate
from validate_datasets import main as validate_main


def test_workload_is_exploratory_until_frozen_and_scores_facts_and_cells():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table item(id integer primary key, value text)")
    conn.executemany("insert into item values (?, ?)", [(1, "a"), (2, "wrong")])
    workload = {"approval_status": "draft", "queries": [{"id": "q1", "sql": "select id,value from item",
        "expected": {"columns": ["id", "value"], "rows": [[1, "a"], [2, "b"]]}}]}
    result = evaluate_workload(conn, workload)
    assert result["status"] == "exploratory_only"
    assert result["answer_fact_metrics"] == {"tp": 1, "fp": 1, "fn": 1, "precision": .5, "recall": .5, "f1": .5}
    assert result["answer_cell_metrics"]["tp"] == 3
    assert result["answer_cell_metrics"]["fp"] == result["answer_cell_metrics"]["fn"] == 1
    assert result["exact_answer_set_match_rate"] == 0
    workload["approval_status"] = "frozen"
    from app.utils.research import stable_hash
    approved = stable_hash({key: value for key, value in workload.items() if key not in {"config_hash", "freeze"}})
    workload["config_hash"] = "caller-controlled-wrong-value"
    workload["freeze"] = {"approved_at": "2026-01-01Z", "approved_by": "researcher", "config_hash": approved}
    assert evaluate_workload(conn, workload)["status"] == "confirmatory_eligible"


def test_failed_workload_query_counts_expected_answers_as_missing():
    result = evaluate_workload(sqlite3.connect(":memory:"), {"approval_status": "draft", "queries": [
        {"id": "bad", "sql": "select * from absent", "expected": {"columns": ["x"], "rows": [[1], [2]]}}
    ]})
    assert result["query_success_rate"] == 0
    assert result["answer_fact_metrics"]["fn"] == 2
    assert result["answer_cell_metrics"]["fn"] == 2


def test_workload_rejects_mutating_sql():
    conn = sqlite3.connect(":memory:")
    conn.execute("create table item(value integer)")
    conn.execute("insert into item values (1)")
    result = evaluate_workload(conn, {"queries": [{"id": "bad", "sql": "delete from item", "expected": {"columns": [], "rows": []}}]})
    assert result["queries"][0]["status"] == "error"
    assert conn.execute("select count(*) from item").fetchone()[0] == 1


def test_dataset_validator_cli_is_nonzero_for_invalid_fixture(tmp_path):
    (tmp_path / "invalid").mkdir()
    assert validate_main(["--datasets", str(tmp_path)]) == 1


def test_experiment_assignment_idempotent_concurrent_and_withdrawal_erases(tmp_path):
    store = tmp_path / "sessions.json"
    erased = []
    services = [ExperimentService(store, project_eraser=erased.append), ExperimentService(store, project_eraser=erased.append)]
    results = []
    threads = [threading.Thread(target=lambda svc=services[i % 2]: results.append(svc.start("subject", "p1", "draft-v1"))) for i in range(12)]
    for thread in threads: thread.start()
    for thread in threads: thread.join()
    assert len({item["session_id"] for item in results}) == 1
    session = results[0]
    artifact = tmp_path / "experiment_artifacts" / session["session_id"] / "surveys" / "x.json"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("{}")
    services[0].transition("subject", "withdrawn")
    assert not artifact.parent.parent.exists()
    assert erased == ["p1"] and "subject_key" not in session


def test_withdrawal_erases_only_bound_project(tmp_path):
    project_a = tmp_path / "projects" / "a"
    project_b = tmp_path / "projects" / "b"
    project_a.mkdir(parents=True); project_b.mkdir(parents=True)
    (project_a / "db.sqlite").write_text("a"); (project_b / "db.sqlite").write_text("b")
    erased = []
    def erase(project_id):
        erased.append(project_id)
        target = tmp_path / "projects" / project_id
        for path in target.iterdir(): path.unlink()
        target.rmdir()
    service = ExperimentService(tmp_path / "sessions.json", project_eraser=erase)
    service.start("subject-a", "a", "draft-v1")
    service.start("subject-b", "b", "draft-v1")
    service.transition("subject-a", "withdrawn")
    assert erased == ["a"] and not project_a.exists() and (project_b / "db.sqlite").exists()


def test_capability_policy_explicit_and_deny_default():
    assert endpoint_capability("/api/projects/p/chat", "POST") == "chat"
    assert endpoint_capability("/api/projects/p/import-sql", "POST") == "import_sql"
    assert endpoint_capability("/api/projects/p/unknown", "POST") == "deny_mutation"
    matrix = {
        ("/api/projects/p/chat", "POST"): {"ai_interface"},
        ("/api/projects/p/chat-accept", "POST"): {"ai_interface"},
        ("/api/projects/p/import-sql", "POST"): {"manual", "ai_interface"},
        ("/api/experiments/compare", "POST"): {"ai_only", "ai_interface"},
        ("/api/projects/p/unknown", "POST"): set(),
    }
    for (path, method), allowed in matrix.items():
        capability = endpoint_capability(path, method)
        assert {arm for arm, capabilities in CAPABILITIES.items() if capability in capabilities} == allowed
    assert {arm for arm, capabilities in CAPABILITIES.items() if "ai_generate" in capabilities} == {"ai_only", "ai_interface"}


def test_rq4_taxonomy_rejects_raw_and_export_is_deidentified(tmp_path):
    envelope = {"event_id": "e1", "sequence_no": 1, "monotonic_ms": 1, "operation_id": "o1",
                "duration_ms": 0, "app_revision": "test", "payload_schema_version": "rq4-envelope-v1"}
    with pytest.raises(ValueError): normalise_event({"type": "rename_column", "prompt": "secret"})
    with pytest.raises(ValueError): normalise_event({"type": "anything"})
    with pytest.raises(ValueError): normalise_event({"type": "navigation", "action": "arbitrary"})
    with pytest.raises(ValueError): normalise_event({"type": "navigation", "phase": "arbitrary"})
    safe = normalise_event({"type": "rename_column", "target_type": "column", "target_name": "email", **envelope})
    assert "target_name" not in safe and safe["target_hash"]
    output = export_participant_events([
        {"timestamp": "t", "project_id": "raw-project", "data": safe},
        {"timestamp": "t", "project_id": "p", "data": {"prompt": "must-not-export"}},
    ], tmp_path / "events")
    text = Path(output["json"]).read_text()
    assert "raw-project" not in text and "must-not-export" not in text and "email" not in text


def test_simulator_is_offline_and_covers_failures(tmp_path):
    report = simulate(tmp_path)
    assert report["status"] == "pass" and report["network_calls"] == 0


def test_statistics_scoring_and_multiplicity():
    assert sus_score([5, 1] * 5) == 100
    nasa = {key: 50 for key in ("mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration")}
    assert raw_nasa_tlx(nasa) == 50
    assert holm([.01, .04, .03]) == [.03, .06, .06]
    records = [{"participant_id": f"p{i}", "condition": condition, "status": "completed", "outcome": i + 1,
                "rq4_events": [{"type": "rename_column"}], "expert_ratings": [1 + i % 3, 2 + i % 3, 3 + i % 3]}
               for i, condition in enumerate(("manual", "manual", "ai_only", "ai_only", "ai_interface", "ai_interface"))]
    report = analyze(records)
    assert set(report["comparisons"]) == {"manual_vs_ai_interface", "ai_only_vs_ai_interface"}
    assert all("holm_adjusted_p_normal_approx" in value for value in report["comparisons"].values())
    assert report["rq4_exploratory"]["label"] == "exploratory_not_confirmatory"
    assert report["inclusion_flow"]["by_arm"]["manual"]["input"] == 2
    assert report["ordinal_krippendorff_alpha_bootstrap_ci95"] == analyze(records)["ordinal_krippendorff_alpha_bootstrap_ci95"]


def test_statistics_flow_separates_missing_outcome_exclusion_and_analysis_denominators():
    records = []
    for arm in ("manual", "ai_only", "ai_interface"):
        records.extend([
            {"condition": arm, "status": "completed", "outcome": 1.0},
            {"condition": arm, "status": "completed"},
            {"condition": arm, "status": "completed", "outcome": "not-numeric"},
            {"condition": arm, "status": "completed", "outcome": 2.0, "excluded": True},
            {"condition": arm, "status": "timed_out"},
        ])
    report = analyze(records)
    for arm in ("manual", "ai_only", "ai_interface"):
        assert report["inclusion_flow"]["by_arm"][arm] == {
            "input": 5, "completed": 4, "noncompleted": 1,
            "missing_outcome": 2, "excluded": 1, "analysis_n": 1,
        }
        assert report["descriptive"][arm]["n"] == 1
    assert report["inclusion_flow"]["analysis_n"] == 3
    assert report["comparisons"]["manual_vs_ai_interface"]["bootstrap"]["status"] == "ok"
    assert report["comparisons"]["ai_only_vs_ai_interface"]["bootstrap"]["status"] == "ok"
    assert report["comparisons"]["manual_vs_ai_interface"]["analysis_n"] == {"manual": 1, "ai_interface": 1}
    assert report["comparisons"]["ai_only_vs_ai_interface"]["analysis_n"] == {"ai_only": 1, "ai_interface": 1}


def test_reproducibility_package_rejects_raw_and_detects_tamper(tmp_path):
    source = tmp_path / "safe"
    source.mkdir()
    (source / "result.json").write_text('{"metric": 1}')
    package = tmp_path / "result.zip"
    export_package(source, package)
    assert verify_package(package)["status"] == "valid"
    tampered = tmp_path / "tampered.zip"
    with zipfile.ZipFile(package) as source_zip, zipfile.ZipFile(tampered, "w") as target_zip:
        for info in source_zip.infolist():
            payload = b'{"metric": 2}' if info.filename == "result.json" else source_zip.read(info.filename)
            target_zip.writestr(info, payload)
    assert verify_package(tampered)["status"] == "invalid"
    (source / "raw.json").write_text('{"prompt": "sensitive"}')
    with pytest.raises(ValueError): export_package(source, tmp_path / "unsafe.zip")


def test_verifier_rejects_extra_and_traversal_entries(tmp_path):
    from app.utils.research import stable_hash
    package = tmp_path / "bad.zip"
    manifest = {"package_version": "benchmark-package-v1", "files": []}
    manifest["content_hash"] = stable_hash(manifest)
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("MANIFEST.json", json.dumps(manifest))
        archive.writestr("../extra.txt", "x")
    reasons = {item["reason"] for item in verify_package(package)["failures"]}
    assert {"unsafe_path", "file_set_mismatch"} <= reasons


def test_verifier_rejects_duplicate_manifest_paths(tmp_path):
    import hashlib
    from app.utils.research import stable_hash
    payload = b'{"metric": 1}'
    entry = {"path": "result.json", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}
    manifest = {"package_version": "benchmark-package-v1", "files": [entry, entry]}
    manifest["content_hash"] = stable_hash(manifest)
    package = tmp_path / "duplicate-manifest.zip"
    with zipfile.ZipFile(package, "w") as archive:
        archive.writestr("MANIFEST.json", json.dumps(manifest)); archive.writestr("result.json", payload)
    assert "duplicate_manifest_paths" in {item["reason"] for item in verify_package(package)["failures"]}
