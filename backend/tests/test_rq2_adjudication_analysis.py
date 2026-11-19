import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from analyze_rq2_adjudication import analyze, read_review


HEADERS = [
    "item_id", "dataset", "table", "natural_key", "candidate_value",
    "reference_value", "decision", "confidence", "notes",
]


def _review(path: Path, decisions: list[tuple[str, str, str]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Review"
    sheet.append(HEADERS)
    for index, (decision, confidence, notes) in enumerate(decisions, start=1):
        sheet.append([
            f"RQ2-{index}", "test", "facts", f"[{index}]", "a", "b",
            decision, confidence, notes,
        ])
    workbook.save(path)


def test_analysis_reports_agreement_and_consensus(tmp_path):
    left = tmp_path / "a.xlsx"
    right = tmp_path / "b.xlsx"
    _review(left, [("errore", "alta", ""), ("alias valido", "media", "")])
    _review(right, [("errore", "alta", ""), ("rappresentazione equivalente", "media", "")])
    mapping = tmp_path / "mapping.json"
    mapping.write_text(json.dumps([
        {"item_id": "RQ2-1", "condition": "baseline", "run": 1},
        {"item_id": "RQ2-2", "condition": "full_llm", "run": 1},
    ]), encoding="utf-8")

    summary = analyze(left, right, mapping, tmp_path / "out")

    assert summary["item_count"] == 2
    assert summary["exact_agreement_rate"] == 0.5
    assert summary["disagreement_count"] == 1
    assert summary["status"] == "awaiting_consensus"
    consensus = (tmp_path / "out" / "consensus_required.csv").read_text(encoding="utf-8")
    assert consensus.count("RQ2-2") == 1
    assert "condition" not in consensus.splitlines()[0]
    assert "run" not in consensus.splitlines()[0]


def test_ambiguous_decision_requires_notes(tmp_path):
    review = tmp_path / "review.xlsx"
    _review(review, [("gold ambiguo", "media", "")])
    with pytest.raises(ValueError, match="notes required"):
        read_review(review)
