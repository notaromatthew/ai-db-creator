"""Run and record the automated pre-pilot checks for RQ0, RQ3 and RQ4."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "backend" / "reports" / "study_protocol_candidate" / "manifest.json"
BACKEND_TESTS = (
    "tests/test_user_study_analysis.py",
    "tests/test_study_protocol_freeze.py",
    "tests/test_research_study.py",
    "tests/test_interaction_logger.py",
)
FRONTEND_TESTS = (
    "src/pages/StudyPage.test.tsx",
    "src/pages/research/ResearchPage.test.tsx",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command: list[str], cwd: Path) -> dict:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    output = result.stdout + "\n" + result.stderr
    recorded_command = ["python", *command[1:]] if command[0] == sys.executable else command
    return {
        "command": recorded_command,
        "exit_code": result.returncode,
        "passed": result.returncode == 0,
        "summary": next(
            (
                match.group(0)
                for pattern in (
                    r"Tests\s+\d+ passed \(\d+\)",
                    r"\d+ passed(?:, \d+ skipped)?",
                    r"built in [0-9.]+s",
                )
                if (match := re.search(pattern, output))
            ),
            "completed" if result.returncode == 0 else "failed",
        ),
    }


def audit(output: Path) -> dict:
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    hash_failures = []
    for relative, expected in protocol["files"].items():
        path = ROOT / relative
        if not path.is_file() or sha256(path) != expected:
            hash_failures.append(relative)

    npm = "npm.cmd" if os.name == "nt" else "npm"
    checks = {
        "protocol_hashes": {
            "passed": not hash_failures,
            "checked": len(protocol["files"]),
            "failures": hash_failures,
        },
        "backend_study_tests": run(
            [sys.executable, "-m", "pytest", *BACKEND_TESTS, "-q"], ROOT / "backend"
        ),
        "frontend_study_tests": run(
            [npm, "run", "test", "--", "--run", *FRONTEND_TESTS], ROOT / "frontend"
        ),
        "frontend_production_build": run([npm, "run", "build"], ROOT / "frontend"),
    }
    automated_ready = all(check["passed"] for check in checks.values())
    manifest = {
        "audit": "participant_study_automated_pre_pilot_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "automated_pre_pilot_ready" if automated_ready else "automated_pre_pilot_failed",
        "protocol_status": protocol["status"],
        "protocol_git_revision": protocol["git_revision"],
        "protocol_manifest_sha256": sha256(PROTOCOL),
        "questionnaires_collected": False,
        "participant_data_generated": False,
        "human_pilot_status": "not_started",
        "main_study_status": "not_started",
        "checks": checks,
        "human_exit_criteria": [
            "Archive the institutional communication, if available.",
            "Run the formative pilot with 5-8 eligible people.",
            "Resolve and document all blocking or high-severity pilot issues.",
            "Approve the final instructions for all three arms.",
            "Freeze the final protocol before recruiting the main sample.",
        ],
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    lines = [
        "# Audit automatico pre-pilot RQ0/RQ3/RQ4",
        "",
        f"Stato: `{manifest['status']}`.",
        "",
        "| Controllo | Esito | Sintesi |",
        "|---|---|---|",
    ]
    for name, check in checks.items():
        summary = check.get("summary") or f"{check.get('checked', 0)} file verificati"
        lines.append(f"| `{name}` | {'PASS' if check['passed'] else 'FAIL'} | {summary} |")
    lines.extend(
        [
            "",
            "L'audit non crea dati di partecipanti e non sostituisce il pilot formativo.",
            "NASA-TLX e SUS restano esclusi dal protocollo corrente.",
            "",
            "## Passaggi umani ancora necessari",
            "",
            "1. Archiviare, se disponibile, la comunicazione istituzionale.",
            "2. Eseguire il pilot con 5–8 persone idonee.",
            "3. Chiudere il registro dei problemi bloccanti o ad alta severità.",
            "4. Approvare le istruzioni definitive dei tre bracci.",
            "5. Congelare il protocollo finale prima dello studio principale.",
        ]
    )
    (output / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not automated_ready:
        raise SystemExit(1)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent / "reports" / "study_pre_pilot_readiness_20261122",
    )
    args = parser.parse_args()
    manifest = audit(args.output)
    print(json.dumps({"status": manifest["status"], "checks": manifest["checks"]}, indent=2))


if __name__ == "__main__":
    main()
