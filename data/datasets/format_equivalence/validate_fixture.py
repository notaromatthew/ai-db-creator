"""Validate semantic parity of CSV, XLSX, TXT and PDF fixture representations."""
from __future__ import annotations

import csv
import json
from pathlib import Path

import pymupdf as fitz
from openpyxl import load_workbook

from prepare_fixture import FIELDS, HERE, SOURCE, record_line, sha256_file


def validate() -> dict:
    csv_rows = list(csv.DictReader((SOURCE / "records.csv").open(encoding="utf-8")))
    workbook = load_workbook(SOURCE / "records.xlsx", read_only=True, data_only=True)
    values = list(workbook["Enrollments"].iter_rows(values_only=True))
    headers = [str(value) for value in values[0]]
    xlsx_rows = [dict(zip(headers, [str(value) for value in row])) for row in values[1:]]
    if csv_rows != xlsx_rows:
        raise ValueError("XLSX rows differ from CSV canonical facts")

    txt = (SOURCE / "records.txt").read_text(encoding="utf-8")
    pdf_document = fitz.open(SOURCE / "records.pdf")
    pdf_text = "\n".join(page.get_text() for page in pdf_document)
    pdf_document.close()
    missing_txt = []
    missing_pdf = []
    for index, row in enumerate(csv_rows, start=1):
        line = record_line(index, row)
        if line not in txt:
            missing_txt.append(index)
        if line not in pdf_text:
            missing_pdf.append(index)
    if missing_txt or missing_pdf:
        raise ValueError(f"Missing records: txt={missing_txt}, pdf={missing_pdf}")
    manifest = json.loads((HERE / "fixture_manifest.json").read_text(encoding="utf-8"))
    if manifest["record_count"] != len(csv_rows):
        raise ValueError("Manifest record count differs from fixture")
    mismatches = [
        relative for relative, expected in manifest["hashes"].items()
        if sha256_file(HERE / relative) != expected
    ]
    if mismatches:
        raise ValueError(f"Fixture hash mismatches: {mismatches}")
    return {
        "status": "valid",
        "record_count": len(csv_rows),
        "field_count": len(FIELDS),
        "formats": ["csv", "xlsx", "txt", "pdf"],
    }


if __name__ == "__main__":
    print(json.dumps(validate(), indent=2))
