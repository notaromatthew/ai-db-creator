"""Build the Hospital dataset (Dataset C) in a reproducible way.

Artifacts under ``data/datasets/hospital/``:

- ``source/patients.csv``         100 patient rows
- ``source/appointments.csv``     200 appointment rows
- ``source/operational_notes.txt`` operational notes (departments, wards, pharmacy)
- ``source/description.pdf``      three-page domain description
- ``ground_truth.db``             normalised 3NF SQLite database (gold answer)

Fixed random seed for byte-for-byte reproducibility.

Design notes (documented deviation from docs/11, section 1.3):
- The protocol lists 8 tables. This consensus-amended implementation covers 30
  columns. Each doctor references one ward, so an appointment inherits its ward
  without storing a redundant ``ward_id``.
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
TREATMENT_FEES = {
    "Visita specialistica": 90.00,
    "Ecografia": 120.00,
    "Radiografia": 75.00,
    "Analisi del sangue": 45.00,
    "Elettrocardiogramma": 80.00,
    "Risonanza magnetica": 300.00,
    "TAC": 250.00,
    "Fisioterapia": 60.00,
    "Infusione endovenosa": 110.00,
    "Biopsia": 220.00,
}
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

    wards = [(wid, WARD_NAMES[wid - 1], DEPARTMENTS[(wid - 1) % len(DEPARTMENTS)])
             for wid in range(1, len(WARD_NAMES) + 1)]

    doctors = []
    for doctor_id in range(1, 13):
        name = f"Dr. {rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        specialty = SPECIALTIES[(doctor_id - 1) % len(SPECIALTIES)]
        ward_id = ((doctor_id - 1) % len(wards)) + 1
        doctors.append((doctor_id, name, specialty, ward_id))

    medications = [(mid, name, ingredient) for mid, (name, ingredient) in enumerate(MEDICATIONS, start=1)]

    appointments = []
    for appointment_id in range(1, 201):
        patient_id = rng.randint(1, 100)
        doctor_id = rng.randint(1, len(doctors))
        rng.randint(1, len(wards))  # Preserve the pre-amendment random stream.
        scheduled = datetime(2026, 1, 1, 8, 0) + timedelta(minutes=rng.randint(0, 420 * 24 * 60))
        appointments.append((appointment_id, patient_id, doctor_id,
                             scheduled.strftime("%Y-%m-%d %H:%M:%S")))

    treatments = []
    for treatment_id in range(1, 251):
        appointment_id = rng.randint(1, 200)
        description = rng.choice(TREATMENT_DESCRIPTIONS)
        treatments.append((treatment_id, appointment_id, description, TREATMENT_FEES[description]))

    prescriptions = []
    prescription_keys = set()
    while len(prescriptions) < 300:
        treatment_id = rng.randint(1, 250)
        medication_id = rng.randint(1, len(medications))
        dosage = rng.choice(DOSAGES)
        key = (treatment_id, medication_id, dosage)
        if key in prescription_keys:
            continue
        prescription_keys.add(key)
        prescriptions.append((len(prescriptions) + 1, treatment_id, medication_id, dosage))

    treatment_fees_by_appointment = {}
    for _, appointment_id, _, fee in treatments:
        treatment_fees_by_appointment.setdefault(appointment_id, 0.0)
        treatment_fees_by_appointment[appointment_id] += fee
    appointment_dates = {row[0]: datetime.fromisoformat(row[3]).date() for row in appointments}
    invoices = []
    for invoice_id, appointment_id in enumerate(sorted(treatment_fees_by_appointment), start=1):
        amount = round(treatment_fees_by_appointment[appointment_id] * 1.15, 2)
        issued = appointment_dates[appointment_id] + timedelta(days=rng.randint(1, 30))
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
            ward = wards[doctor[3] - 1]
            output.write(f"{appt[0]},{appt[1]},{doctor[1]},{doctor[2]},{ward[1]},{appt[3]}\n")

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

    database_path = HERE / "ground_truth.db"
    database_path.unlink(missing_ok=True)
    conn = sqlite3.connect(str(database_path))
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
            ward_id INTEGER NOT NULL,
            UNIQUE (full_name, specialty),
            FOREIGN KEY (ward_id) REFERENCES wards(ward_id)
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
            scheduled_on DATETIME NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES patients(patient_id),
            FOREIGN KEY (doctor_id) REFERENCES doctors(doctor_id)
        );
        CREATE TABLE treatments (
            treatment_id INTEGER PRIMARY KEY,
            appointment_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            fee NUMERIC(10,2) NOT NULL,
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
            UNIQUE (treatment_id, medication_id, dosage),
            FOREIGN KEY (treatment_id) REFERENCES treatments(treatment_id),
            FOREIGN KEY (medication_id) REFERENCES medications(medication_id)
        );
        CREATE TABLE invoices (
            invoice_id INTEGER PRIMARY KEY,
            appointment_id INTEGER NOT NULL UNIQUE,
            amount NUMERIC(10,2) NOT NULL,
            issued_on DATE NOT NULL,
            FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
        );
    """)
    conn.executemany("INSERT INTO patients VALUES (?, ?, ?, ?)", patients)
    conn.executemany("INSERT INTO wards VALUES (?, ?, ?)", wards)
    conn.executemany("INSERT INTO doctors VALUES (?, ?, ?, ?)", doctors)
    conn.executemany("INSERT INTO medications VALUES (?, ?, ?)", medications)
    conn.executemany("INSERT INTO appointments VALUES (?, ?, ?, ?)", appointments)
    conn.executemany("INSERT INTO treatments VALUES (?, ?, ?, ?)", treatments)
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
        "to F). Each doctor is assigned to the ward for the doctor's specialty. An appointment "
        "links a patient to a doctor and records the scheduled date and time; its ward is the "
        "doctor's ward.",
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
    path.unlink(missing_ok=True)
    try:
        document = fitz.open()
        for text in pages:
            page = document.new_page()
            page.insert_textbox(fitz.Rect(50, 50, 545, 792), text, fontsize=11, fontname="helv")
        document.save(path, no_new_id=True, reproducible=True)
        document.close()
    except Exception:
        (HERE / "source" / "description.txt").write_text("\n\n".join(pages), encoding="utf-8")


if __name__ == "__main__":
    build()
