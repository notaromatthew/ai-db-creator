"""Unified fail-closed orchestration for software, pilot and confirmatory gates."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from validate_reproducibility import run
from validate_arm_routes import validate as validate_routes
from validate_event_coverage import validate_instrumentation_manifest
from validate_workload_coverage import validate as validate_workload
from validate_freeze_manifest import validate as validate_freeze
from validate_expert_package import validate as validate_expert
from validate_governance import validate as validate_governance
from validate_research_candidates import validate as validate_candidates

REQUIRED={"software":["reproducibility","arm_routes"],"pilot":["reproducibility","arm_routes","event_instrumentation","workload_coverage","expert_package","governance"],
          "confirmatory":["reproducibility","arm_routes","event_instrumentation","workload_coverage","expert_package","governance","freeze_manifest","allocation_design","locked_stats_model"]}
def _state(result):
 status=result.get("status")
 if status in {"pass","valid","technically_valid"}: return "pass"
 if status in {"missing"}: return "missing"
 return "fail"
def run_checks(root:Path,output:Path,freeze_manifest:Path|None=None,expert_package:Path|None=None,restricted_archive:Path|None=None):
 repro=run(root,output); checks={
  "reproducibility":{"status":"pass" if repro["software_checks"]=="pass" else "fail","details":{"pilot_readiness":repro["pilot_readiness"],"confirmatory":repro["confirmatory_eligibility"]}},
  "arm_routes":validate_routes(),
  "event_instrumentation":validate_instrumentation_manifest(root/"frontend/src/rq4-instrumentation-manifest.json",root/"frontend"),
 }
 workload=[validate_workload(path) for path in sorted((root/"data/datasets").glob("*/functional_workload.json"))]
 technical_coverage=bool(workload) and all(item["status"]=="pass" for item in workload)
 # Technical files cannot self-attest reviewer approval. A separate signed approval
 # workflow must be introduced before this gate is ever promoted to ``pass``.
 checks["workload_coverage"]={"status":"candidate_ready" if technical_coverage else ("missing" if not workload else "blocked"),
                              "technical_coverage":"pass" if technical_coverage else "blocked",
                              "approval_status":"human_approval_missing","human_approval_inferred":False,
                              "datasets":workload}
 checks["freeze_manifest"]={"status":"missing","failures":["freeze_manifest_not_supplied"]} if freeze_manifest is None else validate_freeze(freeze_manifest,root)
 checks["expert_package"]={"status":"missing","failures":["expert_package_not_supplied"]} if expert_package is None else validate_expert(expert_package)
 public=Path(repro["package"]["archive"])
 checks["governance"]=validate_governance(public,restricted_archive)
 candidate=validate_candidates()
 checks["allocation_design"]={"status":candidate["status"],"approval_status":candidate["approval_status"],
                              "confirmatory_eligible":False,"failures":candidate["failures"]}
 checks["locked_stats_model"]={"status":candidate["status"],"approval_status":candidate["approval_status"],
                               "confirmatory_eligible":False,"failures":candidate["failures"]}
 return checks
def build_report(gate,checks):
 required=REQUIRED[gate]; states={name:_state(checks[name]) for name in required}
 status="pass" if all(value=="pass" for value in states.values()) else ("missing" if any(value=="missing" for value in states.values()) else "blocked")
 return {"gate":gate,"status":status,"required_checks":required,"check_states":states,"checks":checks,
         "candidate_readiness":"candidate_ready" if checks["allocation_design"]["status"]==checks["locked_stats_model"]["status"]=="candidate_ready" else "blocked",
         "human_approval":"missing","confirmatory_eligible":False}
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,default=Path(".."));p.add_argument("--output",type=Path,default=Path("reports/readiness"));p.add_argument("--gate",choices=tuple(REQUIRED),default="software");p.add_argument("--freeze-manifest",type=Path);p.add_argument("--expert-package",type=Path);p.add_argument("--restricted-archive",type=Path);a=p.parse_args(argv)
 checks=run_checks(a.root.resolve(),a.output.resolve(),a.freeze_manifest,a.expert_package,a.restricted_archive); report=build_report(a.gate,checks)
 print(json.dumps(report,indent=2));return 0 if report["status"]=="pass" else 1
if __name__=="__main__":raise SystemExit(main())
