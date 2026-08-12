"""Check draft workload coverage requirements without inventing workload queries."""
from __future__ import annotations
import argparse,json
from pathlib import Path
REQUIRED={"lookup","join","filter","aggregate","missing_value","temporal","integrity"}
def validate(path:Path):
 data=json.loads(path.read_text()); ids=[q.get("id") for q in data.get("queries",[])]; kinds={q.get("coverage_type") for q in data.get("queries",[])}
 failures=[]
 if len(ids)!=len(set(ids)) or any(not item for item in ids): failures.append("query_ids_missing_or_duplicate")
 missing=REQUIRED-kinds
 if missing: failures.append("missing_coverage:"+",".join(sorted(missing)))
 return {"status":"pass" if not failures else "blocked","approval_status":data.get("approval_status","draft"),"failures":failures}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("path",type=Path);a=p.parse_args();r=validate(a.path);print(json.dumps(r,indent=2));raise SystemExit(0 if r["status"]=="pass" else 1)
