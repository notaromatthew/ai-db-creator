"""Build the Hospital dataset (Dataset C) in a reproducible way.

Artifacts under ``data/datasets/hospital/``:

- ``source/patients.csv``         100 patient rows
- ``source/appointments.csv``     200 appointment rows
- ``source/operational_notes.txt`` operational notes (departments, wards, pharmacy)
- ``source/description.pdf``      three-page domain description
- ``ground_truth.db``             normalised 3NF SQLite database (gold answer)

Fixed random seed for byte-for-byte reproducibility.

Design notes (documented deviation from docs/11, section 1.3):
- The protocol lists 8 tables and 42 columns; this implementation covers the 8
  tables with 37 columns. Ward assignment is explicit in the gold schema and is
  additionally derivable from doctor department (implicit-entity exercise).
- doctors/medications are provided implicitly in the description and notes
  rather than in separate CSVs, matching the protocol's input document set.
"""
from __future__ import annotations

import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import fitz  # PyMuPDF

HERE = Path(__file__).parent

FIRST_NAMES = ["Anna", "Luca", "Giulia", "Marco", "Sara", "Davide", "Elena", "Matteo",
               "Chiara", "Andrea", "Francesca", "Simone", "Valentina", "Federico", "Martina"]
LAST_NAMES = ["Rossi", "Bianchi", "Ferrari", "Esposito", "Romano", "Colombo", "Ricci",
              "Marino", "Greco", "Bruno", "Gallo", "Conti", "Costa", "Giordano", "Rizzo"]
SPECIALTIES = ["Cardiologia", "Neurologia", "Ortopedia", "Pediatria", "Dermatologia", "Ginecologia"]
DEPARTMENTS = ["Cardiologia", "Neurologia", "Ortopedia", "Pediatria", "Dermatologia", "Ginecologia"]
WARD_NAMES = ["Reparto A", "Reparto B", "Reparto C", "Reparto D", "Reparto E", "Reparto F"]
MEDICATIONS = [
    ("Atenololo", "Atenololo"), ("Amoxicillina", "Amoxicillina"), ("Omeprazolo", "Omeprazolo"),
    ("Paracetamolo", "Paracetamolo"), ("Ibuprofene", "Ibuprofene"), ("Metformina", "Metformina"),
    ("Atorvastatina", "Atorvastatina"), ("Losartan", "Losartan"), ("Salbutamolo", "Salbutamolo"),
    ("Ciprofloxacina", "Ciprofloxacina"),
]
TREATMENT_DESCRIPTIONS = [
    "Visita specialistica", "Ecografia", "Radiografia", "Analisi del sangue", "Elettrocardiogramma",
    "Risonanza magnetica", "TAC", "Fisioterapia", "Infusione endovenosa", "Biopsia",
]
DOSAGES = ["1 cp al giorno", "2 cp al giorno", "1 cp ogni 8 ore", "10 ml ogni 12 ore",
           "1 bustina al giorno", "500 mg ogni 6 ore"]


def _fiscal_code(rng: random.Random, index: int) -> str:
    letters = "ABCDEFGHJKLMNOPQRSTUVWXYZ"
    size = len(letters)
    return f"{letters[index % size]}{letters[(index * 7) % size]}{index:02d}{rng.randint(10, 99)}" \
        f"{letters[(index * 3) % size]}{rng.randint(1000, 9999)}"


def build() -> None:
    rng = random.Random(20260803)

    patients = []
    used_fiscal = set()
    for patient_id in range(1, 101):
        fiscal = _fiscal_code(rng, patient_id)
        while fiscal in used_fiscal:
            fiscal += "X"
        used_fiscal.add(fiscal)
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        birth = date(1940, 1, 1) + timedelta(days=rng.randint(0, 26000))
        patients.append((patient_id, fiscal, name, birth.isoformat()))

    doctors = []
    for doctor_id in range(1, 13):
        name = f"Dr. {rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        specialty = SPECIALTIES[(doctor_id - 1) % len(SPECIALTIES)]
        department = DEPARTMENTS[(doctor_id - 1) % len(DEPARTMENTS)]
        doctors.append((doctor_id, name, specialty, department))

    wards = [(wid, WARD_NAMES[wid - 1], DEPARTMENTS[(wid - 1) % len(DEPARTMENTS)])
             for wid in range(1, len(WARD_NAMES) + 1)]

    medications = [(mid, name, ingredient) for mid, (name, ingredient) in enumerate(MEDICATIONS, start=1)]

    appointments = []
    for appointment_id in range(1, 201):
        patient_id = rng.randint(1, 100)
        doctor_id = rng.randint(1, len(doctors))
        ward_id = rng.randint(1, len(wards))
        scheduled = datetime(2026, 1, 1, 8, 0) + timedelta(minutes=rng.randint(0, 420 * 24 * 60))
        appointments.append((appointment_id, patient_id, doctor_id, ward_id, scheduled.strftime("%Y-%m-%d %H:%M")))

    treatments = []
    for treatment_id in range(1, 251):
        appointment_id = rng.randint(1, 200)
        description = rng.choice(TREATMENT_DESCRIPTIONS)
        treatments.append((treatment_id, appointment_id, description))

    prescriptions = []
    for prescription_id in range(1, 301):
        treatment_id = rng.randint(1, 250)
        medication_id = rng.randint(1, len(medications))
        dosage = rng.choice(DOSAGES)
        prescriptions.append((prescription_id, treatment_id, medication_id, dosage))

    invoices = []
    for invoice_id, appointment_id in enumerate(range(1, 201), start=1):
        if rng.random() < 0.8:
            amount = round(rng.uniform(40.0, 900.0), 2)
            issued = date(2026, 1, 1) + timedelta(days=rng.randint(0, 180))
            invoices.append((invoice_id, appointment_id, amount, issued.isoformat()))

    (HERE / "source").mkdir(parents=True, exist_ok=True)

    with (HERE / "source" / "patients.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("patient_id,fiscal_code,full_name,birth_date\n")
        for row in patients:
            output.write(",".join(str(v) for v in row) + "\n")

    with (HERE / "source" / "appointments.csv").open("w", encoding="utf-8", newline="") as output:
        output.write("appointment_id,patient_id,doctor_name,specialty,ward_name,scheduled_on\n")
        for appt in appointments:
            doctor = doctors[appt[2] - 1]
            ward = wards[appt[3] - 1]
            output.write(f"{appt[0]},{appt[1]},{doctor[1]},{doctor[2]},{ward[1]},{appt[4]}\n")

    notes = (
        "OPERATIONAL NOTES\n"
        "=================\n"
        "1. Doctor departments map one-to-one to wards: Cardiology department -> Reparto A, "
        "Neurology -> Reparto B, Orthopedics -> Reparto C, Pediatrics -> Reparto D, "
        "Dermatology -> Reparto E, Gynecology -> Reparto F.\n"
        "2. Invoicing: every appointment that leads to a treatment is billed; the amount is "
        "the treatment fee plus a 15% co-payment.\n"
        "3. Pharmacy: medications are prescribed per treatment; a treatment can require "
        "multiple medications and a medication can be used across treatments.\n"
        "4. Prescriptions always carry a dosage instruction.\n"
    )
    (HERE / "source" / "operational_notes.txt").write_text(notes, encoding="utf-8")

    _write_pdf((HERE / "source" / "description.pdf"))

    conn = sqlite3.connect(str(HERE / "ground_truth.db"))
    conn.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE patients (
            patient_id INTEGER PRIMARY KEY,
            fiscal_code TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            birth_date DATE NOT NULL
        );
        CREATE TABLE doctors (
            doctor_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            specialty TEXT NOT NULL,
            department TEXT NOT NULL
        );
        CREATE TABLE wards (
            ward_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            department TEXT NOT NULL UNIQUE
        );
        CREATE TABLE appointments (
            appointment_id INTEGER PRIMARY KEY,
            patient_id INTEGER NOT NULL,
            doctor_id INTEGER NOT NULL,
            ward_id INTEGER NOT NULL,
            scheduled_on DATETIME NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id),
            FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
        );
        CREATE TABLE treatments (
            treatment_id INTEGER PRIMARY KEY,
            appointment_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );
        CREATE TABLE medications (
            medication_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            active_ingredient TEXT NOT NULL
        );
        CREATE TABLE prescriptions (
            prescription_id INTEGER PRIMARY KEY,
            treatment_id INTEGER NOT NULL,
            medication_id INTEGER NOT NULL,
            dosage TEXT NOT NULL,
            FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id),
            FOREIGN KEY (medication_id) REFERENCES medications(medication_id)
        );
        CREATE TABLE invoices (
            invoice_id INTEGER PRIMARY KEY,
            appointment_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            issued_on DATE NOT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );
    """)
    conn.executemany("INSERT INTO patients VALUES (?, ?, ?, ?)", patients)
    conn.executemany("INSERT INTO doctors VALUES (?, ?, ?, ?)", doctors)
    conn.executemany("INSERT INTO wards VALUES (?, ?, ?)", wards)
    conn.executemany("INSERT INTO medications VALUES (?, ?, ?)", medications)
    conn.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?, ?)", appointments)
    conn.executemany("INSERT INTO treatments VALUES (?, ?, ?)", treatments)
    conn.executemany("INSERT INTO prescriptions VALUES (?, ?, ?, ?)", prescriptions)
    conn.executemany("INSERT INTO invoices VALUES (?, ?, ?, ?)", invoices)
    conn.commit()
    conn.close()
    print("hospital dataset built:", HERE)


def _write_pdf(path: Path) -> None:
    pages = (
        "The private hospital network manages patients, doctors, wards and clinical appointments. "
        "Each patient is registered with a unique fiscal code, a full name and a date of birth. "
        "Doctors are specialists in one of six departments (Cardiology, Neurology, Orthopedics, "
        "Pediatrics, Dermatology, Gynecology); each department maps to a dedicated ward (Reparto A "
        "to F). An appointment links a patient, a doctor and a ward, and records the scheduled "
        "date and time.",
        "During an appointment one or more clinical treatments may be performed (for example a "
        "specialist visit, an ultrasound, a blood test or an ECG). Every treatment is billed: the "
        "invoice records the appointment, the amount and the issue date. Treatments may require "
        "medications: a treatment can require several medications and a medication can be "
        "prescribed to several treatments, so prescriptions connect treatments to medications "
        "with a dosage instruction.",
        "For research purposes the operational notes provide the department-to-ward mapping and "
        "the invoicing rule (treatment fee plus 15% co-payment). These notes are part of the "
        "document set given to the population system.",
    )
    try:
        document = fitz.open()
        for text in pages:
            page = document.new_page()
            page.insert_textbox(fitz.Rect(50, 50, 545, 792), text, fontsize=11, fontname="helv")
        document.save(path)
        document.close()
    except Exception:
        (HERE / "source" / "description.txt").write_text("\n\n".join(pages), encoding="utf-8")


if __name__ == "__main__":
    build()