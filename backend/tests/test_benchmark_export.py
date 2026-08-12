import json
import zipfile

from export_benchmark_package import export_package


def test_export_package_is_reproducible_and_hash_verifiable(tmp_path):
    reports = tmp_path / "reports"
    reports.mkdir()
    (reports / "run.json").write_text('{"f1": 1.0}', encoding="utf-8")
    first = export_package(reports, tmp_path / "first.zip")
    second = export_package(reports, tmp_path / "second.zip")
    assert first["content_hash"] == second["content_hash"]
    assert first["archive_sha256"] == second["archive_sha256"]
    with zipfile.ZipFile(tmp_path / "first.zip") as archive:
        manifest = json.loads(archive.read("MANIFEST.json"))
    assert manifest["files"][0]["path"] == "run.json"
    assert manifest["files"][0]["sha256"]
