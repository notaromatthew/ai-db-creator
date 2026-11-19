import json
from pathlib import Path

import pytest

import freeze_study_protocol


def test_candidate_manifest_hashes_every_required_file(tmp_path, monkeypatch):
    monkeypatch.setattr(freeze_study_protocol, "DEFAULT_PATHS", ["a.txt", "nested/b.txt"])
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "b.txt").write_text("b", encoding="utf-8")
    monkeypatch.setattr(freeze_study_protocol, "_git", lambda *_args: "")

    output = tmp_path / "report" / "manifest.json"
    manifest = freeze_study_protocol.create_manifest(tmp_path, output)

    assert manifest["status"] == "candidate_pre_pilot_not_final"
    assert manifest["questionnaires_collected"] is False
    assert set(manifest["files"]) == {"a.txt", "nested/b.txt"}
    assert json.loads(output.read_text(encoding="utf-8")) == manifest


def test_candidate_manifest_rejects_missing_protocol_file(tmp_path, monkeypatch):
    monkeypatch.setattr(freeze_study_protocol, "DEFAULT_PATHS", ["missing.txt"])
    with pytest.raises(FileNotFoundError):
        freeze_study_protocol.create_manifest(tmp_path, tmp_path / "manifest.json")
