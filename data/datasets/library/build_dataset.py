"""Build the Library dataset (Dataset B) in a reproducible way.

Artifacts under ``data/datasets/library/``:

- ``source/members.csv``       20 addressing rows (denormalised-ish, 5 cols)
- ``source/books.csv``         50 book rows (title, author, category, ISBN)
- ``source/description.pdf``   one-page domain description
- ``ground_truth.db``          normalised 3NF SQLite database (gold answer)

Fixed random seed for byte-for-byte reproducibility.

Design notes (documented deviation from docs/11, section 1.1):
- The protocol describes members (20 rows) and books (50 rows) as the CSV
  inputs; loans and fines are derived here at record-generation time so the
  ground truth contains them. A denormalised loans+members CSV is also emitted
  (``source/loans_members.csv``) to exercise one-to-many reconstruction.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, timedelta
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).parent

FIRST_NAMES = ["Anna", "Luca", "Giulia", "Marco", "Sara", "Davide", "Elena", "Matteo",
               "Chiara", "Andrea", "Francesca", "Simone", "Valentina", "Federico", "Martina"]
LAST_NAMES = ["Rossi", "Bianchi", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci",
              "Marino", "Greco", "Bruno", "Gallo", "Conti", "Costa", "Giordano", "Rizzo"]
CATEGORIES = ["Fiction", "Saggistica", "Storia", "Scienza", "Fantascienza", "Giallo",
              "Poesia", "Biografia", "Avventura", "Tecnologia"]
TITLE_WORDS = ["L'inverno", "Il ritorno", "Ombre", "La città", "Silenzi", "Orizzonte",
               "Il labirinto", "Specchi", "Le stelle", "Il confine", "Memorie", "Il porto",
               "Cronache", "Il giardino", "Vento", "La soglia", "Fuochi", "Il custode",
               "Sabbia", "Il viaggio", "Echi", "La valle", "Nebbia", "Il faro", "Radici",
               "La corrente", "Tracce", "Il grembo", "Lucciole", "La promessa"]
AUTHORS = ["Alessandro Manzoni", "Italo Calvino", "Primo Levi", "Elsa Morante", "Grazia Deledda",
           "Alberto Moravia", "Natalia Ginzburg", "Dino Buzzati", "Carlo Emilio Gadda", "Leonardo Sciascia",
           "Cesare Pavese", "Umberto Eco", "Andrea Camilleri", "Oriana Fallaci", "Luigi Pirandello"]


def build() -> None:
    rng = random.Random(20260803)

    members = []
    used_emails = set()
    for member_id in range(1, 21):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        email = f"member{member_id}@example.com"
        while email in used_emails:
            email = f"{email}0"
        used_emails.add(email)
        joined = date(2020, 1, 1) + timedelta(days=rng.randint(0, 2200))
        members.append((member_id, name, email, joined.isoformat()))
    members_rows = [(m[0], m[1], m[2], m[3]) for m in members]

    categories = [(cid, name) for cid, name in enumerate(CATEGORIES, start=1)]

    books = []
    used_isbn = set()
    for book_id in range(1, 51):
        while True:
            isbn = "978-0" + str(rng.randint(100, 999)) + "-" + str(rng.randint(100, 999)) \
                + "-" + str(rng.randint(1000, 9999))
            if isbn not in used_isbn:
                used_isbn.add(isbn)
                break
        title = f"{rng.choice(TITLE_WORDS)} {rng.choice(TITLE_WORDS)}"
        author = rng.choice(AUTHORS)
        category_id = rng.randint(1, len(categories))
        books.append((book_id, isbn, title, author, category_id))
    books_rows = [(b[0], b[1], b[2], b[3], b[4]) for b in books]

    loans = []
    for loan_id in range(1, 61):
        book_id = rng.randint(1, 50)
        member_id = rng.randint(1, 20)
        loan_date = date(2026, 1, 1) + timedelta(days=rng.randint(0, 180))
        due_date = loan_date + timedelta(days=rng.randint(7, 42))
        loans.append((loan_id, book_id, member_id, loan_date.isoformat(), due_date.isoformat()))

    fines = []
    for fine_id, loan in enumerate(loans, start=1):
        if rng.random() < 0.35:
            amount = round(rng.uniform(1.0, 15.0), 2)
            paid = None if rng.random() < 0.4 else (date.today().isoformat())
            fines.append((fine_id, loan[0], amount, paid))

    (HERE / "source").mkdir(parents=True, exist_ok=True)

    with (HERE / "source" / "members.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("member_id,full_name,email,joined_on\n")
        for row in members_rows:
            output.write(",".join(str(v) for v in row) + "\n")

    with (HERE / "source" / "books.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("book_id,isbn,title,author,category_name\n")
        for book in books_rows:
            category_name = categories[book[4] - 1][1]
            output.write(f"{book[0]},{book[1]},{book[2]},{book[3]},{category_name}\n")

    loans_by_member = {}
    for loan in loans:
        loans_by_member.setdefault(loan[2], []).append(loan)
    with (HERE / "source" / "loans_members.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("member_id,full_name,email,loan_date,due_date\n")
        for member_id, member_loans in loans_by_member.items():
            member = members_rows[member_id - 1]
            for loan in member_loans:
                output.write(f"{member[0]},{member[1]},{member[2]},{loan[3]},{loan[4]}\n")

    _write_pdf((HERE / "source" / "description.pdf"))

    conn = sqlite3.connect(str(HERE / "ground_truth.db"))
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE categories (
            category_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE
        );
        CREATE TABLE members (
            member_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            joined_on DATE NOT NULL
        );
        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY,
            isbn TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category_id INTEGER NOT NULL,
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        );
        CREATE TABLE loans (
            loan_id INTEGER PRIMARY KEY,
            book_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            loan_date DATE NOT NULL,
            due_date DATE NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books(book_id),
            FOREIGN KEY (member_id) REFERENCES members(member_id)
        );
        CREATE TABLE fines (
            fine_id INTEGER PRIMARY KEY,
            loan_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            paid_on DATE,
            FOREIGN KEY (loan_id) REFERENCES loans(loan_id)
        );
    """)
    conn.executemany("INSERT INTO categories VALUES (?, ?)", categories)
    conn.executemany("INSERT INTO members VALUES (?, ?, ?, ?)", members_rows)
    conn.executemany("INSERT INTO books VALUES (?, ?, ?, ?, ?)", books_rows)
    conn.executemany("INSERT INTO loans VALUES (?, ?, ?, ?, ?)", loans)
    conn.executemany("INSERT INTO fines VALUES (?, ?, ?, ?)", fines)
    conn.commit()
    conn.close()
    print("library dataset built:", HERE)


def _write_pdf(path: Path) -> None:
    paragraphs = (
        "The public city library manages categories, books, registered members and loans. "
        "Each book belongs to exactly one category (for example Fiction, Saggistica or "
        "Scienza) and is identified by its ISBN along with a title and an author. Each "
        "member has a unique account with a full name, an email address and an enrolment date.",
        "A loan records which member borrowed which book, together with the loan date and a "
        "due date. When a book is returned after its due date, a fine is applied to that loan; "
        "the fine has an amount and, once paid, a payment date. A fine depends on its loan, and "
        "a loan depends on both a member and a book.",
    )
    try:
        document = fitz.open()
        page = document.new_page()
        page.insert_textbox(fitz.Rect(50, 50, 545, 792), "\n\n".join(paragraphs),
                            fontsize=11, fontname="helv")
        document.save(path)
        document.close()
    except Exception:
        (HERE / "source" / "description.txt").write_text("\n\n".join(paragraphs), encoding="utf-8")


if __name__ == "__main__":
    build()
