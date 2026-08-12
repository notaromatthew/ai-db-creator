"""Build deterministic, explicitly unapproved research-candidate artifacts.

This script never freezes a protocol and never fabricates human ratings.  Every
expected workload answer is executed against the versioned gold SQLite file.
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sqlite3
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DATASETS = ROOT / "data" / "datasets"
CANDIDATES = ROOT / "data" / "research-candidates"
EXPERT_PACK = CANDIDATES / "expert-pack-candidate"
REQUIRED_COVERAGE = {"lookup", "filter", "join", "aggregate", "missing_value", "temporal", "integrity"}


WORKLOADS = {
    "university": [
        ("U01", "lookup", "Find one student by the source-grounded institutional email.",
         "SELECT student_id, name, email FROM students WHERE email = 'student1@university.example'", False),
        ("U02", "filter", "List high-credit courses.",
         "SELECT course_code, title, credits FROM courses WHERE credits >= 9 ORDER BY course_code", True),
        ("U03", "join", "Resolve enrollment rows to student and course labels.",
         "SELECT s.email, c.course_code, e.semester, e.grade FROM enrollments e JOIN students s ON s.student_id=e.student_id JOIN courses c ON c.course_id=e.course_id ORDER BY s.email, c.course_code LIMIT 8", True),
        ("U04", "aggregate", "Count enrollments per course, retaining courses with zero enrollments.",
         "SELECT c.course_code, COUNT(e.student_id) AS enrollment_count FROM courses c LEFT JOIN enrollments e ON e.course_id=c.course_id GROUP BY c.course_id, c.course_code ORDER BY c.course_code", True),
        ("U05", "missing_value", "Identify students with no enrollment relationship.",
         "SELECT s.email FROM students s LEFT JOIN enrollments e ON e.student_id=s.student_id WHERE e.student_id IS NULL ORDER BY s.email", True),
        ("U06", "temporal", "Traverse the student-course many-to-many relation for semester 2026-01.",
         "SELECT s.email, c.course_code, e.grade FROM enrollments e JOIN students s ON s.student_id=e.student_id JOIN courses c ON c.course_id=e.course_id WHERE e.semester='2026-01' ORDER BY s.email, c.course_code", True),
        ("U07", "integrity", "Count enrollment rows whose student or course parent is missing.",
         "SELECT COUNT(*) AS orphan_count FROM enrollments e LEFT JOIN students s ON s.student_id=e.student_id LEFT JOIN courses c ON c.course_id=e.course_id WHERE s.student_id IS NULL OR c.course_id IS NULL", False),
    ],
    "library": [
        ("L01", "lookup", "Find one book by its source-grounded ISBN.",
         "SELECT book_id, isbn, title, author FROM books WHERE isbn='978-0536-660-9539'", False),
        ("L02", "filter", "List unpaid fines above five euros.",
         "SELECT fine_id, loan_id, amount FROM fines WHERE paid_on IS NULL AND amount > 5 ORDER BY fine_id", True),
        ("L03", "join", "Resolve loans to member and book labels.",
         "SELECT l.loan_id, m.email, b.isbn, l.loan_date, l.due_date FROM loans l JOIN members m ON m.member_id=l.member_id JOIN books b ON b.book_id=l.book_id ORDER BY l.loan_id LIMIT 8", True),
        ("L04", "aggregate", "Count loans by catalogue category.",
         "SELECT c.name AS category, COUNT(l.loan_id) AS loan_count FROM categories c LEFT JOIN books b ON b.category_id=c.category_id LEFT JOIN loans l ON l.book_id=b.book_id GROUP BY c.category_id, c.name ORDER BY c.name", True),
        ("L05", "missing_value", "Identify fines with a missing payment date.",
         "SELECT fine_id, loan_id, amount FROM fines WHERE paid_on IS NULL ORDER BY fine_id", True),
        ("L06", "temporal", "Traverse the member-book many-to-many loan relation during June 2026.",
         "SELECT m.email, b.isbn, l.loan_date FROM loans l JOIN members m ON m.member_id=l.member_id JOIN books b ON b.book_id=l.book_id WHERE l.loan_date >= '2026-06-01' AND l.loan_date < '2026-07-01' ORDER BY l.loan_date, m.email, b.isbn", True),
        ("L07", "integrity", "Count orphaned loan and fine foreign keys.",
         "SELECT (SELECT COUNT(*) FROM loans l LEFT JOIN books b ON b.book_id=l.book_id LEFT JOIN members m ON m.member_id=l.member_id WHERE b.book_id IS NULL OR m.member_id IS NULL) + (SELECT COUNT(*) FROM fines f LEFT JOIN loans l ON l.loan_id=f.loan_id WHERE l.loan_id IS NULL) AS orphan_count", False),
    ],
    "hospital": [
        ("H01", "lookup", "Find one patient by the source-grounded fiscal code.",
         "SELECT patient_id, fiscal_code, full_name, birth_date FROM patients WHERE fiscal_code='BH0128D4951'", False),
        ("H02", "filter", "List the five largest invoices above six hundred euros.",
         "SELECT invoice_id, appointment_id, amount, issued_on FROM invoices WHERE amount > 600 ORDER BY amount DESC, invoice_id LIMIT 5", True),
        ("H03", "join", "Resolve appointments to patient, doctor and ward labels.",
         "SELECT a.appointment_id, p.fiscal_code, d.full_name AS doctor, w.name AS ward, a.scheduled_on FROM appointments a JOIN patients p ON p.patient_id=a.patient_id JOIN doctors d ON d.doctor_id=a.doctor_id JOIN wards w ON w.ward_id=a.ward_id ORDER BY a.appointment_id LIMIT 8", True),
        ("H04", "aggregate", "Count appointments per ward.",
         "SELECT w.name AS ward, COUNT(a.appointment_id) AS appointment_count FROM wards w LEFT JOIN appointments a ON a.ward_id=w.ward_id GROUP BY w.ward_id, w.name ORDER BY w.name", True),
        ("H05", "missing_value", "Identify appointments without an invoice relationship.",
         "SELECT a.appointment_id, a.scheduled_on FROM appointments a LEFT JOIN invoices i ON i.appointment_id=a.appointment_id WHERE i.invoice_id IS NULL ORDER BY a.appointment_id", True),
        ("H06", "temporal", "Traverse the patient-medication many-to-many clinical chain in the first half of 2026.",
         "SELECT p.fiscal_code, m.name AS medication, COUNT(*) AS prescription_count FROM appointments a JOIN patients p ON p.patient_id=a.patient_id JOIN treatments t ON t.appointment_id=a.appointment_id JOIN prescriptions pr ON pr.treatment_id=t.treatment_id JOIN medications m ON m.medication_id=pr.medication_id WHERE a.scheduled_on >= '2026-01-01' AND a.scheduled_on < '2026-07-01' GROUP BY p.fiscal_code, m.medication_id, m.name ORDER BY p.fiscal_code, m.name", True),
        ("H07", "integrity", "Count orphaned foreign keys across the clinical chain.",
         "SELECT (SELECT COUNT(*) FROM appointments a LEFT JOIN patients p ON p.patient_id=a.patient_id LEFT JOIN doctors d ON d.doctor_id=a.doctor_id LEFT JOIN wards w ON w.ward_id=a.ward_id WHERE p.patient_id IS NULL OR d.doctor_id IS NULL OR w.ward_id IS NULL) + (SELECT COUNT(*) FROM treatments t LEFT JOIN appointments a ON a.appointment_id=t.appointment_id WHERE a.appointment_id IS NULL) + (SELECT COUNT(*) FROM prescriptions pr LEFT JOIN treatments t ON t.treatment_id=pr.treatment_id LEFT JOIN medications m ON m.medication_id=pr.medication_id WHERE t.treatment_id IS NULL OR m.medication_id IS NULL) + (SELECT COUNT(*) FROM invoices i LEFT JOIN appointments a ON a.appointment_id=i.appointment_id WHERE a.appointment_id IS NULL) AS orphan_count", False),
    ],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _execute_expected(database: Path, sql: str) -> dict:
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        cursor = connection.execute(sql)
        return {"columns": [item[0] for item in cursor.description or []],
                "rows": [list(row) for row in cursor.fetchall()]}
    finally:
        connection.close()


def build_workload(dataset: str) -> dict:
    database = DATASETS / dataset / "ground_truth.db"
    queries = []
    for query_id, coverage, requirement, sql, ordered in WORKLOADS[dataset]:
        queries.append({
            "id": query_id,
            "coverage_type": coverage,
            "requirement": requirement,
            "source_grounding": {"gold_database": "ground_truth.db", "derivation": "executed_not_hand_authored"},
            "ordered": ordered,
            "sql": sql,
            "expected": _execute_expected(database, sql),
        })
    assert {item["coverage_type"] for item in queries} == REQUIRED_COVERAGE
    return {
        "protocol": "functional-workload-v1",
        "version": "candidate-v2",
        "approval_status": "candidate_unapproved",
        "expected_result_status": "deterministic_gold_derived_candidate",
        "human_approval_required": True,
        "dataset": dataset,
        "canonicalisation_version": "functional-workload-v1",
        "queries": queries,
    }


def write_workloads() -> None:
    for dataset in WORKLOADS:
        path = DATASETS / dataset / "functional_workload.json"
        path.write_text(json.dumps(build_workload(dataset), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def write_expert_pack() -> None:
    artifacts = EXPERT_PACK / "artifacts"
    artifacts.mkdir(parents=True, exist_ok=True)
    blind_order = []
    manifest_artifacts = []
    restricted_mapping = {"status": "candidate_unapproved_restricted", "human_release_required": True, "mapping": {}}
    for index, dataset in enumerate(sorted(WORKLOADS), start=1):
        artifact_id = f"B{index:03d}"
        blind_order.append(artifact_id)
        source = DATASETS / dataset / "gold_schema.json"
        target = artifacts / f"{artifact_id}.json"
        schema = json.loads(source.read_text(encoding="utf-8"))
        target.write_text(json.dumps({"tables": schema["tables"], "relationships": schema["relationships"]},
                                     indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        manifest_artifacts.append({"artifact_id": artifact_id, "path": f"artifacts/{target.name}", "sha256": _sha256(target)})
        restricted_mapping["mapping"][artifact_id] = {"dataset": dataset, "source_sha256": _sha256(source)}
    support_content = {
        "instructions.md": "# Blinded expert review candidate\n\nScore each artifact independently using rubric-v1. Do not infer condition or discuss ratings before lock. This candidate is unapproved and contains no human ratings.\n",
        "rubric.md": "# Rubric v1 candidate\n\nRate 1–5: D1 3NF compliance; D2 naming; D3 constraints; D4 relationships; D5 domain alignment. Follow docs/21-expert-rating-pack-draft.md.\n",
        "calibration-example.json": json.dumps({"status":"synthetic_excluded_candidate","tables":[{"name":"example_entities","columns":["id","label"]}]}, indent=2) + "\n",
        "qualification-template.csv": "rater_id,database_experience,conflict_of_interest,training_completed,calibration_date,qualification_status\n",
        "blind-order.csv": "presentation_order,artifact_id\n" + "".join(f"{index},{artifact_id}\n" for index, artifact_id in enumerate(blind_order, 1)),
    }
    support_files = []
    for name, content in support_content.items():
        path = EXPERT_PACK / name
        path.write_text(content, encoding="utf-8")
        support_files.append({"path": name, "sha256": _sha256(path)})
    seed_material = b"expert-pack-candidate-v1"
    random.Random(int.from_bytes(hashlib.sha256(seed_material).digest(), "big")).shuffle(blind_order)
    if blind_order == sorted(blind_order):
        blind_order = blind_order[1:] + blind_order[:1]
    blind_order_path = EXPERT_PACK / "blind-order.csv"
    blind_order_path.write_text("presentation_order,artifact_id\n" + "".join(
        f"{index},{artifact_id}\n" for index, artifact_id in enumerate(blind_order, 1)), encoding="utf-8")
    for item in support_files:
        if item["path"] == "blind-order.csv":
            item["sha256"] = _sha256(blind_order_path)
    manifest = {
        "status": "candidate_unapproved",
        "technical_status": "candidate_complete",
        "package_version": "expert-pack-candidate-v1",
        "rubric_version": "rubric-v1-candidate",
        "generator": "data/datasets/build_research_candidates.py",
        "purpose": "technical_pack_validation_only_not_human_ratings",
        "seed_hash": hashlib.sha256(seed_material).hexdigest(),
        "blind_order": blind_order,
        "artifacts": manifest_artifacts,
        "support_files": support_files,
        "ratings_status": "not_collected",
        "human_approval_required": True,
        "human_approval_inferred": False,
    }
    (EXPERT_PACK / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    with (EXPERT_PACK / "ratings.csv").open("w", newline="", encoding="utf-8") as output:
        csv.writer(output).writerow(["artifact_id", "rater_id", "presentation_order", "rubric_version",
                                     "d1_3nf", "d2_naming", "d3_constraints", "d4_relationships", "d5_domain",
                                     "comment", "locked_at"])
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    (CANDIDATES / "expert-pack-candidate-restricted-mapping.json").write_text(
        json.dumps(restricted_mapping, indent=2) + "\n", encoding="utf-8")


def write_freeze_candidate() -> None:
    paths = []
    for dataset in sorted(WORKLOADS):
        for name in ("gold_schema.json", "ground_truth.db", "rq2_alignment.json", "functional_workload.json"):
            paths.append(DATASETS / dataset / name)
    manifest = {
        "status": "unapproved",
        "technical_hash_status": "valid",
        "manifest_version": "research-freeze-candidate-v1",
        "approved_by": None,
        "approved_at": None,
        "human_approval_required": True,
        "human_approval_inferred": False,
        "artifacts": [{"path": path.relative_to(ROOT).as_posix(), "sha256": _sha256(path)} for path in paths],
    }
    CANDIDATES.mkdir(parents=True, exist_ok=True)
    (CANDIDATES / "research-freeze-manifest.candidate.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


def write_governance_candidate() -> None:
    template = json.loads((ROOT / "docs" / "templates" / "governance-evidence-template.json").read_text(encoding="utf-8"))
    template.update({
        "status": "candidate_unapproved",
        "technical_status": "template_complete_evidence_missing",
        "evidence_id": "local-research-governance-candidate-v1",
        "public_package": None,
        "restricted_archive": None,
        "human_approval_inferred": False,
        "candidate_artifacts": [
            {"path": "data/research-candidates/research-freeze-manifest.candidate.json",
             "sha256": _sha256(CANDIDATES / "research-freeze-manifest.candidate.json")},
            {"path": "data/research-candidates/expert-pack-candidate/manifest.json",
             "sha256": _sha256(EXPERT_PACK / "manifest.json")},
        ],
    })
    (CANDIDATES / "governance-evidence.candidate.json").write_text(
        json.dumps(template, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    write_workloads()
    write_expert_pack()
    write_freeze_candidate()
    write_governance_candidate()
    print("candidate workloads and research artifacts generated; status remains unapproved")


if __name__ == "__main__":
    main()
