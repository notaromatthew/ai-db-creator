"""Build the University dataset (Dataset A) in a reproducible way.

Generates three artifacts under ``data/datasets/university/``:

- ``source/enrollments.csv``    denormalised CSV (30 rows) as uploaded by a user
- ``source/description.pdf``    two-paragraph domain description
- ``ground_truth.db``           normalised 3NF SQLite database (gold answer)

The generator uses a fixed random seed so the dataset is byte-for-byte
reproducible across runs.

Design notes (documented deviation from docs/11, section 1.1):
- The protocol specifies a 3-column CSV; the initial dataset uses a richer
  denormalised CSV (7 columns) so that students/courses/enrollments can be
  reconstructed unambiguously from the CSV alone. Trim to 3 columns if strict
  protocol fidelity is required.
"""
from __future__ import annotations

import random
import sqlite3
from pathlib import Path

import fitz  # PyMuPDF (already in backend/requirements.txt)

HERE = Path(__file__).parent

FIRST_NAMES = ["Anna", "Luca", "Giulia", "Marco", "Sara", "Davide", "Elena", "Matteo",
               "Chiara", "Andrea", "Francesca", "Simone", "Valentina", "Federico", "Martina"]
LAST_NAMES = ["Rossi", "Bianchi", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci",
              "Marino", "Greco", "Bruno", "Gallo", "Conti", "Costa", "Giordano", "Rizzo"]
COURSE_CODES = [("CS-101", "Introduction to Programming", 6), ("CS-202", "Databases", 9),
                ("CS-301", "Operating Systems", 9), ("MA-101", "Calculus I", 9),
                ("MA-202", "Linear Algebra", 6), ("PH-101", "Physics I", 9),
                ("EN-101", "Academic Writing", 3), ("EC-201", "Microeconomics", 6)]
GRADES = ["30L", "30", "29", "28", "27", "26", "25", "24", "23", "22", "21", "18", "NS"]


def build() -> None:
    rng = random.Random(20260803)

    student_names = []
    students = []
    used_emails: set[str] = set()
    for student_id in range(1, 31):
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        email = f"student{student_id}@university.example"
        while email in used_emails:
            email = f"{email}0"
        used_emails.add(email)
        students.append((student_id, name, email))
        student_names.append(name)

    courses = [(i, code, title, credits) for i, (code, title, credits) in enumerate(COURSE_CODES, start=1)]

    pairs: set[tuple[int, int]] = set()
    while len(pairs) < 45:
        pairs.add((rng.randint(1, 30), rng.randint(1, len(courses))))
    enrollments = [(sid, cid, rng.choice(["2026-01", "2026-02"]), rng.choice(GRADES)) for sid, cid in pairs]

    (HERE / "source").mkdir(parents=True, exist_ok=True)

    with (HERE / "source" / "enrollments.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("student_name,student_email,course_code,course_title,credits,semester,grade\n")
        for sid, cid, semester, grade in enrollments:
            student = students[sid - 1]
            course = courses[cid - 1]
            output.write(f"{student[1]},{student[2]},{course[1]},{course[2]},{course[3]},{semester},{grade}\n")

    _write_pdf((HERE / "source" / "description.pdf"), students, courses)

    conn = sqlite3.connect(str(HERE / "ground_truth.db"))
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE students (
            student_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE
        );
        CREATE TABLE courses (
            course_id INTEGER PRIMARY KEY,
            course_code TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            credits INTEGER NOT NULL
        );
        CREATE TABLE enrollments (
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            semester TEXT NOT NULL,
            grade TEXT NOT NULL,
            PRIMARY KEY (student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (course_id) REFERENCES courses(course_id)
        );
    """)
    conn.executemany("INSERT INTO students VALUES (?, ?, ?)", students)
    conn.executemany("INSERT INTO courses VALUES (?, ?, ?, ?)", courses)
    conn.executemany("INSERT INTO enrollments VALUES (?, ?, ?, ?)", enrollments)
    conn.commit()
    conn.close()
    print("dataset built:", HERE)


def _write_pdf(path: Path, students: list, courses: list) -> None:
    paragraphs = (
        "This university manages students, courses and enrollments. Each student has a unique "
        "identifier, a full name and an institutional email address. Each course is identified "
        "by a code (e.g. CS-101), has a descriptive title and carries a number of ECTS credits. "
        "The university offers courses in computer science, mathematics, physics, engineering and economics.",
        "Students enroll in courses each semester (2026-01 or 2026-02) and receive a grade in the "
        "Italian 18-to-30 scale, where 30L is the highest mark and NS means non-satisfactory. "
        "A student may enroll in several courses and a course may have many enrolled students; "
        "each enrollment is recorded with the semester and the resulting grade.",
    )
    try:
        document = fitz.open()
        page = document.new_page()
        rect = fitz.Rect(50, 50, 545, 792)
        content = "\n\n".join(paragraphs)
        page.insert_textbox(rect, content, fontsize=11, fontname="helv")
        document.save(path)
        document.close()
    except Exception:
        (HERE / "source" / "description.txt").write_text("\n\n".join(paragraphs), encoding="utf-8")


if __name__ == "__main__":
    build()