import fitz  # PyMuPDF
from pathlib import Path

def create_pdf(output_path: str):
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)  # A4 size

    # Colors
    c_blue = (0.08, 0.35, 0.75)
    c_dark = (0.1, 0.1, 0.1)
    c_gray = (0.4, 0.4, 0.4)
    c_light = (0.94, 0.95, 0.98)
    c_border = (0.8, 0.82, 0.88)

    # Header background
    page.draw_rect(fitz.Rect(40, 40, 555, 95), color=None, fill=c_light)
    page.draw_rect(fitz.Rect(40, 40, 48, 95), color=None, fill=c_blue)

    # Header text
    page.insert_text(fitz.Point(60, 65), "TECHSTORE SOLUTIONS - POST-VENDITA & ASSISTENZA", fontsize=14, fontname="helv", color=c_blue)
    page.insert_text(fitz.Point(60, 82), "Registro Ufficiale Ticket Assistenza Clienti, Richieste di Reso e Garanzie", fontsize=9, fontname="helv", color=c_gray)
    page.insert_text(fitz.Point(440, 82), "Data: 01/10/2026", fontsize=9, fontname="helv", color=c_gray)

    # Introduction
    intro_text = (
        "Il presente documento contiene l'estratto semestrale dei ticket di supporto tecnico, "
        "interventi in garanzia e richieste di reso autorizzato (RMA). I dati sono collegati "
        "agli ordini cliente e al catalogo prodotti per il tracciamento qualitativo."
    )
    page.insert_textbox(fitz.Rect(40, 110, 555, 145), intro_text, fontsize=9, fontname="helv", color=c_dark)

    tickets = [
        {
            "id": "TCK-2026-101",
            "cliente": "Marco Rossi (CLI-001)",
            "ordine": "ORD-2026-001",
            "prodotto": "Mouse Wireless Ergonomico (SKU: MOU-101)",
            "tipo": "Sostituzione in Garanzia",
            "stato": "Chiuso",
            "data_apertura": "2026-02-25",
            "data_chiusura": "2026-02-28",
            "descrizione": "Tasto sinistro difettoso dopo 10 giorni d'uso.",
            "risoluzione": "Sostituzione immediata con nuova unità spedita via corriere.",
            "voto": "5/5"
        },
        {
            "id": "TCK-2026-102",
            "cliente": "Laura Bianchi (CLI-002)",
            "ordine": "ORD-2026-002",
            "prodotto": "Tastiera Meccanica RGB (SKU: KEY-102)",
            "tipo": "Supporto Tecnico Software",
            "stato": "Chiuso",
            "data_apertura": "2026-03-15",
            "data_chiusura": "2026-03-15",
            "descrizione": "Difficoltà di configurazione effetti luce RGB su sistema operativo macOS.",
            "risoluzione": "Fornito software compatibile e guida PDF al cliente.",
            "voto": "4/5"
        },
        {
            "id": "TCK-2026-103",
            "cliente": "Giovanni Verdi (CLI-003)",
            "ordine": "ORD-2026-003",
            "prodotto": "Stampante Multifunzione Laser (SKU: STP-501)",
            "tipo": "Intervento Tecnico Hardware",
            "stato": "Risolto",
            "data_apertura": "2026-06-02",
            "data_chiusura": "2026-06-05",
            "descrizione": "Messaggio di inceppamento carta persistente nel cassetto 1.",
            "risoluzione": "Invio tecnico on-site; pulizia sensore e sostituzione rullo presa carta.",
            "voto": "4/5"
        },
        {
            "id": "TCK-2026-104",
            "cliente": "Elena Neri (CLI-004)",
            "ordine": "ORD-2026-004",
            "prodotto": "Monitor Professionale 4K 32\" (SKU: MON-202)",
            "tipo": "Richiesta Reso / Diritto di Recesso",
            "stato": "In Lavorazione",
            "data_apertura": "2026-07-12",
            "data_chiusura": "Aperto",
            "descrizione": "Dimensioni del monitor non adatte alla postazione di lavoro.",
            "risoluzione": "RMA emesso (RMA-8891). In attesa di ricezione articolo in magazzino.",
            "voto": "5/5"
        },
        {
            "id": "TCK-2026-105",
            "cliente": "Alessandro Fontana (CLI-005)",
            "ordine": "ORD-2026-005",
            "prodotto": "Cuffie Bluetooth Noise Cancelling (SKU: CUF-301)",
            "tipo": "Supporto Pairing & Configurazione",
            "stato": "Aperto",
            "data_apertura": "2026-09-20",
            "data_chiusura": "Aperto",
            "descrizione": "Disconnessione frequente durante chiamate vocali su iOS 18.",
            "risoluzione": "Test in corso con il reparto QA per aggiornamento firmware.",
            "voto": "In Valutazione"
        }
    ]

    y = 155
    for t in tickets:
        # Card background
        card_rect = fitz.Rect(40, y, 555, y + 115)
        page.draw_rect(card_rect, color=c_border, fill=(0.98, 0.99, 1.0))
        page.draw_rect(fitz.Rect(40, y, 44, y + 115), color=None, fill=c_blue)

        # Ticket header
        page.insert_text(fitz.Point(52, y + 16), f"Ticket ID: {t['id']}", fontsize=11, fontname="helv", color=c_blue)
        page.insert_text(fitz.Point(220, y + 16), f"Stato: {t['stato']}", fontsize=10, fontname="helv", color=(0.1, 0.55, 0.2) if t['stato'] in ('Chiuso', 'Risolto') else (0.8, 0.4, 0.0))
        page.insert_text(fitz.Point(370, y + 16), f"Apertura: {t['data_apertura']}", fontsize=9, fontname="helv", color=c_gray)
        page.insert_text(fitz.Point(465, y + 16), f"Rating: {t['voto']}", fontsize=9, fontname="helv", color=c_blue)

        # Content details
        page.insert_text(fitz.Point(52, y + 35), f"Cliente: {t['cliente']}", fontsize=9, fontname="helv", color=c_dark)
        page.insert_text(fitz.Point(280, y + 35), f"Rif. Ordine: {t['ordine']}", fontsize=9, fontname="helv", color=c_dark)

        page.insert_text(fitz.Point(52, y + 52), f"Articolo: {t['prodotto']}", fontsize=9, fontname="helv", color=c_dark)
        page.insert_text(fitz.Point(370, y + 52), f"Tipo: {t['tipo']}", fontsize=8.5, fontname="helv", color=c_gray)

        page.insert_text(fitz.Point(52, y + 72), f"Anomalia: {t['descrizione']}", fontsize=8.5, fontname="helv", color=c_dark)
        page.insert_text(fitz.Point(52, y + 92), f"Azione Risolutiva: {t['risoluzione']}", fontsize=8.5, fontname="helv", color=(0.2, 0.2, 0.6))

        y += 125

    # Footer
    page.insert_text(fitz.Point(40, 800), "TechStore Solutions S.r.l. - Dipartimento Supporto & Garanzie - Documento riservato ad uso gestionale", fontsize=8, fontname="helv", color=c_gray)

    doc.save(output_path)
    doc.close()
    print(f"PDF created successfully at: {output_path}")

if __name__ == "__main__":
    create_pdf("/workspace/sample_files/assistenza_e_resi.pdf")
