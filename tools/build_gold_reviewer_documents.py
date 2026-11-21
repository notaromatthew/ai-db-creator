from __future__ import annotations

import sys
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs" / "gold_standard_validation"

NAVY = "17365D"
BLUE = "2F5597"
LIGHT_BLUE = "D9EAF7"
LIGHT_YELLOW = "FFF2CC"
LIGHT_GRAY = "E7E6E6"


def set_cell_shading(cell, fill: str) -> None:
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd")
        tc_pr.append(shd)
    shd.set(qn("w:fill"), fill)


def set_cell_margins(cell, top=90, start=110, bottom=90, end=110) -> None:
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    tc_mar = tc_pr.first_child_found_in("w:tcMar")
    if tc_mar is None:
        tc_mar = OxmlElement("w:tcMar")
        tc_pr.append(tc_mar)
    for margin, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        node = tc_mar.find(qn(f"w:{margin}"))
        if node is None:
            node = OxmlElement(f"w:{margin}")
            tc_mar.append(node)
        node.set(qn("w:w"), str(value))
        node.set(qn("w:type"), "dxa")


def set_repeat_table_header(row) -> None:
    tr_pr = row._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)


def set_col_width(cell, width_cm: float) -> None:
    cell.width = Cm(width_cm)
    tc_pr = cell._tc.get_or_add_tcPr()
    tc_w = tc_pr.find(qn("w:tcW"))
    if tc_w is None:
        tc_w = OxmlElement("w:tcW")
        tc_pr.append(tc_w)
    tc_w.set(qn("w:w"), str(int(width_cm * 567)))
    tc_w.set(qn("w:type"), "dxa")


def add_field_table(doc: Document, rows: list[tuple[str, str]], widths=(5.1, 11.5)) -> None:
    table = doc.add_table(rows=len(rows), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"
    table.autofit = False
    for i, (label, value) in enumerate(rows):
        left, right = table.rows[i].cells
        set_col_width(left, widths[0])
        set_col_width(right, widths[1])
        left.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        right.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        set_cell_shading(left, LIGHT_BLUE)
        set_cell_shading(right, LIGHT_YELLOW)
        set_cell_margins(left)
        set_cell_margins(right)
        p = left.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(label)
        r.bold = True
        p2 = right.paragraphs[0]
        p2.paragraph_format.space_after = Pt(0)
        p2.add_run(value)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def add_checkbox(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.space_after = Pt(4)
    p.add_run("☐ ").bold = True
    p.add_run(text)


def build_form(code: str) -> Path:
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(1.7)
    section.bottom_margin = Cm(1.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)

    styles = doc.styles
    styles["Normal"].font.name = "Arial"
    styles["Normal"].font.size = Pt(10.5)
    styles["Normal"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    styles["Title"].font.name = "Arial"
    styles["Title"].font.size = Pt(22)
    styles["Title"].font.bold = True
    styles["Title"].font.color.rgb = RGBColor(0x17, 0x36, 0x5D)
    styles["Title"]._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
    for style_name in ("Heading 1", "Heading 2"):
        styles[style_name].font.name = "Arial"
        styles[style_name]._element.rPr.rFonts.set(qn("w:eastAsia"), "Arial")
        styles[style_name].font.color.rgb = RGBColor(0x17, 0x36, 0x5D)
    styles["Heading 1"].font.size = Pt(15)
    styles["Heading 2"].font.size = Pt(12)

    title = doc.add_paragraph(style="Title")
    title.alignment = WD_ALIGN_PARAGRAPH.LEFT
    title.add_run("Scheda del valutatore del gold standard")

    subtitle = doc.add_paragraph()
    subtitle.paragraph_format.space_after = Pt(10)
    run = subtitle.add_run(f"AI-DB-Creator · Codice pseudonimo {code}")
    run.bold = True
    run.font.size = Pt(12)
    run.font.color.rgb = RGBColor(0x2F, 0x55, 0x97)

    intro = doc.add_paragraph(
        "Compilare questa scheda prima di iniziare la revisione. Il codice pseudonimo "
        "deve comparire anche nel file Excel restituito. Non inserire valutazioni tecniche in questo documento."
    )
    intro.paragraph_format.space_after = Pt(10)

    doc.add_heading("1. Identificazione pseudonimizzata", level=1)
    add_field_table(
        doc,
        [
            ("Codice del valutatore", code),
            ("Nome e cognome", ""),
            ("Ruolo o posizione attuale", ""),
            ("Organizzazione, facoltativa", ""),
        ],
    )

    doc.add_heading("2. Titolo di studio ed esperienza", level=1)
    add_field_table(
        doc,
        [
            ("Titolo di studio", ""),
            ("Area disciplinare", ""),
            ("Anni di esperienza professionale o accademica", ""),
            ("Descrizione sintetica dell'esperienza pertinente", ""),
        ],
    )

    doc.add_heading("3. Esperienza con database", level=1)
    add_field_table(
        doc,
        [
            ("Anni di esperienza con database relazionali", ""),
            ("Attività svolte", "Progettazione / normalizzazione / SQL / amministrazione / insegnamento / altro:"),
            ("DBMS o strumenti utilizzati", ""),
            ("Esperienza nella valutazione di schemi e vincoli", ""),
        ],
    )

    doc.add_page_break()
    doc.add_heading("4. Dichiarazione d'indipendenza", level=1)
    p = doc.add_paragraph(
        "Dichiaro di svolgere la valutazione in modo individuale e indipendente. Confermo di non aver "
        "collaborato alla costruzione dei tre gold standard e di non consultare l'altro valutatore prima "
        "della consegna della mia scheda. Valuterò soltanto i materiali inclusi nel mio archivio e segnalerò "
        "qualsiasi possibile conflitto d'interesse."
    )
    p.paragraph_format.space_after = Pt(7)

    add_checkbox(doc, "Confermo integralmente la dichiarazione d'indipendenza.")
    add_checkbox(doc, "Non posso confermarla integralmente; descrivo di seguito il motivo.")

    add_field_table(
        doc,
        [
            ("Conflitti d'interesse o rapporti con il progetto", "Nessuno / descrivere:"),
            ("Altre circostanze rilevanti", ""),
        ],
    )

    doc.add_heading("5. Conferma e firma", level=1)
    p = doc.add_paragraph(
        "Con la firma confermo che le informazioni riportate sono corrette e che la valutazione sarà "
        "compilata secondo le istruzioni ricevute."
    )
    p.paragraph_format.space_after = Pt(12)
    add_field_table(
        doc,
        [
            ("Luogo", ""),
            ("Data", "____ / ____ / ________"),
            ("Firma", ""),
        ],
    )

    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(8)
    note.paragraph_format.space_after = Pt(0)
    r = note.add_run(
        "Restituire questa scheda firmata insieme al file Excel compilato. Conservare una copia personale fino alla chiusura del consenso."
    )
    r.italic = True
    r.font.size = Pt(9)

    props = doc.core_properties
    props.title = f"Scheda valutatore gold standard {code}"
    props.subject = "Validazione indipendente dei gold standard AI-DB-Creator"
    props.author = "AI-DB-Creator Research Team"
    props.keywords = "gold standard, independent review, database"

    OUTPUT.mkdir(parents=True, exist_ok=True)
    path = OUTPUT / f"Scheda_valutatore_{code}.docx"
    doc.save(path)
    return path


def main() -> int:
    for code in ("GOLD-A", "GOLD-B"):
        path = build_form(code)
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
