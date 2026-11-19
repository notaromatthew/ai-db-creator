import csv
from datetime import datetime, timedelta, timezone

import pytest

from analyze_user_study import AnalysisError, analyze, benjamini_hochberg, holm_adjust


def _write(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _dataset(tmp_path, missing_outcome=False):
    participants = tmp_path / "participants.csv"
    events = tmp_path / "events.csv"
    outcomes = tmp_path / "outcomes.csv"
    participant_rows, event_rows, outcome_rows = [], [], []
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for arm_index, arm in enumerate(("manual", "ai_only", "ai_interface")):
        for index in range(6):
            pid = f"P{arm_index}{index}"
            participant_rows.append({
                "participant_id": pid, "arm": arm, "completed": "true", "withdrawn": "false",
            })
            event_rows.extend([
                {"participant_id": pid, "arm": arm, "type": "task_start", "created_at": start.isoformat(), "data": "{}"},
                {"participant_id": pid, "arm": arm, "type": "schema_edit" if arm == "ai_interface" and index % 2 else "page_view", "created_at": (start + timedelta(minutes=1)).isoformat(), "data": "{}"},
                {"participant_id": pid, "arm": arm, "type": "task_end", "created_at": (start + timedelta(minutes=10 + index)).isoformat(), "data": "{}"},
            ])
            outcome_rows.append({
                "participant_id": pid, "dataset": "demo", "schema_quality": 3 + arm_index * 0.5 + index * 0.01,
                "residual_error_rate": 0.3 - arm_index * 0.1, "task_success": "true",
            })
    if missing_outcome:
        outcome_rows.pop()
    _write(participants, list(participant_rows[0]), participant_rows)
    _write(events, list(event_rows[0]), event_rows)
    _write(outcomes, list(outcome_rows[0]), outcome_rows)
    return participants, events, outcomes


def test_multiple_testing_adjustments_are_monotone():
    assert holm_adjust([0.01, 0.04, 0.03]) == pytest.approx([0.03, 0.06, 0.06])
    adjusted = benjamini_hochberg([0.01, 0.04, 0.03])
    assert adjusted == pytest.approx([0.03, 0.04, 0.04])


def test_analysis_writes_frozen_outputs(tmp_path):
    inputs = _dataset(tmp_path)
    output = tmp_path / "analysis"
    manifest = analyze(*inputs, output, seed=7, resamples=200)
    assert manifest["complete_nonwithdrawn_participants"] == 18
    assert manifest["arm_counts"] == {"manual": 6, "ai_only": 6, "ai_interface": 6}
    assert {path.name for path in output.iterdir()} == {
        "participant_metrics.csv", "arm_descriptives.csv", "confirmatory_contrasts.csv",
        "rq4_patterns.csv", "rq4_correlations.csv", "rq4_clusters.csv", "manifest.json", "REPORT.md",
    }
    with (output / "confirmatory_contrasts.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 6
    assert sum(row["family"] == "confirmatory" and bool(row["holm_p"]) for row in rows) == 4
    assert (output / "rq4_patterns.csv").read_text(encoding="utf-8").count("task_start") > 0


def test_analysis_rejects_incomplete_outcome_matrix(tmp_path):
    inputs = _dataset(tmp_path, missing_outcome=True)
    with pytest.raises(AnalysisError, match="outcome finale mancante"):
        analyze(*inputs, tmp_path / "analysis", seed=7, resamples=200)
