"""Validate RQ4 envelope coverage and derivable durations without raw payloads."""
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED = {"taxonomy_version", "payload_schema_version", "event_id", "sequence_no", "monotonic_ms",
            "operation_id", "duration_ms", "app_revision", "type"}

def validate(events: list[dict]) -> dict:
    failures=[]; seen=set(); last={}
    for index, event in enumerate(events):
        data=event.get("data", event)
        missing=REQUIRED-set(data)
        if missing: failures.append({"index":index,"reason":"missing_envelope","fields":sorted(missing)}); continue
        if data["event_id"] in seen: failures.append({"index":index,"reason":"duplicate_event_id"})
        seen.add(data["event_id"]); session=data.get("session_id","anonymous")
        if data["sequence_no"] != last.get(session,0)+1: failures.append({"index":index,"reason":"sequence_gap"})
        last[session]=data["sequence_no"]
    return {"status":"pass" if not failures else "fail","events":len(events),"failures":failures,
            "derivation":"duration_ms supplied by monotonic client clock; wall-clock is not used for durations"}

def validate_instrumentation_manifest(path: Path, frontend_root: Path) -> dict:
    if not path.exists(): return {"status":"missing","failures":["instrumentation_manifest_missing"]}
    data=json.loads(path.read_text()); failures=[]; instrumented=data.get("instrumented",{})
    for event_type, sources in instrumented.items():
        for source in sources:
            target=frontend_root/source
            if not target.is_file(): failures.append(f"source_missing:{source}")
            elif event_type not in target.read_text(encoding="utf-8"): failures.append(f"event_not_found_in_source:{event_type}:{source}")
    gaps=sorted(set(data.get("required_for_pilot",[]))-set(instrumented))
    failures.extend(f"required_event_not_instrumented:{gap}" for gap in gaps)
    return {"status":"pass" if not failures else "blocked","failures":failures,"coverage_gaps":gaps,"version":data.get("version")}

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("path",type=Path); a=p.parse_args(); r=validate(json.loads(a.path.read_text())); print(json.dumps(r,indent=2)); raise SystemExit(0 if r["status"]=="pass" else 1)
