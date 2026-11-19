"""Build the PDF representation of the format-equivalence fixture."""
from __future__ import annotations

import csv
import sys
from pathlib import Path

from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

from prepare_fixture import FIELDS, SOURCE, record_line


def build(output: Path) -> None:
    rows = list(csv.DictReader((SOURCE / "records.csv").open(encoding="utf-8")))
    page_width, page_height = landscape(A4)
    document = canvas.Canvas(
        str(output), pagesize=(page_width, page_height), pageCompression=1, invariant=1
    )
    document.setTitle("Format-equivalent university enrollment facts")
    document.setFont("Helvetica-Bold", 13)
    document.drawString(36, page_height - 34, "Format-equivalent university enrollment facts")
    document.setFont("Helvetica", 8)
    document.drawString(36, page_height - 49, "Each record contains one observable enrollment fact.")
    y = page_height - 68
    for index, row in enumerate(rows, start=1):
        if y < 30:
            document.showPage()
            document.setFont("Helvetica-Bold", 10)
            document.drawString(36, page_height - 30, "University enrollment facts - continued")
            y = page_height - 48
        document.setFont("Helvetica", 6.7)
        document.drawString(36, y, record_line(index, row))
        y -= 10.5
    document.setFont("Helvetica", 7)
    document.drawRightString(page_width - 36, 18, f"Records: {len(rows)}")
    document.save()


if __name__ == "__main__":
    build(Path(sys.argv[1]) if len(sys.argv) > 1 else SOURCE / "records.pdf")
