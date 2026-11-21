from __future__ import annotations

import hashlib
import json
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "backend" / "reports" / "gold_standard_consensus_20261121"
CONSENSUS = REPORT / "Consenso_gold_standard_GOLD-A_GOLD-B.xlsx"
DATASETS = ROOT / "data" / "datasets"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def clean(value):
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        return value.date().isoformat()
    return str(value).strip()


def extract_decisions() -> list[dict]:
    workbook = load_workbook(CONSENSUS, read_only=True, data_only=True)
    sheet = workbook["Da discutere"]
    headings = [clean(sheet.cell(4, column).value) for column in range(1, 22)]
    decisions = []
    for row in range(5, sheet.max_row + 1):
        record = {
            headings[column - 1]: clean(sheet.cell(row, column).value)
            for column in range(1, 22)
        }
        if not record.get("Item ID"):
            continue
        if record["Conferma GOLD-A"] != "CONFERMO" or record["Conferma GOLD-B"] != "CONFERMO":
            raise ValueError(f"Decisione non confermata: {record['Item ID']}")
        decisions.append(record)
    if len(decisions) != 25:
        raise ValueError(f"Attese 25 decisioni, trovate {len(decisions)}")
    return decisions


def artifact_manifest() -> list[dict]:
    artifacts = []
    for dataset in ("university", "library", "hospital"):
        root = DATASETS / dataset
        for path in sorted(candidate for candidate in root.rglob("*") if candidate.is_file()):
            artifacts.append(
                {
                    "dataset": dataset,
                    "path": path.relative_to(ROOT).as_posix(),
                    "size_bytes": path.stat().st_size,
                    "sha256": sha256(path),
                }
            )
    return artifacts


def main() -> None:
    decisions = extract_decisions()
    decision_payload = {
        "consensus_date": "2026-11-21",
        "reviewers": ["GOLD-A", "GOLD-B"],
        "technical_consensus_status": "COMPLETE",
        "personal_qualification_forms_status": "DEFERRED_BY_USER",
        "source_workbook": CONSENSUS.relative_to(ROOT).as_posix(),
        "source_workbook_sha256": sha256(CONSENSUS),
        "decision_count": len(decisions),
        "decisions": decisions,
    }
    (REPORT / "consensus_decisions.json").write_text(
        json.dumps(decision_payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    manifest = {
        "artifact_version": "rq2_functional_v2",
        "amendment_date": "2026-11-21",
        "technical_consensus_status": "COMPLETE",
        "personal_qualification_forms_status": "DEFERRED_BY_USER",
        "source_workbook_sha256": sha256(CONSENSUS),
        "pre_amendment_snapshot": REPORT.joinpath("pre_amendment_snapshot").relative_to(ROOT).as_posix(),
        "comparability": "v2 artifacts require a complete new benchmark matrix; v1 results remain historical",
        "artifacts": artifact_manifest(),
    }
    (REPORT / "post_amendment_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"Recorded {len(decisions)} decisions and {len(manifest['artifacts'])} artifact hashes")


if __name__ == "__main__":
    main()
