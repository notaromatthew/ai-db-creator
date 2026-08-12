"""Deterministic planning scenarios; not a confirmatory power calculation."""
from __future__ import annotations
import argparse,csv,json
from pathlib import Path
def scenarios(): return [{"per_arm":n,"arms":3,"total":n*3,"attrition":a,"retained":round(n*3*(1-a))} for n in (20,30,40,50) for a in (.1,.2)]
def main(argv=None):
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True);a=p.parse_args(argv);a.output.mkdir(parents=True,exist_ok=True);rows=scenarios();(a.output/"power-scenarios.json").write_text(json.dumps({"status":"planning_only","locked_sap_model":"not_implemented","scenarios":rows},indent=2));
 with (a.output/"power-scenarios.csv").open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 (a.output/"power-scenarios.tex").write_text("\\begin{tabular}{rrrr}\nPer arm & Arms & Total & Retained \\\\\n"+"\n".join(f"{r['per_arm']} & 3 & {r['total']} & {r['retained']} \\\\" for r in rows)+"\n\\end{tabular}\n");return 0
if __name__=="__main__":raise SystemExit(main())
