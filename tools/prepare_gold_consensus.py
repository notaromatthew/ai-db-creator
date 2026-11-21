from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "gold_standard_consensus"
INPUTS = OUTPUT / "inputs"
SOURCES = {
    "GOLD-A": Path(r"C:\Users\notar\Downloads\Valutazione_gold_standard_GOLD-A.xlsx"),
    "GOLD-B": Path(r"C:\Users\notar\Downloads\Valutazione_gold_standard_GOLD-B.xlsx"),
}


def clean(value):
    if value is None:
        return ""
    return str(value).strip()


def normalized_severity(verdict: str, severity: str) -> str:
    severity = clean(severity).upper()
    if verdict == "ACCETTA" and not severity:
        return "N/A"
    return severity


def read_records(path: Path, reviewer: str) -> dict[str, dict]:
    workbook = load_workbook(path, data_only=False, read_only=True)
    records: dict[str, dict] = {}
    for sheet_name in ("University", "Library", "Hospital"):
        sheet = workbook[sheet_name]
        for row in range(5, 18):
            item_id = clean(sheet.cell(row, 1).value)
            key = item_id
            records[key] = {
                "key": key,
                "dataset": sheet_name.lower(),
                "item_id": item_id,
                "area": clean(sheet.cell(row, 2).value),
                "artifact": clean(sheet.cell(row, 3).value),
                "object": clean(sheet.cell(row, 4).value),
                "criterion": clean(sheet.cell(row, 5).value),
                "critical": "",
                "sql": "",
                "comparison": "",
                "verdict": clean(sheet.cell(row, 6).value).upper(),
                "severity": normalized_severity(
                    clean(sheet.cell(row, 6).value).upper(), clean(sheet.cell(row, 7).value)
                ),
                "correction": clean(sheet.cell(row, 8).value),
                "rationale": clean(sheet.cell(row, 9).value),
                "notes": clean(sheet.cell(row, 10).value),
                "reviewer": reviewer,
            }
    query = workbook["Query"]
    for row in range(5, 35):
        dataset = clean(query.cell(row, 1).value).lower()
        item_id = clean(query.cell(row, 2).value)
        key = f"{dataset}:{item_id}"
        records[key] = {
            "key": key,
            "dataset": dataset,
            "item_id": item_id,
            "area": "Query",
            "artifact": clean(query.cell(row, 12).value),
            "object": clean(query.cell(row, 4).value),
            "criterion": clean(query.cell(row, 4).value),
            "critical": clean(query.cell(row, 3).value),
            "sql": clean(query.cell(row, 5).value),
            "comparison": clean(query.cell(row, 6).value),
            "verdict": clean(query.cell(row, 7).value).upper(),
            "severity": normalized_severity(
                clean(query.cell(row, 7).value).upper(), clean(query.cell(row, 8).value)
            ),
            "correction": clean(query.cell(row, 9).value),
            "rationale": clean(query.cell(row, 10).value),
            "notes": clean(query.cell(row, 11).value),
            "reviewer": reviewer,
        }
    return records


def classify(a: dict, b: dict) -> tuple[str, bool]:
    if a["verdict"] != b["verdict"]:
        return "DISACCORDO_VERDETTO", True
    if a["verdict"] == "ACCETTA":
        return "ACCORDO_ACCETTA", False
    if a["verdict"] == "MODIFICA":
        if a["severity"] != b["severity"]:
            return "ACCORDO_MODIFICA_GRAVITA_DIVERSA", True
        return "ACCORDO_MODIFICA_DA_FORMULARE", True
    if a["verdict"] == "INCERTO":
        return "ACCORDO_INCERTO_DA_RISOLVERE", True
    return "VALORE_NON_VALIDO", True


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    INPUTS.mkdir(parents=True, exist_ok=True)
    manifests = []
    reviews = {}
    for reviewer, source in SOURCES.items():
        if not source.exists():
            raise FileNotFoundError(source)
        target = INPUTS / source.name
        shutil.copy2(source, target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        manifests.append(
            {
                "reviewer": reviewer,
                "source_name": source.name,
                "archived_path": target.relative_to(ROOT).as_posix(),
                "sha256": digest,
                "size_bytes": target.stat().st_size,
            }
        )
        reviews[reviewer] = read_records(target, reviewer)

    keys_a = set(reviews["GOLD-A"])
    keys_b = set(reviews["GOLD-B"])
    if keys_a != keys_b:
        raise ValueError(f"Item non allineati: solo A={sorted(keys_a - keys_b)}, solo B={sorted(keys_b - keys_a)}")

    combined = []
    for key in sorted(keys_a, key=lambda k: (reviews["GOLD-A"][k]["dataset"], reviews["GOLD-A"][k]["area"], k)):
        a = reviews["GOLD-A"][key]
        b = reviews["GOLD-B"][key]
        status, needs_consensus = classify(a, b)
        combined.append(
            {
                "key": key,
                "dataset": a["dataset"],
                "item_id": a["item_id"],
                "area": a["area"],
                "artifact": a["artifact"],
                "object": a["object"],
                "criterion": a["criterion"],
                "critical": a["critical"],
                "sql": a["sql"],
                "comparison": a["comparison"],
                "a": {k: a[k] for k in ("verdict", "severity", "correction", "rationale", "notes")},
                "b": {k: b[k] for k in ("verdict", "severity", "correction", "rationale", "notes")},
                "comparison_status": status,
                "needs_consensus": needs_consensus,
            }
        )

    status_counts = Counter(item["comparison_status"] for item in combined)
    dataset_counts = {}
    for dataset in ("university", "library", "hospital"):
        subset = [item for item in combined if item["dataset"] == dataset]
        dataset_counts[dataset] = {
            "total": len(subset),
            "agreement_accept": sum(item["comparison_status"] == "ACCORDO_ACCETTA" for item in subset),
            "needs_consensus": sum(item["needs_consensus"] for item in subset),
            "verdict_disagreements": sum(item["comparison_status"] == "DISACCORDO_VERDETTO" for item in subset),
        }

    output = {
        "generated_on": date.today().isoformat(),
        "scope": "Technical gold-standard review only; qualification and signed independence forms deferred.",
        "inputs": manifests,
        "summary": {
            "total_items": len(combined),
            "agreement_accept": status_counts["ACCORDO_ACCETTA"],
            "needs_consensus": sum(item["needs_consensus"] for item in combined),
            "verdict_disagreements": status_counts["DISACCORDO_VERDETTO"],
            "status_counts": dict(sorted(status_counts.items())),
            "dataset_counts": dataset_counts,
            "personal_forms_status": "DEFERRED_BY_USER",
        },
        "items": combined,
    }
    path = OUTPUT / "consensus_preparation.json"
    path.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUTPUT / "input_manifest.json").write_text(
        json.dumps({"generated_on": date.today().isoformat(), "inputs": manifests}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(output["summary"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
