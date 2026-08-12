"""Validate retention/deletion and public-versus-restricted artifact policy."""
from __future__ import annotations
import argparse,json
from pathlib import Path
from export_benchmark_package import verify_package
def validate(public_package:Path|None,restricted:Path|None):
 failures=[]
 if public_package is None: failures.append("public_package_missing")
 if restricted is None: failures.append("restricted_archive_policy_evidence_missing")
 if public_package and verify_package(public_package)["status"]!="valid": failures.append("public_package_invalid_or_not_deidentified")
 if restricted and restricted.exists() and "restricted" not in restricted.name.lower(): failures.append("restricted_archive_must_be_explicitly_named")
 return {"status":"pass" if not failures else ("missing" if any(item.endswith("_missing") for item in failures) else "blocked"),"failures":failures,
 "policy":{"public":"deidentified reports only; CI retention 14 days","restricted":"DB/uploads/full run artifacts; approved encrypted storage only","withdrawal":"delete project/uploads/session/surveys/events across stores"}}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument('--public-package',type=Path);p.add_argument('--restricted',type=Path);a=p.parse_args();r=validate(a.public_package,a.restricted);print(json.dumps(r,indent=2));raise SystemExit(0 if r['status']=='pass' else 1)
