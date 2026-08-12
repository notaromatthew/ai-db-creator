"""Fail-closed technical freeze manifest validator; never grants human approval."""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def validate(path: Path, root: Path) -> dict:
    failures=[]
    try: manifest=json.loads(path.read_text())
    except Exception as exc: return {"status":"blocked","failures":[{"reason":"invalid_manifest","type":type(exc).__name__}]}
    if manifest.get("status") != "frozen" or not manifest.get("approved_by") or not manifest.get("approved_at"):
        failures.append({"reason":"human_freeze_attestation_missing"})
    for artifact in manifest.get("artifacts",[]):
        target=(root/artifact.get("path","")).resolve()
        if root.resolve() not in target.parents or not target.is_file(): failures.append({"reason":"artifact_missing_or_unsafe","path":artifact.get("path")}); continue
        if hashlib.sha256(target.read_bytes()).hexdigest()!=artifact.get("sha256"): failures.append({"reason":"hash_mismatch","path":artifact.get("path")})
    return {"status":"technically_valid" if not failures else "blocked","failures":failures,"human_approval_inferred":False}

if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("manifest",type=Path); p.add_argument("--root",type=Path,default=Path("..")); a=p.parse_args(); r=validate(a.manifest,a.root.resolve()); print(json.dumps(r,indent=2)); raise SystemExit(0 if r["status"]=="technically_valid" else 1)
