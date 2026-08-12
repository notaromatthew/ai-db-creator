"""Fail-closed structural validation for unapproved allocation and SAP candidates."""
from __future__ import annotations

import json
from pathlib import Path

from locked_candidate_analysis import BENCHMARK_FIELDS, PARTICIPANT_FIELDS

ROOT = Path(__file__).resolve().parent
ALLOCATION_PATH = ROOT / "research_configs" / "allocation-candidate-v1.json"
SAP_PATH = ROOT / "research_configs" / "sap-locked-candidate-v1.json"
SCHEMA_PATH = ROOT / "research_configs" / "analysis-input-v1.schema.json"

ARMS = ["manual", "ai_only", "ai_interface"]
STRATA = ["dataset_id", "experience_stratum"]
RQ1_OUTCOMES = ["d1_3nf", "d2_naming", "d3_constraints", "d4_relationships", "d5_domain"]
RQ4_FEATURES = ["committed_constraint_fk_edits", "suggestion_review_rate", "review_time_ms"]


def _read(path: Path, label: str, failures: list[str]) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise TypeError("root is not an object")
        return value
    except Exception as exc:
        failures.append(f"{label}_invalid:{type(exc).__name__}")
        return None


def _expect(failures: list[str], condition: bool, code: str) -> None:
    if not condition:
        failures.append(code)


def _validate_allocation(config: dict, failures: list[str]) -> None:
    _expect(failures, config.get("schema_version") == "allocation-candidate-v1", "allocation_schema_version_invalid")
    _expect(failures, config.get("status") == "candidate_unapproved", "allocation_status_invalid")
    _expect(failures, config.get("approval_status") == "human_approval_missing", "allocation_approval_boundary_invalid")
    arms = config.get("arms")
    _expect(failures, arms == ARMS and len(set(arms or [])) == len(ARMS), "allocation_arms_invalid")
    _expect(failures, config.get("ratio") == [1, 1, 1], "allocation_ratio_invalid")
    _expect(failures, config.get("strata") == STRATA, "allocation_strata_invalid")
    _expect(failures, config.get("allowed_experience_strata") == ["none", "some"], "allocation_experience_strata_invalid")
    sizes = config.get("block_sizes")
    valid_sizes = (isinstance(sizes, list) and bool(sizes) and len(set(sizes)) == len(sizes)
                   and all(type(size) is int and size > 0 and size % len(ARMS) == 0 for size in sizes))
    _expect(failures, valid_sizes, "allocation_block_sizes_invalid")
    _expect(failures, config.get("seed_environment_variable") == "EXPERIMENT_ASSIGNMENT_SEED",
            "allocation_seed_environment_invalid")
    _expect(failures, isinstance(config.get("concealment"), str) and bool(config["concealment"].strip()),
            "allocation_concealment_missing")


def _validate_sap(sap: dict, failures: list[str]) -> None:
    _expect(failures, sap.get("schema_version") == "sap-locked-candidate-v1", "sap_schema_version_invalid")
    _expect(failures, sap.get("input_schema_version") == "analysis-input-v1", "sap_input_schema_version_invalid")
    _expect(failures, sap.get("status") == "locked_candidate_unapproved", "sap_status_invalid")
    _expect(failures, sap.get("approval_status") == "human_approval_missing", "sap_approval_boundary_invalid")
    primary = sap.get("primary_family", {})
    _expect(failures, primary.get("multiplicity") == "holm" and primary.get("alpha") == 0.05,
            "sap_primary_multiplicity_invalid")
    analyses = primary.get("analyses")
    indexed = {item.get("id"): item for item in analyses if isinstance(item, dict)} if isinstance(analyses, list) else {}
    _expect(failures, set(indexed) == {"rq0", "rq3"} and len(analyses or []) == 2, "sap_primary_analyses_invalid")
    rq0 = indexed.get("rq0", {})
    _expect(failures, rq0 == {"id": "rq0", "outcome": "schema_composite", "model": "linear_hc3",
                             "contrast": ["ai_interface", "manual"],
                             "covariates": ["dataset_id", "experience_stratum"]}, "sap_rq0_invalid")
    rq3 = indexed.get("rq3", {})
    _expect(failures, rq3 == {"id": "rq3", "outcome": "residual_error_count", "model": "negative_binomial",
                             "fallback": "robust_poisson", "contrast": ["ai_interface", "ai_only"],
                             "covariates": ["dataset_id", "experience_stratum"]}, "sap_rq3_invalid")
    rq1 = sap.get("rq1", {})
    _expect(failures, rq1.get("outcomes") == RQ1_OUTCOMES and rq1.get("model") == "ordinal_mixed_candidate"
            and rq1.get("multiplicity") == "holm", "sap_rq1_invalid")
    rq2 = sap.get("rq2", {})
    _expect(failures, rq2 == {"outcome": "canonical_fact_micro_f1",
                             "model": "stratified_bootstrap_and_randomisation_contrast", "stratum": "dataset_id"},
            "sap_rq2_invalid")
    rq4 = sap.get("rq4", {})
    _expect(failures, rq4 == {"arm": "ai_interface", "outcome": "final_improvement", "features": RQ4_FEATURES,
                             "covariates": ["baseline_quality", "dataset_id", "experience_stratum", "active_time_ms"],
                             "model": "linear_hc3", "multiplicity": "bh_fdr"}, "sap_rq4_invalid")
    missingness = sap.get("missingness", {})
    _expect(failures, missingness.get("primary_population") == "intention_to_treat"
            and missingness.get("primary_handling") == "likelihood_under_mar"
            and missingness.get("sensitivity") == ["complete_case", "multiple_imputation", "technical_failure_bounds"]
            and missingness.get("single_value_imputation") is False, "sap_missingness_invalid")


def _validate_schema(schema: dict, sap: dict, failures: list[str]) -> None:
    _expect(failures, schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
            "analysis_schema_dialect_invalid")
    _expect(failures, schema.get("$id") == sap.get("input_schema_version"), "analysis_schema_version_mismatch")
    _expect(failures, schema.get("type") == "object" and schema.get("additionalProperties") is False
            and set(schema.get("required", [])) == {"schema_version", "records"}
            and set(schema.get("properties", {})) == {"schema_version", "records"}, "analysis_schema_contract_invalid")
    records = schema.get("properties", {}).get("records", {})
    refs = records.get("items", {}).get("oneOf", [])
    _expect(failures, records.get("type") == "array" and refs == [
        {"$ref": "#/$defs/participant"}, {"$ref": "#/$defs/benchmark_run"}], "analysis_schema_units_invalid")
    definitions = schema.get("$defs", {})
    participant = definitions.get("participant", {})
    benchmark = definitions.get("benchmark_run", {})
    participant_properties = participant.get("properties", {})
    benchmark_properties = benchmark.get("properties", {})
    _expect(failures, participant.get("type") == "object" and participant.get("additionalProperties") is False
            and set(participant_properties) == PARTICIPANT_FIELDS
            and set(participant.get("required", [])) == {"unit", "participant_id", "assigned_arm", "dataset_id",
                                                           "experience_stratum", "completion_status"},
            "analysis_participant_fields_invalid")
    _expect(failures, benchmark.get("type") == "object" and benchmark.get("additionalProperties") is False
            and set(benchmark_properties) == BENCHMARK_FIELDS
            and set(benchmark.get("required", [])) == {"unit", "run_id", "condition", "dataset_id", "attempt_status"},
            "analysis_benchmark_fields_invalid")
    exact = {
        "unit": {"const": "participant"}, "participant_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "assigned_arm": {"enum": ARMS}, "dataset_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"},
        "experience_stratum": {"enum": ["none", "some"]},
        "completion_status": {"enum": ["completed", "partial", "abandoned", "technical_failure"]},
        "schema_composite": {"type": "number", "minimum": 1, "maximum": 5},
        "residual_error_count": {"type": "integer", "minimum": 0},
        "final_improvement": {"type": "number"}, "baseline_quality": {"type": "number", "minimum": 1, "maximum": 5},
        "active_time_ms": {"type": "integer", "minimum": 0},
        "committed_constraint_fk_edits": {"type": "integer", "minimum": 0},
        "suggestion_review_rate": {"type": "number", "minimum": 0, "maximum": 1},
        "review_time_ms": {"type": "integer", "minimum": 0},
    }
    for outcome in RQ1_OUTCOMES:
        exact[outcome] = {"type": "number", "minimum": 1, "maximum": 5}
    _expect(failures, all(participant_properties.get(field) == rule for field, rule in exact.items()),
            "analysis_participant_rules_invalid")
    benchmark_exact = {
        "unit": {"const": "benchmark_run"}, "run_id": {"type": "string", "minLength": 1, "maxLength": 128},
        "condition": {"enum": ["full_llm", "baseline"]},
        "dataset_id": {"type": "string", "pattern": "^[A-Za-z0-9_-]{1,64}$"},
        "attempt_status": {"enum": ["success", "failed"]},
        "canonical_fact_micro_f1": {"type": "number", "minimum": 0, "maximum": 1},
    }
    _expect(failures, benchmark_properties == benchmark_exact, "analysis_benchmark_rules_invalid")
    sap_participant_fields = {item["outcome"] for item in sap["primary_family"]["analyses"]} | set(sap["rq1"]["outcomes"])
    sap_participant_fields |= {sap["rq4"]["outcome"], *sap["rq4"]["features"], *sap["rq4"]["covariates"]}
    sap_participant_fields |= {covariate for item in sap["primary_family"]["analyses"] for covariate in item["covariates"]}
    _expect(failures, sap_participant_fields <= set(participant_properties), "analysis_schema_sap_participant_drift")
    _expect(failures, {sap["rq2"]["outcome"], sap["rq2"]["stratum"]} <= set(benchmark_properties),
            "analysis_schema_sap_benchmark_drift")


def validate(allocation_path: Path = ALLOCATION_PATH, sap_path: Path = SAP_PATH,
             schema_path: Path = SCHEMA_PATH) -> dict:
    failures: list[str] = []
    allocation = _read(Path(allocation_path), "allocation_candidate", failures)
    sap = _read(Path(sap_path), "sap_candidate", failures)
    schema = _read(Path(schema_path), "analysis_schema", failures)
    if allocation is not None:
        _validate_allocation(allocation, failures)
    if sap is not None:
        _validate_sap(sap, failures)
    if sap is not None and schema is not None:
        _validate_schema(schema, sap, failures)
    return {"status": "candidate_ready" if not failures else "blocked", "approval_status": "human_approval_missing",
            "confirmatory_eligible": False, "failures": sorted(set(failures))}


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result["status"] == "candidate_ready" else 1)
