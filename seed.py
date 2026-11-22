"""Seed the DB with realistic sample data for the demo."""
from __future__ import annotations

from datetime import datetime, timedelta

from database.models import (
    add_doctor,
    add_lab_result,
    add_patient,
    book_appointment,
)


def seed_all(db_path: str) -> None:
    doctors = [
        ("Aisha Khan",       "General Practice",  "R101"),
        ("Daniel Smith",     "Cardiology",        "R203"),
        ("Priya Menon",      "Paediatrics",       "R110"),
        ("Ethan Brown",      "Dermatology",       "R305"),
        ("Sara Ibrahim",     "Gynaecology",       "R207"),
        ("James O'Connor",   "Orthopaedics",      "R402"),
        ("Li Wei",           "ENT",               "R208"),
        ("Maria Gonzalez",   "Ophthalmology",     "R306"),
    ]
    for name, spec, room in doctors:
        add_doctor(db_path, name=name, specialty=spec, room=room)

    patients = [
        ("P001", "Ayesha",  "Khan",    "1994-05-14", "+44 7700 000001"),
        ("P002", "Jawwad",  "Azam",    "1999-10-02", "+44 7700 000002"),
        ("P003", "Emma",    "Watson",  "1987-02-11", "+44 7700 000003"),
        ("P004", "Raj",     "Patel",   "1972-08-23", "+44 7700 000004"),
    ]
    pid = {}
    for pno, f, l, dob, ph in patients:
        pid[pno] = add_patient(
            db_path, first_name=f, last_name=l, patient_no=pno,
            password="test1234", phone=ph, dob=dob,
        )

    now = datetime.now().replace(second=0, microsecond=0)
    book_appointment(db_path, pid["P001"], "Aisha Khan",    now + timedelta(days=1, hours=1))
    book_appointment(db_path, pid["P002"], "Daniel Smith",  now + timedelta(days=3, hours=3))
    book_appointment(db_path, pid["P003"], "Priya Menon",   now + timedelta(days=5))
    book_appointment(db_path, pid["P004"], "Ethan Brown",   now + timedelta(days=7))

    add_lab_result(
        db_path, pid["P001"], "Full Blood Count",
        taken_at=now - timedelta(days=2),
        result="Haemoglobin 13.4 g/dL, WBC 6.1, Platelets 230 - all within normal range.",
        ready=True,
    )
    add_lab_result(
        db_path, pid["P001"], "Lipid Profile",
        taken_at=now - timedelta(days=1),
        result="", ready=False,
    )
    add_lab_result(
        db_path, pid["P002"], "HbA1c",
        taken_at=now - timedelta(days=4),
        result="5.6% - normal.",
        ready=True,
    )
    add_lab_result(
        db_path, pid["P002"], "ECG",
        taken_at=now - timedelta(days=4),
        result="Normal sinus rhythm.",
        ready=True,
    )
    add_lab_result(
        db_path, pid["P003"], "Thyroid Function",
        taken_at=now - timedelta(days=3),
        result="TSH 2.1 mIU/L - normal.",
        ready=True,
    )
