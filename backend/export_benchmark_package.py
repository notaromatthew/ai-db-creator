"""Create a deterministic, hash-verifiable ZIP from benchmark reports."""
from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path

from app.utils.research import sha256_file, stable_hash

PACKAGE_VERSION = "benchmark-package-v1"
_UNSAFE_PATH = re.compile(r"(^|/)(source|uploads?)(/|$)|\.db$|interactions_store|raw", re.I)
_UNSAFE_TEXT = re.compile(r'(?:"|^|,|\b)(?:api[_-]?key|authorization|password|secret|prompt|email|name|ip|filename|sql|document|content|cell|value|raw)(?:"|\s*[:,=])', re.I)


def _assert_safe(path: Path, relative: str) -> None:
    if _UNSAFE_PATH.search(relative):
        raise ValueError(f"unsafe artifact excluded: {relative}")
    if path.suffix.lower() in {".json", ".csv", ".txt", ".tex"}:
        text = path.read_text(encoding="utf-8", errors="replace")
        if _UNSAFE_TEXT.search(text):
            raise ValueError(f"potential raw/secret field in artifact: {relative}")


def export_package(input_dir: Path, output_path: Path) -> dict:
    input_dir = input_dir.resolve()
    output_path = output_path.resolve()
    files = sorted(path for path in input_dir.rglob("*") if path.is_file() and path.resolve() != output_path)
    for path in files:
        _assert_safe(path, path.relative_to(input_dir).as_posix())
    entries = [{"path": path.relative_to(input_dir).as_posix(), "sha256": sha256_file(path),
                "size": path.stat().st_size} for path in files]
    manifest = {"package_version": PACKAGE_VERSION, "files": entries}
    manifest["content_hash"] = stable_hash(manifest)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path, entry in zip(files, entries):
            info = zipfile.ZipInfo(entry["path"], date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())
        info = zipfile.ZipInfo("MANIFEST.json", date_time=(1980, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8"))
    return {**manifest, "archive": str(output_path), "archive_sha256": sha256_file(output_path)}


def verify_package(path: Path) -> dict:
    with zipfile.ZipFile(path) as archive:
        failures = []
        names = archive.namelist()
        if len(names) != len(set(names)):
            failures.append({"path": "archive", "reason": "duplicate_entries"})
        unsafe = [name for name in names if Path(name).is_absolute() or ".." in Path(name).parts or "\\" in name]
        if unsafe:
            failures.extend({"path": name, "reason": "unsafe_path"} for name in unsafe)
        try:
            manifest = json.loads(archive.read("MANIFEST.json"))
        except (KeyError, json.JSONDecodeError):
            return {"status": "invalid", "failures": failures + [{"path": "MANIFEST.json", "reason": "missing_or_invalid"}]}
        declared = {entry.get("path") for entry in manifest.get("files", [])}
        declared_list = [entry.get("path") for entry in manifest.get("files", [])]
        if len(declared_list) != len(set(declared_list)):
            failures.append({"path": "MANIFEST.json", "reason": "duplicate_manifest_paths"})
        actual = set(names) - {"MANIFEST.json"}
        if declared != actual:
            failures.append({"path": "archive", "reason": "file_set_mismatch"})
        for entry in manifest.get("files", []):
            try:
                payload = archive.read(entry["path"])
            except KeyError:
                failures.append({"path": entry["path"], "reason": "missing"})
                continue
            try:
                relative = entry["path"]
                if _UNSAFE_PATH.search(relative):
                    failures.append({"path": relative, "reason": "unsafe_artifact"})
                elif Path(relative).suffix.lower() in {".json", ".csv", ".txt", ".tex"} and _UNSAFE_TEXT.search(payload.decode("utf-8", errors="replace")):
                    failures.append({"path": relative, "reason": "privacy_scan_failed"})
            except (TypeError, AttributeError):
                failures.append({"path": str(entry.get("path")), "reason": "invalid_manifest_entry"})
            import hashlib
            if hashlib.sha256(payload).hexdigest() != entry["sha256"] or len(payload) != entry["size"]:
                failures.append({"path": entry["path"], "reason": "hash_or_size_mismatch"})
        expected_hash = manifest.get("content_hash")
        actual_hash = stable_hash({key: value for key, value in manifest.items() if key != "content_hash"})
        if expected_hash != actual_hash:
            failures.append({"path": "MANIFEST.json", "reason": "content_hash_mismatch"})
    return {"status": "valid" if not failures else "invalid", "failures": failures}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", help="Benchmark report directory.")
    parser.add_argument("--output", help="Destination ZIP path.")
    parser.add_argument("--verify", help="Verify an existing package instead of exporting.")
    args = parser.parse_args(argv)
    if args.verify:
        result = verify_package(Path(args.verify))
        print(json.dumps(result, indent=2))
        return 0 if result["status"] == "valid" else 1
    if not args.input or not args.output:
        parser.error("--input and --output are required unless --verify is used")
    result = export_package(Path(args.input), Path(args.output))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
