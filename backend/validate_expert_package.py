"""Validate blinded RQ1 expert packages against the locked ratings schema."""
from __future__ import annotations
import argparse,csv,hashlib,json,re
from pathlib import Path
LEAK=re.compile(r"manual|ai[_ +-]?only|ai[_ +-]?interface|condition|participant",re.I)
RATING_FIELDS=["artifact_id","rater_id","presentation_order","rubric_version","d1_3nf","d2_naming","d3_constraints","d4_relationships","d5_domain","comment","locked_at"]
DIMENSIONS=RATING_FIELDS[4:9]
def validate(root:Path):
 failures=[]; manifest_path=root/"manifest.json"
 if not manifest_path.exists(): return {"status":"missing","failures":["manifest_missing"]}
 try: manifest=json.loads(manifest_path.read_text())
 except json.JSONDecodeError: return {"status":"blocked","failures":["manifest_invalid_json"]}
 order=manifest.get("blind_order",[]); artifacts=manifest.get("artifacts",[]); artifact_ids={item.get("artifact_id") for item in artifacts}
 if not manifest.get("seed_hash") or len(order)!=len(set(order)): failures.append("blind_order_or_seed_invalid")
 if not artifact_ids or None in artifact_ids or set(order)!=artifact_ids: failures.append("blind_order_artifact_set_mismatch")
 for artifact in artifacts:
  path=(root/artifact.get("path","")).resolve()
  if root.resolve() not in path.parents or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=artifact.get("sha256"): failures.append(f"artifact_hash_invalid:{artifact.get('artifact_id')}")
  elif LEAK.search(path.read_text(errors="replace")): failures.append(f"condition_leakage:{artifact.get('artifact_id')}")
 ratings=root/"ratings.csv"
 if not ratings.exists(): failures.append("ratings_missing")
 else:
  with ratings.open(newline='',encoding='utf-8') as source:
   reader=csv.DictReader(source); rows=list(reader); header=reader.fieldnames or []
  if header!=RATING_FIELDS: failures.append("ratings_schema_invalid")
  elif not rows: failures.append("ratings_empty")
  else:
   keys=[(row["artifact_id"],row["rater_id"]) for row in rows]
   if len(set(keys))!=len(keys): failures.append("duplicate_artifact_rater")
   if {row["artifact_id"] for row in rows}!=artifact_ids: failures.append("rating_artifact_coverage_mismatch")
   raters={row["rater_id"] for row in rows}
   if any({row["artifact_id"] for row in rows if row["rater_id"]==rater}!=artifact_ids for rater in raters): failures.append("incomplete_artifact_rater_matrix")
   if any(not row["rater_id"] or not row["rubric_version"] or not row["locked_at"] for row in rows): failures.append("ratings_not_locked_or_metadata_missing")
   if any(not row["presentation_order"].isdigit() or int(row["presentation_order"])<1 for row in rows): failures.append("presentation_order_invalid")
   if any(not row[field].isdigit() or not 1<=int(row[field])<=5 for row in rows for field in DIMENSIONS): failures.append("dimension_rating_out_of_range")
   if any(LEAK.search(row["comment"] or "") for row in rows): failures.append("condition_leakage_in_comment")
 return {"status":"pass" if not failures else "blocked","schema_version":"expert-ratings-wide-v1","failures":sorted(set(failures))}
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);a=p.parse_args();r=validate(a.root);print(json.dumps(r,indent=2));raise SystemExit(0 if r["status"]=="pass" else 1)
