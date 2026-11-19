import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from finalize_rq2_adjudication import finalize


REVIEW_HEADERS = [
    "item_id", "dataset", "table", "natural_key", "candidate_value",
    "reference_value", "decision", "confidence", "notes",
]
CONSENSUS_HEADERS = [
    "item_id", "dataset", "table", "natural_key", "candidate_value",
    "reference_value", "reviewer_a_decision", "reviewer_a_confidence",
    "reviewer_a_notes", "reviewer_b_decision", "reviewer_b_confidence",
    "reviewer_b_notes", "consensus_decision", "consensus_notes",
]


def _review(path: Path, decisions: list[str]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Review"
    sheet.append(REVIEW_HEADERS)
    for index, decision in enumerate(decisions, start=1):
        sheet.append([
            f"RQ2-{index}", "test", "facts", f"[{index}]", "a", "b",
            decision, "alta", "nota",
        ])
    workbook.save(path)


def _consensus(path: Path, note: str = "risolto") -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Consenso"
    sheet.append(CONSENSUS_HEADERS)
    sheet.append([
        "RQ2-2", "test", "facts", "[2]", "a", "b", "errore", "alta",
        "nota", "non determinabile", "alta", "nota", "gold ambiguo", note,
    ])
    workbook.save(path)


def test_finalize_builds_unblinded_ledger_and_summary(tmp_path):
    left, right, consensus = tmp_path / "a.xlsx", tmp_path / "b.xlsx", tmp_path / "c.xlsx"
    _review(left, ["errore", "errore"])
    _review(right, ["errore", "non determinabile"])
    _consensus(consensus)
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps([
        {"item_id": "RQ2-1", "condition": "baseline", "run": 1,
         "source_format": "combined", "source_ledger": "a.csv", "source_row": 2},
        {"item_id": "RQ2-2", "condition": "full_llm", "run": 1,
         "source_format": "combined", "source_ledger": "b.csv", "source_row": 2},
    ]), encoding="utf-8")

    result = finalize(left, right, consensus, mapping, tmp_path / "out")

    assert result["status"] == "consensus_complete"
    assert result["final_decision_counts"] == {"errore": 1, "gold ambiguo": 1}
    assert result["by_condition"]["baseline"]["decision_counts"] == {"errore": 1}
    assert (tmp_path / "out" / "final_adjudication_ledger.csv").is_file()
    assert (tmp_path / "out" / "final_manifest.json").is_file()


def test_finalize_requires_consensus_notes(tmp_path):
    left, right, consensus = tmp_path / "a.xlsx", tmp_path / "b.xlsx", tmp_path / "c.xlsx"
    _review(left, ["errore", "errore"])
    _review(right, ["errore", "non determinabile"])
    _consensus(consensus, note="")
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps([
        {"item_id": "RQ2-1", "condition": "baseline", "run": 1,
         "source_format": "combined", "source_ledger": "a.csv", "source_row": 2},
        {"item_id": "RQ2-2", "condition": "full_llm", "run": 1,
         "source_format": "combined", "source_ledger": "b.csv", "source_row": 2},
    ]), encoding="utf-8")

    with pytest.raises(ValueError, match="consensus_notes is required"):
        finalize(left, right, consensus, mapping, tmp_path / "out")
