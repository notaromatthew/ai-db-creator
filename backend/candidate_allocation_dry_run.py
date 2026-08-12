"""Generate an atomic, concealed dry-run of the unapproved allocation candidate."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.allocation_service import CandidateAllocator
from app.utils.research import atomic_write_json, stable_hash


def generate(enrolments: list[dict], output: Path, allocator: CandidateAllocator | None = None) -> dict:
    if not isinstance(enrolments, list):
        raise ValueError("enrolments must be an array")
    allocator = allocator or CandidateAllocator()
    audit = []
    assignments = []
    seen = set()
    for index, enrolment in enumerate(enrolments):
        if not isinstance(enrolment, dict) or set(enrolment) != {"participant_id", "dataset_id", "experience_stratum"}:
            raise ValueError(f"enrolment {index} must contain only the controlled allocation fields")
        participant_id = enrolment.get("participant_id")
        if not isinstance(participant_id, str) or not participant_id.strip() or len(participant_id) > 128:
            raise ValueError(f"enrolment {index} has an invalid participant_id")
        if participant_id in seen:
            raise ValueError("participant_id must be unique in allocation dry-run")
        seen.add(participant_id)
        condition, entry = allocator.assign(audit, enrolment.get("dataset_id", ""), enrolment.get("experience_stratum", ""))
        restricted_entry = {"participant_id": participant_id, "condition": condition, **entry}
        audit.append(restricted_entry)
        assignments.append({"participant_id": participant_id, "condition": condition,
                            "allocation_config_version": entry["allocation_config_version"],
                            "approval_status": "human_approval_missing"})
    report = {"status": "candidate_ready", "mode": "dry_run_only", "confirmatory_eligible": False,
              "approval_status": "human_approval_missing", "generated_at": datetime.now(timezone.utc).isoformat(),
              "allocation_config_hash": allocator.config_hash, "assignments": assignments,
              "restricted_audit": audit, "future_allocations_persisted": False}
    if len({item["participant_id"] for item in audit}) != len(audit):
        raise RuntimeError("allocation audit identities are not unique")
    report["audit_hash"] = stable_hash(audit)
    atomic_write_json(output, report)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    payload = json.loads(args.input.read_text(encoding="utf-8"))
    generate(payload["enrolments"], args.output)
    print(json.dumps({"status": "candidate_ready", "output": str(args.output), "confirmatory_eligible": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
