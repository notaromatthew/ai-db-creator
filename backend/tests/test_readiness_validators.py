import json
from pathlib import Path
from validate_arm_routes import validate as validate_routes
from validate_event_coverage import validate as validate_events
from validate_event_coverage import validate_instrumentation_manifest
from validate_workload_coverage import validate as validate_workload
from validate_freeze_manifest import validate as validate_freeze
from power_scenarios import scenarios
from validate_expert_package import validate as validate_expert
import csv,hashlib

def test_route_matrix_passes(): assert validate_routes()["status"] == "pass"
def test_event_coverage_detects_loss_and_duplicates():
    base={"taxonomy_version":"rq4-taxonomy-v1","payload_schema_version":"rq4-envelope-v1","monotonic_ms":1,"operation_id":"o","duration_ms":0,"app_revision":"r","type":"navigation"}
    assert validate_events([{**base,"event_id":"e1","sequence_no":1},{**base,"event_id":"e2","sequence_no":2}])["status"]=="pass"
    assert validate_events([{**base,"event_id":"e1","sequence_no":2}])["status"]=="fail"
def test_current_workload_is_truthfully_blocked():
    root=Path(__file__).resolve().parents[2]
    assert validate_workload(root/"data/datasets/university/functional_workload.json")["status"]=="blocked"
def test_freeze_manifest_fail_closed(tmp_path):
    path=tmp_path/"freeze.json";path.write_text(json.dumps({"status":"draft","artifacts":[]}))
    result=validate_freeze(path,tmp_path);assert result["status"]=="blocked" and result["human_approval_inferred"] is False
def test_power_scenarios_deterministic(): assert scenarios()==scenarios() and len(scenarios())==8
def test_instrumentation_manifest_is_source_tied_and_complete():
    root=Path(__file__).resolve().parents[2]
    result=validate_instrumentation_manifest(root/"frontend/src/rq4-instrumentation-manifest.json",root/"frontend")
    assert result["status"]=="pass" and result["coverage_gaps"]==[]
def test_official_expert_rating_schema_accepts_complete_locked_matrix(tmp_path):
    artifacts=[]
    for artifact_id in ("A01","A02"):
        path=tmp_path/f"{artifact_id}.json";path.write_text('{"tables":[]}')
        artifacts.append({"artifact_id":artifact_id,"path":path.name,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()})
    (tmp_path/"manifest.json").write_text(json.dumps({"seed_hash":"abc","blind_order":["A02","A01"],"artifacts":artifacts}))
    fields=["artifact_id","rater_id","presentation_order","rubric_version","d1_3nf","d2_naming","d3_constraints","d4_relationships","d5_domain","comment","locked_at"]
    with (tmp_path/"ratings.csv").open('w',newline='',encoding='utf-8') as target:
        writer=csv.DictWriter(target,fieldnames=fields);writer.writeheader()
        for rater in ("R1","R2"):
            for order,artifact in enumerate(("A02","A01"),1):writer.writerow({"artifact_id":artifact,"rater_id":rater,"presentation_order":order,"rubric_version":"v1",**{field:4 for field in fields[4:9]},"comment":"","locked_at":"2026-01-01T00:00:00Z"})
    assert validate_expert(tmp_path)["status"]=="pass"
    text=(tmp_path/"ratings.csv").read_text();(tmp_path/"ratings.csv").write_text(text.replace(",4,4,4,4,4,",",6,4,4,4,4,",1))
    assert validate_expert(tmp_path)["status"]=="blocked"
