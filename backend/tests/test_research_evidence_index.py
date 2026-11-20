import hashlib
import json
from pathlib import Path

import pytest

from build_research_evidence_index import EvidenceSpec, build_index


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(tmp_path: Path):
    root = tmp_path / "repo"
    report = root / "backend/reports/demo"
    report.mkdir(parents=True)
    result = report / "result.json"
    result.write_text('{"ok": true}\n', encoding="utf-8")
    manifest = report / "manifest.json"
    manifest.write_text(json.dumps({
        "software_revision": "rev-1",
        "n_evaluators": 3,
        "n_schemas": 2,
        "n_ratings": 6,
        "outputs": {"result.json": digest(result)},
    }), encoding="utf-8")
    script = root / "backend/build_research_evidence_index.py"
    script.write_text("print('fixture')\n", encoding="utf-8")
    spec = EvidenceSpec(
        "rq1_student_panel", "RQ1", "observed_primary_panel",
        "backend/reports/demo/manifest.json",
        ("backend/reports/demo/manifest.json", "backend/reports/demo/result.json"),
        (("backend/reports/demo/manifest.json", "outputs"),),
    )
    return root, spec


def test_build_index_hashes_public_artifacts_and_internal_outputs(tmp_path, monkeypatch):
    root, spec = fixture(tmp_path)
    monkeypatch.setattr("build_research_evidence_index.__file__", str(root / "backend/build_research_evidence_index.py"))
    output = tmp_path / "output"
    manifest = build_index(root, output, specs=(spec,))
    assert manifest["component_count"] == 1
    assert manifest["selected_public_artifact_count"] == 2
    assert manifest["internal_output_hashes_verified"] == 1
    assert manifest["components"][0]["revisions"] == {"software_revision": "rev-1"}
    assert json.loads((output / "manifest.json").read_text(encoding="utf-8")) == manifest
    assert "mapping privati" in (output / "REPORT.md").read_text(encoding="utf-8")


def test_build_index_rejects_internal_hash_mismatch(tmp_path, monkeypatch):
    root, spec = fixture(tmp_path)
    monkeypatch.setattr("build_research_evidence_index.__file__", str(root / "backend/build_research_evidence_index.py"))
    (root / "backend/reports/demo/result.json").write_text("changed\n", encoding="utf-8")
    with pytest.raises(ValueError, match="internal output hash mismatch"):
        build_index(root, tmp_path / "output", specs=(spec,))


def test_build_index_rejects_private_mapping_and_secret_like_values(tmp_path, monkeypatch):
    root, spec = fixture(tmp_path)
    monkeypatch.setattr("build_research_evidence_index.__file__", str(root / "backend/build_research_evidence_index.py"))
    private = EvidenceSpec(
        "private", "RQ2", "forbidden", spec.anchor,
        ("backend/reports/demo/private_mapping.json",),
    )
    (root / "backend/reports/demo/private_mapping.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="private artifact"):
        build_index(root, tmp_path / "private-output", specs=(private,))
    (root / "backend/reports/demo/result.json").write_text("sk-or-v1-secretvalue", encoding="utf-8")
    secret_spec = EvidenceSpec("secret", "RQ2", "forbidden", spec.anchor, ("backend/reports/demo/result.json",))
    with pytest.raises(ValueError, match="secret-like"):
        build_index(root, tmp_path / "secret-output", specs=(secret_spec,))
