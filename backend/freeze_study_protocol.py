"""Create a reproducible pre-pilot candidate manifest for the participant study."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PATHS = [
    "docs/13-data-governance.md",
    "docs/14-usability-pilot-protocol.md",
    "docs/16-manual-condition-protocol.md",
    "docs/19-user-study-analysis.md",
    "docs/23-study-protocol-amendment-2026-11-18.md",
    "docs/24-participant-study-runbook.md",
    "backend/analyze_user_study.py",
    "backend/app/api/study.py",
    "backend/app/services/research_study.py",
    "frontend/src/pages/StudyPage.tsx",
    "frontend/src/pages/research/studyTexts.ts",
    "frontend/src/research/studyContext.ts",
]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(root: Path, *args: str) -> str | None:
    result = subprocess.run(
        ["git", *args], cwd=root, capture_output=True, text=True, check=False
    )
    return result.stdout.strip() if result.returncode == 0 else None


def create_manifest(root: Path, output: Path) -> dict[str, Any]:
    root = root.resolve()
    missing = [relative for relative in DEFAULT_PATHS if not (root / relative).is_file()]
    if missing:
        raise FileNotFoundError(f"Missing protocol files: {missing}")
    files = {relative: sha256_file(root / relative) for relative in DEFAULT_PATHS}
    status = _git(root, "status", "--porcelain")
    manifest = {
        "protocol": "participant_study_protocol_v1",
        "status": "candidate_pre_pilot_not_final",
        "questionnaires_collected": False,
        "arms": ["manual", "ai_only", "ai_interface"],
        "analysis_entrypoint": "backend/analyze_user_study.py",
        "git_revision": _git(root, "rev-parse", "HEAD"),
        "working_tree_dirty": bool(status),
        "files": files,
        "freeze_rule": (
            "Generate the final manifest only after pilot exit criteria are met; "
            "any later material change requires an explicit amendment."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "reports" / "study_protocol_candidate" / "manifest.json",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(create_manifest(args.root, args.output), indent=2))


if __name__ == "__main__":
    main()
