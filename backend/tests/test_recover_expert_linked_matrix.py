import json
from pathlib import Path

import pytest

from recover_expert_linked_matrix import (
    MANIFEST_VERSION,
    _load_runs,
    _prepare_output,
    _structural_body,
    _tree_entries,
    _validate_output_path,
)


def test_structural_body_ignores_translated_intro(tmp_path: Path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    body = "TABLE people\n  - id (INTEGER) [PK]\n\nRELATIONSHIPS\n"
    first.write_text("# Schema\n\nEnglish introduction.\n\n" + body, encoding="utf-8")
    second.write_text("# Schema\n\nIntroduzione italiana.\n\n" + body, encoding="utf-8")
    assert _structural_body(first) == _structural_body(second)


def test_load_runs_requires_five_runs_per_cell(tmp_path: Path):
    with pytest.raises(ValueError, match="Expected five runs"):
        _load_runs(tmp_path)


def test_recovery_output_must_be_below_reports(tmp_path: Path):
    reports = tmp_path / "backend" / "reports"
    protected = reports / "rq1_expert_package"
    reports.mkdir(parents=True)
    with pytest.raises(ValueError, match="must be below"):
        _validate_output_path(tmp_path / "elsewhere", reports, protected)
    with pytest.raises(ValueError, match="Unsafe recovery output"):
        _validate_output_path(protected, reports, protected)


def test_recovery_output_accepts_new_reports_child(tmp_path: Path):
    reports = tmp_path / "backend" / "reports"
    protected = reports / "rq1_expert_package"
    reports.mkdir(parents=True)
    _validate_output_path(reports / "recovered_matrix", reports, protected)


def test_tree_entries_excludes_transient_recovery_marker(tmp_path: Path):
    (tmp_path / ".recovery-incomplete.json").write_text("{}", encoding="utf-8")
    (tmp_path / "kept.json").write_text("{}", encoding="utf-8")
    entries = _tree_entries(tmp_path)
    assert [entry["path"] for entry in entries] == ["kept.json"]


def test_overwrite_refuses_unrecognised_directory(tmp_path: Path):
    reports = tmp_path / "backend" / "reports"
    protected = reports / "rq1_expert_package"
    output = reports / "recovered_matrix"
    output.mkdir(parents=True)
    (output / "unrelated.txt").write_text("keep", encoding="utf-8")
    with pytest.raises(ValueError, match="unrecognised directory"):
        _prepare_output(output, reports, protected, overwrite=True)
    assert (output / "unrelated.txt").read_text(encoding="utf-8") == "keep"


def test_overwrite_accepts_only_recognised_recovery_directory(tmp_path: Path):
    reports = tmp_path / "backend" / "reports"
    protected = reports / "rq1_expert_package"
    output = reports / "recovered_matrix"
    output.mkdir(parents=True)
    (output / "recovery_manifest.json").write_text(
        json.dumps({"manifest_version": MANIFEST_VERSION}), encoding="utf-8"
    )
    (output / "stale.txt").write_text("remove", encoding="utf-8")
    _prepare_output(output, reports, protected, overwrite=True)
    assert not (output / "stale.txt").exists()
    marker = json.loads(
        (output / ".recovery-incomplete.json").read_text(encoding="utf-8")
    )
    assert marker == {"manifest_version": MANIFEST_VERSION, "status": "incomplete"}
