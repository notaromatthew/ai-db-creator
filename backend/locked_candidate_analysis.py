"""Deterministic SAP candidate pipeline; outputs are never confirmatory without human freeze."""
from __future__ import annotations

import argparse
import json
import math
import re
import statistics
from collections import defaultdict
from pathlib import Path

from app.utils.research import atomic_write_json, sha256_file, stable_hash

ROOT = Path(__file__).resolve().parent
SAP_PATH = ROOT / "research_configs" / "sap-locked-candidate-v1.json"
INPUT_SCHEMA_PATH = ROOT / "research_configs" / "analysis-input-v1.schema.json"
ARMS = {"manual", "ai_only", "ai_interface"}
PARTICIPANT_FIELDS = {"unit", "participant_id", "assigned_arm", "dataset_id", "experience_stratum", "completion_status",
                      "schema_composite", "residual_error_count", "d1_3nf", "d2_naming", "d3_constraints",
                      "d4_relationships", "d5_domain", "final_improvement", "baseline_quality", "active_time_ms",
                      "committed_constraint_fk_edits", "suggestion_review_rate", "review_time_ms"}
BENCHMARK_FIELDS = {"unit", "run_id", "condition", "dataset_id", "attempt_status", "canonical_fact_micro_f1"}
DATASET_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def load_candidate() -> dict:
    sap = json.loads(SAP_PATH.read_text(encoding="utf-8"))
    if sap.get("status") != "locked_candidate_unapproved" or sap.get("approval_status") != "human_approval_missing":
        raise ValueError("SAP candidate must remain explicitly unapproved")
    return sap


def validate_input(payload: dict) -> list[dict]:
    if not isinstance(payload, dict) or payload.get("schema_version") != "analysis-input-v1":
        raise ValueError("analysis input must use schema_version analysis-input-v1")
    records = payload.get("records")
    if not isinstance(records, list):
        raise ValueError("records must be an array")
    participant_required = {"participant_id", "assigned_arm", "dataset_id", "experience_stratum", "completion_status"}
    run_required = {"run_id", "condition", "dataset_id", "attempt_status"}
    seen = set()
    for index, record in enumerate(records):
        unit = record.get("unit", "participant") if isinstance(record, dict) else None
        required = participant_required if unit == "participant" else run_required
        if unit not in {"participant", "benchmark_run"} or not required <= set(record):
            raise ValueError(f"record {index} lacks required analysis fields")
        allowed = PARTICIPANT_FIELDS if unit == "participant" else BENCHMARK_FIELDS
        if not set(record) <= allowed:
            raise ValueError(f"record {index} contains uncontrolled analysis fields")
        identity = record["participant_id"] if unit == "participant" else record["run_id"]
        if not isinstance(identity, str) or not identity.strip() or len(identity) > 128:
            raise ValueError(f"record {index} has an invalid analysis identifier")
        if identity in seen: raise ValueError("analysis identifiers must be unique")
        seen.add(identity)
        if not isinstance(record["dataset_id"], str) or not DATASET_ID.fullmatch(record["dataset_id"]):
            raise ValueError(f"record {index} has an invalid dataset_id")
        if unit == "participant":
            if record["assigned_arm"] not in ARMS or record["experience_stratum"] not in {"none", "some"}:
                raise ValueError(f"record {index} has an invalid controlled value")
            if record["completion_status"] not in {"completed", "partial", "abandoned", "technical_failure"}:
                raise ValueError(f"record {index} has an invalid completion_status")
            _validate_optional_numbers(record, index, {
                "schema_composite": (1, 5, False), "residual_error_count": (0, None, True),
                "d1_3nf": (1, 5, False), "d2_naming": (1, 5, False), "d3_constraints": (1, 5, False),
                "d4_relationships": (1, 5, False), "d5_domain": (1, 5, False),
                "final_improvement": (None, None, False), "baseline_quality": (1, 5, False),
                "active_time_ms": (0, None, True), "committed_constraint_fk_edits": (0, None, True),
                "suggestion_review_rate": (0, 1, False), "review_time_ms": (0, None, True),
            })
        elif record["condition"] not in {"full_llm", "baseline"} or record["attempt_status"] not in {"success", "failed"}:
            raise ValueError(f"record {index} has an invalid benchmark controlled value")
        else:
            _validate_optional_numbers(record, index, {"canonical_fact_micro_f1": (0, 1, False)})
    return records


def _validate_optional_numbers(record: dict, index: int, rules: dict[str, tuple[float | None, float | None, bool]]) -> None:
    for field, (minimum, maximum, integer) in rules.items():
        if field not in record:
            continue
        value = record[field]
        valid_type = type(value) is int if integer else type(value) in {int, float}
        if (not valid_type or not math.isfinite(value) or (minimum is not None and value < minimum)
                or (maximum is not None and value > maximum)):
            raise ValueError(f"record {index} has invalid {field}")


def _finite(record: dict, field: str) -> float | None:
    value = record.get(field)
    return float(value) if type(value) in {int, float} and math.isfinite(value) else None


def _stratified_contrast(records: list[dict], outcome: str, treatment: str, reference: str, ratio: bool = False,
                         group_field: str = "assigned_arm", strata_fields: tuple[str, ...] = ("dataset_id", "experience_stratum")) -> dict:
    strata = defaultdict(lambda: defaultdict(list))
    for record in records:
        value = _finite(record, outcome)
        if value is not None and record.get(group_field) in {treatment, reference}:
            strata[tuple(record.get(field) for field in strata_fields)][record[group_field]].append(value)
    estimates, weights = [], []
    for key in sorted(strata):
        groups = strata[key]
        if groups[treatment] and groups[reference]:
            a, b = statistics.mean(groups[treatment]), statistics.mean(groups[reference])
            estimates.append((a / b) if ratio and b else (a - b))
            weights.append(len(groups[treatment]) + len(groups[reference]))
    if not estimates:
        return {"status": "insufficient_data", "estimand": "incidence_rate_ratio" if ratio else "mean_difference"}
    estimate = sum(value * weight for value, weight in zip(estimates, weights)) / sum(weights)
    return {"status": "candidate_reference_estimate", "estimate": round(estimate, 6),
            "estimand": "incidence_rate_ratio" if ratio else "adjusted_mean_difference",
            "contrast": [treatment, reference], "complete_strata": len(estimates), "inference": "not_run_unapproved"}


def analyze(payload: dict) -> dict:
    sap = load_candidate()
    records = validate_input(payload)
    participant_records = [record for record in records if record.get("unit", "participant") == "participant"]
    benchmark_records = [record for record in records if record.get("unit") == "benchmark_run"]
    completed = [record for record in participant_records if record["completion_status"] == "completed"]
    rq0 = _stratified_contrast(completed, "schema_composite", "ai_interface", "manual")
    rq3 = _stratified_contrast(completed, "residual_error_count", "ai_interface", "ai_only", ratio=True)
    rq2 = _stratified_contrast([record for record in benchmark_records if record["attempt_status"] == "success"],
                               "canonical_fact_micro_f1", "full_llm", "baseline",
                               group_field="condition", strata_fields=("dataset_id",))
    rq2.update({"model": "stratified_bootstrap_and_randomisation_contrast", "quality_population": "successful_runs_conditional"})
    rq1 = {outcome: {"n": sum(_finite(record, outcome) is not None for record in completed),
                     "model": sap["rq1"]["model"], "inference": "not_run_unapproved"}
           for outcome in sap["rq1"]["outcomes"]}
    rq4_records = [record for record in completed if record["assigned_arm"] == "ai_interface"]
    rq4 = {feature: {"n": sum(_finite(record, feature) is not None and _finite(record, "final_improvement") is not None for record in rq4_records),
                     "model": "linear_hc3_with_prespecified_covariates", "inference": "not_run_unapproved"}
           for feature in sap["rq4"]["features"]}
    flow = {arm: {status: sum(r["assigned_arm"] == arm and r["completion_status"] == status for r in participant_records)
                  for status in ("completed", "partial", "abandoned", "technical_failure")} for arm in sorted(ARMS)}
    benchmark_flow = {condition: {status: sum(r["condition"] == condition and r["attempt_status"] == status for r in benchmark_records)
                                  for status in ("success", "failed")} for condition in ("baseline", "full_llm")}
    return {"analysis_status": "locked_candidate_unapproved", "human_approval": "missing",
            "input_schema_version": payload["schema_version"], "sap_version": sap["schema_version"],
            "sap_hash": stable_hash(sap), "participant_flow": flow, "benchmark_flow": benchmark_flow,
            "analyses": {"rq0": {**rq0, "model": "linear_hc3"},
                         "rq1": rq1, "rq2": rq2,
                         "rq3": {**rq3, "model": "negative_binomial", "fallback": "robust_poisson"},
                         "rq4": rq4},
            "multiplicity": {"primary_human": "holm", "rq1_dimensions": "holm", "rq4_features": "bh_fdr"},
            "decision_log": [{"code": "HUMAN_APPROVAL_MISSING", "effect": "confirmatory inference disabled"}]}


def write_outputs(payload: dict, result: dict, output: Path, input_path: Path | None = None) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    atomic_write_json(output / "analysis-candidate.json", result)
    atomic_write_json(output / "decision-log.json", result["decision_log"])
    manifest = {"manifest_version": "analysis-output-candidate-v1", "status": result["analysis_status"],
                "input_schema_version": result["input_schema_version"], "sap_version": result["sap_version"],
                "input_sha256": sha256_file(input_path) if input_path else stable_hash(payload),
                "files": {name: sha256_file(output / name) for name in ("analysis-candidate.json", "decision-log.json")}}
    atomic_write_json(output / "manifest.json", manifest)
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(payload)
    write_outputs(payload, result, args.output, args.input)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
