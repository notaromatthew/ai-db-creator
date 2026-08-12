import json
from pathlib import Path

import pytest

from app.services.allocation_service import CandidateAllocator
from candidate_allocation_dry_run import generate
from locked_candidate_analysis import analyze, write_outputs
from validate_research_candidates import ALLOCATION_PATH, SAP_PATH, SCHEMA_PATH, validate
from research_readiness import build_report


def test_candidate_allocator_balances_blocks_and_never_persists_seed(monkeypatch, tmp_path):
    monkeypatch.setenv("EXPERIMENT_ASSIGNMENT_SEED", "fixture-seed-not-for-study")
    enrolments = [{"participant_id": f"p{i}", "dataset_id": "university", "experience_stratum": "none"} for i in range(12)]
    output = tmp_path / "allocation-audit.json"
    report = generate(enrolments, output)
    stored = json.loads(output.read_text())
    assert "fixture-seed-not-for-study" not in json.dumps(stored)
    assert report["mode"] == "dry_run_only" and report["future_allocations_persisted"] is False
    assert all("position_in_block" not in item for item in report["assignments"])
    for block in {item["block_number"] for item in report["restricted_audit"]}:
        members = [item for item in report["restricted_audit"] if item["block_number"] == block]
        if len(members) in {3, 6}:
            counts = {arm: sum(item["condition"] == arm for item in members)
                      for arm in ("manual", "ai_only", "ai_interface")}
            assert len(set(counts.values())) == 1


def test_candidate_allocator_requires_environment_seed(monkeypatch):
    monkeypatch.delenv("EXPERIMENT_ASSIGNMENT_SEED", raising=False)
    with pytest.raises(RuntimeError, match="environment"):
        CandidateAllocator().assign([], "university", "none")


@pytest.mark.parametrize("enrolments", [
    [{"participant_id": "", "dataset_id": "university", "experience_stratum": "none"}],
    [{"participant_id": "p1", "dataset_id": "university", "experience_stratum": "none"},
     {"participant_id": "p1", "dataset_id": "hospital", "experience_stratum": "some"}],
    [{"participant_id": "p1", "dataset_id": "bad dataset", "experience_stratum": "none"}],
    [{"participant_id": "p1", "dataset_id": "university", "experience_stratum": "expert"}],
    [{"participant_id": "p1", "dataset_id": "university", "experience_stratum": "none", "condition": "manual"}],
])
def test_allocation_dry_run_rejects_invalid_or_duplicate_controlled_input(monkeypatch, tmp_path, enrolments):
    monkeypatch.setenv("EXPERIMENT_ASSIGNMENT_SEED", "fixture-seed")
    with pytest.raises(ValueError):
        generate(enrolments, tmp_path / "audit.json")


def test_locked_candidate_pipeline_is_deterministic_and_nonconfirmatory(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "analysis_input_v1.json"
    payload = json.loads(fixture.read_text())
    first = analyze(payload)
    second = analyze(payload)
    assert first == second
    assert first["analysis_status"] == "locked_candidate_unapproved"
    assert first["human_approval"] == "missing"
    assert first["analyses"]["rq0"]["estimate"] == 1.0
    assert first["analyses"]["rq3"]["estimate"] == 0.5
    assert first["analyses"]["rq2"]["estimate"] == 0.3
    assert set(first["analyses"]["rq1"]) == {"d1_3nf", "d2_naming", "d3_constraints", "d4_relationships", "d5_domain"}
    assert first["benchmark_flow"]["full_llm"] == {"success": 1, "failed": 1}
    manifest = write_outputs(payload, first, tmp_path, fixture)
    assert manifest["status"] == "locked_candidate_unapproved"
    assert set(manifest["files"]) == {"analysis-candidate.json", "decision-log.json"}


def test_candidate_validation_distinguishes_technical_readiness_from_approval():
    result = validate()
    assert result == {"status": "candidate_ready", "approval_status": "human_approval_missing",
                      "confirmatory_eligible": False, "failures": []}


@pytest.mark.parametrize(("mutation", "failure"), [
    (lambda value: value.update(arms=["manual", "ai_only", "ai_only"]), "allocation_arms_invalid"),
    (lambda value: value.update(ratio=[2, 1, 1]), "allocation_ratio_invalid"),
    (lambda value: value.update(strata=["dataset_id"]), "allocation_strata_invalid"),
    (lambda value: value.update(block_sizes=[2, 0]), "allocation_block_sizes_invalid"),
    (lambda value: value.update(seed_environment_variable="INLINE_SEED"), "allocation_seed_environment_invalid"),
    (lambda value: value.update(status="approved"), "allocation_status_invalid"),
    (lambda value: value.update(approval_status="approved"), "allocation_approval_boundary_invalid"),
])
def test_allocation_candidate_validator_rejects_mutated_contract(tmp_path, mutation, failure):
    allocation = json.loads(ALLOCATION_PATH.read_text())
    mutation(allocation)
    path = tmp_path / "allocation.json"
    path.write_text(json.dumps(allocation))
    result = validate(path, SAP_PATH, SCHEMA_PATH)
    assert result["status"] == "blocked" and failure in result["failures"]
    assert result["approval_status"] == "human_approval_missing" and result["confirmatory_eligible"] is False


@pytest.mark.parametrize(("mutation", "failure"), [
    (lambda value: value["primary_family"].update(multiplicity="none"), "sap_primary_multiplicity_invalid"),
    (lambda value: value["primary_family"]["analyses"][0].update(outcome="completion_time_ms"), "sap_rq0_invalid"),
    (lambda value: value["primary_family"]["analyses"][1].update(contrast=["manual", "ai_only"]), "sap_rq3_invalid"),
    (lambda value: value["rq1"].update(outcomes=["d1_3nf"]), "sap_rq1_invalid"),
    (lambda value: value["rq2"].update(model="linear"), "sap_rq2_invalid"),
    (lambda value: value["rq4"].update(multiplicity="holm"), "sap_rq4_invalid"),
    (lambda value: value.pop("missingness"), "sap_missingness_invalid"),
    (lambda value: value.update(approval_status="approved"), "sap_approval_boundary_invalid"),
])
def test_sap_candidate_validator_rejects_mutated_contract(tmp_path, mutation, failure):
    sap = json.loads(SAP_PATH.read_text())
    mutation(sap)
    path = tmp_path / "sap.json"
    path.write_text(json.dumps(sap))
    result = validate(ALLOCATION_PATH, path, SCHEMA_PATH)
    assert result["status"] == "blocked" and failure in result["failures"]
    assert result["approval_status"] == "human_approval_missing" and result["confirmatory_eligible"] is False


def test_candidate_validator_rejects_input_schema_version_drift(tmp_path):
    schema = json.loads(SCHEMA_PATH.read_text())
    schema["$id"] = "analysis-input-v2"
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema))
    result = validate(ALLOCATION_PATH, SAP_PATH, path)
    assert result["status"] == "blocked"
    assert "analysis_schema_version_mismatch" in result["failures"]


@pytest.mark.parametrize(("mutation", "failure"), [
    (lambda value: value.update(additionalProperties=True), "analysis_schema_contract_invalid"),
    (lambda value: value["$defs"]["participant"]["properties"].pop("schema_composite"), "analysis_participant_fields_invalid"),
    (lambda value: value["$defs"]["participant"]["properties"]["suggestion_review_rate"].update(maximum=100),
     "analysis_participant_rules_invalid"),
    (lambda value: value["$defs"]["benchmark_run"]["properties"]["canonical_fact_micro_f1"].pop("maximum"),
     "analysis_benchmark_rules_invalid"),
    (lambda value: value["properties"]["records"]["items"].update(oneOf=[]), "analysis_schema_units_invalid"),
])
def test_candidate_validator_rejects_schema_code_drift(tmp_path, mutation, failure):
    schema = json.loads(SCHEMA_PATH.read_text())
    mutation(schema)
    path = tmp_path / "schema.json"
    path.write_text(json.dumps(schema))
    result = validate(ALLOCATION_PATH, SAP_PATH, path)
    assert result["status"] == "blocked" and failure in result["failures"]


@pytest.mark.parametrize(("field", "value"), [
    ("schema_composite", 6), ("residual_error_count", -1), ("suggestion_review_rate", 1.1),
    ("active_time_ms", 1.5), ("participant_id", ""), ("dataset_id", "bad dataset"),
])
def test_analysis_code_enforces_schema_bounds_and_identifiers(field, value):
    payload = json.loads((Path(__file__).parent / "fixtures" / "analysis_input_v1.json").read_text())
    payload["records"][0][field] = value
    with pytest.raises(ValueError):
        analyze(payload)


def test_analysis_code_rejects_uncontrolled_properties():
    payload = json.loads((Path(__file__).parent / "fixtures" / "analysis_input_v1.json").read_text())
    payload["records"][0]["post_hoc_outcome"] = 1
    with pytest.raises(ValueError, match="uncontrolled"):
        analyze(payload)


def test_confirmatory_gate_stays_blocked_when_candidates_are_ready():
    checks = {name: {"status": "pass"} for name in (
        "reproducibility", "arm_routes", "event_instrumentation", "workload_coverage",
        "expert_package", "governance", "freeze_manifest"
    )}
    checks.update({name: {"status": "candidate_ready", "approval_status": "human_approval_missing"}
                   for name in ("allocation_design", "locked_stats_model")})
    report = build_report("confirmatory", checks)
    assert report["candidate_readiness"] == "candidate_ready"
    assert report["human_approval"] == "missing"
    assert report["status"] == "blocked" and report["confirmatory_eligible"] is False


def test_workload_files_cannot_self_attest_human_approval(monkeypatch, tmp_path):
    import research_readiness
    monkeypatch.setattr(research_readiness, "validate_workload", lambda _path: {
        "status": "pass", "approval_status": "frozen", "failures": []})
    root = tmp_path / "root"; datasets = root / "data" / "datasets" / "demo"
    datasets.mkdir(parents=True); (datasets / "functional_workload.json").write_text("{}")
    monkeypatch.setattr(research_readiness, "run", lambda *_args: {
        "software_checks":"pass", "pilot_readiness":"blocked", "confirmatory_eligibility":"blocked",
        "package":{"archive":str(tmp_path/"public.zip")}})
    monkeypatch.setattr(research_readiness, "validate_routes", lambda: {"status":"pass"})
    monkeypatch.setattr(research_readiness, "validate_instrumentation_manifest", lambda *_args: {"status":"pass"})
    monkeypatch.setattr(research_readiness, "validate_governance", lambda *_args: {"status":"missing"})
    monkeypatch.setattr(research_readiness, "validate_candidates", lambda: {"status":"candidate_ready", "approval_status":"human_approval_missing", "failures":[]})
    checks = research_readiness.run_checks(root, tmp_path/"output")
    assert checks["workload_coverage"]["status"] == "candidate_ready"
    assert checks["workload_coverage"]["human_approval_inferred"] is False


def test_pilot_gate_does_not_treat_technical_workload_coverage_as_approval():
    checks = {name: {"status": "pass"} for name in (
        "reproducibility", "arm_routes", "event_instrumentation", "expert_package", "governance"
    )}
    checks["workload_coverage"] = {"status": "candidate_ready", "technical_coverage": "pass",
                                   "approval_status": "human_approval_missing"}
    checks.update({name: {"status": "candidate_ready"} for name in ("allocation_design", "locked_stats_model")})
    report = build_report("pilot", checks)
    assert report["status"] == "blocked"
    assert report["check_states"]["workload_coverage"] == "fail"


def test_analysis_schema_rejects_duplicate_identifiers():
    payload = json.loads((Path(__file__).parent / "fixtures" / "analysis_input_v1.json").read_text())
    payload["records"].append(dict(payload["records"][0]))
    with pytest.raises(ValueError, match="unique"):
        analyze(payload)
