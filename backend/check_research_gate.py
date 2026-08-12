"""Verify that dataset readiness matches the explicitly versioned research gate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_datasets import discover_dataset_dirs, validate_dataset


def check(datasets: Path, expectations_path: Path) -> dict:
    expected = json.loads(expectations_path.read_text(encoding="utf-8"))
    reports = {path.name: validate_dataset(path) for path in discover_dataset_dirs(datasets)}
    mismatches = []
    expected_datasets = expected.get("datasets", {})
    if set(reports) != set(expected_datasets):
        mismatches.append({"code": "dataset_set_mismatch", "expected": sorted(expected_datasets), "actual": sorted(reports)})
    for name, specification in expected_datasets.items():
        report = reports.get(name)
        if not report:
            continue
        for expected_key, report_key in (("validation_status", "status"), ("confirmatory_status", "confirmatory_status")):
            if report.get(report_key) != specification.get(expected_key):
                mismatches.append({"code": f"{name}_{report_key}_mismatch", "expected": specification.get(expected_key), "actual": report.get(report_key)})
        issue_codes = {issue["code"] for issue in report.get("issues", [])}
        required = set(specification.get("required_issue_codes", []))
        if not required <= issue_codes:
            mismatches.append({"code": f"{name}_required_issues_missing", "expected": sorted(required), "actual": sorted(issue_codes)})
        unexpected = issue_codes - required
        if unexpected:
            mismatches.append({"code": f"{name}_unexpected_issues", "actual": sorted(unexpected)})
    research_status = "eligible" if reports and all(item.get("status") == "valid" and item.get("confirmatory_status") == "eligible" for item in reports.values()) else "blocked"
    return {"software_gate": "pass" if not mismatches else "fail", "research_freeze_gate": research_status,
            "expectations_version": expected.get("version"), "mismatches": mismatches,
            "datasets": {name: {"validation_status": item.get("status"), "confirmatory_status": item.get("confirmatory_status"),
                                 "issue_codes": sorted({issue["code"] for issue in item.get("issues", [])})}
                         for name, item in reports.items()}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", type=Path, default=Path("../data/datasets"))
    parser.add_argument("--expectations", type=Path, default=Path("../data/datasets/research-gate-expectations.json"))
    args = parser.parse_args(argv)
    result = check(args.datasets.resolve(), args.expectations.resolve())
    print(json.dumps(result, indent=2))
    return 0 if result["software_gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
