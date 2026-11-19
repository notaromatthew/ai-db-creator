import csv
import json
from pathlib import Path

import pytest

from prepare_rq2_blind_adjudication import collect_items, finalize_package, prepare_package


FIELDS = [
    "dataset", "source_format", "condition", "run", "table", "natural_key",
    "row_key_columns", "column", "source_value", "generated_value", "gold_value",
    "error_type", "source_document", "source_location", "alignment_method",
]


def _matrix(tmp_path: Path) -> Path:
    root = tmp_path / "matrix"
    (root / "protocol_manifest.json").parent.mkdir(parents=True)
    (root / "protocol_manifest.json").write_text("{}", encoding="utf-8")
    for dataset in ("university", "library", "hospital"):
        for condition in ("baseline", "full_llm"):
            for run in range(1, 6):
                path = root / dataset / condition / f"run{run:02d}" / "cell_discrepancies.csv"
                path.parent.mkdir(parents=True)
                with path.open("w", encoding="utf-8", newline="") as handle:
                    writer = csv.DictWriter(handle, fieldnames=FIELDS)
                    writer.writeheader()
                    writer.writerow({
                        "dataset": dataset,
                        "source_format": "combined",
                        "condition": condition,
                        "run": run,
                        "table": "facts",
                        "natural_key": f'["{dataset}-{condition}-{run}"]',
                        "row_key_columns": '["id"]',
                        "column": "value",
                        "generated_value": '"candidate"',
                        "gold_value": '"reference"',
                        "error_type": "WV",
                        "alignment_method": "declared_row_key",
                    })
    return root


def test_collect_items_requires_complete_30_run_matrix(tmp_path):
    root = _matrix(tmp_path)
    next(root.glob("*/*/run??/cell_discrepancies.csv")).unlink()
    with pytest.raises(ValueError, match="Expected 30"):
        collect_items(root)


def test_package_is_blinded_complete_and_reproducible(tmp_path):
    root = _matrix(tmp_path)
    output = tmp_path / "out"
    manifest = prepare_package(root, output, seed=42)
    a = json.loads((output / "reviewer_a_items.json").read_text(encoding="utf-8"))
    b = json.loads((output / "reviewer_b_items.json").read_text(encoding="utf-8"))
    mapping = json.loads((output / "private_mapping.json").read_text(encoding="utf-8"))

    assert manifest["item_count"] == 30
    assert {row["item_id"] for row in a} == {row["item_id"] for row in b}
    assert [row["item_id"] for row in a] != [row["item_id"] for row in b]
    assert len(mapping) == 30
    forbidden = {"condition", "run", "provider", "model", "scores"}
    assert forbidden.isdisjoint(a[0])
    assert {row["condition"] for row in mapping} == {"baseline", "full_llm"}
    assert all(row["decision"] == "" and row["confidence"] == "" for row in a)
    assert set(manifest["prepared_outputs"]) == {
        "private_mapping.json", "reviewer_a_items.json", "reviewer_b_items.json",
    }

    second = tmp_path / "out2"
    prepare_package(root, second, seed=42)
    assert (output / "reviewer_a_items.json").read_bytes() == (
        second / "reviewer_a_items.json"
    ).read_bytes()


def test_finalize_hashes_all_workbooks(tmp_path):
    output = tmp_path / "out"
    output.mkdir()
    (output / "manifest.json").write_text("{}", encoding="utf-8")
    for name in ("reviewer_a.xlsx", "reviewer_b.xlsx", "coordinator_private_mapping.xlsx"):
        (output / name).write_bytes(name.encode())
    manifest = finalize_package(output)
    assert set(manifest["workbooks"]) == {
        "reviewer_a.xlsx", "reviewer_b.xlsx", "coordinator_private_mapping.xlsx",
    }
