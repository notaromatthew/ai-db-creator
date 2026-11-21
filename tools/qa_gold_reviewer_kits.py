from __future__ import annotations

import hashlib
import json
import sqlite3
import zipfile
from pathlib import Path

from docx import Document
from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "gold_standard_validation"
DATASETS = ROOT / "data" / "datasets"
EXPECTED_SHEETS = ["Istruzioni", "Profilo", "University", "Library", "Hospital", "Query", "Riepilogo"]


def check_docx(code: str) -> None:
    path = OUTPUT / f"Scheda_valutatore_{code}.docx"
    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs)
    text += "\n" + "\n".join(cell.text for table in doc.tables for row in table.rows for cell in row.cells)
    required = [code, "Titolo di studio", "Esperienza con database", "Dichiarazione d'indipendenza", "Data", "Firma"]
    for item in required:
        assert item in text, f"{path.name}: campo mancante {item}"
    assert len(doc.sections) >= 1


def check_xlsx(code: str) -> None:
    path = OUTPUT / f"Valutazione_gold_standard_{code}.xlsx"
    wb = load_workbook(path, data_only=False)
    assert wb.sheetnames == EXPECTED_SHEETS, wb.sheetnames
    assert wb["Profilo"]["B5"].value == code
    assert wb["Riepilogo"]["B5"].value == "=ROWS('University'!F5:F17)"
    assert wb["Riepilogo"]["D9"].value == "=SUM(D5:D8)"
    for sheet_name, verdict_range in (
        ("University", "F5:F17"),
        ("Library", "F5:F17"),
        ("Hospital", "F5:F17"),
        ("Query", "G5:G34"),
    ):
        sheet = wb[sheet_name]
        validations = list(sheet.data_validations.dataValidation)
        assert any(verdict_range in str(v.sqref) for v in validations), f"{sheet_name}: dropdown verdetto assente"
    assert wb["Query"].max_row == 34


def check_datasets() -> None:
    for dataset in ("university", "library", "hospital"):
        base = DATASETS / dataset
        spec = json.loads((base / "evaluation_spec.json").read_text(encoding="utf-8"))
        schema = json.loads((base / "gold_schema.json").read_text(encoding="utf-8"))
        assert spec["dataset"] == dataset
        assert len(spec["functional_queries"]) == 10
        assert schema.get("tables"), f"{dataset}: schema privo di tabelle"
        with sqlite3.connect(base / "ground_truth.db") as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            violations = conn.execute("PRAGMA foreign_key_check").fetchall()
            assert not violations, f"{dataset}: violazioni FK {violations[:5]}"
            for query in spec["functional_queries"]:
                conn.execute(query["sql"]).fetchall()


def check_zip(code: str) -> None:
    path = OUTPUT / f"Kit_validazione_gold_standard_{code}.zip"
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        names = set(archive.namelist())
        required = {
            "LEGGIMI.txt",
            f"Scheda_valutatore_{code}.docx",
            f"Valutazione_gold_standard_{code}.xlsx",
            "Protocollo/11-benchmark-protocol.md",
            "Protocollo/20-rq2-functional-equivalence-protocol.md",
            "Datasets/university/ground_truth.db",
            "Datasets/library/ground_truth.db",
            "Datasets/hospital/ground_truth.db",
            "MANIFEST_SHA256.txt",
        }
        assert required <= names, f"{path.name}: file mancanti {sorted(required - names)}"
        manifest = archive.read("MANIFEST_SHA256.txt").decode("utf-8").splitlines()
        for line in manifest:
            expected, name = line.split("  ", 1)
            actual = hashlib.sha256(archive.read(name)).hexdigest()
            assert actual == expected, f"{path.name}: hash errato per {name}"
        other = "GOLD-B" if code == "GOLD-A" else "GOLD-A"
        assert not any(other in name for name in names), f"{path.name}: contiene materiali nominativi di {other}"


def main() -> None:
    check_datasets()
    for code in ("GOLD-A", "GOLD-B"):
        check_docx(code)
        check_xlsx(code)
        check_zip(code)
    print("QA OK: dataset, DOCX, XLSX, formule, convalide, ZIP e manifest verificati")


if __name__ == "__main__":
    main()
