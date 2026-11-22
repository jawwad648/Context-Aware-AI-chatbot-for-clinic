"""
SQLite data access layer.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import bcrypt

SCHEMA = """
CREATE TABLE IF NOT EXISTS doctors (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL,
    specialty   TEXT    NOT NULL,
    room        TEXT
);

CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_no      TEXT    UNIQUE,
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    dob             TEXT,
    phone           TEXT,
    password_hash   TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    doctor_id   INTEGER NOT NULL REFERENCES doctors(id),
    scheduled   TEXT    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'booked',
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS lab_results (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id  INTEGER NOT NULL REFERENCES patients(id),
    test_name   TEXT    NOT NULL,
    result      TEXT,
    ready       INTEGER NOT NULL DEFAULT 0,
    taken_at    TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS chat_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT    NOT NULL,
    role        TEXT    NOT NULL,
    message     TEXT    NOT NULL,
    intent      TEXT,
    confidence  REAL,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);
"""


def _conn(db_path: str) -> sqlite3.Connection:
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON;")
    return c


def init_db(db_path: str) -> None:
    if os.path.exists(db_path):
        os.remove(db_path)
    with _conn(db_path) as c:
        c.executescript(SCHEMA)


def add_doctor(db_path: str, name: str, specialty: str, room: str = "") -> int:
    with _conn(db_path) as c:
        cur = c.execute(
            "INSERT INTO doctors (name, specialty, room) VALUES (?, ?, ?)",
            (name, specialty, room),
        )
        return int(cur.lastrowid)


def get_all_doctors(db_path: str) -> List[Dict[str, Any]]:
    with _conn(db_path) as c:
        rows = c.execute("SELECT * FROM doctors ORDER BY name").fetchall()
    return [dict(r) for r in rows]


def get_doctor_names(db_path: str) -> List[str]:
    return [d["name"] for d in get_all_doctors(db_path)]


def get_doctors_by_specialty(db_path: str, specialty: str) -> List[str]:
    s = specialty.lower()
    with _conn(db_path) as c:
        rows = c.execute(
            "SELECT name FROM doctors WHERE LOWER(specialty) LIKE ?",
            (f"%{s}%",),
        ).fetchall()
    return [r["name"] for r in rows]


def _doctor_id_by_name(conn: sqlite3.Connection, name: str) -> Optional[int]:
    row = conn.execute(
        "SELECT id FROM doctors WHERE LOWER(name) = LOWER(?)", (name,)
    ).fetchone()
    return int(row["id"]) if row else None


def add_patient(
    db_path: str,
    first_name: str,
    last_name: str,
    patient_no: str,
    password: str = "test1234",
    phone: str = "",
    dob: str = "",
) -> int:
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    with _conn(db_path) as c:
        cur = c.execute(
            """INSERT INTO patients
               (patient_no, first_name, last_name, dob, phone, password_hash)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (patient_no, first_name, last_name, dob, phone, pw_hash),
        )
        return int(cur.lastrowid)


def get_or_create_patient_by_name(
    db_path: str, first_name: str, last_name: str
) -> int:
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT id FROM patients WHERE LOWER(first_name)=? AND LOWER(last_name)=?",
            (first_name.lower(), last_name.lower()),
        ).fetchone()
        if row:
            return int(row["id"])
        pno = f"P{int(datetime.utcnow().timestamp())}"
        cur = c.execute(
            """INSERT INTO patients
               (patient_no, first_name, last_name, password_hash)
               VALUES (?, ?, ?, ?)""",
            (pno, first_name, last_name, ""),
        )
        return int(cur.lastrowid)


def authenticate_patient(
    db_path: str, patient_no: str, password: str
) -> Optional[Dict[str, Any]]:
    with _conn(db_path) as c:
        row = c.execute(
            "SELECT * FROM patients WHERE patient_no = ?", (patient_no,)
        ).fetchone()
    if not row:
        return None
    if not row["password_hash"]:
        return None
    if not bcrypt.checkpw(password.encode(), row["password_hash"].encode()):
        return None
    return {
        "id": int(row["id"]),
        "name": f"{row['first_name']} {row['last_name']}",
        "patient_no": row["patient_no"],
    }


def book_appointment(
    db_path: str, patient_id: int, doctor_name: str, when: datetime
) -> int:
    with _conn(db_path) as c:
        did = _doctor_id_by_name(c, doctor_name)
        if did is None:
            raise ValueError(f"Unknown doctor: {doctor_name}")
        cur = c.execute(
            """INSERT INTO appointments (patient_id, doctor_id, scheduled, status)
               VALUES (?, ?, ?, 'booked')""",
            (patient_id, did, when.strftime("%Y-%m-%d %H:%M")),
        )
        return int(cur.lastrowid)


def cancel_appointment_for_patient(
    db_path: str, patient_id: int, when: datetime
) -> bool:
    lo = (when - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    hi = (when + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")
    with _conn(db_path) as c:
        cur = c.execute(
            """UPDATE appointments
                  SET status = 'cancelled'
                WHERE patient_id = ? AND status = 'booked'
                  AND scheduled BETWEEN ? AND ?""",
            (patient_id, lo, hi),
        )
        return cur.rowcount > 0


def get_appointments_for_patient(
    db_path: str, patient_id: int
) -> List[Dict[str, Any]]:
    with _conn(db_path) as c:
        rows = c.execute(
            """SELECT a.id, a.scheduled AS date, d.name AS doctor, a.status
                 FROM appointments a
                 JOIN doctors d ON d.id = a.doctor_id
                WHERE a.patient_id = ?
                  AND a.status = 'booked'
                  AND a.scheduled >= datetime('now')
             ORDER BY a.scheduled""",
            (patient_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_all_appointments(db_path: str) -> List[Dict[str, Any]]:
    with _conn(db_path) as c:
        rows = c.execute(
            """SELECT a.id,
                      a.scheduled,
                      a.status,
                      p.first_name || ' ' || p.last_name AS patient,
                      d.name AS doctor
                 FROM appointments a
                 JOIN patients p ON p.id = a.patient_id
                 JOIN doctors  d ON d.id = a.doctor_id
             ORDER BY a.scheduled DESC
                LIMIT 200"""
        ).fetchall()
    return [dict(r) for r in rows]


def add_lab_result(
    db_path: str,
    patient_id: int,
    test_name: str,
    taken_at: datetime,
    result: str = "",
    ready: bool = False,
) -> int:
    with _conn(db_path) as c:
        cur = c.execute(
            """INSERT INTO lab_results (patient_id, test_name, result, ready, taken_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                patient_id,
                test_name,
                result,
                1 if ready else 0,
                taken_at.strftime("%Y-%m-%d"),
            ),
        )
        return int(cur.lastrowid)


def get_lab_results_for_patient(
    db_path: str, patient_id: int
) -> List[Dict[str, Any]]:
    with _conn(db_path) as c:
        rows = c.execute(
            """SELECT id, test_name AS test, result, ready, taken_at AS date
                 FROM lab_results
                WHERE patient_id = ?
             ORDER BY taken_at DESC""",
            (patient_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def log_chat(
    db_path: str,
    session_id: str,
    role: str,
    message: str,
    intent: Optional[str] = None,
    confidence: Optional[float] = None,
) -> None:
    with _conn(db_path) as c:
        c.execute(
            """INSERT INTO chat_log (session_id, role, message, intent, confidence)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, role, message, intent, confidence),
        )
