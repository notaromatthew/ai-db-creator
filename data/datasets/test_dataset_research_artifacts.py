from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from pathlib import Path

from build_research_candidates import CANDIDATES, DATASETS, EXPERT_PACK, REQUIRED_COVERAGE, ROOT, build_workload


def test_candidate_workloads_are_complete_and_gold_derived():
    for dataset in ("university", "library", "hospital"):
        workload = build_workload(dataset)
        assert workload["approval_status"] == "candidate_unapproved"
        assert workload["human_approval_required"] is True
        assert {query["coverage_type"] for query in workload["queries"]} == REQUIRED_COVERAGE
        connection = sqlite3.connect(DATASETS / dataset / "ground_truth.db")
        try:
            for query in workload["queries"]:
                cursor = connection.execute(query["sql"])
                assert [item[0] for item in cursor.description or []] == query["expected"]["columns"]
                assert [list(row) for row in cursor.fetchall()] == query["expected"]["rows"]
        finally:
            connection.close()


def test_freeze_candidate_hashes_are_valid_but_not_approved():
    manifest = json.loads((CANDIDATES / "research-freeze-manifest.candidate.json").read_text())
    assert manifest["status"] == "unapproved"
    assert manifest["technical_hash_status"] == "valid"
    assert manifest["human_approval_inferred"] is False
    assert manifest["approved_by"] is None and manifest["approved_at"] is None
    for artifact in manifest["artifacts"]:
        path = ROOT / artifact["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]


def test_expert_pack_is_blinded_and_has_no_human_ratings():
    manifest = json.loads((EXPERT_PACK / "manifest.json").read_text())
    assert manifest["status"] == "candidate_unapproved"
    assert manifest["technical_status"] == "candidate_complete"
    assert manifest["human_approval_inferred"] is False
    assert manifest["ratings_status"] == "not_collected"
    assert manifest["rubric_version"] == "rubric-v1-candidate"
    assert {item["path"] for item in manifest["support_files"]} == {
        "instructions.md", "rubric.md", "calibration-example.json",
        "qualification-template.csv", "blind-order.csv"}
    assert set(manifest["blind_order"]) == {item["artifact_id"] for item in manifest["artifacts"]}
    with (EXPERT_PACK / "blind-order.csv").open(newline="", encoding="utf-8") as source:
        order_rows = list(csv.DictReader(source))
    assert [row["artifact_id"] for row in order_rows] == manifest["blind_order"]
    assert manifest["blind_order"] != sorted(manifest["blind_order"])
    for artifact in manifest["artifacts"]:
        path = EXPERT_PACK / artifact["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    for support in manifest["support_files"]:
        path = EXPERT_PACK / support["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == support["sha256"]
    with (EXPERT_PACK / "ratings.csv").open(newline="", encoding="utf-8") as source:
        assert len(list(csv.reader(source))) == 1


def test_governance_candidate_cannot_claim_approval():
    evidence = json.loads((CANDIDATES / "governance-evidence.candidate.json").read_text())
    assert evidence["status"] == "candidate_unapproved"
    assert evidence["technical_status"] == "template_complete_evidence_missing"
    assert evidence["human_approval_inferred"] is False
    assert evidence["human_approval_required"] is True
    assert evidence["public_package"] is None and evidence["restricted_archive"] is None
