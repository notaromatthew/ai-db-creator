"""One-command offline validation, simulation, analysis, export and verification."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from analyze_experiment import analyze, write_outputs
from export_benchmark_package import export_package, verify_package
from participant_simulator import simulate
from validate_datasets import discover_dataset_dirs, validate_dataset
from check_research_gate import check as check_research_gate


def synthetic_records() -> list[dict]:
    nasa = {key: 50 for key in ("mental_demand", "physical_demand", "temporal_demand", "performance", "effort", "frustration")}
    return [
        {"participant_id": f"p-{index}", "condition": ("manual", "ai_only", "ai_interface")[index % 3],
         "status": "completed", "outcome": 0.8 + (index % 2) * 0.1,
         "sus": [4,2,4,2,4,2,4,2,4,2], "nasa_tlx": nasa, "expert_ratings": [4,4,5]}
        for index in range(8)
    ]


def run(root: Path, output: Path, check_build: bool = False) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    datasets = [validate_dataset(path, check_build) for path in discover_dataset_dirs(root / "data" / "datasets")]
    simulation = simulate(output / "simulation")
    analysis = analyze(synthetic_records())
    write_outputs(analysis, output / "analysis")
    validation_summary = {"datasets": [{"dataset": item["dataset"], "status": item["status"],
                                         "confirmatory_status": item.get("confirmatory_status")} for item in datasets],
                          "simulation": simulation["status"], "analysis_status": analysis["analysis_status"]}
    (output / "validation-summary.json").write_text(json.dumps(validation_summary, indent=2), encoding="utf-8")
    package = export_package(output, output.parent / "reproducibility-package.zip")
    verification = verify_package(Path(package["archive"]))
    research_gate = check_research_gate(root / "data" / "datasets", root / "data" / "datasets" / "research-gate-expectations.json")
    software_checks = "pass" if simulation["status"] == "pass" and verification["status"] == "valid" and research_gate["software_gate"] == "pass" else "fail"
    pilot_readiness = "pass" if all(item["status"] == "valid" for item in datasets) else "blocked"
    confirmatory = "eligible" if datasets and all(item.get("confirmatory_status") == "eligible" for item in datasets) else "blocked"
    return {"status": software_checks, "software_checks": software_checks, "pilot_readiness": pilot_readiness,
            "confirmatory_eligibility": confirmatory, "research_gate": research_gate,
            "datasets": datasets, "simulation": simulation,
            "analysis": analysis, "package": package, "verification": verification}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(".."))
    parser.add_argument("--output", type=Path, default=Path("reports/reproducibility"))
    parser.add_argument("--check-build", action="store_true")
    parser.add_argument("--gate", choices=("software", "pilot", "confirmatory"), default="software")
    args = parser.parse_args(argv)
    result = run(args.root.resolve(), args.output.resolve(), args.check_build)
    print(json.dumps({"software_checks": result["software_checks"], "pilot_readiness": result["pilot_readiness"],
                      "confirmatory_eligibility": result["confirmatory_eligibility"], "package": result["package"],
                      "verification": result["verification"]}, indent=2))
    passed = (result["software_checks"] == "pass" if args.gate == "software" else
              result["pilot_readiness"] == "pass" if args.gate == "pilot" else
              result["confirmatory_eligibility"] == "eligible")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
